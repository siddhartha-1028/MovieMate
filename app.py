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
import joblib
import re
import pandas as pd

# -------------------- Configuration --------------------
load_dotenv()

app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database.db'
app.config['UPLOAD_FOLDER'] = 'static/profile_pics'
API_KEY = os.getenv('API_KEY')

#Load your final_movie_data.csv and ML files
new_df = pd.read_csv('Datapreprocessing/final_movie_data.csv')
model, tfidf, vectorizer = load_model()

db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

#Recommendation function
def movie_recommender(movie_title, k=5):
    movie_title = movie_title.lower()
    if movie_title not in new_df['title'].values:
        return []  # Movie not found in dataset

    movie_index = new_df[new_df['title'] == movie_title].index[0]
    movie_tfidf = tfidf[movie_index]

    distances, indices = model.kneighbors(movie_tfidf, n_neighbors=k+1)
    indices = indices.flatten()[1:]
    recommended_movies = new_df.iloc[indices]['title'].values

    return recommended_movies

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
def home():
    # Fetch trending movies from TMDB
    trending_url = f"https://api.themoviedb.org/3/trending/movie/week?api_key={API_KEY}"
    trending_movies = []
    try:
        trending_resp = requests.get(trending_url, timeout=5).json()
        trending_movies = trending_resp.get("results", [])
    except:
        flash("Failed to load trending movies", "warning")

    # Fetch popular movies from TMDB
    popular_url = f"https://api.themoviedb.org/3/movie/popular?api_key={API_KEY}"
    popular_movies = []
    try:
        popular_resp = requests.get(popular_url, timeout=5).json()
        popular_movies = popular_resp.get("results", [])
    except:
        flash("Failed to load popular movies", "warning")

    return render_template("home.html",
                           trending_movies=trending_movies,
                           popular_movies=popular_movies)



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


@app.route("/search_page", methods=["GET", "POST"])
@login_required
def search_page():
    form = SearchForm()
    return render_template('search.html', form=form)

@app.route("/search")
@login_required
def search():
    query = request.args.get('query', '').strip()

    # Block empty, too short, or non-alphanumeric input
    if not query or len(query) < 2 or not re.match(r"^[a-zA-Z0-9\s:,'&\.\-\(\)\[\]!]+$", query):
        flash("Invalid search input. Please enter a valid movie name.", "warning")
        return redirect(url_for('search_page'))
        
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
        # ✅ Save the search to the database
        # from models import UserSearch
        search_record = UserSearch(movie_title=query, user_id=current_user.id)
        db.session.add(search_record)
        db.session.commit()

        # ✅ Get ML recommendations based on this movie
        recommended_titles = movie_recommender(query)
        recommended_movies = []

        # ✅ For each recommended title, fetch poster via TMDB
        for title in recommended_titles:
            if title.lower() in seen_titles:
                continue
            seen_titles.add(title.lower())
            results = fetch_tmdb_results(title)

            if results:
                first_result = next(
                    (m for m in results if m.get('title', '').lower() == title.lower()), 
                    results[0] if results else None
                )
                recommended_movies.append({
                    'title': first_result.get('title'),
                    'poster_path': first_result.get('poster_path'),
                    'overview': first_result.get('overview', '')[:100]
                })
            else:
                recommended_movies.append({
                    'title': title,
                    'poster_path': None,
                    'overview': ''
                })

        return render_template('results.html', movies=movies, recommended_movies=recommended_movies)

    except requests.exceptions.Timeout:
        flash("Cannot connect to TMDB. Try again later.", "danger")
        return render_template('results.html', movies=[], recommended_movies=[])

    except requests.exceptions.RequestException:
        flash("Unexpected error occurred. Try again later.", "danger")
        return render_template('results.html', movies=[], recommended_movies=[])

@app.route("/recommendations")
@login_required
def recommendations():
    user_searches = (
        db.session.query(UserSearch.movie_title)
        .filter_by(user_id=current_user.id)
        .order_by(UserSearch.timestamp.desc())
        .limit(10)
        .all()
    )

    movie_titles = [r[0] for r in user_searches]

    if not movie_titles:
        flash("You haven't searched for any movies yet.", "info")
        return render_template("recommendations.html", rec_movies=[])

    recommended_df = recommend_from_history(movie_titles)

    if recommended_df.empty:
        flash("Start searching for movies to get personalized recommendations!", "info")
        return render_template("recommendations.html", rec_movies=[])

    rec_movies = []
    for _, row in recommended_df.iterrows():
        results = fetch_tmdb_results(row['title'])
        poster_path = results[0]['poster_path'] if results else None
        overview = results[0]['overview'] if results else "No description."

        rec_movies.append({
            "title": row['title'],
            "poster_path": poster_path,
            "overview": overview
        })

    return render_template("recommendations.html", rec_movies=rec_movies)

# -------------------- Run App --------------------
if __name__ == '__main__':
    app.run(debug=True)
