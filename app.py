from flask import Flask, render_template

app = Flask(__name__)


@app.get("/ping")
def ping():
    return {"ping": "pong"}


@app.get("/")
def home():
    return render_template("index.html")


@app.get("/visualize")
def visualize():
    return render_template("visualize.html")
