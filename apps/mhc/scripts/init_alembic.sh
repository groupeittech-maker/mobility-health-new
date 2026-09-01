#!/bin/bash

# Script to initialize Alembic for the project

echo "Initializing Alembic..."

# Check if alembic directory exists
if [ ! -d "alembic" ]; then
    echo "Creating alembic directory structure..."
    alembic init alembic
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Please create one from .env.example"
fi

# Create initial migration
echo "Creating initial migration..."
alembic revision --autogenerate -m "Initial migration"

echo "Alembic initialized successfully!"
echo "To apply migrations, run: alembic upgrade head"


















