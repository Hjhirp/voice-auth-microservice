#!/bin/bash

# Setup script for voice authentication microservice development environment

echo "Setting up conda environment for voice-auth-microservice..."

# Create conda environment from environment.yml
conda env create -f environment.yml

echo "Environment created successfully!"
echo ""
echo "To activate the environment, run:"
echo "conda activate voice-auth-microservice"
echo ""
echo "To deactivate when done, run:"
echo "conda deactivate"
echo ""
echo "To remove the environment later, run:"
echo "conda env remove -n voice-auth-microservice"