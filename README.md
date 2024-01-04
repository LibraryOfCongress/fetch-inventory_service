# FETCH API

An API serving the Findings Environment for Collected Holdings application

# Setup

This is a containerized application for both local and deployed environments.  Below steps will get you up and running locally. Virtual Environment management is only needed for developers who will be updating the application's dependencies and working with scripts. Otherwise, everything is handled inside Pods / Containers.

## Docker
This project assumes you have locally setup [Docker Desktop](https://www.docker.com/products/docker-desktop/). It is posssible to use Homebrew for this. https://formulae.brew.sh/cask/docker 

## Poetry
This project's environment and dependencies are managed with Poetry.

[Poetry's](https://python-poetry.org/) workflow ties the developer's virtual environment to the project itself, allowing for rapid ramp-up, team standardization, and reduced maintenance divergence.  Poetry [provides hooks](https://python-poetry.org/docs/pre-commit-hooks/) to integrate with pre-commit, further ensuring dependency integrity on commits. This includes synchronization of Poetry's dependency management with the traditional `requirements.txt` used in Python frameworks. Finally, poetry also streamlines the process of publishing a Python package on PyPy should the need arise.

### Installation
```sh
$ python3 -m ensurepip
$ python3 -m pip install --upgrade pip
$ pip3 install poetry
```

### Configuration

Configure poetry to store `.venv` inside project structure (this is .gitignored).

```sh
$ poetry config virtualenvs.in-project true
```

## Virtual Environment

First install [pyenv](https://github.com/pyenv/pyenv#installation), and add it to your `PATH`
```sh
$ brew install pyenv
$ nano $HOME/.zshenv

# In .zshenv
export PYENV_ROOT="$HOME/.pyenv"
export PATH="$PYENV_ROOT/bin:$PATH"
eval "$(pyenv init -)"
```
Save your zsh environment, exit, and then reload the shell with `$ zsh -l`

Now create a local virtual environment.
```sh
$ cd path/to/repository/root
$ poetry install
```

Activate the environment and verify everything looks right.
```sh
$ poetry shell
$ poetry env info
$ python --version
$ where python
```
If your terminal / shell supports it, the activated virtual environment will also display in your prompt. e.g `(api-py3.11)` or rather `(<project-name>-python version)`.

If / when you want to get out of the environment, simply `$ exit` or `$ deactivate`

Dependency management
```sh
$ poetry add <package>
$ poetry remove <package>
```

# Run

```
./helper.sh build local
```
Simply calling the command again will take care of tear down and rebuild. The application should now be running on your localhost at http://127.0.0.1:8001/

Under the hood, the image takes the necessary steps to generate the API's package requirements from the pyproject.toml and poetry lock files.

Additional environments can be built by passing their names, `dev`, `test`, etc.


# Project

## Settings

Environment variables should be set through the environment. The [Pydantic settings](https://docs.pydantic.dev/latest/usage/pydantic_settings/) system is used to set default values for expected `.env` keys. The application will automatically override these if matching keys are found in the environment.

For local builds, there is no need to have a `.env` file.  For deployed environments, devops should handle seeding this file into the repository root before building.

## Containerization

The Python Slim image is used as a base for the container.  This image itself is based on Debian:Buster, thus any need to interact with the container system should refer to Debian documentation. 


## Database Migrations

[Alembic](https://alembic.sqlalchemy.org/en/latest/) is used for migration management. The target database for the Inventory Service is `inventory_service`.

Revision logic has been configured to output with an inverted date format instead of the default random strings Alembic would normally generate. This allows our files to be sequential, and the history command to display reverse chronological order.

```sh
2023_10_15_06:52:16 -> 2023_10_15_06:54:53 (head), Add Module table
2023_10_15_06:33:28 -> 2023_10_15_06:52:16, Add Module Number table
<base> -> 2023_10_15_06:33:28, Add building table
```

Add models for Alembic tracking in `/migrations/models.py`. The order of import is initially important when first adding new tables, as to satisfy the dependency of foreign key relationships. After a migration file is generated though, it's safe to allow our pre-commit hooks to sort imports however it likes.

Unlike other common migration tools, Alembic only stores the current version in the database.  We should assume that all previous revisions in the dowgrade history have been applied.  A future task may be to add a separate tracking table.

Commands:

```sh
# Add a new migration file
alembic revision -m "Update some model field" --autogenerate

# Run all migrations up to the latest
alembic upgrade head

# Reverse the last migration
alembic downgrade -1

# Revert to a previous migration
alembic downgrade [target_version]

# Show the current migration version in the database
alembic current

# List version migration scripts in order
alembic history
```

Helper commands have been created to allow CLI migration management from outside a running container on local only (future support may be added for other environments by simply updating the MIGRATION_URL environment variable for those environments).

* `./helper.sh makemigrations "Your Message Here"` - generates a new migration
* `./helper.sh migrate` - runs alembic upgrade head
* `./helper.sh current` - Reports the current db migration.
