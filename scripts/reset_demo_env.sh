#!/bin/bash
# ==============================================================================
# GeoVault AI — SIH Demo Environment Reset & Fast Restore (Linux / macOS)
# ==============================================================================
set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$DIR"

echo "[!] Resetting GeoVault AI demonstration environment..."
echo "[*] Restarting containers..."
docker compose restart backend frontend worker

echo "[*] Waiting 5 seconds for services to initialize..."
sleep 5

echo "[*] Running fast SIH Smoke-Test..."
python3 scripts/smoke_test_demo.py

echo "[✓] Environment reset and certified ready for presentation!"
