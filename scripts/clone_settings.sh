#!/bin/bash
set -e

# init settings.ini
EXAMPLE_SETTINGS_FILE="settings.example.ini"
OUTPUT_SETTINGS_FILE="settings.ini"

if [ ! -f "$EXAMPLE_SETTINGS_FILE" ]; then
    echo "Error: $EXAMPLE_SETTINGS_FILE not found. Are you running this from the project root?"
    exit 1
fi

if [ -f "$OUTPUT_SETTINGS_FILE" ]; then
    echo "Warning: $OUTPUT_SETTINGS_FILE already exists. Delete it first if you want to regenerate."
else
  cp "$EXAMPLE_SETTINGS_FILE" "$OUTPUT_SETTINGS_FILE"
fi

# init .env
EXAMPLE_ENV_FILE=".env.example"
OUTPUT_ENV_FILE=".env"

if [ ! -f "$EXAMPLE_ENV_FILE" ]; then
    echo "Error: $EXAMPLE_ENV_FILE not found. Are you running this from the project root?"
    exit 1
fi

if [ -f "$OUTPUT_ENV_FILE" ]; then
    echo "Warning: $OUTPUT_ENV_FILE already exists. Delete it first if you want to regenerate."
else
  cp "$EXAMPLE_ENV_FILE" "$OUTPUT_ENV_FILE"
fi
