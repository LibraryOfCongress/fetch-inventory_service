#!/bin/bash

# Generate self-signed certificate and key
openssl req -x509 -newkey rsa:4096 -keyout app/saml/test/key.pem -out app/saml/test/cert.pem -days 7300 -nodes -subj "/CN=test"

echo "Self-signed certificate and key generated in the app/saml/test directory."
