from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from app import db, bcrypt
from app.models.models import User
from app.forms.forms import RegistrationForm, LoginForm, UpdateAccountForm
from app.utils.helpers import save_picture
import os

auth = Blueprint('auth', __name__)

@auth.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
        user = User(username=form.username.data, email=form.email.data, password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account created successfully! Please log in to continue.', 'success')
        return redirect(url_for('auth.login'))
    return render_template('register.html', form=form)

@auth.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password, form.password.data):
            login_user(user, remember=form.remember.data)
            next_page = request.args.get('next')
            flash('Login Successful! You can search for movies now', 'success')
            return redirect(next_page) if next_page else redirect(url_for('main.home'))
        else:
            flash('Invalid login. Please check your email and password.', 'danger')
    return render_template('login.html', form=form)

@auth.route("/logout")
def logout():
    logout_user()
    flash("You have been logged out.", "info")
    return redirect(url_for('main.home'))

@auth.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            # ✅ Check file size (limit to 1MB)
            form.picture.data.seek(0, os.SEEK_END)
            size = form.picture.data.tell()
            form.picture.data.seek(0)
            if size > 1 * 1024 * 1024:
                flash("Profile picture must be under 1MB", "danger")
                return redirect(url_for('auth.account'))

            picture_file = save_picture(form.picture.data)
            current_user.image_file = picture_file

        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your profile has been updated successfully.', 'success')
        return redirect(url_for('auth.account'))

    elif request.method == 'GET':
        form.username.data = current_user.username
        form.email.data = current_user.email

    image_file = url_for('static', filename='profile_pics/' + current_user.image_file)
    return render_template('account.html', image_file=image_file, form=form)