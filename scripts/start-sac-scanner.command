#!/bin/zsh
set -e

cd "$(dirname "$0")/.."
python3 -m sac_scanner.server --port 8765
