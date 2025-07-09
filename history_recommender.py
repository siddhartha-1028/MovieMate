# recommender.py
import pickle
import numpy as np
import pandas as pd

# Load artifacts
vectorizer = pickle.load(open("models/tfidf_vectorizer.pkl", "rb"))
model = pickle.load(open("models/nn_model.pkl", "rb"))
movie_data = pd.read_csv("Datapreprocessing/final_movie_data.csv")

def recommend_from_history(movie_titles, top_n=8):
    vectors = []
    for title in movie_titles:
        idx = movie_data[movie_data['title'].str.lower() == title.lower()].index
        if not idx.empty:
            vectors.append(vectorizer.transform([movie_data.loc[idx[0], 'tags']]))

    if not vectors:
        return []

    avg_vector = sum(vectors) / len(vectors)
    distances, indices = model.kneighbors(avg_vector, n_neighbors=top_n + len(vectors))
    
    # Exclude input movies
    result_indices = [i for i in indices.flatten() if movie_data.iloc[i]['title'].lower() not in [t.lower() for t in movie_titles]][:top_n]
    recommended = movie_data.iloc[result_indices]

    return recommended
