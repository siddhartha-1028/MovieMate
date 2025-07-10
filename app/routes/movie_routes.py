from flask import Blueprint, render_template, flash, redirect, request, url_for, current_app
from flask_login import login_required, current_user
from app.forms.forms import SearchForm
from app.utils.tmdb import fetch_tmdb_results
from app.utils.recommender import get_user_recommendations
from app.models.models import UserSearch
from app import db
import re
from app.utils.history_recommender import recommend_from_history
import requests

movie = Blueprint('movie', __name__)

@movie.route("/search", methods=["GET", "POST"])
@login_required
def search():
    form = SearchForm()

    # If GET request without query param, show clean search page with empty form
    if request.method == "GET" and not request.args.get('query'):
        return render_template('search.html', form=form, movies=None, recommended_movies=None)

    # If POST form submitted and valid
    if request.method == "POST" and form.validate_on_submit():
        query = form.query.data.strip()
    else:
        # GET with ?query=...
        query = request.args.get('query', '').strip()

    # If query is empty, show clean page again (no results or flash)
    if not query:
        return render_template('search.html', form=form, movies=None, recommended_movies=None)

    # Validate query input
    if len(query) < 2 or not re.match(r"^[a-zA-Z0-9\s:,'&\.\-\(\)\[\]!]+$", query):
        flash("Invalid search input. Please enter a valid movie name.", "warning")
        return render_template('search.html', form=form, movies=[], recommended_movies=[])

    try:
        movies = fetch_tmdb_results(query)
        seen_titles = set()
        filtered_movies = []
        for movie_item in movies:
            title = movie_item.get('title')
            if title and title not in seen_titles:
                seen_titles.add(title)
                filtered_movies.append(movie_item)

        movies = filtered_movies
        if not movies:
            flash("No results found for that search.", "warning")

        # Save user search to DB
        search_record = UserSearch(movie_title=query, user_id=current_user.id)
        db.session.add(search_record)
        db.session.commit()

        # Get recommendations based on history
        recommended_df = recommend_from_history([query], top_n=8)
        recommended_movies = []
        for _, row in recommended_df.iterrows():
            results = fetch_tmdb_results(row['title'])
            if results:
                best_match = next(
                    (m for m in results if m.get('title', '').lower() == row['title'].lower()),
                    results[0]
                )
                recommended_movies.append({
                    'id': best_match.get('id'),
                    'title': best_match.get('title'),
                    'poster_path': best_match.get('poster_path'),
                    'overview': best_match.get('overview', '')[:100]
                })
            else:
                recommended_movies.append({
                    'id': None,
                    'title': row['title'],
                    'poster_path': None,
                    'overview': ''
                })

        return render_template('search.html', form=form, movies=movies, recommended_movies=recommended_movies)

    except requests.exceptions.Timeout:
        flash("Cannot connect to TMDB. Try again later.", "danger")
        return render_template('search.html', form=form, movies=[], recommended_movies=[])

    except requests.exceptions.RequestException:
        flash("Unexpected error occurred. Try again later.", "danger")
        return render_template('search.html', form=form, movies=[], recommended_movies=[])

@movie.route("/recommendations")
@login_required
def recommendations():
    rec_movies = get_user_recommendations(current_user.id)
    if not rec_movies:
        flash("Start searching for movies to get personalized recommendations!", "info")
    return render_template("recommendations.html", rec_movies=rec_movies)

@movie.route("/movie/<int:movie_id>")
@login_required
def movie_detail(movie_id):
    api_key = current_app.config['API_KEY']
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        movie = response.json()
    except Exception:
        flash("Could not fetch movie details.", "danger")
        return redirect(url_for("movie.search"))
    return render_template("movie_detail.html", movie=movie)