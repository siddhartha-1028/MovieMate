import joblib

def load_model():
    model = joblib.load("Datapreprocessing/movie_recommender_model.pkl")
    vectorizer = joblib.load("Datapreprocessing/tfidf_vectorizer.pkl")
    tfidf = joblib.load("Datapreprocessing/tfidf_matrix.pkl")
    return model, tfidf, vectorizer
