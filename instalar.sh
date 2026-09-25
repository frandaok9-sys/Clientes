#!/usr/bin/env bash
# Crea el entorno virtual e instala las dependencias.
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
. .venv/bin/activate
pip install -q --upgrade pip
pip install -q -r requirements.txt
echo "Listo. Activa el entorno con:  source .venv/bin/activate"
