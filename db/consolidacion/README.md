# Consolidación — contrato para el proceso de carga

`articulos_consolidacion` es el **catálogo maestro** de piezas del mercado: `db_diagrams` + todos los proveedores scrapeados,
estandarizado con AutoCare (ADR 0009, 0011). **Este esquema gobierna**: el proceso de carga se adapta a él, no al revés.

| Archivo | Qué es |
|---|---|
| [migraciones/](migraciones/) | DDL versionado. La fuente de verdad del esquema |
| [ejemplos/ejemplo_carga.sql](ejemplos/ejemplo_carga.sql) | Tres diagramas reales de `db_diagrams` cargados según el contrato |
| [ejemplos/ejemplo_carga.md](ejemplos/ejemplo_carga.md) | El mismo ejemplo explicado paso a paso |
| [../pruebas/probar.py](../pruebas/probar.py) | Pruebas: lo que el contrato acepta y lo que rechaza |

## Diagrama

```mermaid
erDiagram
    fuente ||--o{ registro_fuente : "trae"
    corrida }o--|| fuente : "de"
    corrida ||--o{ registro_fuente : "escribe"
    parte ||--o{ registro_fuente : "consolida"
    parte ||--o{ parte_numero : ""
    parte ||--o{ parte_atributo : ""
    parte ||--o{ parte_aplicacion : ""
    parte ||--o{ aplicacion_sin_homologar : ""
    parte ||--o{ parte_imagen : ""
    parte ||--o{ conflicto : ""
    parte |o--o| parte : "fusionada_en"
    parte_aplicacion ||--o{ parte_aplicacion_region : ""
    marca_pieza ||--o{ parte_numero : "de quién es el número"
    registro_fuente ||--o{ parte_numero : "origen del dato"
    registro_fuente ||--o{ parte_atributo : "origen del dato"
    registro_fuente ||--o{ parte_aplicacion : "origen del dato"

    parte {
        bigint id PK "estable"
        int part_terminology_id "PCdb"
        enum estado "ACTIVA/FUSIONADA/DESCARTADA"
    }
    registro_fuente {
        bigint id PK
        smallint fuente_id
        text id_en_fuente "único por fuente"
        jsonb datos_crudos
        text hash_contenido
        bool vigente
    }
    parte_numero {
        enum tipo "OEM/DPI/PROVEEDOR/INTERCAMBIO"
        text numero
        text numero_norm "generado"
    }
    parte_atributo {
        int paid "PAdb"
        numeric valor_num
        text uom_code
        int valid_value_id
        text valor_original
    }
    parte_aplicacion {
        int base_vehicle_id "o equipment_base_id"
        int engine_config_id
        int transmission_id
        text vcdb_version
    }
```

Esquemas: `catalogo` (datos), `carga` (corridas), `ref` (copia de referencia de AutoCare, solo lectura para el proceso).

## Reglas del contrato

Las marcadas con 🔒 las hace cumplir la base: si el proceso las viola, la escritura falla con un error `CONTRATO: …`.

1. **Corridas.** Toda carga abre un `carga.corrida` (`EN_PROCESO`), escribe y la cierra (`COMPLETA` o `FALLIDA`) con sus conteos.
   🔒 No se puede escribir un `registro_fuente` en una corrida cerrada.
2. **Un registro por pieza y fuente.** `registro_fuente` se escribe con *upsert* por (`fuente_id`, `id_en_fuente`). 🔒 Único.
   Si `hash_contenido` (sha256 de `datos_crudos`) no cambió, no se toca nada y se cuenta en `sin_cambios`.
3. **Nada se pierde.** `datos_crudos` guarda **todo** lo que vino, sin transformar.
4. **Nunca DELETE.** 🔒 Lo que ya no publica la fuente queda `vigente = false`. Si dos partes son la misma, una pasa a
   `FUSIONADA` con `fusionada_en_id` (🔒 obligatorio); una parte errónea pasa a `DESCARTADA`. Los IDs de `parte` son estables
   porque Nexo los referencia.
5. **Trazabilidad.** Cada número, atributo, aplicación e imagen lleva el `registro_fuente_id` del que salió.
6. **Tipo de parte.** 🔒 `part_terminology_id` debe existir en PCdb (2172 Radiator, 6708 A/C Condenser, 12616 Intercooler…;
   ver `context/categorias.md`).
7. **Números.** `numero` tal como viene; `numero_norm` lo calcula la base (mayúsculas, solo `A-Z0-9`).
   🔒 OEM, PROVEEDOR e INTERCAMBIO requieren `marca_pieza_id`; DPI no. Si un campo trae varios números (`2531022050/22070`),
   se separan en filas y se expanden las abreviaturas, con menor `confianza`.
8. **Atributos PAdb.** 🔒 El `paid` debe estar asignado a ese tipo de parte. 🔒 Exactamente uno de `valor_num`,
   `valid_value_id` o `valor_texto`. 🔒 Si PAdb asigna unidades al atributo, `valor_num` lleva `uom_code`.
   Longitudes **en mm**. `valor_original` guarda el texto de origen (`335x608x16/22/26`).
   Medidas del panal: 267 Core Height, 269 Core Width (largo), 268 Core Thickness (ancho).
9. **Aplicaciones ACES.** 🔒 Exactamente uno de `base_vehicle_id` o `equipment_base_id`, y deben existir en AutoCare,
   o ser IDs ≥ 1 000 000 000 de MercadoExterno. Las regiones son opcionales (`parte_aplicacion_region`).
   Los calificadores que no se resuelvan a ID (motor en texto) van en `notas`.
10. **Lo que no se puede estandarizar no se inventa.** Un vehículo que no se pudo llevar a `base_vehicle_id` va a
    `aplicacion_sin_homologar` con su `motivo`. Un dato contradictorio va a `conflicto`. Si es un vehículo que falta en AutoCare,
    se registra en MercadoExterno (`fn_registrar_vehiculo`) y se usa el ID que devuelve.
11. **Imágenes.** Solo URL (o bucket y objeto de MinIO); no se copian.

## Cómo empezar (ambiente local)

```bash
uv run db/aplicar.py consolidacion --dsn "host=postgres dbname=mi_prueba user=postgres password=postgres"
uv run db/ref/cargar_ref.py consolidacion --destino "host=postgres dbname=mi_prueba user=postgres password=postgres"
psql "host=postgres dbname=mi_prueba user=postgres" -f db/consolidacion/ejemplos/ejemplo_carga.sql
```

## Pendiente de acordar
- **Reglas de deduplicación:** cuándo dos `registro_fuente` son la misma `parte` (mismo OEM con la misma marca, mismo DPI,
  mismas medidas ± tolerancia…) y con qué `vinculo_confianza`.
- Lista inicial de `fuente` y `marca_pieza` (con `brand_aaiaid` de PIES cuando exista).
