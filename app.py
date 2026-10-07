import os
import sqlite3
import uuid
from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = "my-secret-key"     

BASE = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE, "blog.db")
UPLOAD_FOLDER = os.path.join(BASE, "static", "uploads")
ALLOWED = {"png", "jpg", "jpeg", "gif", "webp"}

USERNAME = "admin"
PASSWORD = "1234"


def db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = db()
    conn.execute("""CREATE TABLE IF NOT EXISTS posts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT, text TEXT, image TEXT)""")
    conn.execute("""CREATE TABLE IF NOT EXISTS comments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        post_id INTEGER, name TEXT, text TEXT)""")
    conn.commit()
    conn.close()


def save_image(file):
    if not file or file.filename == "":
        return None
    ext = file.filename.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED:
        return None
    name = uuid.uuid4().hex + "_" + secure_filename(file.filename)
    file.save(os.path.join(UPLOAD_FOLDER, name))
    return name


def delete_image(name):
    if name:
        path = os.path.join(UPLOAD_FOLDER, name)
        if os.path.exists(path):
            os.remove(path)
@app.route("/")
def index():
    conn = db()
    posts = conn.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    conn.close()
    return render_template("index.html", posts=posts)


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["username"] == USERNAME and request.form["password"] == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
        flash("Username or password is wrong!")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("index"))


@app.route("/new", methods=["GET", "POST"])
def new_post():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    if request.method == "POST":
        image = save_image(request.files.get("image"))
        conn = db()
        conn.execute("INSERT INTO posts (title, text, image) VALUES (?, ?, ?)",
                     (request.form["title"], request.form["text"], image))
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    return render_template("post_form.html", post=None)


@app.route("/edit/<int:post_id>", methods=["GET", "POST"])
def edit_post(post_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    conn = db()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post is None:
        conn.close()
        return redirect(url_for("index"))

    if request.method == "POST":
        image = post["image"]
        new_image = save_image(request.files.get("image"))
        if new_image:                    
            delete_image(image)
            image = new_image
        conn.execute("UPDATE posts SET title = ?, text = ?, image = ? WHERE id = ?",
                     (request.form["title"], request.form["text"], image, post_id))
        conn.commit()
        conn.close()
        return redirect(url_for("index"))

    conn.close()
    return render_template("post_form.html", post=post)

@app.route("/delete/<int:post_id>")
def delete_post(post_id):
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    conn = db()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post:
        delete_image(post["image"])
        conn.execute("DELETE FROM comments WHERE post_id = ?", (post_id,))
        conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        conn.commit()
    conn.close()
    return redirect(url_for("index"))

@app.route("/comments/<int:post_id>", methods=["GET", "POST"])
def comments(post_id):
    conn = db()
    post = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if post is None:
        conn.close()
        return redirect(url_for("index"))

    if request.method == "POST":
        conn.execute("INSERT INTO comments (post_id, name, text) VALUES (?, ?, ?)",
                     (post_id, request.form["name"], request.form["text"]))
        conn.commit()
        conn.close()
        return redirect(url_for("comments", post_id=post_id))

    all_comments = conn.execute("SELECT * FROM comments WHERE post_id = ? ORDER BY id DESC",
                                (post_id,)).fetchall()
    conn.close()
    return render_template("comments.html", post=post, comments=all_comments)


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    init_db()
    app.run(debug=True)
