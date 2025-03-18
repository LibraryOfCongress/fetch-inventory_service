# Stage 1: Requirements stage
FROM python:3.11.4-slim AS requirements-stage

WORKDIR /tmp

RUN pip install poetry==1.6.1

COPY pyproject.toml poetry.lock* /tmp/

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
        postgresql-client \
        gcc \
        g++ \
        make \
        libxml2-dev \
        libxslt-dev \
        libxmlsec1-dev \
        libxmlsec1-openssl \
        pkg-config && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

WORKDIR /code

# Copy Python requirements from the first stage
COPY --from=requirements-stage /tmp/requirements.txt /code/requirements.txt

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt && \
    pip install --no-cache-dir --force-reinstall lxml xmlsec

# Copy your application code
COPY app /code/app
COPY migrations /code/migrations
COPY alembic.ini /code/alembic.ini

# Add SchemaSpy
# snapshot release fixes graphiz warnings. Update when official release.
ADD schemaspy/schemaspy-7.0.0-SNAPSHOT.jar /code/schemaspy.jar
ADD schemaspy/postgresql-42.7.0.jar /code/postgresql.jar

# Wait for db container before starting api
COPY schemaspy/db-ready-check.sh /code/db-ready-check.sh
RUN chmod +x /code/db-ready-check.sh

# Generate self-signed certs for SSO over localhost
RUN app/saml/local/gen_self_signed_certs.sh

# Expose the application port
EXPOSE 8001

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--ssl-keyfile", "app/saml/local/key.pem", "--ssl-certfile", "app/saml/local/cert.pem"]
