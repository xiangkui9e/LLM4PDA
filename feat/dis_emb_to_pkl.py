import ast
import pandas as pd

dis_emb = '02-疾病嵌入生成-small/gpt-5.4_dis_emb.txt'
data = pd.read_csv(dis_emb, sep=r':{4,}', header=0, engine='python')
all_data = data.drop_duplicates(subset=['Disease'])
final_data = all_data[['Disease', 'Embedding']]

# Apply the funcption to get embeddings and create a dictionary mapping 'Disease' to embeddings
disease_emb_dict = {dis: emb for dis, emb in zip(final_data['Disease'], final_data['Embedding'].apply(ast.literal_eval))}
pd.to_pickle(disease_emb_dict, '02-疾病嵌入生成-small/gpt-5.4_dis_emb.pkl')