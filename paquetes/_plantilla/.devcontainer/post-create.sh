#!/usr/bin/env bash
set -euo pipefail
cd /workspace
[ -f .env ] || cp .env.example .env
uv sync
echo "Listo. Primera sesión: abre Claude Code y ejecuta /arranque"
