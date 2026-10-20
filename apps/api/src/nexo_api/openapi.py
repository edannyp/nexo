"""Exporta el contrato OpenAPI para generar el cliente del frontend (packages/api-client).

Uso: uv run python -m nexo_api.openapi ../../packages/api-client/openapi.json
"""

import json
import sys
from pathlib import Path

from .main import crear_app

if __name__ == "__main__":
    destino = Path(sys.argv[1])
    destino.write_text(json.dumps(crear_app().openapi(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"OpenAPI → {destino}")
