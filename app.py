import logging
import os

# from pathlib import Path
import secrets
import xml.etree.ElementTree as ET
from datetime import timedelta
from io import BytesIO
from urllib.parse import urlencode

import requests
from dotenv import load_dotenv
from flask import Flask, abort, redirect, render_template, request, session, url_for
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, current_user, login_user, logout_user
from flask_turnstile import Turnstile

from database import DB_CONNECTION_URI, db_session, init_db
from models import User
from visualizer.api_helper import build_df_from_mal_api_data
from visualizer.visualizer import VisualizationOptions, Visualizer

load_dotenv("./credentials.env")
init_db()


app = Flask(__name__)
app.secret_key = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = DB_CONNECTION_URI
app.config["MAX_CONTENT_LENGTH"] = 16 * 1000 * 1000  # 16MB
app.config["OAUTH2_PROVIDERS"] = {
    "myanimelist": {
        "client_id": os.environ.get("MAL_CLIENT_ID"),
        "client_secret": os.environ.get("MAL_CLIENT_SECRET"),
        "authorize_url": "https://myanimelist.net/v1/oauth2/authorize",
        "token_url": "https://myanimelist.net/v1/oauth2/token",
        "redirect_uri": "localhost:5000/callback/myanimelist",
        "userinfo_url": "https://api.myanimelist.net/v2/users/@me",
        "animelist_url": "https://api.myanimelist.net/v2/users/@me/animelist?limit=1000&fields=id,title,my_list_status,num_episodes,media_type&nsfw=1",
    },
}

# setup for reverse proxy
if int(os.environ["PROD"]):
    from werkzeug.middleware.proxy_fix import ProxyFix

    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

# flask login settings
app.config["REMEMBER_COOKIE_DURATION"] = timedelta(days=30)
app.config["REMEMBER_COOKIE_REFRESH_EACH_REQUEST"] = False
# // todo add logging config


# def get_logging_filepath():
#     logs_dir = Path("./logs")
#     if not logs_dir.exists():
#         logs_dir.mkdir()

#     today_log_file = logs_dir / str(date.today())
#     return today_log_file


# logging.basicConfig()

login_manager = LoginManager()
login_manager.init_app(app)

limiter = Limiter(
    get_remote_address,
    app=app,
    headers_enabled=True,
    storage_uri=os.environ["FLASK_LIMITER_STORAGE_URI"],
    default_limits=["60/minute", "1/second"],
)

turnstile = Turnstile(
    app=app,
    is_enabled=True,
    site_key=os.environ["TURNSTILE_SITE_KEY"],
    secret_key=os.environ["TURNSTILE_SECRET_KEY"],
)


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
    # doing this string manipulation because the provider passed by
    # abort looks like this -> 401 Unauthorized: provider
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
        logging.debug("missing provider data")
        abort(404)

    if "error" in request.args:
        logging.error("error in request.args")
        logging.error(request.args)
        abort(401, provider)

    # make sure that the state parameter matches the one we created in the
    # authorization request
    if request.args["state"] != session.get("oauth2_state"):
        logging.warning("states dont match")
        abort(401, provider)

    # make sure that the authorization code is present
    if "code" not in request.args:
        logging.warning("code not presesnt in request.args")
        logging.warning(request.args)
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
        logging.warning("token request failed")
        abort(401, provider)

    resp_json = resp.json()
    oauth2_token = resp_json.get("access_token")
    refresh_token = resp_json.get("refresh_token")
    if not oauth2_token or not refresh_token:
        logging.warning("tokens not present in token response")
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
        logging.warning("unable to get user info")
        abort(401, provider)

    # find or create the user in the database
    username = response.json()["name"]
    user: User = User.query.filter_by(name=username).first()
    if not user:
        user = User(username, provider, oauth2_token, refresh_token)
        db_session.add(user)
    else:
        user.oauth2_token = oauth2_token
        user.refresh_token = refresh_token
    db_session.commit()

    login_user(user, remember=True)
    return redirect(url_for("home"))


def issue_new_token(user: User):
    provider_data = app.config["OAUTH2_PROVIDERS"][user.login_provider]
    if not provider_data:
        logging.debug("unable to get provider data in issue_new_token")
        return False

    resp = requests.post(
        provider_data["token_url"],
        data={
            "client_id": provider_data["client_id"],
            "client_secret": provider_data["client_secret"],
            "refresh_token": user.refresh_token,
            "grant_type": "refresh_token",
        },
        headers={"Accept": "application/json"},
    )

    if resp.status_code != 200:
        logging.warning("issuing new access token using refresh token failed")
        return False

    resp_json = resp.json()
    oauth2_token = resp_json.get("access_token")
    refresh_token = resp_json.get("refresh_token")

    if not oauth2_token or not refresh_token:
        logging.warning("tokens not present in token response")
        return False

    user.refresh_token = refresh_token
    user.oauth2_token = oauth2_token
    db_session.commit()


@app.route("/logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for("home"))


@app.get("/visualize")
def visualize_page():
    return render_template("visualize.html")


@app.post("/visualize")
@limiter.limit("6/minute;1/10second")
def visualize():
    if not turnstile.verify():
        # print("cpatcha verification failed")
        abort(401, "captcha")

    disable_nsfw = request.form.get("disable_nsfw")
    if not disable_nsfw:
        disable_nsfw = True
    else:
        disable_nsfw = disable_nsfw == "true"
    animelist_file = request.files.get("file")

    opts = VisualizationOptions(disable_nsfw, False)

    if animelist_file:
        try:
            # todo add a queued column in the database for every user
            # for non-logged in users, hash the animelist file

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
            results = viz.visualize_all()
            results_json = [r.as_dict() for r in results]
            return {
                "success": True,
                "message": "All visualizations drawn successfully.",
                "results": results_json,
            }

        except ET.ParseError:
            return {
                "success": False,
                "message": "unable to parse the animelist.xml file",
                "results": [],
            }

    else:
        if not current_user.is_authenticated:
            abort(401, "myanimelist")

        try:
            oauth2_token = current_user.oauth2_token
            login_provider = current_user.login_provider
            provider_data = app.config["OAUTH2_PROVIDERS"][login_provider]
            animelist_url = provider_data["animelist_url"]

            paging_available = True
            data = []
            while paging_available:
                resp = requests.get(
                    animelist_url, headers={"Authorization": "Bearer " + oauth2_token}
                )
                if resp.status_code == 401:
                    if issue_new_token(current_user):
                        continue
                    else:
                        return {
                            "success": False,
                            "message": "Unable to authorize the user! Please logout and login once.",
                            "results": [],
                        }

                resp.raise_for_status()
                resp_json = resp.json()
                data += resp_json["data"]
                paging_available = resp_json["paging"].get("next")
                if paging_available:
                    animelist_url = resp_json["paging"]["next"]

            df = build_df_from_mal_api_data(data)
            viz = Visualizer(df, opts)
            results = viz.visualize_all()
            results_json = [r.as_dict() for r in results]
            return {
                "success": True,
                "message": "All visualizations drawn successfully.",
                "results": results_json,
            }

        except Exception as e:
            logging.error("cant get user animelist")
            logging.exception(e)
            abort(500)
