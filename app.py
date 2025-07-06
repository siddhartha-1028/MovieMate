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
import requests
import joblib
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
model = joblib.load('movie_recommender_model.pkl')
tfidf = joblib.load('tfidf_matrix.pkl')
vectorizer = joblib.load('tfidf_vectorizer.pkl')

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


# -------------------- Models --------------------
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)

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

# -------------------- Utility Functions --------------------
def save_picture(form_picture):
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
    return render_template('home.html')


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
        flash('Your account has been created! You can now log in.', 'success')
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
            flash('Login Unsuccessful. Please check email and password', 'danger')
    return render_template('login.html', form=form)


@app.route("/logout")
def logout():
    logout_user()
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
        flash('Your account has been updated!', 'success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email
    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', image_file=image_file, form=form)


@app.route("/search_page")
@login_required
def search_page():
    return render_template('search.html')


@app.route("/search")
@login_required
def search():
    query = request.args.get('query', '').strip()

    if not query:
        flash("Please enter a movie to search.", "warning")
        return redirect(url_for('search_page'))

    url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={query}"
    
    try:
        response = requests.get(url, timeout=5)
        response.raise_for_status()
        data = response.json()
        movies = data.get('results', [])

        #Get ML recommendations
        recommended_titles = movie_recommender(query)
        recommended_movies = []

        #For each recommended title, fetch poster via TMDB
        for title in recommended_titles:
            tmdb_url = f"https://api.themoviedb.org/3/search/movie?api_key={API_KEY}&query={title}"
            rec_response = requests.get(tmdb_url, timeout=5)
            rec_response.raise_for_status()
            rec_data = rec_response.json()
            results = rec_data.get('results', [])
            
            if results:
                first_result = results[0]  #Take the first matching movie
                recommended_movies.append({
                    'title': first_result.get('title'),
                    'poster_path': first_result.get('poster_path'),
                    'overview': first_result.get('overview', '')[:100]  #Short overview
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



# -------------------- Run App --------------------
if __name__ == '__main__':
    app.run(debug=True)
