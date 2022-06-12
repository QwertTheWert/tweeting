from ast import Index
import secrets
import os
from PIL import Image

from flask import render_template, url_for, redirect, flash, request, abort, jsonify

from project import app, db#, bcrypt
from project.models import User, Tweet
from project.forms import RegistrationForm, LoginForm, UpdateProfileForm, TweetForm

from flask_login import login_user, current_user, logout_user, login_required


@app.route("/", methods=['GET', 'POST']) # 127.0.0.1:8000
@app.route("/home", methods=['GET', 'POST']) # 127.0.0.1:8000/home
def home():
	form = TweetForm()

	if form.validate_on_submit() and current_user.is_authenticated: 
		tweet = Tweet(content=form.content.data, user_id = current_user.id)
		db.session.add(tweet)
		db.session.commit()
		flash("Your tweet has been created!", "success")
		return redirect(url_for("home"))

	# tweets = Tweet.query.order_by(Tweet.date_posted.desc()).all()
	tweets = Tweet.query.order_by(Tweet.date_posted.desc()).paginate(per_page=5)

	try:
		last_page = list(tweets.iter_pages())[-1]
	except IndexError:
		last_page = 1

	return render_template('home.html', tweets=tweets, form=form, last_page=last_page)

@app.route("/register", methods=['GET', 'POST'])
def register():
	form = RegistrationForm()
	if form.validate_on_submit():
		hashed_password = form.password.data #bcrypt.generate_password_hash(form.password.data).decode('utf-8')
		user = User(username=form.username.data, email=form.email.data, password=hashed_password)
		db.session.add(user)
		db.session.commit()
		flash(f"Your account has been created!, You are now able to log in.", "success")
		return redirect(url_for('login'))	
	return render_template('register.html', title='Register', form=form)


@app.route("/login", methods=['GET', 'POST'])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		user = User.query.filter_by(email=form.email.data).first()
		
		# if user and bcrypt.check_password_hash(user.password, form.password.data):
		if user and (user.password == form.password.data):
			login_user(user, remember=form.remember.data)
			return redirect(url_for('profile', user_id = current_user.id))

		flash('Login Unsuccessful. Please check email and password', 'danger')
	return render_template('login.html', title='Login', form=form)


@app.route("/logout")
def logout():
	logout_user()
	return redirect(url_for('home'))

def save_data(form_picture):
	#file name and path
	random_file_name = secrets.token_hex(16)
	f_name, f_ext = os.path.splitext(form_picture.filename)
	picture_file_name = random_file_name + f_ext
	picture_file_path = os.path.join(app.root_path, 'static/profile_pictures', picture_file_name)

	#image compress processing
	output_size = (125, 125)
	image = Image.open(form_picture)
	image.thumbnail(output_size)
	image.save(picture_file_path)

	return picture_file_name

@app.route("/profile/<int:user_id>", methods=['GET', 'POST'])
def profile(user_id):
	user = User.query.get_or_404(user_id)
	form = TweetForm()
	tweets = Tweet.query.filter_by(user_id=user_id).order_by(Tweet.date_posted.desc()).paginate(per_page=5)
	print(tweets.items)
	try:
		last_page = list(tweets.iter_pages())[-1]
	except IndexError:
		last_page = 1

	if form.validate_on_submit() and current_user.is_authenticated: 
		tweet = Tweet(content=form.content.data, user_id = current_user.id)
		db.session.add(tweet)
		db.session.commit()
		flash("Your tweet has been created!", "success")
		return redirect(request.url)


	return render_template('profile.html', tweets=tweets, user=user, title="Profile", last_page=last_page, form=form)

@app.route("/edit_profile", methods=['GET', 'POST'])
@login_required
def edit_profile():
	form = UpdateProfileForm()
	if form.validate_on_submit():

		if form.picture.data:
			current_user.image_file = save_data(form.picture.data)
		
		if form.current_password.data != "":
			if current_user and (current_user.password == form.current_password.data):
				if len(form.new_password.data) > 0:
					### hashed_password = form.new_password.data #bcrypt.generate_password_hash(form.password.data).decode('utf-8')
					current_user.password = form.new_password.data
				else:
					flash("Your new password must not be empty", "danger")
					return redirect(url_for('edit_profile'))
			else:
				flash("Your current password is incorrect", "danger")
				return redirect(url_for('edit_profile'))

		current_user.username = form.username.data
		db.session.commit()
		flash("Your account has been updated!", "success")
		return redirect(url_for('profile'), user_id=current_user.id)

	elif request.method == 'GET':
		form.username.data = current_user.username
	image_file = url_for('static', filename='profile_pictures/'+current_user.image_file)
	return render_template('edit_profile.html', title="Edit Profile", image_file=image_file, form=form)

@app.route("/about")
def about():
	return render_template('about.html', title='About Us')

@app.route("/tweet/<int:tweet_id>", methods=["GET", "POST"])
def tweet(tweet_id):
	tweet = Tweet.query.get_or_404(tweet_id)

	if tweet.author != current_user:
		abort(403)

	form = TweetForm()

	if form.validate_on_submit():
		tweet.content = form.content.data
		db.session.commit()
		flash("Your tweet has been updated!", "success")
		return redirect(url_for("profile", user_id=current_user.id))

	form.content.data = tweet.content
	return render_template("tweet.html", title="Tweet", form=form, tweet=tweet)

@app.route("/delete_tweet/<int:tweet_id>", methods=["POST"])
def delete_tweet(tweet_id, source_url):
	tweet = Tweet.query.get(tweet_id)

	if tweet.author != current_user:
		abort(403)
	
	db.session.delete(tweet)
	db.session.commit()
	flash("Your tweet has been deleted!", "success")
	return redirect(url_for("profile"), user_id=current_user.id)

@app.route("/trending/<string:tag>", methods=["GET", "POST"])
def trending(tag):

	# tweets = Tweet.query.order_by(Tweet.date_posted.desc()).all()
	tweets = Tweet.query.filter(Tweet.content.like(tag)).paginate(per_page=5)

	try:
		last_page = list(tweets.iter_pages())[-1]
	except IndexError:
		last_page = 1

	return render_template('trending.html', tweets=tweets, tag=tag, last_page=last_page)

@app.errorhandler(404)
def error_404(error):
	return render_template("errors/404.html"), 404

@app.errorhandler(403)
def error_403(error):
	return render_template("errors/403.html"), 403

@app.errorhandler(500)
def error_500(error):
	return render_template("errors/500.html"), 500

#API ROUTES
@app.route("/get_user_api/<string:username>")
def get_user_api(username):
	user = User.query.filter_by(username=username).first()
	if user is None:
		return jsonify({
			'success': False
		})
	
	return jsonify({
		"id": user.id,
		"username": user.username,
		"email": user.email,
		"image_file": user.image_file
	})
