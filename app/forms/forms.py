from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError, Optional
from flask_wtf.file import FileField, FileAllowed
from flask_login import current_user
from app.models.models import User

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
    """
    Main movie search form.
    query      → the text to search for
    genre_id   → TMDB genre filter (optional)
    year       → release year filter (optional)
    min_rating → minimum vote average filter (optional)
    """
    query = StringField('Search', validators=[DataRequired()])

    # TMDB genre IDs: https://developers.themoviedb.org/3/genres/get-movie-list
    genre_id = SelectField('Genre', validators=[Optional()], choices=[
        ('', 'All Genres'),
        ('28', 'Action'), ('12', 'Adventure'), ('16', 'Animation'),
        ('35', 'Comedy'), ('80', 'Crime'), ('99', 'Documentary'),
        ('18', 'Drama'), ('10751', 'Family'), ('14', 'Fantasy'),
        ('36', 'History'), ('27', 'Horror'), ('10402', 'Music'),
        ('9648', 'Mystery'), ('10749', 'Romance'), ('878', 'Sci-Fi'),
        ('53', 'Thriller'), ('10752', 'War'), ('37', 'Western'),
    ])

    year = SelectField('Year', validators=[Optional()], choices=(
        [('', 'All Years')] +
        [(str(y), str(y)) for y in range(2025, 1970, -1)]
    ))

    min_rating = SelectField('Min Rating', validators=[Optional()], choices=[
        ('', 'Any Rating'), ('9', '9+'), ('8', '8+'),
        ('7', '7+'), ('6', '6+'), ('5', '5+'),
    ])

    submit = SubmitField('Search')
