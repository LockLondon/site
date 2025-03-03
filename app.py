#!/usr/bin/env python3
from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required
import sqlite3

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
DATABASE = 'database.db'

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, id, username, email, age):
        self.id = id
        self.username = username
        self.email = email
        self.age = age

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@login_manager.user_loader
def load_user(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (user_id,)).fetchone()
    conn.close()
    if user is None:
        return None
    return User(user['id'], user['username'], user['email'], user['age'])

@app.route('/')
def index():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    selected_category = request.args.get('category')
    selected_category_name = 'Всі публікації'
    if selected_category:
        posts = conn.execute('''
            SELECT posts.*, users.username 
            FROM posts JOIN users ON posts.author_id = users.id 
            WHERE posts.category_id = ?''', (selected_category,)).fetchall()
        selected_category_name = conn.execute('SELECT name FROM categories WHERE id = ?', (selected_category,)).fetchone()['name']
    else:
        posts = conn.execute('''
            SELECT posts.*, users.username 
            FROM posts JOIN users ON posts.author_id = users.id''').fetchall()
    conn.close()
    return render_template('index.html', posts=posts, categories=categories, selected_category=selected_category, selected_category_name=selected_category_name)

@app.route('/login', methods=('GET', 'POST'))
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, password)).fetchone()
        conn.close()

        if user:
            email = user['email'] if 'email' in user.keys() else 'Email not found'
            age = user['age'] if 'age' in user.keys() else 'Age not specified'
            user_obj = User(user['id'], user['username'], email, age)
            login_user(user_obj)
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password')

    return render_template('login.html')


@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/register', methods=('GET', 'POST'))
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        email = request.form['email']
        age = request.form['age']

        if int(age) < 0:
            flash('Age cannot be negative')
            return render_template('register.html')

        conn = get_db_connection()
        conn.execute('INSERT INTO users (username, password, email, age) VALUES (?, ?, ?, ?)', (username, password, email, age))
        conn.commit()
        conn.close()
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category_id = request.form.get('category')

        if not category_id:
            flash('Category is required!')
            return render_template('create.html', categories=categories)

        conn.execute('INSERT INTO posts (title, content, author_id, category_id) VALUES (?, ?, ?, ?)', (title, content, current_user.id, category_id))
        conn.commit()
        conn.close()

        return redirect('/')

    conn.close()
    return render_template('create.html', categories=categories)


@app.route('/edit_post/<int:post_id>', methods=('GET', 'POST'))
@login_required
def edit_post(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    categories = conn.execute('SELECT * FROM categories').fetchall()
    if request.method == 'POST':
        title = request.form['title']
        content = request.form['content']
        category_id = request.form.get('category')

        if post and post['author_id'] == current_user.id:
            conn.execute('UPDATE posts SET title = ?, content = ?, category_id = ? WHERE id = ?', (title, content, category_id, post_id))
            conn.commit()
            flash('Post successfully updated!')
        else:
            flash('You are not authorized to edit this post')
        conn.close()
        return redirect(url_for('post', post_id=post_id))

    conn.close()
    return render_template('edit_post.html', post=post, categories=categories)


@app.route('/delete/<int:post_id>', methods=('POST',))
@login_required
def delete(post_id):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM posts WHERE id = ?', (post_id,)).fetchone()
    if post and post['author_id'] == current_user.id:
        conn.execute('DELETE FROM posts WHERE id = ?', (post_id,))
        conn.commit()
        flash('Post successfully deleted!')
    else:
        flash('You are not authorized to delete this post')
    conn.close()
    return redirect(url_for('index'))


@app.route('/post/<int:post_id>', methods=('GET', 'POST'))
def post(post_id):
    conn = get_db_connection()
    post = conn.execute('''
        SELECT posts.*, users.username 
        FROM posts JOIN users ON posts.author_id = users.id 
        WHERE posts.id = ?''', (post_id,)).fetchone()
    comments = conn.execute('''
        SELECT comments.*, users.username 
        FROM comments JOIN users ON comments.author_id = users.id 
        WHERE comments.post_id = ?''', (post_id,)).fetchall()
    conn.close()

    if request.method == 'POST':
        content = request.form['content']
        if not current_user.is_authenticated:
            flash('You need to be logged in to comment!')
            return redirect(url_for('post', post_id=post_id))

        conn = get_db_connection()
        conn.execute('INSERT INTO comments (content, post_id, author_id) VALUES (?, ?, ?)', (content, post_id, current_user.id))
        conn.commit()
        conn.close()
        return redirect(url_for('post', post_id=post_id))

    return render_template('post.html', post=post, comments=comments)


@app.route('/edit_comment/<int:comment_id>', methods=('GET', 'POST'))
@login_required
def edit_comment(comment_id):
    conn = get_db_connection()
    comment = conn.execute('SELECT * FROM comments WHERE id = ?', (comment_id,)).fetchone()
    if request.method == 'POST':
        content = request.form['content']
        
        if comment and comment['author_id'] == current_user.id:
            conn.execute('UPDATE comments SET content = ? WHERE id = ?', (content, comment_id))
            conn.commit()
            flash('Comment successfully updated!')
        else:
            flash('You are not authorized to edit this comment')
        conn.close()
        return redirect(url_for('post', post_id=comment['post_id']))

    conn.close()
    return render_template('edit_comment.html', comment=comment)

@app.route('/delete_comment/<int:comment_id>', methods=('POST',))
@login_required
def delete_comment(comment_id):
    conn = get_db_connection()
    comment = conn.execute('SELECT * FROM comments WHERE id = ?', (comment_id,)).fetchone()
    if comment and comment['author_id'] == current_user.id:
        conn.execute('DELETE FROM comments WHERE id = ?', (comment_id,))
        conn.commit()
        flash('Comment successfully deleted!')
    else:
        flash('You are not authorized to delete this comment')
    conn.close()
    return redirect(request.referrer)

    
@app.route('/profile')
@login_required
def profile():
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (current_user.id,)).fetchone()
    conn.close()
    return render_template('profile.html', user=user)

@app.route('/edit_profile', methods=('GET', 'POST'))
@login_required
def edit_profile():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        age = request.form['age']

        if int(age) < 0:
            flash('Age cannot be negative')
            return render_template('edit_profile.html', user=current_user)

        conn = get_db_connection()
        conn.execute('UPDATE users SET username = ?, email = ?, age = ? WHERE id = ?', (username, email, age, current_user.id))
        conn.commit()
        conn.close()

        flash('Profile successfully updated!')
        return redirect(url_for('profile'))

    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (current_user.id,)).fetchone()
    conn.close()
    return render_template('edit_profile.html', user=user)

if __name__ == '__main__':
    app.run(host='0.0.0.0',port=5000,debug=True)
