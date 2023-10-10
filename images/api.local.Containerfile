FROM python:3.11.4-slim as requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY ../pyproject.toml ../poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

FROM python:3.11.4-slim

WORKDIR /code

COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git

RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

COPY ../app /code/app

COPY ../migrations /code/migrations

COPY ../alembic.ini /code/alembic.ini

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
