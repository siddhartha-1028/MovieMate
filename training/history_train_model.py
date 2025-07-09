import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.neighbors import NearestNeighbors
import joblib
from scipy.sparse import issparse
import os

# Create output directory
os.makedirs("Datapreprocessing", exist_ok=True)

# Step 1: Load data
new_df = pd.read_csv('Datapreprocessing/final_movie_data.csv')

# Step 2: TF-IDF Vectorization with stopwords
vectorizer = TfidfVectorizer(ngram_range=(1, 2), stop_words='english')
tfidf = vectorizer.fit_transform(new_df["tags"])

# Step 3: Ensure sparse matrix
if not issparse(tfidf):
    tfidf = tfidf.tocsr()

# Step 4: Train Nearest Neighbors
model = NearestNeighbors(metric='cosine', algorithm='brute')
model.fit(tfidf)

# Step 5: Save to disk using joblib
joblib.dump(model, 'Datapreprocessing/movie_recommender_model.pkl')
joblib.dump(tfidf, 'Datapreprocessing/tfidf_matrix.pkl')
joblib.dump(vectorizer, 'Datapreprocessing/tfidf_vectorizer.pkl')

print("✅ Model training complete and files saved.")
