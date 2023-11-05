# RD8 foosball elo rating app

This is the RD8 foosball elo rating app. A small hobby project to keep track of the games of foosball played at the RD8 HQ and, most importantly, compute and store elo ratings of the involved players in order to maintain an internal ranking.

# Installing dependencies

The dependencies are managed with pipenv. To install dependencies as well as run a virtual environment first move to the project root folder (the one containing the `manage.py` file). Install dependencies with:
```
pipenv install 
```
and run the dev environment with
```
pipenv shell
```

At the time of writing, django is the only requirement to run the app, so this step may be redundant.

# Running tests

From the project root folder run:
```
python manage.py test [app_name]
```
where app_name is an optional parameter - if ommitted it will run all tests of all apps.

# Running the web app locally

First we need to migrate the database. From the project root folder run:
```
python manage.py migrate
```
The database is now migrated, and the app can be run with the following command:
```
python manage.py runserver
```
after which the app is accessible on port 8000.

# Populating the database

The database can either be populated through django's built-in admin interface, which is accessed at the url [host_name]/admin/. An interactive shell session can be run with the command:
```
python manage.py shell
```
through which one can also interact with the database.