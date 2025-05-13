#!/bin/bash

# Generate self-signed certificate and key
openssl req -x509 -newkey rsa:4096 -keyout app/saml/stage/key.pem -out app/saml/stage/cert.pem -days 7300 -nodes -subj "/CN=stage"

echo "Self-signed certificate and key generated in the app/saml/stage directory."
