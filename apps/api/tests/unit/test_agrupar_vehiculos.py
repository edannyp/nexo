"""Configuraciones del selector: un renglón por submodelo + motor como se lee, aunque VCdb cambie el id del motor entre años."""

from nexo_api.adapters.vehiculos import Configuracion
from nexo_api.modules.vehiculos import agrupar


def cfg(anio, bv, sub, motor_id, motor="2.4L L4 2RZ-FE · Gasolina", regiones=("USA",)):
    return Configuracion(anio, bv, sub, "Base", motor_id, motor, "AUTOCARE", list(regiones))


def test_mismo_motor_con_ids_distintos_es_un_renglon():
    g = agrupar([cfg(1995, 1, 10, 100), cfg(1996, 2, 10, 101), cfg(1996, 2, 10, 101, regiones=("CAN",)),
                 cfg(1996, 2, 10, 300, motor="3.4L V6 5VZ-FE · Gasolina")], 1995, 1997)
    assert [(x.motor, [(a.anio, a.engine_config_id) for a in x.anios], x.completa) for x in g] == [
        ("2.4L L4 2RZ-FE · Gasolina", [(1995, 100), (1996, 101)], False), ("3.4L V6 5VZ-FE · Gasolina", [(1996, 300)], False)]


def test_completa_cuenta_anios_no_motores():
    g = agrupar([cfg(2000, 1, 10, 100), cfg(2000, 1, 10, 101), cfg(2001, 2, 10, 100)], 2000, 2001)
    assert len(g) == 1 and g[0].completa and len(g[0].anios) == 3
