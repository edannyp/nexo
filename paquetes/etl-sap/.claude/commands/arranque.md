Primera sesión en el ETL de entrada SAP → Nexo.

1. Lee `CLAUDE.md` y, en este orden: `contexto/arquitectura/contratos.md` (sección ETL de entrada),
   `contexto/arquitectura/mapeo-fuentes.md`, `contexto/categorias.md` y `referencia/lote_sap_local.py`.
2. Levanta la base local con `bash base-local/levantar.sh` y confirma que existe `staging.articulo_sap` y el usuario `etl_entrada`.
3. Resume en pocas líneas el contrato tal como lo entendiste (foto completa: qué se envía, en qué orden, qué hace Nexo y qué no
   hace el ETL).
4. Propón el plan del ETL por pasos pequeños (lectura de SAP, escritura en staging, llamada a fn_procesar_staging, log del
   resultado, pruebas con la base local) y pregúntame lo que esté en "Pendiente de decidir", una pregunta a la vez.
No escribas código hasta que confirme el plan.
