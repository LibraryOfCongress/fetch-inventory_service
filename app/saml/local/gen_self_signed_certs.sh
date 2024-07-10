#!/bin/bash

# Generate self-signed certificate and key
openssl req -x509 -newkey rsa:4096 -keyout app/saml/local/key.pem -out app/saml/local/cert.pem -days 7300 -nodes -subj "/CN=localhost"

echo "Self-signed certificate and key generated in the app/saml/local directory."
