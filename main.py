import flask
from slugify import slugify
from tinydb import TinyDB, Query
from cryptography.fernet import Fernet

# Generate a key
key = Fernet.generate_key()

# Create the fernet
f = Fernet(key)

# Create the Flask app
app = flask.Flask(__name__)

# Create the secret key
app.secret_key = 'secret'

# Create the database
db = TinyDB('db.json')

# Create the database tables
users = db.table('users')
posts = db.table('posts')

# Send prf.png
@app.route('/prf.png')
def send_prf():
    return flask.send_file('images/prf.png')

# Send doge.png
@app.route('/doge.png')
def send_doge():
    return flask.send_file('images/doge.png')

# Create the main page
@app.route('/')
def index():
    if 'user' not in flask.session:
      return flask.render_template('index.html')
    else:
      return flask.redirect('app')

# Create the user registration page
@app.route('/signup', methods=['GET', 'POST'])
def signup():
    try:
      if flask.session['user'] is not None:
        return flask.redirect('app')
    except:
      pass

    if flask.request.method == 'GET':
        return flask.render_template('signup.html')
    else:
        # Get the username and password from the form
        username = flask.request.form['username']
        password = flask.request.form['password']

        # Check if the username is already taken
        if users.contains(Query().username == username):
            return flask.render_template('signup.html', error='Username already taken')
        
        # Encrypt the password
        password = f.encrypt(password.encode())

        # Add the user to the database
        users.insert({'username': username, 'password': password.decode()})

        # Log the user in
        flask.session['user'] = username

        # Redirect to the app
        return flask.redirect('app')

# Create the user login page
@app.route('/signin', methods=['GET', 'POST'])
def signin():
    try:
      if flask.session['user'] is not None:
        return flask.redirect('app')
    except:
      pass
    if flask.request.method == 'GET':
        return flask.render_template('signin.html')
    else:
        # Get the username and password from the form
        username = flask.request.form['username']
        password = flask.request.form['password']
        
        # Get the user from the database
        user = users.get(Query().username == username)

        # Check if the user exists
        if user is None:
            return flask.render_template_string('''
                Username not found.
            ''')

        # Decrypt the password
        password_ = f.decrypt(user['password'].encode()).decode()

        # Check if the password is correct
        if password != password_:
            return flask.render_template('signin.html', error='Incorrect password')
        
        # Log the user in
        flask.session['user'] = username

        # Redirect to the app
        return flask.redirect('app')

# Create the main app page
@app.route('/app')
def _app():
    if 'user' not in flask.session:
        return flask.redirect(flask.url_for('signin'))
    else:
        return flask.render_template('app.html', posts=posts)

# Create the profile page
@app.route('/profile/<user>')
def profile(user):
    if 'user' not in flask.session:
        return flask.redirect(flask.url_for('signin'))
    else:
        user = users.search(Query().username == user)
        if len(user) < 1:
            return '<h1>User not found</h1>'
        else:
            return flask.render_template('profile.html', user=user[0])

# Create the signout page
@app.route('/signout')
def signout():
    flask.session.pop('user', None)
    return flask.redirect(flask.url_for('index'))

# Create a new post page
@app.route('/newpost', methods=['GET', 'POST'])
def newpost():
    if 'user' not in flask.session:
        return flask.redirect(flask.url_for('signin'))
    else:
        if flask.request.method == 'GET':
            return flask.render_template('newpost.html')
        else:
            # Get the user data from the form
            title = flask.request.form['title']
            content = flask.request.form['content']

            # Add the post to user's posts
            user = users.search(Query().username == flask.session['user'])
            user[0]['posts'].append({'title': title, 'content': content})
            users.update(user[0], Query().username == user[0]['username'])

            # Add the post to the database
            posts.insert({'title': title, 'content': content, 'author': flask.session['user'], 'slug': slugify(title), 'id': len(posts)})

            # Redirect to the main page
            return flask.redirect(flask.url_for('_app'))

# Create the follow page
@app.route('/follow/<user>')
def follow(user):
    if 'user' not in flask.session:
        return flask.redirect(flask.url_for('signin'))
    else:
        user = users.search(Query().username == user)
        if len(user) < 1:
            return '<h1>User not found</h1>'
        else:
            if user[0]['username'] == flask.session['user']:
                return '<h1>You cannot follow yourself</h1>'
            else:
                user[0]['followers'].append(flask.session['user'])
                # Update the followers_n and the followers_p
                user[0]['followers_n'] = len(user[0]['followers'])
                user[0]['followers_p'] = ','.join(user[0]['followers'])
                users.update(user[0], Query().username == user[0]['username'])
                
                return flask.redirect(flask.url_for('profile', user=user[0]['username']))

# Create the unfollow page
@app.route('/unfollow/<user>')
def unfollow(user):
    if 'user' not in flask.session:
        return flask.redirect(flask.url_for('signin'))
    else:
        user = users.search(Query().username == user)
        if len(user) < 1:
            return '<h1>User not found</h1>'
        else:
            if flask.session['user'] in user[0]['followers_p']:
                user = user[0]
                user['followers_p'].remove(flask.session['user'])
                user['followers_n'] -= 1
                users.update({'followers_n': user['followers_n'], 'followers_p': user['followers_p']}, Query().username == user['username'])
            else:
                return '<h1>You are not following this user</h1>'

            return flask.redirect(flask.url_for('profile', user=user['username']))


# Create the post page
@app.route('/post/<slug>')
def post(slug):
    if 'user' not in flask.session:
        return flask.redirect(flask.url_for('signin'))
    else:
        post = posts.search(Query().slug == slug)
        if len(post) < 1:
            return '<h1>Post not found</h1>'
        else:
            return flask.render_template('post.html', post=post[0])

# Delete user page
@app.route('/delete')
def delete():
    if 'user' not in flask.session:
        return flask.redirect(flask.url_for('signin'))
    else:
        users.remove(Query().username == flask.session['user'])
        # remove all users posts
        posts.remove(Query().author == flask.session['user'])
        flask.session.pop('user', None)

        return flask.redirect(flask.url_for('signout'))

# Delete post page
@app.route('/delete/<post_title>')
def delete_post(post_title):
    if 'user' not in flask.session:
        return flask.redirect(flask.url_for('signin'))
    else:
        if flask.session['user'] != posts.search(Query().title == post_title)[0]['author']:
            return '<h1>You are not the author of this post</h1>'
        else:
            post = posts.search(Query().title == post_title)
            if len(post) < 1:
                return '<h1>Post not found</h1>'
            else:
                posts.remove(Query().title == post_title)
                return flask.redirect(flask.url_for('_app'))

# Create the post edit page
@app.route('/edit/<post_id>', methods=['GET', 'POST'])
def edit(post_id):
    if 'user' not in flask.session:
        return flask.redirect(flask.url_for('signin'))
    else:
        post = posts.search(Query().id == post_id)
        if len(post) < 1:
            return '<h1>Post not found</h1>'
        else:
            if flask.session['user'] != post[0]['author']:
                return '<h1>You are not the author of this post</h1>'
            else:
                if flask.request.method == 'GET':
                    return flask.render_template('edit.html', post=post[0])
                else:
                    title = flask.request.form['title']
                    content = flask.request.form['content']
                    slug = slugify(title)
                    post = posts.search(Query().slug == slug)
                    if len(post) > 0:
                        return '<h1>Post already exists</h1>'
                    else:
                        post = post[0]
                        post['title'] = title
                        post['content'] = content
                        post['slug'] = slug
                        posts.update(post, Query().id == post_id)

                        return flask.redirect(flask.url_for('post', slug=slug))

# Create the post delete page
@app.route('/delete/<post_title>')
def delete_post_page(post_title):
    if 'user' not in flask.session:
        return flask.redirect(flask.url_for('signin'))
    else:
        if flask.session['user'] != posts.search(Query().title == post_title)[0]['author']:
            return '<h1>You are not the author of this post</h1>'
        else:
            post = posts.search(Query().title == post_title)
            if len(post) < 1:
                return '<h1>Post not found</h1>'
            else:
                # Remove the post from user's posts
                user = users.search(Query().username == flask.session['user'])
                user[0]['posts'].remove(post[0])
                users.update(user[0], Query().username == user[0]['username'])

                # Redirect to the main page
                return flask.redirect(flask.url_for('_app'))

# Run the app
if __name__ == '__main__':
    app.run(debug=True)