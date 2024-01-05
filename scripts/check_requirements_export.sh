#!/bin/sh
set -eu

echo "Exporting Poetry requirements to test.txt..."
poetry export -f requirements.txt --output test.txt

if cmp "requirements.txt" "test.txt"; then
  echo "No changes found, requirements.txt is up to date!"
  exit 0
else
  echo "test.txt not equal to provided requirements.txt!
  Please make sure you commit a new export of the requirements by running the following command:

  $ poetry export -f requirements.txt --output requirements.txt"
  exit 1
fi
