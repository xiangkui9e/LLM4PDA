#LLM4PDA
### 1. Install Required Dependencies

Once the environment is activated, install the required Python packages using `pip`:

```bash
pip install numpy==1.25.0
pip install scipy==1.11.1
pip install pandas==1.5.3
pip install openpyxl==3.0.10
pip install scikit-learn==1.2.2
pip install biopython==1.83
pip install obonet==1.0.0
pip install gensim==4.3.1
pip install tqdm==4.65.0
pip install jupyterlab==3.6.3
pip install matplotlib==3.8.2
pip install torch==2.1.2 torchvision==0.16.2 torchaudio==2.1.2 --index-url https://download.pytorch.org/whl/cu118
```

For PyTorch Geometric and related libraries, use the following:

```bash
pip install https://data.pyg.org/whl/torch-2.1.0%2Bcu118/torch_cluster-1.6.2%2Bpt21cu118-cp310-cp310-win_amd64.whl
pip install https://data.pyg.org/whl/torch-2.1.0%2Bcu118/torch_scatter-2.1.2%2Bpt21cu118-cp310-cp310-win_amd64.whl
pip install https://data.pyg.org/whl/torch-2.1.0%2Bcu118/torch_sparse-0.6.18%2Bpt21cu118-cp310-cp310-win_amd64.whl
pip install https://data.pyg.org/whl/torch-2.1.0%2Bcu118/torch_spline_conv-1.2.2%2Bpt21cu118-cp310-cp310-win_amd64.whl
pip install torch-geometric
```

## Training Models

To train models using cross-validation, follow the steps below:

1. Run `main.py` in the **LLM4PDA** folder.
2. For other methods mentioned in the paper, navigate to the respective directories and run `main.py`:
    - **ETGPDA**
    - **iPiDi-PUL**
    - **iPiDA-GCN**
    - **iPiDA-SWGCN**
    - **iPiDA-GBNN**
    - **PUTransGCN_come_5**
    - **MambaCAttnGCN**
    - **piRDA**
