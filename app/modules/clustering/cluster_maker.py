import os
import pandas as pd
from sentence_transformers import SentenceTransformer, util
import numpy as np
import pickle

from modules.constants import *

df = None
comments_list = None

def load_data(filename):
    '''
    Load data from a CSV file and preprocess it.
    '''
    try:
        df = pd.read_csv(f'./data/{filename}')
        print(f"Data loaded successfully from {filename}")

        # Replace NaN values in the 'Comment' column with an empty string
        df['Comment'] = df['Comment'].fillna('')

        # Ensure all values in the 'Comment' column are strings
        df['Comment'] = df['Comment'].astype(str)

        # Filter out comments that are too short (less than 23 characters)
        df = df[df['Comment'].apply(lambda comment: len(comment) >= 23)]

        # Extract the short and long comments lists
        short_comments_list = df['Comment'].tolist()
        long_comments_list = [comment for comment in short_comments_list if len(comment) >= 23]

        return short_comments_list, long_comments_list, df

    except Exception as e:
        print(f"Error loading data from {filename}: {e}")
        return [], [], None


def _detect_clusters(embeddings, threshold=0.85, min_community_size=15, init_max_size=5000):
    # Compute cosine similarity scores
    cos_scores = util.pytorch_cos_sim(embeddings, embeddings)

    # Minimum size for a community
    top_k_values, _ = cos_scores.topk(k=min_community_size, largest=True)

    # Filter for rows >= min_threshold
    extracted_communities = []
    for i in range(len(top_k_values)):
        if top_k_values[i][-1] >= threshold:
            new_cluster = []

                        # Only check top k most similar entries
            # Determine the valid value for k
            valid_k = min(init_max_size, len(cos_scores[i]))

            # Use valid_k instead of init_max_size
            top_val_large, top_idx_large = cos_scores[i].topk(k=valid_k, largest=True)
            top_idx_large = top_idx_large.tolist()
            top_val_large = top_val_large.tolist()

            if top_val_large[-1] < threshold:
                for idx, val in zip(top_idx_large, top_val_large):
                    if val < threshold:
                        break

                    new_cluster.append(idx)
            else:
                # Iterate over all entries (slow)
                for idx, val in enumerate(cos_scores[i].tolist()):
                    if val >= threshold:
                        new_cluster.append(idx)

            extracted_communities.append(new_cluster)

    # Largest cluster first
    extracted_communities = sorted(extracted_communities, key=lambda x: len(x), reverse=True)

    # Step 2) Remove overlapping communities
    unique_communities = []
    extracted_ids = set()

    for community in extracted_communities:
        add_cluster = True
        for idx in community:
            if idx in extracted_ids:
                add_cluster = False
                break

        if add_cluster:
            unique_communities.append(community)
            for idx in community:
                extracted_ids.add(idx)

    return unique_communities



def get_clusters_from_file(filename, comments_list = None):
    if not os.path.isfile(os.path.join(PATH_TO_DATA_CACHE, f'{filename}_embedding_cache.pkl')):
        model = SentenceTransformer('distilbert-base-nli-stsb-quora-ranking')
        corpus_embeddings = model.encode(comments_list, show_progress_bar=True, convert_to_numpy=True)

        with open(os.path.join(PATH_TO_DATA_CACHE, f'{filename}_embedding_cache.pkl'), 'wb') as f:
            pickle.dump(corpus_embeddings, f)
    else:
        # load embeddings from cache
        with open(os.path.join(PATH_TO_DATA_CACHE, f'{filename}_embedding_cache.pkl'), 'rb') as f:
            corpus_embeddings = pickle.load(f)

    all_clusters = _detect_clusters(corpus_embeddings)
        

    all_clusters.sort()

    # for i, cluster in enumerate(clusters_to_show):
    #     print(f'Topic {i}: ')
    #     for sentence_id in cluster[:5]:
    #         print("\t", comments_list[sentence_id])
        
    #     print('-------------')

    return all_clusters