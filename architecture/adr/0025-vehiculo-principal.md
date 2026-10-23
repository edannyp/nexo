# 0025. Vehículo principal del artículo (ACES)

- **Estado:** Aceptada. Implementada en la migración 0016 (2026-10-23).
- **Fecha:** 2026-10-21

## Contexto
SAP guarda un solo vehículo por artículo (`U_Marca`, `U_Linea`, `U_anio1`–`U_anio2`), en texto libre y con códigos propios. En Nexo
el operador agrega aplicaciones ACES (vehículo base por año, submodelo y motor) sin distinguir cuál es la del artículo y cuáles son
adicionales. El negocio necesita ese vehículo principal estandarizado para devolverlo a SAP, armar el nombre del artículo, mostrarlo y
filtrar por él.

## Decisión
- Cada artículo tiene **un vehículo principal**: un grupo de sus aplicaciones (misma marca, modelo y submodelo en uno o varios
  años; el motor del grupo puede tener un `engine_config_id` distinto por rango de años) o un mismo equipo. Las demás aplicaciones
  son adicionales.
- **Obligatorio para enviar a validar**, confirmado (requisito `VEHICULO_PRINCIPAL`; reemplaza «al menos una aplicación o un
  emparejamiento»). El validador lo revisa con el resto (ADR 0012).
- El operador lo elige en la pestaña Aplicaciones: al agregar desde el selector (casilla marcada si aún no hay principal) o con
  «Principal» en un grupo. El Fabricado lo hereda del Importado como sugerencia.
- **Manda Nexo:** si el principal no coincide con SAP (marca y modelo por la homologación confirmada o, sin ella, por nombre; años
  que se solapen), la base abre el hallazgo de calidad `VEHICULO_DISTINTO` para corregir SAP. Se recalcula al cambiar el principal,
  el vehículo en SAP o una homologación, y se cierra solo cuando coinciden.
- Cada aplicación guarda una **copia** de marca, modelo y año del catálogo (AutoCare o MercadoExterno) para agrupar, filtrar y
  comparar sin consultar el catálogo.
- El proceso de salida (Nexo → SAP, otro proyecto) lee `app.v_vehiculo_principal`: el principal confirmado con sus códigos de SAP
  según las homologaciones confirmadas (`contratos.md`).
- La propuesta del **nombre del artículo** a partir del principal queda para otra decisión (reglas por categoría).

## Consecuencias
- Emparejar con el catálogo maestro ya no basta para enviar a validar: falta el principal.
- Explorar muestra el vehículo principal y filtra por «tiene principal» y por marca o modelo.
- Mientras una marca o un modelo de SAP no tenga homologación confirmada, el proceso de salida recibe su código en `null`.
