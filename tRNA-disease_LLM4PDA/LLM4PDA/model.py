import torch
from torch import nn
import numpy as np
import torch.nn.functional as F


class DeepLncLoc(nn.Module):
    def __init__(self, w2v_emb, dropout, merge_win_size, context_size_list, out_size):
        super().__init__()
        self.embedding = nn.Embedding.from_pretrained(w2v_emb, freeze=False)
        self.dropout = nn.Dropout(dropout)
        self.merge_win = nn.AdaptiveAvgPool1d(merge_win_size)
        assert out_size % len(context_size_list) == 0
        filter_out_size = int(out_size / len(context_size_list))
        self.con_list = nn.ModuleList(
            [
                nn.Sequential(
                    nn.Conv1d(
                        in_channels=w2v_emb.shape[1],
                        out_channels=filter_out_size,
                        kernel_size=context_size_list[i],
                    ),
                    nn.ReLU(),
                    nn.AdaptiveMaxPool1d(1),
                )
                for i in range(len(context_size_list))
            ]
        )

    def forward(self, p_kmers_id):
        # p_kmers: num_p × all kmers of each p
        x = self.dropout(self.embedding(p_kmers_id))
        x = x.transpose(1, 2)
        x = self.merge_win(x)
        x = [conv(x).squeeze(dim=2) for conv in self.con_list]
        x = torch.cat(x, dim=1)
        return x


class GraphAttentionLayer(nn.Module):
    def __init__(self, in_features, out_features, dropout, alpha):
        super(GraphAttentionLayer, self).__init__()
        self.dropout = dropout
        self.in_features = in_features
        self.out_features = out_features
        self.alpha = alpha

        self.W = nn.Parameter(torch.empty(size=(in_features, out_features)))
        nn.init.xavier_uniform_(self.W.data, gain=1.414)
        self.a = nn.Parameter(torch.empty(size=(2 * out_features, 1)))
        nn.init.xavier_uniform_(self.a.data, gain=1.414)

        self.leakyrelu = nn.LeakyReLU(self.alpha)

    def forward(self, h, adj):
        Wh = torch.mm(h, self.W)
        # h.shape: (N, in_features), Wh.shape: (N, out_features)
        e = self._prepare_attentional_mechanism_input(Wh)

        zero_vec = -9e15 * torch.ones_like(e)
        attention = torch.where(adj > 0, e, zero_vec)
        attention = F.softmax(attention, dim=1)
        attention = F.dropout(attention, self.dropout, training=self.training)
        h_prime = torch.matmul(attention, Wh)

        return F.elu(h_prime)

    def _prepare_attentional_mechanism_input(self, Wh):
        Wh1 = torch.matmul(Wh, self.a[: self.out_features, :])
        Wh2 = torch.matmul(Wh, self.a[self.out_features :, :])
        e = Wh1 + Wh2.T
        return self.leakyrelu(e)

    def __repr__(self):
        return (
            self.__class__.__name__
            + " ("
            + str(self.in_features)
            + " -> "
            + str(self.out_features)
            + ")"
        )


class GAT(nn.Module):
    def __init__(
        self,
        p_feat_dim,
        d_feat_dim,
        hidden_dim,
        out_dim,
        dropout,
        alpha,
        nheads,
    ):
        super(GAT, self).__init__()
        self.dropout = dropout
        self.bn_p = nn.BatchNorm1d(p_feat_dim)
        self.bn_d = nn.BatchNorm1d(d_feat_dim)
        self.linear_p = nn.Linear(p_feat_dim, hidden_dim)
        self.linear_d = nn.Linear(d_feat_dim, hidden_dim)
        assert out_dim % nheads == 0
        nhid_per_head = int(out_dim / nheads)
        self.layer1 = [
            GraphAttentionLayer(hidden_dim, nhid_per_head, dropout=dropout, alpha=alpha)
            for _ in range(nheads)
        ]
        for i, head in enumerate(self.layer1):
            self.add_module("layer1_head_{}".format(i), head)

        self.out_att = GraphAttentionLayer(
            nhid_per_head * nheads, out_dim, dropout=dropout, alpha=alpha
        )

    def forward(self, p_feat, d_feat, adj):
        p_feat_hidden = self.linear_p(self.bn_p(p_feat))
        d_feat_hidden = self.linear_d(self.bn_d(d_feat))
        x = torch.cat((p_feat_hidden, d_feat_hidden), dim=0)

        x = F.dropout(x, self.dropout, training=self.training)
        x = torch.cat([att(x, adj) for att in self.layer1], dim=1)

        x = F.dropout(x, self.dropout, training=self.training)
        x = self.out_att(x, adj)
        p_feat = x[: p_feat.shape[0], :]
        d_feat = x[p_feat.shape[0] :, :]
        return p_feat, d_feat


class PositionWiseFFN(nn.Module):
    def __init__(self, ffn_num_input, ffn_num_hiddens, ffn_num_outputs, **kwargs):
        super(PositionWiseFFN, self).__init__(**kwargs)
        self.dense1 = nn.Linear(ffn_num_input, ffn_num_hiddens)
        self.relu = nn.ReLU()
        self.dense2 = nn.Linear(ffn_num_hiddens, ffn_num_outputs)

    def forward(self, X):
        return self.dense2(self.relu(self.dense1(X)))


# @save

class DyT(nn.Module):
    def __init__(self, num_features, alpha_init_value=0.5):
        super().__init__()
        self.alpha = nn.Parameter(torch.ones(1) * alpha_init_value)
        self.weight = nn.Parameter(torch.ones(num_features))
        self.bias = nn.Parameter(torch.zeros(num_features))

    def forward(self, x):
        # x.shape: [*, num_features]
        return torch.tanh(self.alpha * x) * self.weight + self.bias

class AddNorm(nn.Module):
    def __init__(self, normalized_shape, dropout, **kwargs):
        super(AddNorm, self).__init__(**kwargs)
        self.dropout = nn.Dropout(dropout)
        self.ln = nn.LayerNorm(normalized_shape)

    def forward(self, X, Y):
        return self.ln(self.dropout(Y) + X)


def transpose_qkv(X, num_heads):
    X = X.reshape(X.shape[0], num_heads, -1)
    X = X.permute(1, 0, 2)
    return X


def transpose_output(X, num_heads):
    X = X.permute(1, 0, 2)
    return X.reshape(X.shape[0], -1)


def sequence_mask(X, valid_len, value=0):
    maxlen = X.size(1)
    mask = (
        torch.arange((maxlen), dtype=torch.float32, device=X.device)[None, :]
        < valid_len[:, None]
    )
    X[~mask] = value
    return X


class DotProductAttention(nn.Module):
    def __init__(self, dropout, **kwargs):
        super(DotProductAttention, self).__init__(**kwargs)
        self.dropout = nn.Dropout(dropout)

    def forward(self, Q_p, K_p, V_p):
        d = Q_p.shape[-1]
        scores = torch.bmm(Q_p, K_p.transpose(1, 2)) / np.sqrt(d)
        self.attention_weights = nn.functional.softmax(scores, dim=-1)
        return torch.bmm(self.dropout(self.attention_weights), V_p)


class MultiHeadAttention(nn.Module):
    def __init__(
        self,
        q_in_dim,
        kv_in_dim,
        key_size,
        query_size,
        value_size,
        num_heads,
        dropout,
        bias=False,
        **kwargs
    ):
        super(MultiHeadAttention, self).__init__(**kwargs)
        self.num_heads = num_heads
        self.attention = DotProductAttention(dropout)
        self.W_q = nn.Linear(q_in_dim, query_size, bias=bias)
        self.W_k = nn.Linear(kv_in_dim, key_size, bias=bias)
        self.W_v = nn.Linear(kv_in_dim, value_size, bias=bias)
        self.W_o = nn.Linear(value_size, q_in_dim, bias=bias)

    def forward(self, queries, keys, values):
        Q_p = transpose_qkv(self.W_q(queries), self.num_heads)
        K_p = transpose_qkv(self.W_k(keys), self.num_heads)
        V_p = transpose_qkv(self.W_v(values), self.num_heads)
        output = self.attention(Q_p, K_p, V_p)
        output_concat = transpose_output(output, self.num_heads)
        return self.W_o(output_concat)


class EncoderBlock(nn.Module):
    def __init__(
        self,
        q_in_dim,
        kv_in_dim,
        key_size,
        query_size,
        value_size,
        num_heads,
        dropout,
        bias=False,
        **kwargs
    ):
        super(EncoderBlock, self).__init__(**kwargs)
        self.attention = MultiHeadAttention(
            q_in_dim,
            kv_in_dim,
            key_size,
            query_size,
            value_size,
            num_heads,
            dropout,
            bias,
        )
        self.addnorm1 = AddNorm([q_in_dim], dropout)

    def forward(self, queries, keys, values):
        Y = self.addnorm1(queries, self.attention(queries, keys, values))
        return Y


class Encoder(nn.Module):
    def __init__(self, **kwargs):
        super(Encoder, self).__init__(**kwargs)

    def forward(self, *args):
        raise NotImplementedError


# @save
class TransformerEncoder(Encoder):
    def __init__(
        self,
        q_in_dim,
        kv_in_dim,
        key_size,
        query_size,
        value_size,
        ffn_num_hiddens,
        num_heads,
        num_layers,
        dropout,
        bias=False,
        **kwargs
    ):
        super(TransformerEncoder, self).__init__(**kwargs)
        self.blks = nn.Sequential()
        for i in range(num_layers):
            self.blks.add_module(
                "block" + str(i),
                EncoderBlock(
                    q_in_dim,
                    kv_in_dim,
                    key_size,
                    query_size,
                    value_size,
                    num_heads,
                    dropout,
                    bias,
                ),
            )

    def forward(self, p_feat, d_feat, *args):
        Y = p_feat
        self.attention_weights = [None] * len(self.blks)
        for i, blk in enumerate(self.blks):
            Y = blk(Y, d_feat, d_feat)
            self.attention_weights[i] = blk.attention.attention.attention_weights
        return Y

class MultiScaleConvEncoder(nn.Module):
    """
    多尺度一维卷积模块，前置MLP降维与特征处理
    """
    def __init__(self, in_dim, out_dim, mid_dim=256, conv_channels=64, kernel_sizes=[3,5,7], dropout=0.1):
        super().__init__()
        # 前置降维MLP
        self.mlp = nn.Sequential(
            nn.Linear(in_dim, mid_dim),
            nn.ReLU(),
            nn.Dropout(dropout)
        )
        self.convs = nn.ModuleList([
            nn.Conv1d(1, conv_channels, k, padding=k//2)
            for k in kernel_sizes
        ])
        self.act = nn.ReLU()
        self.dropout = nn.Dropout(dropout)
        self.projector = nn.Linear(conv_channels * len(kernel_sizes), out_dim)
    
    def forward(self, x):
        # x: [batch, in_dim]
        x = self.mlp(x)            # [batch, mid_dim]
        x_unsq = x.unsqueeze(1)    # [batch, 1, mid_dim]
        conv_outs = [self.act(conv(x_unsq)) for conv in self.convs]  # [batch, C, mid_dim]
        feats = [self.dropout(y) for y in conv_outs]
        pooled = [torch.mean(y, dim=2) for y in feats]               # global avg pool: [batch, C]
        cat = torch.cat(pooled, dim=1)                               # [batch, C * n_scale]
        out = self.projector(cat)                                    # [batch, out_dim]
        return out


class FlexibleEncoder(nn.Module):
    def __init__(
            self, 
            in_dim, 
            out_dim, 
            method='mlp',         # 或'multiscale_cnn'
            mlp_hidden=128, 
            conv_channels=64,
            conv_kernel_sizes=[3,5,7],
            dropout=0.1
        ):
        super(FlexibleEncoder, self).__init__()
        assert method in ['mlp', 'multiscale_cnn']
        self.method = method
        if method == 'mlp':
            self.encoder = nn.Sequential(
                nn.Linear(in_dim, mlp_hidden),
                nn.LayerNorm(mlp_hidden),
                nn.SiLU(),
                #nn.Dropout(dropout),
                nn.Linear(mlp_hidden, out_dim),
                nn.LayerNorm(out_dim),      # 也可不加，看实验效果
                # nn.Dropout(mlp_dropout)   # 若特征很大可考虑也加dropout
            )
        else: 
            self.encoder = MultiScaleConvEncoder(
                in_dim=in_dim,
                out_dim=out_dim,
                conv_channels=conv_channels,
                kernel_sizes=conv_kernel_sizes,
                dropout=dropout
            )

    def forward(self, x):
        return self.encoder(x)


class Predictor(nn.Module):
    def __init__(self):
        super(Predictor, self).__init__()

    def forward(self, p_feat, d_feat):
        res = p_feat.mm(d_feat.t())
        return F.sigmoid(res)


class PUTransGCN(nn.Module):
    def __init__(self, p_encoder_ae, d_encoder_ae, predictor, **kwargs):
        super(PUTransGCN, self).__init__(**kwargs)
        self.p_encoder_ae = p_encoder_ae
        self.d_encoder_ae = d_encoder_ae
        self.predictor = predictor

    def forward(self, d_feat, p_feat, adj_mat):
        p_enc_ae = self.p_encoder_ae(p_feat)
        d_enc_ae = self.d_encoder_ae(d_feat)
        return self.predictor(p_enc_ae, d_enc_ae)
