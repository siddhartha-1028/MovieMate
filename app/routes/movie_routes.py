from flask import Blueprint, render_template, flash, redirect, request, url_for, current_app, jsonify
from flask_login import login_required, current_user
from app.forms.forms import SearchForm
from app.utils.tmdb import fetch_tmdb_results, fetch_movie_videos
from app.utils.recommender import get_user_recommendations
from app.models.models import UserSearch, Watchlist, Review
from app import db
import re
from app.utils.history_recommender import recommend_from_history
import requests

movie = Blueprint('movie', __name__)

# ─────────────────────────────────────────────────────────────────────────────
# SEARCH (with optional genre + year filters)
# ─────────────────────────────────────────────────────────────────────────────
@movie.route("/search", methods=["GET", "POST"])
@login_required
def search():
    """
    Search for movies via TMDB.
    Supports a basic text query plus optional genre/year filters passed as URL params.
    """
    form = SearchForm()

    # GET with no query → show clean search page
    if request.method == "GET" and not request.args.get('query'):
        return render_template('search.html', form=form, movies=None, recommended_movies=None)

    # POST: form submitted
    if request.method == "POST" and form.validate_on_submit():
        query = form.query.data.strip()
    else:
        # GET with ?query=...
        query = request.args.get('query', '').strip()

    if not query:
        return render_template('search.html', form=form, movies=None, recommended_movies=None)

    # Basic input validation
    if len(query) < 2 or not re.match(r"^[a-zA-Z0-9\s:,'\&\.\-\(\)\[\]!]+$", query):
        flash("Invalid search input. Please enter a valid movie name.", "warning")
        return render_template('search.html', form=form, movies=[], recommended_movies=[])

    # Optional filter params
    genre_id = request.args.get('genre_id', '')   # TMDB genre numeric ID
    year     = request.args.get('year', '')        # e.g. "2023"
    min_rating = request.args.get('min_rating', '') # e.g. "7"

    try:
        api_key = current_app.config['API_KEY']

        # Build the TMDB URL – use discover endpoint if filters present, else plain search
        if genre_id or year:
            tmdb_url = (
                f"https://api.themoviedb.org/3/discover/movie"
                f"?api_key={api_key}"
                f"&with_genres={genre_id}"
                f"&primary_release_year={year}"
                f"&query={query}"
                f"&sort_by=popularity.desc"
            )
        else:
            tmdb_url = (
                f"https://api.themoviedb.org/3/search/movie"
                f"?api_key={api_key}&query={query}"
            )

        resp = requests.get(tmdb_url, timeout=5)
        resp.raise_for_status()
        movies = resp.json().get("results", [])

        # Apply client-side min_rating filter
        if min_rating:
            try:
                min_r = float(min_rating)
                movies = [m for m in movies if m.get('vote_average', 0) >= min_r]
            except ValueError:
                pass

        # De-duplicate by title
        seen_titles = set()
        filtered_movies = []
        for m in movies:
            title = m.get('title')
            if title and title not in seen_titles:
                seen_titles.add(title)
                filtered_movies.append(m)
        movies = filtered_movies

        if not movies:
            flash("No results found for that search.", "warning")

        # Persist search history
        search_record = UserSearch(movie_title=query, user_id=current_user.id)
        db.session.add(search_record)
        db.session.commit()

        # ML-based recommendations based on this search
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
                recommended_movies.append({'id': None, 'title': row['title'], 'poster_path': None, 'overview': ''})

        return render_template(
            'search.html',
            form=form,
            movies=movies,
            recommended_movies=recommended_movies,
            query=query,
            genre_id=genre_id,
            year=year,
            min_rating=min_rating
        )

    except requests.exceptions.Timeout:
        flash("Cannot connect to TMDB. Try again later.", "danger")
        return render_template('search.html', form=form, movies=[], recommended_movies=[])
    except requests.exceptions.RequestException:
        flash("Unexpected error occurred. Try again later.", "danger")
        return render_template('search.html', form=form, movies=[], recommended_movies=[])


# ─────────────────────────────────────────────────────────────────────────────
# RECOMMENDATIONS PAGE
# ─────────────────────────────────────────────────────────────────────────────
@movie.route("/recommendations")
@login_required
def recommendations():
    rec_movies = get_user_recommendations(current_user.id)
    if not rec_movies:
        flash("Start searching for movies to get personalized recommendations!", "info")
    return render_template("recommendations.html", rec_movies=rec_movies)


# ─────────────────────────────────────────────────────────────────────────────
# MOVIE DETAIL PAGE (+ trailer + reviews + watchlist status)
# ─────────────────────────────────────────────────────────────────────────────
@movie.route("/movie/<int:movie_id>")
@login_required
def movie_detail(movie_id):
    """
    Fetches full movie info from TMDB, including the YouTube trailer key,
    user's reviews for this film, and whether it's in their watchlist.
    """
    api_key = current_app.config['API_KEY']
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={api_key}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        movie_data = response.json()
    except Exception:
        flash("Could not fetch movie details.", "danger")
        return redirect(url_for("movie.search"))

    # Fetch YouTube trailer key from TMDB /videos endpoint
    trailer_key = fetch_movie_videos(movie_id)

    # Check if already in current user's watchlist
    in_watchlist = Watchlist.query.filter_by(
        user_id=current_user.id, movie_id=movie_id
    ).first() is not None

    # Fetch all reviews for this movie (all users, not just current)
    reviews = Review.query.filter_by(movie_id=movie_id).order_by(Review.timestamp.desc()).all()

    # Check if current user already reviewed this movie
    user_review = Review.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()

    return render_template(
        "movie_detail.html",
        movie=movie_data,
        trailer_key=trailer_key,
        in_watchlist=in_watchlist,
        reviews=reviews,
        user_review=user_review
    )


# ─────────────────────────────────────────────────────────────────────────────
# WATCHLIST: ADD / REMOVE
# ─────────────────────────────────────────────────────────────────────────────
@movie.route("/watchlist/add/<int:movie_id>", methods=["POST"])
@login_required
def watchlist_add(movie_id):
    """
    Saves a movie to the logged-in user's watchlist.
    Expects movie_title and poster_path in the POST form body.
    """
    movie_title = request.form.get('movie_title', 'Unknown')
    poster_path = request.form.get('poster_path', '')

    # Don't add duplicates
    existing = Watchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if not existing:
        entry = Watchlist(
            user_id=current_user.id,
            movie_id=movie_id,
            movie_title=movie_title,
            poster_path=poster_path
        )
        db.session.add(entry)
        db.session.commit()
        flash(f"'{movie_title}' added to your Watchlist!", "success")
    else:
        flash(f"'{movie_title}' is already in your Watchlist.", "info")

    return redirect(url_for('movie.movie_detail', movie_id=movie_id))


@movie.route("/watchlist/remove/<int:movie_id>", methods=["POST"])
@login_required
def watchlist_remove(movie_id):
    """Removes a movie from the logged-in user's watchlist."""
    entry = Watchlist.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if entry:
        movie_title = entry.movie_title
        db.session.delete(entry)
        db.session.commit()
        flash(f"'{movie_title}' removed from your Watchlist.", "info")

    return redirect(url_for('movie.movie_detail', movie_id=movie_id))


# ─────────────────────────────────────────────────────────────────────────────
# REVIEWS: SUBMIT / DELETE
# ─────────────────────────────────────────────────────────────────────────────
@movie.route("/movie/<int:movie_id>/review", methods=["POST"])
@login_required
def submit_review(movie_id):
    """
    Handles review form submission. Validates rating (1-5) and saves to DB.
    One review per user per movie — updates if already exists.
    """
    rating  = request.form.get('rating', type=int)
    content = request.form.get('content', '').strip()
    movie_title = request.form.get('movie_title', 'Unknown')

    if not rating or not (1 <= rating <= 5):
        flash("Please provide a valid rating (1-5 stars).", "warning")
        return redirect(url_for('movie.movie_detail', movie_id=movie_id))

    existing = Review.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if existing:
        existing.rating = rating
        existing.content = content
        flash("Your review has been updated!", "success")
    else:
        review = Review(
            user_id=current_user.id,
            movie_id=movie_id,
            movie_title=movie_title,
            rating=rating,
            content=content
        )
        db.session.add(review)
        flash("Your review has been posted!", "success")

    db.session.commit()
    return redirect(url_for('movie.movie_detail', movie_id=movie_id))


@movie.route("/movie/<int:movie_id>/review/delete", methods=["POST"])
@login_required
def delete_review(movie_id):
    """Deletes the current user's review for a given movie."""
    review = Review.query.filter_by(user_id=current_user.id, movie_id=movie_id).first()
    if review:
        db.session.delete(review)
        db.session.commit()
        flash("Your review has been deleted.", "info")
    return redirect(url_for('movie.movie_detail', movie_id=movie_id))