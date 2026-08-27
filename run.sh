#!/bin/zsh
# Launch Multi-Tofu. Run this from Terminal.app so macOS attributes the
# Accessibility permission to a stable app.
cd "$(dirname "$0")"
exec ./.venv/bin/python -m multitofu "$@"
