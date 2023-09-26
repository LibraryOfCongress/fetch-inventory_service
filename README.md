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

## Containerization

The Python Slim image is used as a base for the container.  This image itself is based on Debian:Buster, thus any need to interact with the container system should refer to Debian documentation. 
