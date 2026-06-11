import numpy as np
from utils import *
import torch
from model import *
from sklearn.preprocessing import PolynomialFeatures
import pandas as pd
import pickle
import matplotlib
import pickle

matplotlib.use("TkAgg")
import matplotlib.pyplot as plt

seed_everything(42)
device = torch.device("cuda")

import os

path = "scores/"
if not os.path.exists(path):
    os.makedirs(path)

# load adj, sim
# Load adjacent matrix(data_processing.py)
adj_np = pd.read_csv(r"../data/adj.csv", index_col=0).values
# Load piRNA similarity based on Smith-Waterman method(gen_half_p2p_simth.py)
p_sim_np = pd.read_csv(r"../data/p2p_smith.csv", index_col=0).values
# Load disease similarity based on DO DAG(gen_d2d_do.py)
d_sim_np = pd.read_csv(r"../data/d2d_do.csv", index_col=0).values

# === LLM ===
with open("../feat/LLM_disease_emb.pkl", "rb") as f:
    disease_emb_dict = pickle.load(f)
df_disease = pd.read_csv("../data/doid.csv")
disease_names = df_disease["disease"].tolist()
disease_emb_matrix = np.array([disease_emb_dict[name] for name in disease_names])
disease_LLM = torch.FloatTensor(disease_emb_matrix).to(device)
d_feat = disease_LLM

# RNA-FM
with open("../feat/LLM_piRNA_emb.pkl", "rb") as f:
    piRNA_embed_dict = pickle.load(f)
df_piRNA = pd.read_csv("../feat/piRNA_name.csv")
piRNA_names = df_piRNA["piRNA_name"].tolist()
piRNA_embed_matrix = np.array([piRNA_embed_dict[mid] for mid in piRNA_names])
piRNA_embed_tensor = torch.FloatTensor(piRNA_embed_matrix).to(device)
p_feat = piRNA_embed_tensor

num_p, num_d = adj_np.shape


adj = torch.FloatTensor(adj_np).to(device)
gcn_hidden_dim = 16
dropout = 0.15

lr, num_epochs = 0.001, 100

feat_init_d = d_feat.shape[1]
feat_init_p = p_feat.shape[1]


class MaskedBCELoss(nn.BCELoss):
    def forward(self, pred, adj, train_mask, test_mask):
        self.reduction = "none"
        unweighted_loss = super(MaskedBCELoss, self).forward(pred, adj)
        train_loss = (unweighted_loss * train_mask).sum()
        test_loss = (unweighted_loss * test_mask).sum()
        return train_loss, test_loss


def grad_clipping(net, theta):
    if isinstance(net, nn.Module):
        params = [p for p in net.parameters() if p.requires_grad]
    else:
        params = net.params
    norm = torch.sqrt(sum(torch.sum((p.grad**2)) for p in params))
    if norm > theta:
        for param in params:
            param.grad[:] *= theta / norm


def fit(
    fold_cnt,
    model,
    adj,
    d_feat,
    p_feat,
    train_mask,
    test_mask,
    lr,
    num_epochs,
):
    def xavier_init_weights(m):
        if type(m) == nn.Linear:
            nn.init.xavier_uniform_(m.weight)

    model.apply(xavier_init_weights)
    # optimizer = torch.optim.RMSprop(net.parameters(), lr, 0.9)
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    loss = MaskedBCELoss()

    test_idx = torch.argwhere(test_mask == 1)
    # test_idx = torch.argwhere(torch.ones_like(test_mask) == 1)
    for epoch in range(num_epochs):
        # for epoch in range(50):
        model.train()
        optimizer.zero_grad()
        pred = model(d_feat, p_feat)
        train_loss, test_loss = loss(pred, adj, train_mask, test_mask)
        train_loss.backward()
        grad_clipping(model, 1)
        optimizer.step()

        model.eval()
        pred = model(d_feat, p_feat)

        scores = pred[tuple(list(test_idx.T))].cpu().detach().numpy()
        # print(len(set(scores)))
        np.save(rf"./scores/f{fold_cnt}_e{epoch}_scores.npy", scores)
        logger.update(
            fold_cnt, epoch, adj, pred, test_idx, train_loss.item(), test_loss.item()
        )

    return 0


logger = Logger(5)

with open(r"../data/fold_info.pickle", "rb") as f:
    fold_info = pickle.load(f)
with open(rf"../spy/rn_ij_list_5.pickle", "rb") as f:
    rn_ij_list_spy = pickle.load(f)
with open(rf"../pu_bagging/rn_ij_list.pickle", "rb") as f:
    rn_ij_list_pu = pickle.load(f)
with open(rf"../two_step/rn_ij_list.pickle", "rb") as f:
    rn_ij_list_two = pickle.load(f)


pos_train_ij_list = fold_info["pos_train_ij_list"]
pos_test_ij_list = fold_info["pos_test_ij_list"]
unlabelled_train_ij_list = fold_info["unlabelled_train_ij_list"]
unlabelled_test_ij_list = fold_info["unlabelled_test_ij_list"]
p_gip_list = fold_info["p_gip_list"]
d_gip_list = fold_info["d_gip_list"]

for i in range(5):
    print(f"fold {i}")
    pos_train_ij = pos_train_ij_list[i]
    pos_test_ij = pos_test_ij_list[i]
    unlabelled_train_ij = unlabelled_train_ij_list[i]
    unlabelled_test_ij = unlabelled_test_ij_list[i]
    p_gip = p_gip_list[i]
    d_gip = d_gip_list[i]

    rn_ij = np.concatenate((rn_ij_list_spy[i], rn_ij_list_pu[i], rn_ij_list_two[i]))

    train_mask_np = np.zeros_like(adj_np)
    train_mask_np[tuple(list(pos_train_ij.T))] = 1
    train_mask_np[tuple(list(rn_ij.T))] = 1

    test_mask_np = np.zeros_like(adj_np)
    test_mask_np[tuple(list(pos_test_ij.T))] = 1
    test_mask_np[tuple(list(unlabelled_test_ij.T))] = 1

    train_mask = torch.FloatTensor(train_mask_np).to(device)
    test_mask = torch.FloatTensor(test_mask_np).to(device)

    torch.cuda.empty_cache()
    
    p_encoder_ae = FlexibleEncoder(
        in_dim=feat_init_p, 
        out_dim=gcn_hidden_dim, 
        method='mlp',      # # 或'multiscale_cnn' 'mlp'
        mlp_hidden=512,  
        conv_channels=8,
        conv_kernel_sizes=[3],
        dropout=dropout,
    ).to(device)
    
    d_encoder_ae = FlexibleEncoder(
        in_dim=feat_init_d, 
        out_dim=gcn_hidden_dim, 
        method='mlp',      # or 'transformer'
        mlp_hidden=512,  
        conv_channels=8,
        conv_kernel_sizes=[3],
        dropout=dropout,
    ).to(device)

    predictor = Predictor().to(device)

    model = LLM4PDA(p_encoder_ae, d_encoder_ae, predictor).to(device)
    fit(
        i,
        model,
        adj,
        d_feat,
        p_feat,
        train_mask,
        test_mask,
        lr,
        num_epochs,
    )
    max_allocated_memory = torch.cuda.max_memory_allocated()
    print(f"最大已分配内存量: {max_allocated_memory / 1024 ** 2} MB")

logger.save("LLM4PDA_comb_5")
# torch.save(model, "params.pt")
