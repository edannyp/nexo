# Respuestas del equipo de Nexo al plan de la carga del catálogo maestro (2026-10-23)

Respuestas a `PREGUNTAS-NEXO.md` y observaciones a `PLAN.md`. Lo que cambió ya está en `CLAUDE.md`, en el contrato
(`db/consolidacion/README.md`) y en el ADR 0026 (sección *Precisiones*).

## Preguntas
1. **Agente de visión:** fuera de esta carga. `DB_DIAGRAMS` = `datos_maestros`, `compatibilidades`, `oem_codigos` y
   `proveedor_codigos`, mantenidos por PICsys y enriquecidos con JJ. `staging_radiadores` / `silver_*` no se leen.
2. **Cruce diagrama ↔ JJ:** decisión del negocio: **solo `jjradiator_cross_reference`**, sin vetar con `proveedor_codigos`.
   `confirmado` → misma parte, `vinculo_confianza` 1,0; `revisar_manual` → misma parte, 0,5, y conflicto `NUMERO_DUPLICADO` si
   el OEM no coincide. Además:
   - **Una unión ya hecha no se deshace sola.** Si en otra corrida el cruce cambia o desaparece, la parte no se toca: se abre un
     conflicto `POSIBLE_FUSION` con el cambio, para revisión. Los `parte.id` son estables porque Nexo los referencia.
   - **Dos diagramas → el mismo JJ:** hoy no ocurre (verificado: 0 casos). Si ocurre, el JJ se une con el de cruce más fuerte
     (`confirmado` antes que `revisar_manual`, luego el de menor id) y entre las dos partes se abre `POSIBLE_FUSION`.
3. **Marca del OEM:** la marca del vehículo cuando es una marca real (`TOYOTA` → Toyota, `GM` → General Motors, `BENZ` →
   Mercedes-Benz; de `HYUNDAI/KIA`, la primera). Si no lo es (`INTERCOOLER`, `CHINA`, `CHINACAR`, vacía), el OEM se publica con
   la marca reservada **«Sin marca»** (`marca_pieza` tipo `OEM`, la crea el proceso). Nexo empareja por `numero_norm`. La lista
   de `marca_pieza` la construyen ustedes desde las marcas de las fuentes; `brand_aaiaid` solo si lo tienen.
4. **Tipo de parte:** de acuerdo. Mapeo explícito `datos_maestros.parte` → `part_terminology_id`; lo que no mapee queda **fuera
   de la carga** y se reporta en `carga.corrida.notas` (no se adivina). `Radiator Tanks` de JJ → **48305**, salvo que el texto
   diga inlet/outlet (17700/17701).
5. **Vehículos de JJ sin revisión humana:** de acuerdo con escribir directo lo inequívoco (marca, modelo **y** años completos).
   La revisión humana existe igual, en Nexo: las aplicaciones del catálogo maestro llegan al artículo como **sugerencias** que el
   operador confirma (y el validador revisa). No hace falta la cola de `importaciones_pendientes`.
6. **Medidas de tanque:** sí se cargan, como ya hace Nexo con SAP (`mapeo-fuentes.md`): `tank_size` `598.5x76.6` →
   **270 Inlet Header Length** = 598,5 MM y **316 Inlet Header Width** = 76,6 MM. Con dos anchos (`756*33/48`), solo
   `valor_original` en la medida del largo; no se adivina. Para JJ, con el intercambio que encontraron: su `core_size` es el tanque
   y su `tank_size`, el panal.
7. **Abreviaturas de OEM:** sí, la misma expansión para las dos fuentes (`2025001000/1100` → `2025001000` y `2025001100`),
   para que `numero_norm` sea comparable. El número **reconstruido** lleva 0,2 menos de confianza que el original (0,8 si viene de
   un confirmado, 0,3 si de un pendiente).
8. **Cobertura de vehículos de los diagramas:** entendido y esperado (119 de 7 405 con `compatibilidades`). No es un error del
   proceso.
9. **Frecuencia:** de acuerdo: primera carga manual y coordinada; luego automática, al menos **semanal**, al terminar la cadena
   de la sección 6 del plan. La orquestación es de ustedes.
10. **Accesos:** sí, un usuario **de solo lectura y separado** en 10.20.20.6 (`connect` + `select` en `db_diagrams`, `db_scrapper`
    y `autocare_global`). **Nunca el superusuario `postgres`**, ni para leer. En Consolidación (10.10.60.6), uno en
    `grp_consolidacion_carga`. Mientras desarrollan: solo la base local (`CONSOLIDACION_*` → `host=postgres`).
11. **Fuentes futuras:** diseñen el vínculo de forma extensible (un paso «buscar parte existente por `numero_norm`» que hoy no se
    usa), pero no lo implementen todavía: la regla se acuerda cuando entre NRF, CSF o TYC.

## Sobre el plan
- **Primera carga en producción después de la etapa 1 (solo `DB_DIAGRAMS`)**, sin esperar a JJ: Nexo empieza a tener candidatos
  semanas antes. JJ entra después en su propia corrida.
- **Imágenes de JJ:** si la descarga falla, se guarda igual la `url` original sin objeto de MinIO y se reintenta en la siguiente
  corrida (las que ya están copiadas no se vuelven a descargar). El acceso de escritura a `rlt-diagramas/jjradiator/` se pide al
  administrador de MinIO.
- **Pruebas de la lógica que reutilizan** (`cross_reference.py`, `sugerir_compatibilidades.py`): de acuerdo, cúbranla antes de
  apoyarse en ella.
- **El intercambio `core_size` / `tank_size` de JJ** va en las pruebas: un caso JJ que termine con el mismo alto, largo y espesor
  que su diagrama.
