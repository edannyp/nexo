# 0027. Vista del artículo en dos modos y descripción armada por Nexo

- **Estado:** Aceptada. Implementada en la migración 0017 y la consola (2026-11-09).
- **Fecha:** 2026-11-09

## Contexto
Al abrir un artículo se entraba directo a la pestaña Ficha (un formulario de edición), con un encabezado fijo muy cargado (estado,
venta, reserva, acciones, requisitos) y siete pestañas al mismo nivel que mezclaban consulta y trabajo. Lo más importante para
reconocer la pieza (fotos, vehículo principal, medidas) no se veía de un vistazo. Además, el artículo solo tenía la descripción de
SAP, escrita a mano y sin formato fijo (`RAD. TOYOTA HILUX 2.4 M/03 A-RLT`, `RADIADOR KIA RIO M 06/07 AT`).

## Decisión
- **Dos modos.** Al abrir, un **Resumen** de solo lectura: carrusel de fotos (propias y del catálogo maestro), descripción de Nexo
  y la de SAP, ★ vehículo principal (ADR 0025), medidas del panal y atributos confirmados, qué falta para enviar a revisión, y
  Datos SAP e Historial como secciones plegables. **Trabajar** reserva el artículo y abre el espacio de edición (Ficha, Aplicaciones,
  Emparejamiento y, en fabricados, Equivalencia) con un encabezado compacto (reserva, Soltar, Enviar a revisión, lo que falta). Si
  el artículo ya está reservado por quien lo abre, se entra directo a Trabajar. Validar y Rechazar siguen en el encabezado del
  Resumen.
- **Lo necesario a la vista mientras se trabaja:** una franja en el encabezado fijo, con el código (en pantalla grande; en celular va
  debajo, sin fijar): la foto (carrusel compacto) y, a su lado, la **descripción sugerida** (con «Ajustar»), la de SAP y el
  **★ vehículo principal**. Las pestañas (Ficha, Aplicaciones, Emparejamiento…) también quedan fijas en ese encabezado, en
  pantalla grande y en celular; su contenido usa todo el ancho.
- **Lo editable se distingue:** en la Ficha, cada campo que se edita en Nexo lleva un lápiz (y resalta el borde al pasar); la columna
  de SAP lleva un candado (solo lectura). Una leyenda lo explica. Sin permiso de edición no hay lápices.
- **Comparar fotos al emparejar:** un modal amplio con las fotos del artículo a la izquierda y las imágenes del candidato a la
  derecha (con miniaturas), y las medidas en el medio; recorre los candidatos (botones o flechas) y vincula desde ahí. Las imágenes
  del catálogo copiadas a MinIO se muestran desde la copia (ADR 0026).
- **Sin pestaña Fotos:** el carrusel las muestra; quien tiene el rol Fotos las sube y ordena desde el carrusel («Subir u ordenar»).
- **Descripción de Nexo**, además de la de SAP (que no se toca): Nexo la propone sola con el **patrón de SAP sin abreviar**
  `TIPO MARCA MODELO M AA/AA MOTOR TRANSMISIÓN` y, en fabricados, el material (`RADIADOR TOYOTA HILUX M 05/15 2.5L MT`,
  `RADIADOR KENWORTH T600A M 14 COBRE LATON`), hasta 100 caracteres:
  - tipo según el tipo de parte (o la categoría), marca, modelo, años y motor del vehículo principal; transmisión de SAP;
    material de la sub-subcategoría de SAP;
  - se recalcula sola cuando cambia lo que la forma; sin vehículo principal queda vacía (no se inventa);
  - el operador la puede **ajustar** a mano y desde ahí queda fija, hasta que elija «Volver a la automática»; el validador la ve.

## Consecuencias
- Cada aplicación guarda también el texto del motor del catálogo (como marca y modelo en 0016).
- La descripción de Nexo queda disponible en `app.articulo.descripcion_nexo`. Si el proceso de salida la escribirá en SAP
  (`ItemName`) se decide con ese proyecto.
- Los enlaces con `?pestana=sap` o `?pestana=historial` abren el Resumen, donde ahora están esas secciones.
