import os
import secrets
from PIL import Image
from dotenv import load_dotenv
from flask import Flask, render_template, url_for, flash, redirect, request
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from datetime import datetime
from history_recommender import recommend_from_history
from model_loader import load_model
import requests
import re
import pandas as pd

# -------------------- Configuration --------------------
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/profile_pics'
API_KEY = os.getenv('API_KEY')

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

def fetch_tmdb_results(query, endpoint="search/movie"):
    try:
        url = f"https://api.themoviedb.org/3/{endpoint}?api_key={API_KEY}&query={query}"
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        return response.json().get("results", [])
    except requests.exceptions.Timeout:
        flash("TMDb API timed out. Please try again later.", "danger")
        return []
    except requests.exceptions.RequestException:
        flash("TMDb API failed. Please try again later.", "danger")
        return []

# Helper to get personalized recommendations
def get_user_recommendations(user_id, top_n=16):
    user_searches = (
        db.session.query(UserSearch.movie_title)
        .filter_by(user_id=user_id)
        .order_by(UserSearch.timestamp.desc())
        .limit(15)
        .all()
    )
    movie_titles = [r[0] for r in user_searches]

    if not movie_titles:
        return []

    recommended_df = recommend_from_history(movie_titles, top_n=top_n)

    rec_movies = []
    if not recommended_df.empty:
        for _, row in recommended_df.iterrows():
            results = fetch_tmdb_results(row['title'])
            if results:
                rec_movies.append(results[0])

    return rec_movies

# -------------------- Models --------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class UserSearch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_title = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserSearch {self.movie_title} by User {self.user_id}>"
    
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    searches = db.relationship('UserSearch', backref='user', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"

# -------------------- Forms --------------------
class RegistrationForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        user = User.query.filter_by(email=email.data).first()
        if user:
            raise ValidationError('That email is taken. Please choose a different one.')


class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')


class UpdateAccountForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(min=2, max=20)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    picture = FileField('Update Profile Picture', validators=[FileAllowed(['jpg', 'png'])])
    submit = SubmitField('Update')

    def validate_username(self, username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user:
                raise ValidationError('That username is taken. Please choose a different one.')

    def validate_email(self, email):
        if email.data != current_user.email:
            user = User.query.filter_by(email=email.data).first()
            if user:
                raise ValidationError('That email is taken. Please choose a different one.')

class SearchForm(FlaskForm):
    query = StringField('Search', validators=[DataRequired()])
    submit = SubmitField('Search')

# -------------------- Utility Functions --------------------
def save_picture(form_picture):
    # Check file size (limit to 1 MB)
    form_picture.seek(0, os.SEEK_END)
    size = form_picture.tell()
    form_picture.seek(0)
    if size > 1 * 1024 * 1024:  # 1 MB
        flash("Profile picture must be under 1MB", "danger")
        return current_user.image_file  # keep the old one

    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(form_picture.filename)
    picture_fn = random_hex + f_ext
    picture_path = os.path.join(app.root_path, 'static/profile_pics', picture_fn)

    output_size = (125, 125)
    i = Image.open(form_picture)
    i.thumbnail(output_size)
    i.save(picture_path)

    return picture_fn

# -------------------- Routes --------------------
@app.route("/")
@app.route("/home")
@login_required
def home():
    # Fetch trending movies
    trending_url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={API_KEY}"
    trending_movies = []
    try:
        trending_resp = requests.get(trending_url, timeout=5).json()
        trending_movies = trending_resp.get("results", [])
    except:
        flash("Failed to load trending movies", "warning")

    # Fetch most searched movies (top 20)
    most_searched = (
        db.session.query(UserSearch.movie_title, db.func.count(UserSearch.movie_title).label('count'))
        .group_by(UserSearch.movie_title)
        .order_by(db.desc('count'))
        .limit(20)
        .all()
    )
    most_searched_titles = [row.movie_title for row in most_searched]
    most_searched_movies = []
    for title in most_searched_titles:
        results = fetch_tmdb_results(title)
        if results:
            most_searched_movies.append(results[0])

    # Get personalized recommendations (up to 16)
    recommended_movies = get_user_recommendations(current_user.id, top_n=16)

    return render_template(
        "home.html",
        trending_movies=trending_movies,
        most_searched_movies=most_searched_movies,
        recommended_movies=recommended_movies,
    )

@app.route("/movie/<int:movie_id>")
@login_required
def movie_detail(movie_id):
    url = f"https://api.themoviedb.org/3/movie/{movie_id}?api_key={API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        movie = response.json()
    except Exception as e:
        flash("Could not fetch movie details.", "danger")
        return redirect(url_for("search"))

    return render_template("movie_detail.html", movie=movie)

@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please log in to continue.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login Successful! You can search for movies now', 'success')
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Invalid login. Please check your email and password.', 'danger')
    return render_template('login.html', form=form)


@app.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('home'))

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your profile has been updated successfully.', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', image_file=image_file, form=form)

@app.route("/search", methods=["GET", "POST"])
@login_required
def search():
    form = SearchForm()

    # If form is submitted via POST
    if request.method == "POST" and form.validate_on_submit():
        query = form.query.data.strip()
    else:
        # fallback to query param for direct URL searches
        query = request.args.get('query', '').strip()

    # If no query provided yet, just render search page with empty form
    if not query:
        return render_template('search.html', form=form)

    # Validate query format
    if len(query) < 2 or not re.match(r"^[a-zA-Z0-9\s:,'&\.\-\(\)\[\]!]+$", query):
        flash("Invalid search input. Please enter a valid movie name.", "warning")
        return render_template('search.html', form=form)

    try:
        movies = fetch_tmdb_results(query)
        seen_titles = set()
        filtered_movies = []

        for movie in movies:
            title = movie.get('title')
            if title and title not in seen_titles:
                seen_titles.add(title)
                filtered_movies.append(movie)

        movies = filtered_movies

        if not movies:
            flash("No results found for that search.", "warning")

        # Save user search
        search_record = UserSearch(movie_title=query, user_id=current_user.id)
        db.session.add(search_record)
        db.session.commit()

        # ML-based recommendations
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
        return render_template('results.html', form=form, movies=movies, recommended_movies=recommended_movies)

    except requests.exceptions.Timeout:
        flash("Cannot connect to TMDB. Try again later.", "danger")
        return render_template('results.html', movies=[], recommended_movies=[], form=form)

    except requests.exceptions.RequestException:
        flash("Unexpected error occurred. Try again later.", "danger")
        return render_template('results.html', movies=[], recommended_movies=[], form=form)
    

@app.route("/recommendations")
@login_required
def recommendations():
    rec_movies = get_user_recommendations(current_user.id)
    
    if not rec_movies:
        flash("Start searching for movies to get personalized recommendations!", "info")
    
    return render_template("recommendations.html", rec_movies=rec_movies)

# -------------------- Run App --------------------
if __name__ == '__main__':
    app.run(debug=True)
