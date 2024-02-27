# animevisualised

This is the repository for the website [animevisualised](). 


### Setting up the development environment

1. Install [poetry](https://python-poetry.org/), [mysql](https://www.mysql.com/products/community/) (make sure `mysql` is on PATH) and (optionally) [stella](https://github.com/shravanasati/stellapy) on your system.

2. Clone the repository (fork first if you want to contribute).

```sh
git clone https://github.com/shravanasati/animevisualised.git
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
poetry install
```

5. Setup the database.

Login into MySQL using the command:
```sh
mysql -u {username} -p
```

Create the `animevisualised` database:
```sh
create database animevisualised;
```

Now, go the project base and add a file named with `credentials.env` with the following content:

```
MYSQL_USERNAME={username}
MYSQL_PASSWORD={password}
MYSQL_HOST=localhost
MYSQL_PORT=3306
```

The host and port arguments here are the default ones. If your MySQL server runs on a different host and port, modify them accordingly.

(don't include curly braces in the file)


6. MAL setup.

It is quite lengthy, read the [mal_setup.md](./mal_setup.md) file for more information.

After you obtain the client ID and client secret from MyAnimeList, append the following lines in `credentials.env`:

```
MAL_CLIENT_ID={client_id}
MAL_CLIENT_SECRET={client_secret}
```

(again DO NOT include curly braces)

7. Secret key setup.

The last configuration you'd need to be able to run the server is `SECRET_KEY`, which is used by login manager to keep client-side sessions secure.

Generate a safe secret key using python:
```py
>>> import secrets
>>> secrets.token_hex(64)
```

Set the value as follows, in the `credentials.env` file:
```
SECRET_KEY={secret_key}
```

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