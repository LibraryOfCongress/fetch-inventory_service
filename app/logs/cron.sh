#!/bin/sh

# Start the cron service for log rotation
service cron start

# Execute the CMD from the Containerfile to start the FastAPI app
exec "$@"
