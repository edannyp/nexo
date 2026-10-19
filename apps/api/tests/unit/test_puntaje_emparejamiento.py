"""Puntaje de candidatos del catálogo maestro: medidas como par sin orden con tolerancia, números y vehículos en común."""

from decimal import Decimal as D

from nexo_api.adapters.consolidacion import Candidato, Medidas, ResumenParte
from nexo_api.modules.emparejamiento import puntuar


def candidato(alto, largo, ancho, numeros=(), comunes=0) -> Candidato:
    r = ResumenParte(1, 2172, "Radiator", "x", None, Medidas(D(alto), D(largo), D(ancho)), 0, 1, None)
    return Candidato(r, list(numeros), comunes)


ART = Medidas(D(400), D(518), D(26))


def test_medidas_iguales_y_numero():
    p, razones, inv = puntuar(ART, candidato(400, 518, 26, ["DPI 945"], 3), 10)
    assert (p, inv) == (100, False)
    assert razones == ["Alto y largo 400×518 iguales", "Ancho 26", "DPI 945 coincide", "3 vehículos en común"]


def test_invertidas_dentro_de_tolerancia_y_ancho_distinto():
    p, razones, inv = puntuar(ART, candidato(520, 398, 40), 10)
    assert (p, inv) == (35, True)
    assert razones == ["Alto y largo invertidos (520×398)", "Ancho distinto (+14 mm)"]
    assert puntuar(ART, candidato(520, 398, 32), 10)[0] == 50                   # 6 mm de ancho está dentro de la tolerancia


def test_fuera_de_tolerancia_no_suma():
    assert puntuar(ART, candidato(412, 518, 26), 10)[0] == 15
    assert puntuar(Medidas(), candidato(400, 518, 26), 10) == (0, [], False)
