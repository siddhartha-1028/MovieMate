from Datapreprocessing.model_loader import load_model
import pandas as pd

model, tfidf, vectorizer = load_model()
movie_data = pd.read_csv("Datapreprocessing/final_movie_data.csv")

def recommend_from_history(movie_titles, top_n=8):
    vectors = []
    matched_titles = []

    for title in movie_titles:
        idx = movie_data[movie_data['title'].str.lower() == title.lower()].index
        if not idx.empty:
            matched_titles.append(title)
            vectors.append(vectorizer.transform([movie_data.loc[idx[0], 'tags']]))

    if not vectors:
        return pd.DataFrame()

    avg_vector = sum(vectors) / len(vectors)
    distances, indices = model.kneighbors(avg_vector, n_neighbors=top_n + len(vectors))

    input_titles_lower = [t.lower() for t in matched_titles]
    recommended_indices = [
        i for i in indices.flatten()
        if movie_data.iloc[i]['title'].lower() not in input_titles_lower
    ][:top_n]

    return movie_data.iloc[recommended_indices]
