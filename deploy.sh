#!/bin/bash
set -e

echo "Pulling latest code..."
git pull origin main

echo "Building containers..."
docker-compose build

echo "Restarting containers..."
docker-compose down
docker-compose up -d

echo "Deployment completed successfully."
