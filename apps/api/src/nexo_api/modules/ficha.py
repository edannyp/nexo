"""Ficha de atributos del artículo (propuesta UX §6.4 "Pestaña Ficha", ADR 0019).

- Lectura: los atributos habilitados del tipo de parte, agrupados y en orden, con el valor de SAP como referencia, el valor en Nexo
  (sugerido o confirmado), las opciones de PIES traducidas y lo que falta.
- Guardado (botón Guardar, decisión UX 1): todos los cambios de la pestaña juntos, solo por quien tiene la reserva, en Pendiente o
  Rechazado, con la versión que ve el usuario. Todo lo que se guarda queda confirmado por él.
"""

import re
from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from fastapi import APIRouter
from pydantic import BaseModel, Field, model_validator
from sqlalchemy import Connection, text

from ..auth.dependencias import Usuario, UsuarioActual
from ..auth.registro import fijar_actor
from ..core.bd import Conexion
from ..core.errores import Problema
from ..core.negocio import reglas_de_negocio

router = APIRouter(prefix="/articulos/{item_code}/ficha", tags=["ficha"])

ESTADOS_EDITABLES = {"PENDIENTE", "RECHAZADO"}
_IDENTIFICADOR = re.compile(r"^[a-z_][a-z0-9_]*$")


class TipoCampo(StrEnum):
    NUMERO = "numero"
    LISTA = "lista"
    TEXTO = "texto"


class Opcion(BaseModel):
    valid_value_id: int
    valor: str              # PIES (inglés)
    valor_es: str | None    # traducción, si existe


class ValorAtributo(BaseModel):
    valor_num: Decimal | None = None
    uom_code: str | None = None
    valid_value_id: int | None = None
    valor_texto: str | None = None


class AtributoFicha(BaseModel):
    paid: int
    etiqueta: str
    nombre_pies: str
    grupo: str
    obligatorio: bool
    tipo: TipoCampo
    requiere_uom: bool
    uom_defecto: str | None
    opciones: list[Opcion]
    sugerencias: list[str]           # para texto libre: valores ya usados en SAP en este tipo de parte
    valor_sap: str | None            # el dato de SAP tal cual (referencia, solo lectura)
    valor: ValorAtributo | None      # el valor en Nexo
    origen: str | None               # SAP, MANUAL, CONSOLIDACION, HEREDADO_EQUIVALENTE
    confirmado: bool
    confirmado_por: str | None
    confirmado_en: datetime | None


class Ficha(BaseModel):
    version: int
    editable: bool
    razon_no_editable: str | None
    atributos: list[AtributoFicha]


class Cambio(ValorAtributo):
    paid: int

    @model_validator(mode="after")
    def un_solo_valor(self) -> "Cambio":
        if sum(v is not None for v in (self.valor_num, self.valid_value_id, self.valor_texto)) != 1:
            raise ValueError("Cada atributo lleva exactamente un valor: número, opción de la lista o texto.")
        if self.valor_texto is not None and not self.valor_texto.strip():
            raise ValueError("El texto no puede estar vacío.")
        return self


class Guardado(BaseModel):
    version: int = Field(description="Versión del artículo que ve el usuario: si otro lo cambió, responde 409")
    cambios: list[Cambio] = []
    quitar: list[int] = Field([], description="paid de los atributos que se dejan sin valor")


def _editable(a, usuario: Usuario) -> str | None:
    """None si el usuario puede editar; si no, la razón para mostrarla."""
    if not a.activo:
        return "El artículo está inactivo."
    if a.estado not in ESTADOS_EDITABLES:
        return "La ficha solo se edita en Pendiente o Rechazado."
    if not (a.asignado_a == usuario.id and a.reservado):
        return "Toma el artículo para editar la ficha." if not a.reservado else f"{a.reservado_por} lo está trabajando."
    return None


def _articulo(c: Connection, item_code: str, bloquear: bool = False):
    a = c.execute(text(f"""
        select a.*, a.estado::text as estado, coalesce(a.asignado_hasta > now(), false) as reservado, u.nombre as reservado_por
        from app.articulo a left join app.usuario u on u.id = a.asignado_a
        where a.item_code = upper(:ic) {'for update of a' if bloquear else ''}
    """), {"ic": item_code}).one_or_none()
    if a is None:
        raise Problema(404, "El artículo no existe")
    return a


def _texto_sap(v: object) -> str | None:
    if v is None:
        return None
    if isinstance(v, Decimal):
        return format(v.normalize(), "f")
    return str(v)


def cargar_ficha(c: Connection, item_code: str, usuario: Usuario) -> Ficha:
    a = _articulo(c, item_code)
    c.rollback()  # termina la lectura: la precarga va en su propia transacción y se confirma
    if a.activo and a.estado in ESTADOS_EDITABLES:
        # Sugerencias desde SAP (idempotente: solo agrega las que faltan, nunca pisa lo capturado)
        with c.begin():
            c.execute(text("select set_config('app.usuario_id', 'PROCESO:PRECARGA_SAP', true)"))
            c.execute(text("select app.fn_precargar_atributos_sap(:id)"), {"id": a.id})
    filas = c.execute(text("""
        select r.paid, coalesce(r.etiqueta, r.nombre) as etiqueta, r.nombre as nombre_pies, r.grupo::text as grupo, r.obligatorio,
               r.requiere_uom, r.uom_defecto, r.columna_sap, r.conversion::text as conversion,
               t.valor_num, t.uom_code, t.valid_value_id, t.valor_texto, t.origen::text as origen,
               t.confirmado_por is not null as confirmado, u.nombre as confirmado_por, t.confirmado_en,
               coalesce((select json_agg(json_build_object('valid_value_id', v.valid_value_id, 'valor', v.valor, 'valor_es', tr.valor_es)
                                         order by v.valor)
                         from meta.atributo_valor_permitido v left join meta.traduccion_valor tr using (valid_value_id)
                         where v.part_terminology_id = r.part_terminology_id and v.paid = r.paid), '[]') as opciones
        from meta.atributo_config r
        left join app.articulo_atributo t on t.articulo_id = :id and t.paid = r.paid
        left join app.usuario u on u.id = t.confirmado_por
        where r.part_terminology_id = :pt and r.habilitado
        order by r.orden nulls last, r.paid
    """), {"id": a.id, "pt": a.part_terminology_id}).all()

    columnas = set(a._mapping.keys())
    atributos = []
    for f in filas:
        col = f.columna_sap if f.columna_sap and _IDENTIFICADOR.match(f.columna_sap) and f.columna_sap in columnas else None
        if f.opciones:
            tipo = TipoCampo.LISTA
        elif f.conversion in ("NUMERO", "NUMERO_EN_TEXTO", "PARTE_DE_MEDIDA") or f.requiere_uom:
            tipo = TipoCampo.NUMERO
        else:
            tipo = TipoCampo.TEXTO
        sugerencias = []
        if tipo == TipoCampo.TEXTO and col:
            sugerencias = list(c.execute(text(f"""
                select {col}::text from app.articulo where part_terminology_id = :pt and {col} is not null
                group by 1 order by count(*) desc limit 30"""), {"pt": a.part_terminology_id}).scalars())
        hay_valor = any(x is not None for x in (f.valor_num, f.valid_value_id, f.valor_texto))
        atributos.append(AtributoFicha(
            paid=f.paid, etiqueta=f.etiqueta, nombre_pies=f.nombre_pies, grupo=f.grupo, obligatorio=f.obligatorio, tipo=tipo,
            requiere_uom=f.requiere_uom, uom_defecto=f.uom_defecto, opciones=[Opcion(**o) for o in f.opciones], sugerencias=sugerencias,
            valor_sap=_texto_sap(a._mapping[col]) if col else None,
            valor=ValorAtributo(valor_num=f.valor_num, uom_code=f.uom_code, valid_value_id=f.valid_value_id,
                                valor_texto=f.valor_texto) if hay_valor else None,
            origen=f.origen, confirmado=f.confirmado, confirmado_por=f.confirmado_por, confirmado_en=f.confirmado_en,
        ))
    razon = _editable(a, usuario)
    return Ficha(version=a.version, editable=razon is None, razon_no_editable=razon, atributos=atributos)


@router.get("", response_model=Ficha, summary="Ficha de atributos del artículo (con las sugerencias de SAP)")
def obtener_ficha(item_code: str, usuario: UsuarioActual, c: Conexion) -> Ficha:
    return cargar_ficha(c, item_code, usuario)


@router.put("", response_model=Ficha, summary="Guardar la ficha (botón Guardar): todo lo guardado queda confirmado",
            responses={409: {"description": "Versión distinta, no reservado o estado no editable"},
                       422: {"description": "Valor no válido para PIES"}})
def guardar_ficha(item_code: str, datos: Guardado, usuario: UsuarioActual, c: Conexion) -> Ficha:
    with c.begin():
        fijar_actor(c, usuario.id)
        a = _articulo(c, item_code, bloquear=True)
        razon = _editable(a, usuario)
        if razon:
            raise Problema(409, "No puedes editar la ficha ahora", razon)
        if a.version != datos.version:
            raise Problema(409, "Otro usuario cambió este artículo", "Recarga para ver los cambios antes de guardar.")
        for cambio in datos.cambios:
            nuevo = cambio.model_dump(exclude={"paid"})
            actual = c.execute(text("""select valor_num, uom_code, valid_value_id, valor_texto from app.articulo_atributo
                                       where articulo_id = :a and paid = :p"""), {"a": a.id, "p": cambio.paid}).one_or_none()
            with reglas_de_negocio():
                if actual is not None and dict(actual._mapping) == nuevo:
                    # Mismo valor (p. ej. aceptar lo sugerido por SAP): se confirma conservando su origen
                    c.execute(text("""update app.articulo_atributo set confirmado_por = :u, confirmado_en = now()
                                      where articulo_id = :a and paid = :p"""), {"a": a.id, "p": cambio.paid, "u": usuario.id})
                else:
                    c.execute(text("""
                        insert into app.articulo_atributo (articulo_id, paid, valor_num, uom_code, valid_value_id, valor_texto,
                                                           origen, confirmado_por, confirmado_en)
                        values (:a, :p, :valor_num, :uom_code, :valid_value_id, :valor_texto, 'MANUAL', :u, now())
                        on conflict (articulo_id, paid) do update set valor_num = excluded.valor_num, uom_code = excluded.uom_code,
                          valid_value_id = excluded.valid_value_id, valor_texto = excluded.valor_texto, origen = 'MANUAL',
                          confirmado_por = excluded.confirmado_por, confirmado_en = excluded.confirmado_en
                    """), {"a": a.id, "p": cambio.paid, "u": usuario.id, **nuevo})
        if datos.quitar:
            c.execute(text("delete from app.articulo_atributo where articulo_id = :a and paid = any(:p)"), {"a": a.id, "p": datos.quitar})
        c.execute(text("update app.articulo set version = version + 1, actualizado_en = now() where id = :a"), {"a": a.id})
    return cargar_ficha(c, item_code, usuario)
