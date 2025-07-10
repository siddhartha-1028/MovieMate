from flask import Blueprint, render_template, flash, current_app
from flask_login import current_user
from app.forms.forms import SearchForm
from app.utils.tmdb import fetch_tmdb_results
from app.utils.recommender import get_user_recommendations
from app.models.models import UserSearch
from app import db
import requests

main = Blueprint('main', __name__)

@main.route("/")
@main.route("/home")
def home():
    api_key = current_app.config['API_KEY']
    trending_url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={api_key}"
    trending_movies = []

    try:
        response = requests.get(trending_url, timeout=5)
        response.raise_for_status()
        trending_resp = response.json()
        trending_movies = trending_resp.get("results", [])
    except Exception as e:
        print("Trending fetch failed:", e)
        flash("Failed to load trending movies", "warning")

    most_searched = (
        db.session.query(UserSearch.movie_title, db.func.count(UserSearch.movie_title).label('count'))
        .group_by(UserSearch.movie_title)
        .order_by(db.desc('count'))
        .limit(20)
        .all()
    )

    most_searched_titles = [row.movie_title for row in most_searched]
    seen_titles = set()
    unique_titles = []
    for title in most_searched_titles:
        if title not in seen_titles:
            unique_titles.append(title)
            seen_titles.add(title)

    seen_movie_ids = set()
    most_searched_movies = []
    for title in unique_titles:
        results = fetch_tmdb_results(title)
        if results:
            movie = results[0]
            if movie['id'] not in seen_movie_ids:
                most_searched_movies.append(movie)
                seen_movie_ids.add(movie['id'])

    recommended_movies = []
    if current_user.is_authenticated:
        recommended_movies = get_user_recommendations(current_user.id, top_n=32)

    return render_template(
        "home.html",
        trending_movies=trending_movies,
        most_searched_movies=most_searched_movies,
        recommended_movies=recommended_movies
    )

@main.route("/about")
def about():
    return render_template('about.html', title='About')
