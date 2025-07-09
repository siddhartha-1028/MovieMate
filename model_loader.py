import joblib

def load_model():
    model = joblib.load('movie_recommender_model.pkl')
    tfidf = joblib.load('tfidf_matrix.pkl')
    vectorizer = joblib.load('tfidf_vectorizer.pkl')
    return model, tfidf, vectorizer
