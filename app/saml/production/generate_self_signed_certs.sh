#!/bin/bash

# Generate self-signed certificate and key
openssl req -x509 -newkey rsa:4096 -keyout app/saml/production/key.pem -out app/saml/production/cert.pem -days 7300 -nodes -subj "/CN=production"

echo "Self-signed certificate and key generated in the app/saml/production directory."
