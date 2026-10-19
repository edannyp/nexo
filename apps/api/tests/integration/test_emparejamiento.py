"""Emparejamiento: candidatos con puntaje y razones, comparación lado a lado, vincular (principal, traer sugerencias), cambiar la
principal y desvincular, con la regla de edición de la ficha (propuesta UX §6.4). El catálogo maestro es un doble."""

from decimal import Decimal as D

import psycopg
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from nexo_api.adapters.consolidacion import (
    AplicacionParte,
    AtributoParte,
    Candidato,
    DetalleParte,
    FuenteParte,
    ImagenParte,
    Medidas,
    NumeroParte,
    ResumenParte,
    normalizar_numero,
)
from nexo_api.auth.dependencias import cargar_usuario, usuario_actual
from nexo_api.core.bd import obtener_motor
from nexo_api.main import crear_app
from nexo_api.modules.emparejamiento import obtener_catalogo_maestro, obtener_firmador
from nexo_api.modules.vehiculos import obtener_vehiculos

from .apoyo import articulo, cargar, crear_usuario

URL = "/api/v1/articulos/RAD00188"


def resumen(pid, alto, largo, ancho, pt=2172, estado="ACTIVA", fusionada=None):
    return ResumenParte(pid, pt, "Radiator", f"Radiador {pid}", None, Medidas(D(alto), D(largo), D(ancho)), 2, 1, None, estado, fusionada)


def atr(paid, num=None, vv=None):
    return AtributoParte(paid, D(num) if num is not None else None, "MM" if num is not None and paid in (267, 268, 269) else None, vv,
                         None, None)


PARTES = {
    7001: DetalleParte(resumen(7001, 400, 518, 32), [NumeroParte("DPI", None, "945"), NumeroParte("OEM", "Toyota", "16400-35090")],
                       [atr(267, 400), atr(269, 518), atr(268, 32), atr(302, vv=203), atr(5061, 2), atr(305, vv=999)],
                       [AplicacionParte(13, 5, 7, None), AplicacionParte(14, None, None, None)],
                       [ImagenParte("DIAGRAMA", "https://diagramas.test/7001.png", None, None),
                        ImagenParte("FOTO", None, "rlt-diagramas", "fotos/7001.webp")],
                       [FuenteParte("JJ Radiator", "945", "https://jj.test/945")]),
    7002: DetalleParte(resumen(7002, 518, 400, 26), [NumeroParte("PROVEEDOR", "NRF", "50123")], [atr(267, 518), atr(269, 400)], [], [],
                       []),
    7003: DetalleParte(resumen(7003, 400, 518, 26, estado="FUSIONADA", fusionada=7001), [], [], [], [], []),
    7004: DetalleParte(resumen(7004, 400, 518, 26, pt=6708), [], [], [], [], []),
}


class MaestroFalso:
    def candidatos(self, pt, medidas, tolerancia, numeros, base_vehicle_ids, limite=60):
        nums, bvs = {normalizar_numero(n) for n in numeros}, set(base_vehicle_ids)
        return [Candidato(d.parte, [f"{n.tipo} {n.numero}" for n in d.numeros if normalizar_numero(n.numero) in nums],
                          len(bvs & {a.base_vehicle_id for a in d.aplicaciones}))
                for d in PARTES.values() if d.parte.part_terminology_id == pt and d.parte.estado == "ACTIVA"]

    def buscar(self, pt, q, tolerancia, limite=30):
        return [d.parte for d in PARTES.values() if q in (d.parte.descripcion or "")]

    def resumenes(self, ids):
        return {i: PARTES[i].parte for i in ids if i in PARTES}

    def detalle(self, parte_id):
        return PARTES.get(parte_id)


class FirmadorFalso:
    def firmar(self, objeto, bucket=None, segundos=3600):
        return f"https://minio.test/{bucket}/{objeto}?firma=1"


MAESTRO = MaestroFalso()


@pytest.fixture(scope="module")
def entorno(bd):
    with psycopg.connect(bd, autocommit=True) as c:
        cargar(c, [articulo("RAD00188", panal_alto=40, panal_alto_unidad=2, panal_largo=518, panal_largo_unidad=1, panal_ancho=26,
                            panal_ancho_unidad=1, numero_parte_proveedor="JJ-945")])
        ids = {u: crear_usuario(c, u, "OPERADOR") for u in ("op1", "op2")}
    partes = dict(p.split("=") for p in bd.split())
    motor = create_engine(f"postgresql+psycopg://postgres:postgres@{partes['host']}:5432/{partes['dbname']}")
    return motor, ids, bd


def como(entorno, usuario: str, maestro=MAESTRO) -> TestClient:
    motor, ids, _ = entorno
    with motor.connect() as c:
        u = cargar_usuario(c, ids[usuario])
    app = crear_app()
    app.dependency_overrides[obtener_motor] = lambda: motor
    app.dependency_overrides[usuario_actual] = lambda: u
    app.dependency_overrides[obtener_catalogo_maestro] = lambda: maestro
    app.dependency_overrides[obtener_firmador] = FirmadorFalso
    app.dependency_overrides[obtener_vehiculos] = lambda: None
    return TestClient(app)


def vincular(cli, version, parte_id, **kw):
    return cli.post(f"{URL}/partes", json={"version": version, "parte_id": parte_id, **kw})


def test_01_candidatos_con_puntaje_y_razones(entorno):
    e = como(entorno, "op1").get(f"{URL}/emparejamiento").json()
    assert not e["editable"] and e["catalogo_disponible"] and e["vinculadas"] == [] and e["part_terminology_id"] == 2172
    assert e["medidas"] == {"alto": "400.00", "largo": "518.00", "ancho": "26.00"}
    assert [(c["parte"]["parte_id"], c["puntaje"], c["invertida"]) for c in e["candidatos"]] == [(7001, 55, False), (7002, 50, True)]
    assert e["candidatos"][0]["razones"] == ["Alto y largo 400×518 iguales", "Ancho 32"]
    estrecho = como(entorno, "op1").get(f"{URL}/emparejamiento?tolerancia=5").json()
    assert [(c["parte"]["parte_id"], c["puntaje"]) for c in estrecho["candidatos"]] == [(7002, 50), (7001, 40)]
    assert estrecho["candidatos"][1]["razones"][-1] == "Ancho distinto (+6 mm)"


def test_02_comparacion_lado_a_lado(entorno):
    c = como(entorno, "op1").get(f"{URL}/emparejamiento/7001").json()
    filas = {f["etiqueta"]: f for f in c["filas"]}
    assert (filas["Alto"]["articulo"], filas["Alto"]["parte"], filas["Alto"]["coincide"]) == ("400 mm", "400 mm", True)
    assert (filas["Ancho"]["coincide"], filas["Ancho"]["diferencia"]) == (True, "+6 mm")
    assert (filas["Material panal"]["articulo"], filas["Material panal"]["parte"], filas["Material panal"]["coincide"]) == (
        None, "Aluminum (Aluminio)", None)
    assert [i["url"] for i in c["imagenes"]] == ["https://diagramas.test/7001.png", "https://minio.test/rlt-diagramas/fotos/7001.webp?firma=1"]
    assert [n["numero"] for n in c["numeros"]] == ["945", "16400-35090"] and c["fuentes"][0]["url"] == "https://jj.test/945"
    assert c["vehiculos"] == ["2 vehículos (catálogo de vehículos no disponible)"] and not c["vinculada"] and not c["invertida"]
    assert como(entorno, "op1").get(f"{URL}/emparejamiento/7002").json()["invertida"]
    assert como(entorno, "op1").get(f"{URL}/emparejamiento/9999").status_code == 404


def test_03_solo_quien_lo_tiene_reservado(entorno):
    op1, op2 = como(entorno, "op1"), como(entorno, "op2")
    assert op1.post(f"{URL}/asignacion").status_code == 200
    v = op1.get(f"{URL}/emparejamiento").json()["version"]
    r = vincular(op2, v, 7002)
    assert r.status_code == 409 and r.json()["detail"] == "op1 lo está trabajando."


def test_04_la_primera_queda_principal_y_cumple_el_requisito(entorno):
    op1 = como(entorno, "op1")
    e = op1.get(f"{URL}/emparejamiento").json()
    r = vincular(op1, e["version"], 7002, traer_sugerencias=False).json()
    assert [(p["parte_id"], p["es_principal"], p["confirmado_por"]) for p in r["vinculadas"]] == [(7002, True, "op1")]
    assert r["traidos"] is None and [c["parte"]["parte_id"] for c in r["candidatos"]] == [7001]   # ya no aparece como candidata
    requisitos = [x["codigo"] for x in op1.get(URL).json()["requisitos"]]
    assert "APLICACION_O_EMPAREJAMIENTO" not in requisitos


def test_05_vincular_principal_trae_sugerencias_sin_pisar(entorno):
    op1 = como(entorno, "op1")
    _, _, bd = entorno
    v = op1.get(f"{URL}/emparejamiento").json()["version"]
    r = vincular(op1, v, 7001, principal=True).json()
    assert [(p["parte_id"], p["es_principal"]) for p in r["vinculadas"]] == [(7001, True), (7002, False)]
    assert r["traidos"] == {"atributos": 5, "aplicaciones": 2}                  # 305 con un valor fuera de PIES se omite
    with psycopg.connect(bd) as c:
        filas = c.execute("""select paid, origen::text, parte_id, confirmado_por from app.articulo_atributo
                             where articulo_id = (select id from app.articulo where item_code = 'RAD00188') order by paid""").fetchall()
        assert {f[0] for f in filas} == {267, 268, 269, 302, 5061} and {(f[1], f[2], f[3]) for f in filas} == {("CONSOLIDACION", 7001, None)}
    again = vincular(op1, r["version"], 7001).json()                            # volver a vincular no duplica ni pisa
    assert again["traidos"] == {"atributos": 0, "aplicaciones": 0} and again["vinculadas"][0]["es_principal"]


def test_06_cambiar_principal_y_desvincular(entorno):
    op1 = como(entorno, "op1")
    _, _, bd = entorno
    v = op1.get(f"{URL}/emparejamiento").json()["version"]
    r = op1.post(f"{URL}/partes/principal", json={"version": v, "parte_id": 7002}).json()
    assert [(p["parte_id"], p["es_principal"]) for p in r["vinculadas"]] == [(7002, True), (7001, False)]
    r = op1.post(f"{URL}/partes/quitar", json={"version": r["version"], "parte_id": 7002}).json()
    assert [(p["parte_id"], p["es_principal"]) for p in r["vinculadas"]] == [(7001, True)]      # la otra pasa a principal
    r = op1.post(f"{URL}/partes/quitar", json={"version": r["version"], "parte_id": 7001}).json()
    assert r["vinculadas"] == []
    with psycopg.connect(bd) as c:                                              # sus sugerencias sin confirmar se van con ella
        assert c.execute("select count(*) from app.articulo_atributo where parte_id = 7001").fetchone()[0] == 0
        assert c.execute("select count(*) from app.articulo_aplicacion where parte_id = 7001").fetchone()[0] == 0


def test_07_validaciones(entorno):
    op1 = como(entorno, "op1")
    v = op1.get(f"{URL}/emparejamiento").json()["version"]
    fusionada = vincular(op1, v, 7003)
    assert fusionada.status_code == 422 and "se fusionó en la parte 7001" in fusionada.json()["detail"]
    otro = vincular(op1, v, 7004)
    assert otro.status_code == 422 and otro.json()["title"] == "La parte es de otro tipo"
    vieja = vincular(op1, v - 1, 7001)
    assert vieja.status_code == 409 and vieja.json()["title"] == "Otro usuario cambió este artículo"
    no_vinculada = op1.post(f"{URL}/partes/quitar", json={"version": v, "parte_id": 7001})
    assert no_vinculada.status_code == 404
    assert op1.get(f"{URL}/emparejamiento").json()["version"] == v


def test_08_sin_catalogo_maestro(entorno):
    sin = como(entorno, "op1", maestro=None)
    e = sin.get(f"{URL}/emparejamiento").json()
    assert not e["catalogo_disponible"] and e["candidatos"] == []
    assert sin.get("/api/v1/catalogo/partes?q=radiador").status_code == 503
    assert vincular(sin, e["version"], 7001).status_code == 503
    assert [p["parte_id"] for p in como(entorno, "op1").get("/api/v1/catalogo/partes?q=Radiador 700").json()] == [7001, 7002, 7003, 7004]


def test_09_auditado_con_el_usuario(entorno):
    _, ids, bd = entorno
    with psycopg.connect(bd) as c:
        actores = {r[0] for r in c.execute("select actor from audit.auditoria_evento where entidad = 'app.articulo_parte'")}
    assert str(ids["op1"]) in actores
