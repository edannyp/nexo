"""Lo que AutoCare quita queda obsoleto en la copia de Nexo (migración 0014): no se asigna de nuevo, no se precarga desde SAP, no se
exige para enviar a revisión y no se ofrece en la ficha; lo que un artículo ya tenía se conserva y se sigue mostrando."""

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.auth.dependencias import cargar_usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app

from .apoyo import articulo, cargar, crear_usuario

FLUJO, VERTICAL, ALTO = 7448, 444, 267            # Tipo flujo · Down Flow · Core Height (obligatorio)


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00601", tipo_flujo="Down Flow"), articulo("RAD00602"), articulo("RAD00603")])
        uid = crear_usuario(c, "op1", "OPERADOR")
        ids = dict(c.execute("select item_code, id from app.articulo").fetchall())
        # RAD00602 ya tenía el valor antes de que AutoCare lo quitara
        c.execute("insert into app.articulo_atributo (articulo_id, paid, valid_value_id, origen) values (%s, %s, %s, 'MANUAL')",
                  (ids["RAD00602"], FLUJO, VERTICAL))
        c.execute("update meta.atributo_valor_permitido set obsoleto_en = now() where paid = %s and valid_value_id = %s", (FLUJO, VERTICAL))
        c.execute("update meta.atributo_config set obsoleto_en = now() where part_terminology_id = 2172 and paid = %s", (ALTO,))
    partes = dict(p.split("=") for p in bd.split())
    motor = create_engine(f"postgresql+psycopg://postgres:postgres@{partes['host']}:5432/{partes['dbname']}")
    return bd, motor, uid, ids


def ficha(entorno, item_code: str) -> dict:
    _, motor, uid, _ = entorno
    with motor.connect() as c:
        u = cargar_usuario(c, uid)
    app = crear_app()
    app.dependency_overrides[obtener_motor] = lambda: motor
    app.dependency_overrides[usuario_actual] = lambda: u
    return {a["paid"]: a for a in TestClient(app).get(f"/api/v1/articulos/{item_code}/ficha").json()["atributos"]}


def test_no_se_precarga_ni_se_ofrece_lo_obsoleto(entorno):
    f = ficha(entorno, "RAD00601")                                              # SAP dice "Down Flow", que ya es obsoleto
    assert f[FLUJO]["valor"] is None
    assert VERTICAL not in [o["valid_value_id"] for o in f[FLUJO]["opciones"]]
    assert ALTO not in f                                                        # atributo obsoleto y sin valor: no se muestra


def test_lo_que_ya_tenia_se_conserva_y_se_muestra(entorno):
    bd, _, _, ids = entorno
    f = ficha(entorno, "RAD00602")
    assert f[FLUJO]["valor"]["valid_value_id"] == VERTICAL and VERTICAL in [o["valid_value_id"] for o in f[FLUJO]["opciones"]]
    with psycopg.connect(bd, autocommit=True) as c:                             # actualizar otra cosa de esa fila sigue permitido
        c.execute("update app.articulo_atributo set valid_value_id = valid_value_id, origen = 'SAP' where articulo_id = %s and paid = %s",
                  (ids["RAD00602"], FLUJO))


def test_no_se_asigna_de_nuevo(entorno):
    bd, _, _, ids = entorno
    with psycopg.connect(bd, autocommit=True) as c:
        with pytest.raises(psycopg.errors.RaiseException, match="VALOR_NO_VALIDO"):
            c.execute("insert into app.articulo_atributo (articulo_id, paid, valid_value_id, origen) values (%s, %s, %s, 'MANUAL')",
                      (ids["RAD00603"], FLUJO, VERTICAL))
        with pytest.raises(psycopg.errors.RaiseException, match="ATRIBUTO_OBSOLETO"):
            c.execute("insert into app.articulo_atributo (articulo_id, paid, valor_num, uom_code, origen) values (%s, %s, 400, 'MM', 'MANUAL')",
                      (ids["RAD00603"], ALTO))


def test_un_obligatorio_obsoleto_ya_no_se_exige(entorno):
    bd, _, _, ids = entorno
    with psycopg.connect(bd) as c:
        faltan = c.execute("select app.fn_requisitos_por_validar(%s)", (ids["RAD00603"],)).fetchone()[0]
        nombre = c.execute("select nombre from meta.atributo_config where part_terminology_id = 2172 and paid = %s", (ALTO,)).fetchone()[0]
    assert f"ATRIBUTO:{nombre}" not in faltan and any(x.startswith("ATRIBUTO:") for x in faltan)
