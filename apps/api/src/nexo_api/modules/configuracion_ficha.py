"""Configuración de la ficha de atributos por tipo de parte desde la consola (ADR 0019, ADR 0029). Permiso CONFIGURAR_FICHA.

- Los atributos de AutoCare (PAdb) que admite el tipo de parte: habilitar, obligatorio, etiqueta, grupo, orden y precarga desde SAP.
- Campos propios de Nexo, que AutoCare no tiene: número (con o sin medida en mm), lista de opciones, texto libre o sí/no. Sus
  códigos empiezan en 1 000 000 y la carga de AutoCare no los toca. Por ahora solo viven en Nexo.
- Homologación de valores de SAP a opciones (`meta.valor_sap_pies`) y traducción al español de los valores de PIES.

La configuración no cambia lo ya capturado: un atributo deshabilitado deja de mostrarse, pero sus valores se conservan.
"""

from enum import StrEnum
from typing import Annotated

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import Connection, text

from ..auth.dependencias import Permiso, Usuario, requiere_permiso
from ..auth.registro import fijar_actor
from ..core.bd import Conexion
from ..core.errores import Problema

router = APIRouter(prefix="/configuracion", tags=["configuracion"])
Configurador = Annotated[Usuario, Depends(requiere_permiso(Permiso.CONFIGURAR_FICHA))]

PROPIO_DESDE = 1_000_000


class GrupoAtributo(StrEnum):
    MEDIDAS = "MEDIDAS"
    MATERIALES = "MATERIALES"
    CONSTRUCCION = "CONSTRUCCION"
    CONEXIONES = "CONEXIONES"
    INCLUYE = "INCLUYE"
    OTROS = "OTROS"


class TipoPropio(StrEnum):
    NUMERO = "NUMERO"
    LISTA = "LISTA"
    TEXTO = "TEXTO"
    SI_NO = "SI_NO"


class ConversionSap(StrEnum):
    NUMERO = "NUMERO"
    NUMERO_EN_TEXTO = "NUMERO_EN_TEXTO"
    PARTE_DE_MEDIDA = "PARTE_DE_MEDIDA"
    LISTA = "LISTA"
    TEXTO = "TEXTO"
    SI_NO = "SI_NO"


# Qué conversiones de SAP sirven para cada clase de campo
_CONVERSIONES = {
    "NUMERO": {ConversionSap.NUMERO, ConversionSap.NUMERO_EN_TEXTO, ConversionSap.PARTE_DE_MEDIDA},
    "LISTA": {ConversionSap.LISTA},
    "TEXTO": {ConversionSap.TEXTO},
    "SI_NO": {ConversionSap.SI_NO},
}


# ---------------------------------------------------------------------------------------------------------------------------
# Modelos
# ---------------------------------------------------------------------------------------------------------------------------
class OpcionConfig(BaseModel):
    valid_value_id: int
    valor: str                       # PIES en inglés, o el texto de la opción de un campo propio
    valor_es: str | None             # traducción (solo en las de PIES)
    propia: bool
    obsoleta: bool
    en_uso: int                      # artículos de este tipo de parte con esa opción
    homologados: list[str]           # valores de SAP que se convierten en esta opción


class AtributoConfig(BaseModel):
    paid: int
    nombre: str                      # PAdb (inglés) o el nombre del campo propio
    etiqueta: str | None
    propio: bool
    tipo: str                        # NUMERO, LISTA, TEXTO o SI_NO (en AutoCare, deducido de PAdb)
    requiere_uom: bool               # medida: se captura en mm, cm o pulgadas y se guarda en mm
    habilitado: bool
    obligatorio: bool
    grupo: GrupoAtributo
    orden: int | None
    columna_sap: str | None
    conversion: ConversionSap | None
    parte: int | None
    obsoleto: bool
    en_uso: int                      # artículos de este tipo de parte con un valor
    opciones: list[OpcionConfig]


class FichaConfig(BaseModel):
    part_terminology_id: int
    categorias: list[str]            # categorías de SAP que usan este tipo de parte
    atributos: list[AtributoConfig]


class ColumnaSap(BaseModel):
    columna: str                     # columna de app.articulo
    campo_sap: str | None            # U_CoreMaterial…
    descripcion: str | None


class CambiosAtributo(BaseModel):
    habilitado: bool | None = None
    obligatorio: bool | None = None
    etiqueta: str | None = Field(None, max_length=60, description="Vacío vuelve al nombre de PAdb")
    grupo: GrupoAtributo | None = None
    orden: int | None = Field(None, ge=0, le=999)
    columna_sap: str | None = None
    conversion: ConversionSap | None = None
    parte: int | None = Field(None, ge=1, le=2)


class NuevoCampo(BaseModel):
    nombre: str = Field(min_length=2, max_length=60)
    tipo: TipoPropio
    grupo: GrupoAtributo = GrupoAtributo.OTROS
    medida: bool = Field(False, description="Solo NUMERO: es una medida (se captura en mm, cm o pulgadas y se guarda en mm)")
    opciones: list[str] = Field([], description="Solo LISTA: las opciones, en el orden en que se muestran")
    obligatorio: bool = False

    @field_validator("nombre")
    @classmethod
    def _sin_espacios(cls, v: str) -> str:
        return " ".join(v.split())


class TextoOpcion(BaseModel):
    valor: str = Field(min_length=1, max_length=60)


class Homologacion(BaseModel):
    valor_sap: str = Field(min_length=1, max_length=80)
    valid_value_id: int


class ValorSap(BaseModel):
    valor: str                       # como viene de SAP (ya en mayúsculas para comparar)
    articulos: int
    valid_value_id: int | None       # la opción a la que se homologa, si ya está


class Traduccion(BaseModel):
    valor_es: str | None = Field(None, max_length=80, description="Vacío o null quita la traducción")


# ---------------------------------------------------------------------------------------------------------------------------
# Lectura
# ---------------------------------------------------------------------------------------------------------------------------
_ATRIBUTOS = """
    select r.paid, r.nombre, r.etiqueta, r.propio, r.tipo::text as tipo, r.requiere_uom, r.habilitado, r.obligatorio,
           r.grupo::text as grupo, r.orden, r.columna_sap, r.conversion::text as conversion, r.parte, r.obsoleto_en is not null as obsoleto,
           (select count(*) from app.articulo_atributo t join app.articulo a on a.id = t.articulo_id
            where t.paid = r.paid and a.part_terminology_id = r.part_terminology_id) as en_uso,
           coalesce((select json_agg(json_build_object(
                       'valid_value_id', v.valid_value_id, 'valor', v.valor, 'valor_es', tr.valor_es, 'propia', v.propio,
                       'obsoleta', v.obsoleto_en is not null,
                       'en_uso', (select count(*) from app.articulo_atributo t join app.articulo a on a.id = t.articulo_id
                                  where t.paid = v.paid and t.valid_value_id = v.valid_value_id
                                    and a.part_terminology_id = v.part_terminology_id),
                       'homologados', coalesce((select json_agg(s.valor_sap order by s.valor_sap) from meta.valor_sap_pies s
                                                where s.paid = v.paid and s.valid_value_id = v.valid_value_id), '[]'))
                       order by case when v.propio then v.valid_value_id end, v.valor)
                     from meta.atributo_valor_permitido v left join meta.traduccion_valor tr using (valid_value_id)
                     where v.part_terminology_id = r.part_terminology_id and v.paid = r.paid), '[]') as opciones
    from meta.atributo_config r
    where r.part_terminology_id = :pt {filtro}
    order by not r.habilitado, r.orden nulls last, coalesce(r.etiqueta, r.nombre)
"""


def _tipo(f) -> str:
    if f.tipo:
        return f.tipo
    if f.opciones:
        return "LISTA"
    if f.requiere_uom or f.conversion in ("NUMERO", "NUMERO_EN_TEXTO", "PARTE_DE_MEDIDA"):
        return "NUMERO"
    return "TEXTO"


def _atributo(f) -> AtributoConfig:
    return AtributoConfig(
        paid=f.paid, nombre=f.nombre, etiqueta=f.etiqueta, propio=f.propio, tipo=_tipo(f), requiere_uom=f.requiere_uom,
        habilitado=f.habilitado, obligatorio=f.obligatorio, grupo=f.grupo, orden=f.orden, columna_sap=f.columna_sap,
        conversion=f.conversion, parte=f.parte, obsoleto=f.obsoleto, en_uso=f.en_uso, opciones=[OpcionConfig(**o) for o in f.opciones])


def _leer(c: Connection, pt: int, paid: int) -> AtributoConfig:
    f = c.execute(text(_ATRIBUTOS.format(filtro="and r.paid = :paid")), {"pt": pt, "paid": paid}).one_or_none()
    if f is None:
        raise Problema(404, "Ese atributo no existe para este tipo de parte")
    return _atributo(f)


def _columnas_sap(c: Connection) -> dict[str, ColumnaSap]:
    filas = c.execute(text("""
        select d.columna, d.campo_origen, d.descripcion from meta.diccionario_campo d
        join information_schema.columns i on i.table_schema = 'app' and i.table_name = 'articulo' and i.column_name = d.columna
        where d.esquema = 'app' and d.tabla = 'articulo' and d.fuente = 'SAP' order by d.columna""")).all()
    return {f.columna: ColumnaSap(columna=f.columna, campo_sap=f.campo_origen, descripcion=f.descripcion) for f in filas}


@router.get("/ficha/columnas-sap", response_model=list[ColumnaSap], summary="Columnas de SAP que pueden precargar un atributo")
def listar_columnas_sap(_: Configurador, c: Conexion) -> list[ColumnaSap]:
    return list(_columnas_sap(c).values())


@router.get("/ficha/{part_terminology_id}", response_model=FichaConfig,
            summary="Atributos del tipo de parte (AutoCare y propios) con su configuración, opciones y homologación")
def obtener_configuracion_ficha(part_terminology_id: int, _: Configurador, c: Conexion) -> FichaConfig:
    categorias = list(c.execute(text("select nombre from app.categoria where part_terminology_id_defecto = :pt order by nombre"),
                                {"pt": part_terminology_id}).scalars())
    filas = c.execute(text(_ATRIBUTOS.format(filtro="")), {"pt": part_terminology_id}).all()
    if not filas and not categorias:
        raise Problema(404, "Ese tipo de parte no está en Nexo")
    return FichaConfig(part_terminology_id=part_terminology_id, categorias=categorias, atributos=[_atributo(f) for f in filas])


# ---------------------------------------------------------------------------------------------------------------------------
# Configurar un atributo
# ---------------------------------------------------------------------------------------------------------------------------
@router.patch("/ficha/{part_terminology_id}/{paid}", response_model=AtributoConfig,
              summary="Habilitar, obligatorio, etiqueta, grupo, orden y precarga desde SAP de un atributo",
              responses={422: {"description": "Configuración no válida"}})
def configurar_atributo(part_terminology_id: int, paid: int, datos: CambiosAtributo, usuario: Configurador, c: Conexion
                        ) -> AtributoConfig:
    actual = _leer(c, part_terminology_id, paid)
    columnas = _columnas_sap(c)
    c.rollback()
    puestos = datos.model_fields_set
    nuevo = actual.model_dump() | {k: getattr(datos, k) for k in puestos}
    if "etiqueta" in puestos:
        nuevo["etiqueta"] = " ".join((datos.etiqueta or "").split()) or None
    if "habilitado" in puestos and not nuevo["habilitado"]:
        nuevo["obligatorio"] = False                       # deshabilitar quita lo obligatorio
    if nuevo["habilitado"] and actual.obsoleto and not actual.habilitado:
        raise Problema(422, "AutoCare ya no usa ese atributo", "No se puede habilitar un atributo obsoleto.")
    if nuevo["obligatorio"] and not nuevo["habilitado"]:
        raise Problema(422, "Solo un atributo habilitado puede ser obligatorio")
    # Precarga desde SAP: columna y conversión van juntas (sin columna, sin precarga)
    if "columna_sap" in puestos and not datos.columna_sap:
        nuevo |= {"columna_sap": None, "conversion": None, "parte": None}
    if nuevo["columna_sap"]:
        if nuevo["columna_sap"] not in columnas:
            raise Problema(422, "Esa columna no viene de SAP", f"«{nuevo['columna_sap']}» no es una columna de SAP del artículo.")
        if nuevo["conversion"] is None:
            raise Problema(422, "Falta cómo convertir el valor de SAP")
        if nuevo["conversion"] not in _CONVERSIONES[actual.tipo]:
            raise Problema(422, "Esa conversión no sirve para este atributo",
                           f"Un campo de tipo {actual.tipo} se precarga con: "
                           + ", ".join(sorted(x.value for x in _CONVERSIONES[actual.tipo])) + ".")
        if nuevo["conversion"] == ConversionSap.PARTE_DE_MEDIDA:
            if nuevo["parte"] not in (1, 2):
                raise Problema(422, "Falta qué parte de la medida", "1 = antes del «*», 2 = después.")
        else:
            nuevo["parte"] = None
    else:
        nuevo |= {"conversion": None, "parte": None}
    with c.begin():
        fijar_actor(c, usuario.id)
        c.execute(text("""
            update meta.atributo_config set habilitado = :habilitado, obligatorio = :obligatorio, etiqueta = :etiqueta,
              grupo = cast(:grupo as meta.grupo_atributo), orden = :orden, columna_sap = :columna_sap,
              conversion = cast(:conversion as meta.conversion_sap), parte = :parte, actualizado_en = now()
            where part_terminology_id = :pt and paid = :paid
        """), {k: (v.value if isinstance(v, StrEnum) else v) for k, v in nuevo.items()
               if k in {"habilitado", "obligatorio", "etiqueta", "grupo", "orden", "columna_sap", "conversion", "parte"}}
              | {"pt": part_terminology_id, "paid": paid})
    return _leer(c, part_terminology_id, paid)


# ---------------------------------------------------------------------------------------------------------------------------
# Campos propios
# ---------------------------------------------------------------------------------------------------------------------------
def _propio(c: Connection, pt: int, paid: int) -> AtributoConfig:
    a = _leer(c, pt, paid)
    if not a.propio:
        raise Problema(422, "Es un atributo de AutoCare", "Las opciones de AutoCare no se cambian en Nexo; solo se traducen.")
    return a


@router.post("/ficha/{part_terminology_id}/propios", response_model=AtributoConfig, status_code=201,
             summary="Crear un campo propio de Nexo (que no existe en AutoCare)",
             responses={409: {"description": "Ya hay un campo con ese nombre"}, 422: {"description": "Datos no válidos"}})
def crear_campo_propio(part_terminology_id: int, datos: NuevoCampo, usuario: Configurador, c: Conexion) -> AtributoConfig:
    obtener_configuracion_ficha(part_terminology_id, usuario, c)          # el tipo de parte existe
    c.rollback()
    opciones = [" ".join(o.split()) for o in datos.opciones if o.strip()]
    if datos.tipo == TipoPropio.LISTA and not opciones:
        raise Problema(422, "Una lista necesita opciones", "Escribe al menos una opción.")
    if datos.tipo != TipoPropio.LISTA and opciones:
        raise Problema(422, "Solo una lista lleva opciones")
    if len({o.upper() for o in opciones}) != len(opciones):
        raise Problema(422, "Hay opciones repetidas")
    if datos.medida and datos.tipo != TipoPropio.NUMERO:
        raise Problema(422, "Solo un número puede ser una medida")
    if c.execute(text("""select 1 from meta.atributo_config where part_terminology_id = :pt
                         and upper(coalesce(etiqueta, nombre)) = upper(:n)"""), {"pt": part_terminology_id, "n": datos.nombre}).first():
        c.rollback()
        raise Problema(409, "Ya hay un atributo con ese nombre", f"«{datos.nombre}» ya está en la ficha de este tipo de parte.")
    c.rollback()
    with c.begin():
        fijar_actor(c, usuario.id)
        paid = c.execute(text("""
            insert into meta.atributo_config (part_terminology_id, paid, nombre, etiqueta, tipo, requiere_uom, uom_defecto, habilitado,
                                              obligatorio, grupo, orden)
            values (:pt, nextval('meta.codigo_propio'), :n, :n, cast(:tipo as meta.tipo_atributo), :medida, :uom, true, :obl,
                    cast(:grupo as meta.grupo_atributo),
                    (select coalesce(max(orden), 0) + 1 from meta.atributo_config where part_terminology_id = :pt and habilitado))
            returning paid
        """), {"pt": part_terminology_id, "n": datos.nombre, "tipo": datos.tipo.value, "medida": datos.medida,
               "uom": "MM" if datos.medida else None, "obl": datos.obligatorio, "grupo": datos.grupo.value}).scalar_one()
        for o in opciones:
            c.execute(text("""insert into meta.atributo_valor_permitido (part_terminology_id, paid, valid_value_id, valor)
                              values (:pt, :paid, nextval('meta.codigo_propio'), :v)"""), {"pt": part_terminology_id, "paid": paid, "v": o})
    return _leer(c, part_terminology_id, paid)


@router.delete("/ficha/{part_terminology_id}/{paid}", status_code=204, summary="Borrar un campo propio que ningún artículo usa",
               responses={409: {"description": "Ya está en uso: se deshabilita en lugar de borrarse"}})
def borrar_campo_propio(part_terminology_id: int, paid: int, usuario: Configurador, c: Conexion) -> Response:
    a = _propio(c, part_terminology_id, paid)
    c.rollback()
    if a.en_uso:
        raise Problema(409, "Ese campo ya está en uso", f"{a.en_uso} artículos lo tienen: deshabilítalo en lugar de borrarlo.")
    with c.begin():
        fijar_actor(c, usuario.id)
        c.execute(text("delete from meta.valor_sap_pies where paid = :paid"), {"paid": paid})
        c.execute(text("delete from meta.atributo_valor_permitido where part_terminology_id = :pt and paid = :paid"),
                  {"pt": part_terminology_id, "paid": paid})
        c.execute(text("delete from meta.atributo_config where part_terminology_id = :pt and paid = :paid"),
                  {"pt": part_terminology_id, "paid": paid})
    return Response(status_code=204)


def _lista_propia(c: Connection, pt: int, paid: int) -> AtributoConfig:
    a = _propio(c, pt, paid)
    if a.tipo != "LISTA":
        raise Problema(422, "Ese campo no es una lista")
    return a


def _repetida(a: AtributoConfig, valor: str, salvo: int | None = None) -> None:
    if any(o.valor.upper() == valor.upper() and o.valid_value_id != salvo for o in a.opciones):
        raise Problema(409, "Esa opción ya existe", f"«{valor}» ya está en la lista.")


@router.post("/ficha/{part_terminology_id}/{paid}/opciones", response_model=AtributoConfig, status_code=201,
             summary="Agregar una opción a un campo propio de tipo lista")
def agregar_opcion(part_terminology_id: int, paid: int, datos: TextoOpcion, usuario: Configurador, c: Conexion) -> AtributoConfig:
    a = _lista_propia(c, part_terminology_id, paid)
    c.rollback()
    valor = " ".join(datos.valor.split())
    _repetida(a, valor)
    with c.begin():
        fijar_actor(c, usuario.id)
        c.execute(text("""insert into meta.atributo_valor_permitido (part_terminology_id, paid, valid_value_id, valor)
                          values (:pt, :paid, nextval('meta.codigo_propio'), :v)"""), {"pt": part_terminology_id, "paid": paid, "v": valor})
    return _leer(c, part_terminology_id, paid)


@router.patch("/ficha/{part_terminology_id}/{paid}/opciones/{valid_value_id}", response_model=AtributoConfig,
              summary="Cambiar el texto de una opción de un campo propio (los artículos que la tienen la conservan)")
def renombrar_opcion(part_terminology_id: int, paid: int, valid_value_id: int, datos: TextoOpcion, usuario: Configurador,
                     c: Conexion) -> AtributoConfig:
    a = _lista_propia(c, part_terminology_id, paid)
    c.rollback()
    if not any(o.valid_value_id == valid_value_id for o in a.opciones):
        raise Problema(404, "Esa opción no existe")
    valor = " ".join(datos.valor.split())
    _repetida(a, valor, salvo=valid_value_id)
    with c.begin():
        fijar_actor(c, usuario.id)
        c.execute(text("""update meta.atributo_valor_permitido set valor = :v
                          where part_terminology_id = :pt and paid = :paid and valid_value_id = :vv"""),
                  {"pt": part_terminology_id, "paid": paid, "vv": valid_value_id, "v": valor})
        c.execute(text("update meta.valor_sap_pies set valor_pies = :v where paid = :paid and valid_value_id = :vv"),
                  {"paid": paid, "vv": valid_value_id, "v": valor})
    return _leer(c, part_terminology_id, paid)


@router.delete("/ficha/{part_terminology_id}/{paid}/opciones/{valid_value_id}", response_model=AtributoConfig,
               summary="Quitar una opción de un campo propio que ningún artículo usa",
               responses={409: {"description": "La opción está en uso"}})
def quitar_opcion(part_terminology_id: int, paid: int, valid_value_id: int, usuario: Configurador, c: Conexion) -> AtributoConfig:
    a = _lista_propia(c, part_terminology_id, paid)
    c.rollback()
    o = next((o for o in a.opciones if o.valid_value_id == valid_value_id), None)
    if o is None:
        raise Problema(404, "Esa opción no existe")
    if o.en_uso:
        raise Problema(409, "Esa opción está en uso", f"{o.en_uso} artículos la tienen.")
    if len(a.opciones) == 1:
        raise Problema(422, "Una lista necesita al menos una opción")
    with c.begin():
        fijar_actor(c, usuario.id)
        c.execute(text("delete from meta.valor_sap_pies where paid = :paid and valid_value_id = :vv"), {"paid": paid, "vv": valid_value_id})
        c.execute(text("""delete from meta.atributo_valor_permitido
                          where part_terminology_id = :pt and paid = :paid and valid_value_id = :vv"""),
                  {"pt": part_terminology_id, "paid": paid, "vv": valid_value_id})
    return _leer(c, part_terminology_id, paid)


# ---------------------------------------------------------------------------------------------------------------------------
# Homologación SAP → opciones, y traducciones
# ---------------------------------------------------------------------------------------------------------------------------
@router.get("/ficha/{part_terminology_id}/{paid}/valores-sap", response_model=list[ValorSap],
            summary="Valores distintos que trae SAP en la columna de precarga del atributo, con cuántos artículos y su homologación")
def valores_sap(part_terminology_id: int, paid: int, _: Configurador, c: Conexion) -> list[ValorSap]:
    a = _leer(c, part_terminology_id, paid)
    if not a.columna_sap or a.columna_sap not in _columnas_sap(c):
        return []
    filas = c.execute(text(f"""
        select upper(btrim(x.{a.columna_sap}::text)) as valor, count(*) as articulos, s.valid_value_id
        from app.articulo x left join meta.valor_sap_pies s on s.paid = :paid and s.valor_sap = upper(btrim(x.{a.columna_sap}::text))
        where x.part_terminology_id = :pt and x.activo and nullif(btrim(x.{a.columna_sap}::text), '') is not null
        group by 1, 3 order by 2 desc, 1 limit 200"""), {"pt": part_terminology_id, "paid": paid}).all()
    return [ValorSap(valor=f.valor, articulos=f.articulos, valid_value_id=f.valid_value_id) for f in filas]


@router.put("/ficha/{part_terminology_id}/{paid}/homologacion", response_model=AtributoConfig,
            summary="Reemplazar la homologación de valores de SAP a opciones del atributo (vale para todos los tipos de parte)")
def homologar(part_terminology_id: int, paid: int, pares: list[Homologacion], usuario: Configurador, c: Conexion) -> AtributoConfig:
    a = _leer(c, part_terminology_id, paid)
    c.rollback()
    if a.tipo != "LISTA":
        raise Problema(422, "Solo se homologan atributos de lista")
    opciones = {o.valid_value_id: o.valor for o in a.opciones}
    vistos: set[str] = set()
    for p in pares:
        if p.valid_value_id not in opciones:
            raise Problema(422, "Esa opción no es del atributo", f"{p.valid_value_id} no es una opción de {a.etiqueta or a.nombre}.")
        clave = " ".join(p.valor_sap.split()).upper()
        if clave in vistos:
            raise Problema(422, "Un valor de SAP va a una sola opción", f"«{clave}» está repetido.")
        vistos.add(clave)
    with c.begin():
        fijar_actor(c, usuario.id)
        c.execute(text("delete from meta.valor_sap_pies where paid = :paid"), {"paid": paid})
        for p in pares:
            c.execute(text("insert into meta.valor_sap_pies (paid, valor_sap, valid_value_id, valor_pies) values (:paid, :s, :vv, :v)"),
                      {"paid": paid, "s": " ".join(p.valor_sap.split()).upper(), "vv": p.valid_value_id, "v": opciones[p.valid_value_id]})
    return _leer(c, part_terminology_id, paid)


@router.put("/traducciones/{valid_value_id}", status_code=204, summary="Traducir al español un valor de PIES (vacío la quita)",
            responses={404: {"description": "No es un valor de PIES"}})
def traducir_valor(valid_value_id: int, datos: Traduccion, usuario: Configurador, c: Conexion) -> Response:
    if valid_value_id >= PROPIO_DESDE:
        raise Problema(422, "Las opciones propias ya están en español", "Cambia su texto en lugar de traducirla.")
    if not c.execute(text("select 1 from meta.atributo_valor_permitido where valid_value_id = :vv"), {"vv": valid_value_id}).first():
        c.rollback()
        raise Problema(404, "No es un valor de PIES")
    c.rollback()
    valor = " ".join((datos.valor_es or "").split()) or None
    with c.begin():
        fijar_actor(c, usuario.id)
        if valor is None:
            c.execute(text("delete from meta.traduccion_valor where valid_value_id = :vv"), {"vv": valid_value_id})
        else:
            c.execute(text("""insert into meta.traduccion_valor (valid_value_id, valor_es) values (:vv, :v)
                              on conflict (valid_value_id) do update set valor_es = excluded.valor_es, actualizado_en = now()"""),
                      {"vv": valid_value_id, "v": valor})
    return Response(status_code=204)

