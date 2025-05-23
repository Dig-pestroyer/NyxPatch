#!/bin/bash

echo "Starting NyxPatcher..."
echo

# Check if Python is installed
if ! command -v python3 &> /dev/null && ! command -v python &> /dev/null; then
    echo "Error: Python is not installed or not in PATH."
    echo "Please install Python 3.7 or higher and try again."
    exit 1
fi

# Determine which Python command to use
PYTHON_CMD="python"
if command -v python3 &> /dev/null; then
    PYTHON_CMD="python3"
fi

# Run the module
$PYTHON_CMD -m data "$@"
EXIT_CODE=$?

if [ $EXIT_CODE -ne 0 ]; then
    echo
    echo "NyxPatcher encountered an error. Please check the logs above."
    echo "If the issue persists, please report it on the project's issue tracker."
    exit $EXIT_CODE
else
    echo
    echo "NyxPatcher completed successfully."
fi

