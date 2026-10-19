# 0003. Backend en Python con FastAPI

- **Estado:** Propuesta
- **Fecha:** 2026-10-15

## Contexto
La APP se integra con PostgreSQL, ClickHouse, potencialmente SAP HANA y con procesos de IA. Necesita contratos claros para el frontend.

## Decisión
FastAPI + SQLAlchemy 2 + Alembic + Pydantic v2, organizado por módulos de dominio (`auth`, `articulos`, `workflow`, `aplicaciones`, `diagramas`, `matching`, `auditoria`).

## Consecuencias
OpenAPI generado automáticamente; el frontend genera su cliente. Alternativa descartada: NestJS (un solo lenguaje, pero drivers de HANA/ClickHouse y librerías de datos más débiles).
