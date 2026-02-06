#!/bin/bash
# Script to start the backend server
# This script starts the FastAPI backend server on port 8000

echo "Starting Mobility Health Backend Server..."

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Warning: .env file not found. Creating from env.example..."
    if [ -f "env.example" ]; then
        cp env.example .env
        echo "Please update .env with your configuration before continuing."
    else
        echo "Error: env.example file not found. Please create a .env file manually."
        exit 1
    fi
fi

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install/update dependencies
echo "Checking dependencies..."
pip install -q -r requirements.txt

# Check if database is accessible (optional)
echo "Starting backend server on http://localhost:8000"
echo "API Documentation will be available at http://localhost:8000/docs"
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

