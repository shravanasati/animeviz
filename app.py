import os
from flask import Flask, render_template

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or os.urandom(24)


@app.get("/ping")
def ping():
    return {"ping": "pong"}


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/login")
def login():
    # todo replace this with oauth code
    return render_template("login.html")


@app.get("/visualize")
def visualize():
    return render_template("visualize.html")
