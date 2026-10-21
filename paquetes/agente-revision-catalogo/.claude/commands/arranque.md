Primera sesión en el agente de revisión del catálogo.

1. Lee `CLAUDE.md`, `contexto/arquitectura/contratos.md` (sección Agente de revisión del catálogo), la sección Verificación de
   `contexto/workflow-estados.md` y `contexto/arquitectura/modelo-consolidacion.md`.
2. Levanta las bases locales con `bash base-local/levantar.sh` y confirma que `app.fn_partes_emparejadas()` devuelve las partes 1, 2
   y 3 y que `app.fn_datos_emparejamiento` devuelve lo validado de cada artículo.
3. Resume el contrato en pocas líneas, cómo se decide qué cambio importa y cómo se arma la huella.
4. Propón el diseño del agente por pasos pequeños y pregúntame lo que esté en "Pendiente de acordar", una pregunta a la vez.
No escribas código hasta que confirme el plan.
