# Stage 1: Requirements stage
FROM python:3.11.4-slim as requirements-stage

ENV SEED_FAKE_DATA=${SEED_FAKE_DATA_ARG:-false}

WORKDIR /tmp

RUN pip install poetry

COPY pyproject.toml poetry.lock* /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# Stage 2: Build the actual image
FROM python:3.11.4-slim

# Install Java, Graphviz, pg tools
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y git && \
    apt-get install -y default-jdk graphviz && \
    apt-get install -y postgresql-client && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy Python requirements from the first stage
COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy your application code
COPY app /code/app
COPY migrations /code/migrations
COPY alembic.ini /code/alembic.ini

# Add SchemaSpy
ADD schemaspy/schemaspy-6.2.4.jar /code/schemaspy.jar
ADD schemaspy/postgresql-42.7.0.jar /code/postgresql.jar

# Wait for db container before starting api
COPY schemaspy/db-ready-check.sh /code/db-ready-check.sh
RUN chmod +x /code/db-ready-check.sh

# Expose the application port
EXPOSE 8001

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]
