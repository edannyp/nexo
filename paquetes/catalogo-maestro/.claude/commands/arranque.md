Primera sesión en la carga del catálogo maestro (Consolidación).

1. Lee `CLAUDE.md`, `db/consolidacion/README.md` (el contrato), `db/consolidacion/ejemplos/ejemplo_carga.md`,
   `contexto/arquitectura/modelo-consolidacion.md` y `contexto/fuentes/diagrams.md`.
2. Levanta la base local con `bash base-local/levantar.sh` y corre `uv run db/pruebas/probar.py --host postgres`.
3. Resume el contrato en pocas líneas y lo que Nexo necesita para emparejar (medidas, números, aplicaciones, imágenes, IDs estables).
4. Propón el plan por pasos pequeños (empezando por `db_diagrams`, la fuente propia) y pregúntame lo que esté en
   "Pendiente de acordar", una pregunta a la vez.
No escribas código hasta que confirme el plan.
