# 0014. MercadoExterno: vehículos y marcas fuera de AutoCare con estándar ACES

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
- VCdb no cubre todo el mercado local. Changan existe, pero solo con 68 base vehicles (BRA, CHL, COL, MEX) y faltan modelos y años
  vendidos en Guatemala.
- De 131 marcas SAP en alcance, 35 (456 artículos) no tienen equivalente directo. La mayoría son **equipos** (Perkins, Cummins, Generac,
  Yale, JCB, Komatsu), que VCdb Global modela como `equipment_base`, no como `base_vehicle`.
- `mercado_externo` existe (vacía) junto a `autocare_global` en la capa de Extracción del diagrama.
- **MercadoExterno es el catálogo de vehículos del mercado externo a AutoCare.** No es un destino de publicación de artículos.

## Decisión
- `mercado_externo` es una **extensión de VCdb** con la **misma estructura** que AutoCare: `make`, `model`, `base_vehicle`, `sub_model`,
  `engine_config` (litros, cilindros, combustible, designación), `transmission`, `equipment_model`, `equipment_base` y regiones.
  Solo contiene lo que **no** está en AutoCare: si la marca existe (Changan), se reutiliza su `make_id` y solo se agregan los modelos o años que faltan.
- **Mismo espacio de IDs**: los IDs de MercadoExterno empiezan en **1 000 000 000**. Así, las columnas `base_vehicle_id`, `engine_config_id`, etc.
  de Nexo y Consolidación aceptan ambos sin columnas extra, y se distinguen por rango.
- **Quién escribe**:
  - El **proceso de IA con búsqueda web** (otro proyecto): si encuentra un vehículo que no está en AutoCare, verifica si ya existe en
    MercadoExterno y, si no, lo agrega. **No requiere aprobación humana.**
  - La **APP**: el operador agrega el vehículo o equipo que necesite y no exista, con la misma verificación.
- **"Ya existe"** se determina por una llave normalizada: marca + modelo + año (+ submodelo), comparada contra AutoCare **y** MercadoExterno.
  Un índice único en MercadoExterno impide duplicados aunque la IA y la APP escriban a la vez.
- **Localización**: nombre comercial local (`nombre_mercado`) y regiones donde se vende (tabla de detalle, como en ADR 0011).
- **Trazabilidad**: cada registro guarda `origen` (`IA_WEB`, `APP`), `creado_por` (usuario o proceso), `evidencia` (URLs, ficha técnica) y `confianza`.
- **Reconciliación**: cuando una versión nueva de VCdb agrega el vehículo, el registro queda `REEMPLAZADO` con `reemplazado_por_id`
  (ID oficial) y las referencias en Nexo y Consolidación se migran.
- **Aplicaciones a equipos**: toda aplicación referencia **o** un vehículo (`base_vehicle_id`) **o** un equipo (`equipment_base_id`).

## Consecuencias
- Las búsquedas por vehículo en la APP unen AutoCare y MercadoExterno (vista o adaptador, ver `modelo-mercado-externo.md`).
- El proceso de carga de Consolidación, en vez de dejar vehículos en `aplicacion_sin_homologar`, puede homologarlos contra MercadoExterno.
- Se reemplaza la idea anterior de "publicar el catálogo validado en MercadoExterno".
