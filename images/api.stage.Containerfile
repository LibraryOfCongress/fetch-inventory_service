# Stage 1: Requirements stage
FROM python:3.11.4-slim as requirements-stage

WORKDIR /tmp

RUN pip install poetry

COPY pyproject.toml ../poetry.lock* /tmp/

COPY .env /tmp/

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

# COPY --from=requirements-stage /tmp/.env /code/.env

# Install dependencies
RUN pip install --no-cache-dir --upgrade -r /code/requirements.txt

# Copy your application code
COPY app /code/app
COPY --from=requirements-stage /tmp/.env /code/app/config/.env
COPY migrations /code/migrations
COPY alembic.ini /code/alembic.ini

# Add log rotation to container
COPY app/logs/log_rotate.conf /etc/logrotate.d/fetch
COPY app/logs/logrotate-cron.sh /etc/cron.daily/logrotate-cron
COPY app/logs/cron.sh /code/app/cron.sh
RUN chmod +x /etc/cron.daily/logrotate-cron
COPY app/logs/cronjob.txt /etc/cron.d/cronjob
RUN apt-get update && apt-get install -y logrotate cron
RUN crontab /etc/cron.d/cronjob

# Add SchemaSpy
# ADD schemaspy/schemaspy-6.2.4.jar /code/schemaspy.jar
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

# Start logrotate cron schedule
ENTRYPOINT ["/code/app/cron.sh"]

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"]

# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001", "--ssl-keyfile", "app/saml/stage/key.pem", "--ssl-certfile", "app/saml/stage/cert.pem"]
