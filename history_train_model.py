# recommendation_engine.py

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
import pickle

# Step 1: Load your preprocessed data
new_df = pd.read_csv("Datapreprocessing/final_movie_data.csv")  # This contains ['title', 'tags', 'movie_id']

# Step 2: TF-IDF Vectorization
vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
tfidf_matrix = vectorizer.fit_transform(new_df['tags'])

# Step 3: Nearest Neighbors
model = NearestNeighbors(metric='cosine', algorithm='brute')
model.fit(tfidf_matrix)

# Step 4: Save for reuse
pickle.dump(vectorizer, open("models/tfidf_vectorizer.pkl", "wb"))
pickle.dump(model, open("models/nn_model.pkl", "wb"))
