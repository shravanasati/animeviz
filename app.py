from io import BytesIO
import os
import secrets
from urllib.parse import urlencode
import xml.etree.ElementTree as ET

from dotenv import load_dotenv
from flask import (
    Flask,
    abort,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_login import LoginManager, current_user, login_user, logout_user
import requests

from database import DB_CONNECTION_URI, db_session, init_db
from models import User
from visualizer.visualizer import Visualizer

load_dotenv("./credentials.env")
init_db()


app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = DB_CONNECTION_URI
app.config["OAUTH2_PROVIDERS"] = {
    "myanimelist": {
        "client_id": os.environ.get("MAL_CLIENT_ID"),
        "client_secret": os.environ.get("MAL_CLIENT_SECRET"),
        "authorize_url": "https://myanimelist.net/v1/oauth2/authorize",
        "token_url": "https://myanimelist.net/v1/oauth2/token",
        "redirect_uri": "localhost:5000/callback/myanimelist",
        "userinfo_url": "https://api.myanimelist.net/v2/users/@me",
    },
}

login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(id):
    return db_session.get(User, int(id))


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html")


@app.errorhandler(401)
def unauthorized(provider):
    # doing this because the provider passed by abort looks like this
    # 401 Unauthorized: provider
    provider = str(provider).split(":")[-1].strip()
    return render_template("401.html", provider=provider)


@app.get("/ping")
def ping():
    return {"ping": "pong"}


@app.get("/")
def home():
    return render_template("index.html", current_user=current_user)


@app.get("/login/<provider>")
def login(provider: str):
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    provider_data = app.config["OAUTH2_PROVIDERS"].get(provider)
    if not provider_data:
        abort(404)

    session["oauth2_state"] = secrets.token_urlsafe(64)
    session["code_verifier"] = secrets.token_urlsafe(100)[:128]
    query = urlencode(
        {
            "response_type": "code",
            "client_id": provider_data["client_id"],
            "code_challenge_method": "plain",
            "code_challenge": session["code_verifier"],
            "state": session["oauth2_state"],
            # "redirect_uri": provider_data["redirect_uri"],
        }
    )

    return redirect(provider_data["authorize_url"] + "?" + query)


@app.get("/callback/<provider>")
def callback(provider: str):
    if current_user.is_authenticated:
        return redirect(url_for("home"))

    provider_data = app.config["OAUTH2_PROVIDERS"].get(provider)
    if not provider_data:
        print("missing provider data")
        abort(404)

    if "error" in request.args:
        print("error in request.args")
        print(request.args)
        abort(401, provider)

    # make sure that the state parameter matches the one we created in the
    # authorization request
    if request.args["state"] != session.get("oauth2_state"):
        print("states dont match")
        abort(401, provider)

    # make sure that the authorization code is present
    if "code" not in request.args:
        print("code not presesnt in request.args")
        print(request.args)
        abort(401, provider)

    resp = requests.post(
        provider_data["token_url"],
        data={
            "client_id": provider_data["client_id"],
            "client_secret": provider_data["client_secret"],
            "code": request.args["code"],
            "code_verifier": session["code_verifier"],
            "grant_type": "authorization_code",
        },
        headers={"Accept": "application/json"},
    )

    if resp.status_code != 200:
        print("token request failed")
        abort(401, provider)

    oauth2_token = resp.json().get("access_token")
    if not oauth2_token:
        print("oauth2 token not present in token response")
        abort(401, provider)

    # use the access token to get the username
    response = requests.get(
        provider_data["userinfo_url"],
        headers={
            "Authorization": "Bearer " + oauth2_token,
            # "Accept": "application/json",
        },
    )
    if response.status_code != 200:
        print("unable to get user info")
        abort(401, provider)

    # find or create the user in the database
    username = response.json()["name"]
    user = User.query.filter(User.name == username).first()
    if not user:
        user = User(username)
        db_session.add(user)
        db_session.commit()

    login_user(user, remember=True)
    return redirect(url_for("home"))


@app.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for("home"))


@app.get("/visualize")
def visualize_page():
    return render_template("visualize.html")


@app.post("/visualize")
def visualize():
    disable_nsfw = request.form["disable_nsfw"]
    animelist_file = request.files.get("file")
    if animelist_file:
        try:
            tree = ET.parse(animelist_file.stream)
            root = tree.getroot()
            if not root:
                raise ET.ParseError("unable to get xml root")
            userinfo = root.find("myinfo")
            if userinfo is not None:
                root.remove(userinfo)
            
            xml_buf = BytesIO()
            tree.write(xml_buf)
            xml_buf.seek(0)

            viz = Visualizer.from_xml(xml_buf, opts)
            # todo construct successfull json response from viz
            return {"success": True, "message": "All visualizations drawn successfully.", "results": results}

        except ET.ParseError:
            return {"success": False, "message": "unable to parse the animelist.xml file", "results": []}

    else:
        if not current_user.is_authenticated:
            abort(401, "myanimelist")
        pass
