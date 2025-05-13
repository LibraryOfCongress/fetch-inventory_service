#!/bin/bash

# Generate self-signed certificate and key
openssl req -x509 -newkey rsa:4096 -keyout app/saml/develop/key.pem -out app/saml/develop/cert.pem -days 7300 -nodes -subj "/CN=develop"

echo "Self-signed certificate and key generated in the app/saml/develop directory."
