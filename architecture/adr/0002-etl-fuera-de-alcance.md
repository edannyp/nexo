# 0002. ETL y procesos de IA fuera de este repositorio

- **Estado:** Aceptada
- **Fecha:** 2026-10-15

## Contexto
El diagrama ubica un ETL dentro de la capa de Integración, pero ese trabajo (entrada desde SAP, regreso a SAP vía Service Layer, detección de cambio de `hash_control`) se manejará en otro proyecto, al igual que el scraping y la IA.

## Decisión
Este repositorio no contiene ETL ni orquestadores de jobs. Define el modelo de Nexo y los **contratos** que esos procesos deben cumplir (`architecture/datos/contratos.md`).

## Consecuencias
Las transiciones de estado que hacen procesos externos deben pasar por una función o regla de Nexo para no saltarse la máquina de estados.
