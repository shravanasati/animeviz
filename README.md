# animeviz

This is the repository for the website [animeviz](https://animeviz.ninja). 


### Setting up the development environment

1. Install [python](https://python.org), [poetry](https://python-poetry.org/), [mysql](https://www.mysql.com/products/community/) (make sure `mysql` is on PATH) and (optionally) [stella](https://github.com/shravanasati/stellapy) on your system.

2. Clone the repository (fork first if you want to contribute).

```sh
git clone https://github.com/shravanasati/animeviz.git
```

Change the github username in the above URL if you have forked the repository.

3. Create a virtual environment (strongly recommended). 

```sh
python -m venv venv
```

And activate it.

On Windows powershell
```powershell
./venv/Scripts/Activate.ps1
```

On unix based systems
```sh
source ./venv/bin/activate
```

4. Install all the dependencies.

```sh
poetry install --no-root
```

5. Setup the database.

Login into MySQL using the command:
```sh
mysql -u {username} -p
```

Create the `animeviz` database:
```sh
create database animeviz;
```

Now, go the project base and add a file named with `credentials.env` with the following content:

```
MYSQL_USERNAME={username}
MYSQL_PASSWORD={password}
MYSQL_HOST=localhost
MYSQL_PORT=3306
DB_POOL_SIZE=50
DB_POOL_RECYCLE=1800
```

The host and port arguments here are the default ones. If your MySQL server runs on a different host and port, modify them accordingly. The `DB_POOL_SIZE` indicates the size of connection pool used my SQLAlchemy. The `DB_POOL_RECYCLE` value indicates the duration in seconds after which the connection should be recycled

(don't include curly braces in the file)


6. MAL setup.

It is quite lengthy, read the [mal_setup.md](./mal_setup.md) file for more information.

After you obtain the client ID and client secret from MyAnimeList, append the following lines in `credentials.env`:

```
MAL_CLIENT_ID={client_id}
MAL_CLIENT_SECRET={client_secret}
```

(again DO NOT include curly braces)

7. Cloudflare Turnstile setup.

The website uses the Cloudflare [Turnstile](https://developers.cloudflare.com/turnstile/) captcha service to protect the visualization endpoint from bots.

Generate a site key and a secret key from the turnstile dashboard and put them in the credentials.env file.

```
TURNSTILE_SITE_KEY={sitekey}
TURNSTILE_SECRET_KEY={secretkey}
```

Along with that you'd also need to change the [`form.js`](./static/scripts/form.js) file and change the site key in the `window.onloadTurnstileCallback` function.

8. More configurations.

Another configuration you'd need to be able to run the server is `SECRET_KEY`, which is used by login manager to keep client-side sessions secure.

Generate a safe secret key using python:
```sh
python -c "import secrets;print(secrets.token_hex(64))"
```

Set the value as follows, in the `credentials.env` file:
```
SECRET_KEY={secret_key}
```

The application employs the `flask-limiter` library to rate limit all incoming requests. During development phase, `memory` backend is suggested to be used.

Add this line to the `credentials.env` file too.
```
FLASK_LIMITER_STORAGE_URI=memory://
```

These are more configurations:
```
PROD=0
MAX_ANIME_SEARCH_THREADS=25
```

The `PROD` variable indicates if the website is running on a production server, behind a reverse proxy like nginx. Set it to `1` only when this python app is being reverse proxied.

`MAX_ANIME_SEARCH_THREADS` is the number of threads the application will spawn when searching genres of anime from the data. 

8. Run the server.

```sh
flask --app app run
```

If you've installed stella, you can get live reloading capabilities for both backend and frontend.

```sh
stella run server
```
for just running the server.

```sh
stella run
```
for running the server as well as having reload on browser.


### Deployment Guide

This guide demonstrates how to self host *animeviz* on a VPS with `Ubuntu 22.04`.

1. Do the above (setting up the development environment) steps.

2. Follow this [tutorial](https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04) to install and setup gunicorn, nginx, and certbot.

3. Install and configure MySQL using this [tutorial](https://www.digitalocean.com/community/tutorials/how-to-install-mysql-on-ubuntu-22-04).

4. Install and configure redis using this [tutorial](https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-redis-on-ubuntu-22-04).

5. Edit the `FLASK_LIMITER_STORAGE_URI` parameter in `credentials.env` to something like this `redis://:foobared@localhost:6379` where `foobared` is the redis authentication password, and `localhost` and `6379` are the host and port redis is listening on, respectively. Refer the [flask limiter docs](https://limits.readthedocs.io/en/stable/storage.html#storage-scheme) for more details.

6. Go to the MAL API page and edit the **App Redirect URL** to replace `localhost` with the domain you've configured, and the **homepage URL** too.
