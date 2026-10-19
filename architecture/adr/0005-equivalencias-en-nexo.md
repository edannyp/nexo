# 0005. La equivalencia Fabricado ↔ Importado se gestiona en Nexo

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
Un Fabricado debe ser equivalente funcional de un Importado: mismas aplicaciones vehiculares y medidas.
Al explorar SAP (`SBO_LIVE_RLT`, 2026-10-15) se vio que:
- la línea se marca en la subcategoría (`OITM.U_SubCat` → `@IGT_CAT2.Name` = `IMPORTADOS` / `FABRICADOS`);
- no existe una relación confiable entre Fabricado e Importado: `@IGT_EQUIVALENCIAS`, `@IGT_ITEM_OEM(S)` y `OALI`
  están vacías, y `U_CodAnterior` solo apunta a un Importado en ~30 Fabricados y no siempre es el equivalente;
- SAP es **solo lectura** para este proyecto.

## Decisión
- Solo entran a Nexo artículos de subcategoría `IMPORTADOS` o `FABRICADOS` de las categorías en alcance
  (`context/categorias.md`). `MODIFICADOS`, `REPARADOS` y `USADOS` quedan fuera.
- La equivalencia vive en `app.articulo_equivalencia` (N:M) y la gestiona el operador desde la APP.
- El criterio de equivalencia sigue la **estandarización de AutoCare**: comparten aplicaciones vehiculares (ACES)
  y atributos/medidas (PIES). Las sugerencias pueden venir de la IA/Consolidación o de `U_CodAnterior`,
  pero solo cuentan cuando el operador las confirma.
- Nada se escribe en SAP. Si en el futuro la equivalencia debe regresar a SAP, lo hace el proceso de salida
  externo (contrato en `architecture/datos/contratos.md`).

## Consecuencias
- La APP necesita una pantalla o sección para buscar el Importado equivalente y confirmarlo, mostrando
  la comparación de aplicaciones y medidas.
- Un Fabricado puede heredar aplicaciones y diagrama de su Importado confirmado (regla a detallar).
- El contrato del ETL de entrada debe filtrar por categoría y subcategoría, o Nexo debe descartar el resto.
