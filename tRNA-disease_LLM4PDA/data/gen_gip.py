import pandas as pd
import numpy as np
import math
import pickle


def seed_everything(seed: int = None):
    """
    """
    import random
    import os
    import numpy as np
    import torch
    import time
    import uuid

    if seed is not None:
        print(f"Using fixed seed: {seed}")
    else:
        seed = random.randint(0, 2024)
        print(f"Using random seed: {seed}")

    random.seed(seed)
    os.environ["PYTHONHASHSEED"] = str(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    torch.cuda.manual_seed(seed)
    torch.backends.cudnn.deterministic = True
    torch.backends.cudnn.benchmark = True


def Getgauss_miRNA(adjacentmatrix, nm):
    """
    MiRNA Gaussian interaction profile kernels similarity
    """
    KM = np.zeros((nm, nm))

    gamaa = 1
    sumnormm = 0
    for i in range(nm):
        normm = np.linalg.norm(adjacentmatrix[i]) ** 2
        sumnormm = sumnormm + normm
    gamam = gamaa / (sumnormm / nm)

    for i in range(nm):
        for j in range(nm):
            KM[i, j] = math.exp(
                -gamam * (np.linalg.norm(adjacentmatrix[i] - adjacentmatrix[j]) ** 2)
            )
    return KM


def Getgauss_disease(adjacentmatrix, nd):
    """
    Disease Gaussian interaction profile kernels similarity
    """
    KD = np.zeros((nd, nd))
    gamaa = 1
    sumnormd = 0
    for i in range(nd):
        normd = np.linalg.norm(adjacentmatrix[:, i]) ** 2
        sumnormd = sumnormd + normd
    gamad = gamaa / (sumnormd / nd)

    for i in range(nd):
        for j in range(nd):
            KD[i, j] = math.exp(
                -(
                    gamad
                    * (np.linalg.norm(adjacentmatrix[:, i] - adjacentmatrix[:, j]) ** 2)
                )
            )
    return KD


seed_everything()
adj_df = pd.read_csv(r"adj.csv", index_col=0)
adj = adj_df.values
num_p, num_d = adj.shape



p_gip_ = Getgauss_miRNA(adj, num_p)
d_gip_ = Getgauss_disease(adj, num_d)
p_gip = pd.DataFrame(p_gip_)
d_gip = pd.DataFrame(d_gip_)
p_gip.to_csv(r"p_gip.csv")
d_gip.to_csv(r"d_gip.csv")
