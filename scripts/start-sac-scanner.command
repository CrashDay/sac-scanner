#!/bin/zsh
set -e

cd "/Users/tonyday/sac-scanner"
python3 -m sac_scanner.server --port 8765
