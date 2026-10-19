# Arquitectura general

Imagen original: [arquitectura-general.jpg](arquitectura-general.jpg)

```mermaid
flowchart LR
  subgraph EXT["Extracción (otro proyecto)"]
    SAP[(SAP HANA)]
    ELT{{ELT}}
    AC[(AutoCare<br/>Postgres)]
    ME[(MercadoExterno<br/>Postgres)]
    ELT --> SAP
    ELT --> AC
  end

  subgraph ING["Scraping e ingeniería de fuentes (otro proyecto)"]
    CONS[(Consolidación)]
    DIA[(Diagrams)]
    JJ[(JJRadiators)]
    NF[(n_fuentes)]
    JJ --> DIA --> CONS
    NF --> DIA
    JJ --> CONS
    NF --> CONS
  end

  IA([Procesos de IA]) --> ING

  subgraph INT["Integración (ESTE proyecto)"]
    ETL{{ETL<br/>otro proyecto}}
    BD[(Nexo)]
    APP[APP<br/>backend + frontend]
    ETL --> BD
    APP --> BD
  end

  ELT --> BD
  ETL --> SAP
  APP --> ME
  APP --> CONS
```

Lectura del diagrama:
- **Negro**: el ELT de extracción alimenta Nexo desde SAP y conecta con AutoCare.
- **Morado**: el ETL de integración regresa datos a SAP.
- **Naranja**: el ETL escribe en Nexo; la APP lee/escribe Nexo, agrega vehículos fuera de AutoCare en MercadoExterno (ADR 0014) y consulta Consolidación.
- **Verde / rojo**: el scraping alimenta Diagrams y Consolidación.
- **Azul**: los procesos de IA operan sobre toda la capa de ingeniería de fuentes.

Este proyecto implementa solo **Nexo** y la **APP**. Los ETL/ELT aparecen como contratos.
