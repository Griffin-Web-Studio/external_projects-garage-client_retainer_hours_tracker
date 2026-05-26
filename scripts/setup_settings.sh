#!/bin/bash
set -e

# Install precommit hooks
pre-commit install
pre-commit install --hook-type commit-msg

# generate settings.ini file
./scripts/clone_settings.sh

# Run app migrations
python manage.py migrate
