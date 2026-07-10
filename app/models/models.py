from app import db, login_manager
from flask_login import UserMixin
from datetime import datetime

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    searches = db.relationship('UserSearch', backref='user', lazy=True)

    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"

class UserSearch(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    movie_title = db.Column(db.String(255), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<UserSearch {self.movie_title} by User {self.user_id}>"

class Watchlist(db.Model):
    """
    Stores movies a user has saved to their watchlist.
    Each row = one movie saved by one user.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, nullable=False)           # TMDB's ID for the movie
    movie_title = db.Column(db.String(255), nullable=False)
    poster_path = db.Column(db.String(255), nullable=True)
    added_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<Watchlist movie={self.movie_title} user={self.user_id}>"

class Review(db.Model):
    """
    Stores a star rating + written review left by a user on a specific movie.
    Each row = one review by one user on one movie.
    """
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    movie_id = db.Column(db.Integer, nullable=False)           # TMDB's ID for the movie
    movie_title = db.Column(db.String(255), nullable=False)
    rating = db.Column(db.Integer, nullable=False)             # 1 to 5 stars
    content = db.Column(db.Text, nullable=True)                # written review text
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships: easy access to the user who wrote this review
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))

    def __repr__(self):
        return f"<Review movie={self.movie_title} rating={self.rating} user={self.user_id}>"
