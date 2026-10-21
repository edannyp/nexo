# Paquetes de arranque para los procesos externos

Nexo define contratos con procesos que construyen otros equipos (`architecture/datos/contratos.md`). Para cada uno, este directorio
arma un **repositorio inicial** con su `CLAUDE.md`, devcontainer con la memoria de Claude persistente, el contexto de gobernanza que
le toca y una base local igual a la de producción.

| Paquete | Proceso | Escribe en |
|---|---|---|
| `etl-sap` | ETL de entrada: SAP Business One → Nexo | `staging` de `nexo` (`10.10.60.6`) |
| `catalogo-maestro` | Carga del catálogo maestro: diagramas y scraping → Consolidación | `consolidacion_articulos` (`10.10.60.6`) |
| `ia-vehiculos` | IA con búsqueda web: vehículos fuera de AutoCare | `mercado_externo` (`10.10.60.6`) |
| `agente-revision-catalogo` | Agente de IA: cambios del catálogo maestro → verificaciones de Nexo | funciones de `nexo` (`10.10.60.6`) |

```bash
uv run paquetes/armar.py            # todos → entregables/<paquete>/ y entregables/<paquete>.zip
uv run paquetes/armar.py etl-sap    # uno
```

- Lo propio de cada paquete (instrucciones, scripts) está en `paquetes/<paquete>/`; lo común en `paquetes/_plantilla/`.
- La documentación de gobernanza **se copia del repositorio al armar**: cuando cambie un contrato, una migración o un ADR, se
  vuelven a armar y entregar los paquetes afectados. `entregables/` no se versiona.
