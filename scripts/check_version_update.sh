#!/bin/sh
set -eu

latest_tag=$(git describe --tags "$(git rev-list --tags --max-count=1)")
poetry_version=$(poetry version --short)

echo "Most recent tag found: ${latest_tag}, current Poetry version: ${poetry_version}"

if [ "$poetry_version" = "$latest_tag" ]; then
  echo "User forgot to commit version bump! Exiting with error..."
  exit 1
else
  echo "User bumped version from ${latest_tag} to ${poetry_version}"
fi
