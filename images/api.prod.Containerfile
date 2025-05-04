# Stage 1: Requirements stage
FROM python:3.11.4-slim AS requirements-stage

WORKDIR /tmp

RUN pip install poetry==1.6.1

COPY pyproject.toml ../poetry.lock* /tmp/

COPY .env /tmp/

RUN poetry export -f requirements.txt --output requirements.txt --without-hashes

# Stage 2: Build the actual image
FROM python:3.11.4-slim

# Install Java, Graphviz, pg tools
RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y \
        git \
        openjdk-17-jdk \
        graphviz \
        postgresql-client && \
        # gcc \
        # g++ \
        # make \
        # libxml2-dev \
        # libxslt-dev \
        # libxmlsec1-dev \
        # libxmlsec1-openssl \
        # pkg-config && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy Python requirements from the first stage
COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

# COPY --from=requirements-stage /tmp/.env /code/.env

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt
    # pip install --no-cache-dir --force-reinstall lxml xmlsec

# Copy your application code
COPY app /code/app
COPY --from=requirements-stage /tmp/.env /code/app/config/.env
COPY migrations /code/migrations
COPY alembic.ini /code/alembic.ini

# Add SchemaSpy
# snapshot release fixes graphiz warnings. Update when official release.
ADD schemaspy/schemaspy-7.0.0-SNAPSHOT.jar /code/schemaspy.jar
ADD schemaspy/postgresql-42.7.0.jar /code/postgresql.jar

# Ready check could be used in the future. Not needed in deployed atm
# COPY schemaspy/db-ready-check.sh /code/db-ready-check.sh
# RUN chmod +x /code/db-ready-check.sh

# Generate self-signed certs for SSO over develop
# RUN app/saml/stage/gen_self_signed_certs.sh

# Expose the application port
EXPOSE 8001

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

# workers = 2 * cpu_cores + 1
CMD ["gunicorn", "app.main:app", \
    "-k", "uvicorn.workers.UvicornWorker", \
    "--workers", "5", "--bind", "0.0.0.0:8001", \
    "--max-requests", "10000", \
    "--max-requests-jitter", "5000"]
# CMD ["fastapi", "run", "app.main:app", "--bind", "0.0.0.0:8001", "--workers", "2"]
