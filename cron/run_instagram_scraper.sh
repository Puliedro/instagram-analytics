#!/bin/bash
# Path to the virtual environment activation script
VENV_PATH="/Users/pulie/Documents/instagram-analytics/.venv/bin/activate"

# Path to the Python script
SCRIPT_PATH="/Users/pulie/Documents/instagram-analytics/scrapper/scrapper_final.py"

# API key for Instagram API
export RAPIDAPI_KEY="d8ef3e4bdemshbaf48b985fb6385p16c7a1jsn896889469996"

# Activate the virtual environment
source $VENV_PATH

# Run the Python script for daily updates (last 365 days)
python $SCRIPT_PATH sabrinacarpenter 365 >> /Users/pulie/Documents/instagram-analytics/cron/daily_log.log 2>&1

# Check if today is the day of the week to run the weekly update (e.g., Sunday = 0)
if [ "$(date +%u)" = "7" ]; then
    # Run the Python script for weekly updates (since account creation, assumed to be 3000 days)
    python $SCRIPT_PATH sabrinacarpenter 3000 >> /Users/pulie/Documents/instagram-analytics/cron/weekly_log.log 2>&1
fi
