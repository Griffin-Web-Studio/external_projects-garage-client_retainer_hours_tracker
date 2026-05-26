#!/bin/bash
set -e

# init settings.ini
EXAMPLE_FILE="settings.example.ini"
OUTPUT_FILE="settings.ini"

if [ ! -f "$EXAMPLE_FILE" ]; then
    echo "Error: $EXAMPLE_FILE not found. Are you running this from the project root?"
    exit 1
fi

if [ -f "$OUTPUT_FILE" ]; then
    echo "Warning: $OUTPUT_FILE already exists. Delete it first if you want to regenerate."
else
  cp "$EXAMPLE_FILE" "$OUTPUT_FILE"
fi
