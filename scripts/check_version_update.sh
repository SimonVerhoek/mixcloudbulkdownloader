#!/bin/sh
set -eu

latest_tag=$(git describe --tags "$(git rev-list --tags --max-count=1)")
poetry_version=$(poetry version --short)
spec_version=$(grep app.spec -e "(?<=^APP_VERSION = ')(.*)(?=')" -Po)

echo "Most recent tag found: ${latest_tag}, current Poetry version: ${poetry_version}, current app.spec version: ${spec_version}"

if [ "$poetry_version" = "$latest_tag" ]; then
  echo "User forgot to commit version bump in pyproject.toml! Exiting with error..."
  exit 1
elif [ "$spec_version" = "$latest_tag" ]; then
  echo "User forgot to commit version bump in app.spec! Exiting with error..."
  exit 1
else
  echo "User bumped version from ${latest_tag} to ${poetry_version}"
fi
