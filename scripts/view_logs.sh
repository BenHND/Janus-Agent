#!/bin/bash
# Janus Logs Viewer Launcher
# Quick launcher script to view Janus logs

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
# Go to the parent directory (repository root)
REPO_ROOT="$SCRIPT_DIR/.."

# Check if we're in the right directory
if [ ! -f "$REPO_ROOT/main.py" ]; then
    echo "Error: Could not find main.py in $REPO_ROOT"
    echo "Please run this script from the Janus repository."
    exit 1
fi

# Launch the logs viewer
cd "$REPO_ROOT" && python main.py --logs
