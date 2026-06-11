import torch
from torch import nn
import numpy as np
import torch.nn.functional as F

# @save
class MultiScaleConvEncoder(nn.Module):
    def __init__(self, in_dim, out_dim, mid_dim=256, conv_channels=64, kernel_sizes=[3,5,7], dropout=0.1):
        super().__init__()
        # MLP
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
            method='mlp',         # or'multiscale_cnn'
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
                nn.ReLU(),
                #nn.Dropout(dropout),
                nn.Linear(mlp_hidden, out_dim),
                nn.LayerNorm(out_dim),  
                # nn.Dropout(mlp_dropout)
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


class LLM4PDA(nn.Module):
    def __init__(self, p_encoder_ae, d_encoder_ae, predictor, **kwargs):
        super(LLM4PDA, self).__init__(**kwargs)
        self.p_encoder_ae = p_encoder_ae
        self.d_encoder_ae = d_encoder_ae
        self.predictor = predictor

    def forward(self, d_feat, p_feat):
        p_enc_ae = self.p_encoder_ae(p_feat)
        d_enc_ae = self.d_encoder_ae(d_feat)
        return self.predictor(p_enc_ae, d_enc_ae)
