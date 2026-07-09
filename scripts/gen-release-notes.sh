#!/bin/sh
# Generates release notes for a RetainerTracker GitLab Release: the tagged
# version's CHANGELOG.md section (written by `cz bump` before the tag lands
# here) plus a quick-start docker run snippet.
# Usage: gen-release-notes.sh <tag> <registry-image> [project-url]
set -eu

TAG=$1
IMAGE=$2
PROJECT_URL=${3:-}

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
CHANGELOG="$SCRIPT_DIR/CHANGELOG.md"

if [ -f "$CHANGELOG" ]; then
  awk -v tag="$TAG" '
    $0 ~ "^## " tag { found=1; print; next }
    found && /^## / { exit }
    found { print }
  ' "$CHANGELOG"
fi

cat << EOF

---

## Quick start

\`\`\`bash
docker pull $IMAGE:$TAG

docker run -d -p 8000:8000 \\
  --env-file .env \\
  -e DB_DIR=/app/data \\
  -v retainer-data:/app/data \\
  -v \$(pwd)/settings.ini:/app/settings.ini:ro \\
  $IMAGE:$TAG
\`\`\`

Full production setup (nginx reverse proxy, TLS options, database backups):
see [docs/DEPLOYMENT.md](${PROJECT_URL:+$PROJECT_URL/-/blob/$TAG/}docs/DEPLOYMENT.md).
EOF
