import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
import joblib
from scipy.sparse import issparse


new_df = pd.read_csv('Datapreprocessing/final_movie_data.csv')

vectorizer = TfidfVectorizer(ngram_range=(1, 2))
tfidf = vectorizer.fit_transform(new_df["tags"])


if not issparse(tfidf):
    tfidf = tfidf.tocsr()

model = NearestNeighbors(metric='cosine', algorithm='brute')
model.fit(tfidf)

joblib.dump(model, 'movie_recommender_model.pkl')
joblib.dump(tfidf, 'tfidf_matrix.pkl')
joblib.dump(vectorizer, 'tfidf_vectorizer.pkl')

print("Model training complete and files saved.")
