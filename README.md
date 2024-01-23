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

## Deployment

Containerfiles are used in deployment. For deployed environments, Kubernetes / Terraform uses the repository root for the build context. In local environments, we use either a build script or a compose file in the `fetch-local` repository, which assumes a different build context.  This is why pathing is different between the images.

# Editor Configuration

## PyCharm IDE: Python Configuration
1. Configure Python Interpreter
Ensure that you have a Python interpreter configured for your project:

Go to File > Settings (or PyCharm > Preferences on macOS).
Navigate to Project: [Your Project Name] > Python Interpreter.
Select an interpreter or add a new one.

4. Install Formatting Tools
Install Python code formatting tools like Black, isort, or autopep8. You can do this within PyCharm or using a terminal:

Open the terminal in PyCharm or your regular terminal.
Install the tools using pip. For example:
```
pip install black
pip install isort
pip install autopep8

```
5. Configure Code Style in PyCharm
To configure the code style settings:

Go to File > Settings > Editor > Code Style > Python.
Here, you can adjust various settings like indentation, spaces, wrapping, etc., to match your preferred style or the style guide of your project.
6. Set Up Black and/or isort
To integrate Black or isort:

Go to File > Settings > Tools.
For Black:
Navigate to External Tools and add a new tool.
Set 'Program' to the path of Black (you can find it with which black in the terminal), and 'Arguments' to $FilePath$.
For isort:
Navigate to Python Integrated Tools and set the 'Sorting import' option to isort.
7. Enable PEP 8 Warnings
PyCharm can highlight PEP 8 violations:

Go to File > Settings > Editor > Inspections.
Under Python, ensure PEP 8 coding style violation is checked.
8. Format Code on Save
To automatically format code on save:

Go to File > Settings > Tools > Actions on Save.
Enable Reformat Code to apply PyCharm's code style settings.
Optionally, enable Optimize Imports to automatically organize imports on save.
9. Use Code Reformat
You can manually reformat code anytime:

Right-click on a file or folder in the Project view and select Reformat Code.
Or use the shortcut Ctrl+Alt+L (Windows/Linux) or Cmd+Alt+L (macOS).
10. Additional Plugins
Consider installing plugins for enhanced Python development:

Go to File > Settings > Plugins.
Search for Python-related plugins like SonarLint, GitToolBox, etc., and install as needed.
11. Test Your Setup
Write some Python code and try saving the file or manually reformatting to see the formatting in action.


## VS Code IDE: Python Configuration

1. Install Visual Studio Code
If you haven't already, download and install VS Code from the official website.

Setting up Visual Studio Code (VS Code) for Python code formatting involves installing and configuring extensions and tools that help in linting and formatting your Python code. Here's a step-by-step guide to set up VS Code for Python development with code formatting:

1.1. Install Visual Studio Code
If you haven't already, download and install VS Code from the official website.

2. Install the Python Extension
The Python extension for VS Code provides a rich set of features including linting, debugging, IntelliSense, code navigation, code formatting, etc.

Open VS Code.
Go to the Extensions view by clicking on the square icon on the sidebar, or press Ctrl+Shift+X.
Search for Python (look for the extension published by Microsoft).
Click on the Install button.
3. Install Python
Ensure that Python is installed on your system. You can download it from the official Python website. VS Code's Python extension will automatically detect the installed Python interpreters.

4. Select Python Interpreter
Open a Python file or create a new one.
Click on the Python version in the status bar at the bottom or use the command palette (Ctrl+Shift+P) and type Python: Select Interpreter to choose the appropriate interpreter for your project.
5. Install Formatting Tools
VS Code supports various Python code formatters. The most popular ones are autopep8, black, and yapf. You can install them using pip:
```
pip install autopep8
pip install black
pip install yapf
```
6. Configure the Formatter in VS Code
Open the Command Palette (Ctrl+Shift+P).
Type Preferences: Open Settings (JSON).
Add or modify the following settings to select your preferred formatter (e.g., black):
```
{
    "python.formatting.provider": "black",
    "editor.formatOnSave": true
}
```

7. Optional: Configure Linting
VS Code's Python extension supports various linters like pylint, flake8, mypy, etc. To use a linter:

Install the linter, e.g., for pylint:
```
pip install pylint
```
2. Configure VS Code to use the linter:
```
{
    "python.linting.enabled": true,
    "python.linting.pylintEnabled": true
}
```

8. Test Your Setup
Create or open a Python file and write some code. Try saving the file to see if it gets formatted automatically.


