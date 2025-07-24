#!/bin/bash
# Script to create a .env file from env.example

# Check if env.example exists
if [ ! -f "env.example" ]; then
    echo "Error: env.example file not found!"
    exit 1
fi

# Check if .env already exists
if [ -f ".env" ]; then
    read -p ".env file already exists. Overwrite? (y/n): " answer
    if [[ $answer != "y" && $answer != "Y" ]]; then
        echo "Operation cancelled."
        exit 0
    fi
fi

# Copy the example file
cp env.example .env

echo "Created .env file from env.example."
echo "Please edit .env with your specific configuration values."

# Make the file executable
chmod +x create_env.sh 