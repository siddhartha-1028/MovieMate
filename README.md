# 🎬 MovieMate

**MovieMate** is a full-stack web application for discovering, searching, and getting personalized movie recommendations — built with Flask, Python, and the TMDB API.

> ✨ Designed with a Netflix-style cinematic dark UI and powered by a machine learning recommendation engine.

---

## 🚀 Features

| Feature | Description |
|---|---|
| 🔍 **Smart Search** | Search movies with genre, release year, and rating filters via TMDB API |
| 🎯 **AI Recommendations** | ML-powered movie suggestions based on your search history (KNN + TF-IDF) |
| 🎬 **Trailer Playback** | Watch official YouTube trailers directly on the movie details page |
| ⭐ **Reviews & Ratings** | Leave star ratings (1–5) and written reviews on any movie |
| 📋 **Watchlist** | Save movies to your personal watchlist and manage them from your profile |
| 👤 **User Accounts** | Secure registration, login, and profile management with photo upload |

---

## 🛠️ Tech Stack

- **Backend:** Python 3, Flask, Flask-Login, Flask-SQLAlchemy, Flask-Bcrypt, Flask-WTF
- **Frontend:** HTML5, Bootstrap 5, Custom CSS (Netflix-style cinematic dark theme)
- **Database:** SQLite (via SQLAlchemy ORM)
- **ML Model:** Scikit-learn (KNN + TF-IDF vectorizer) trained on the TMDB 5000 movie dataset
- **External API:** [The Movie Database (TMDB)](https://www.themoviedb.org/)

---

## ⚙️ Setup & Run Locally

### 1. Clone the repository
```bash
git clone https://github.com/siddhartha-1028/MovieMate.git
cd MovieMate
```

### 2. Create & activate a virtual environment
```bash
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure environment variables
```bash
cp .env.example .env
```
Open `.env` and fill in:
```
SECRET_KEY=your_random_secret_key
API_KEY=your_tmdb_api_key
```
Get a free TMDB API key at: https://www.themoviedb.org/settings/api

### 5. Run the app
```bash
python run.py
```
Open your browser and go to: **http://127.0.0.1:5000**

---

## 📂 Project Structure

```
MovieMate/
├── app/
│   ├── forms/          # WTForms form definitions
│   ├── models/         # SQLAlchemy database models
│   ├── routes/         # Flask route handlers (blueprints)
│   ├── static/         # CSS, images, logos
│   ├── templates/      # Jinja2 HTML templates
│   └── utils/          # TMDB API helpers, ML recommender
├── Datapreprocessing/  # ML model, vectorizer, and dataset
├── .env.example        # Environment variable template
├── requirements.txt    # Python dependencies
└── run.py              # App entry point
```

---

## 📸 Screenshots

*Coming soon — add screenshots of the homepage, movie details, and search results.*

---

## 🙏 Credits

- Movie data & API: [The Movie Database (TMDB)](https://www.themoviedb.org/)
- Dataset: [TMDB 5000 Movie Dataset](https://www.kaggle.com/datasets/tmdb/tmdb-movie-metadata)
