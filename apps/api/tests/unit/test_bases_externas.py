"""Si una base externa no responde, el adaptador responde 503 (problem+json), no un error interno."""

import pytest
from sqlalchemy import create_engine

from nexo_api.adapters.consolidacion import Consolidacion
from nexo_api.adapters.vehiculos import AutoCare
from nexo_api.core.errores import Problema

CAIDA = "postgresql+psycopg://x:x@127.0.0.1:1/x?connect_timeout=1"


@pytest.mark.parametrize(("consulta", "titulo"), [
    (lambda: Consolidacion(create_engine(CAIDA)).buscar(None, "radiador", 10), "Catálogo maestro no disponible"),
    (lambda: AutoCare(create_engine(CAIDA)).submodelos([1]), "AutoCare no disponible"),
])
def test_base_caida_es_503(consulta, titulo):
    with pytest.raises(Problema) as e:
        consulta()
    assert (e.value.status, e.value.title) == (503, titulo)
