/*
 * Procesos de Nexo en BPMN, con cifras en vivo del tipo de artículo elegido:
 * - Artículo: de SAP a SAP con doble control (context/workflow-estados.md, ADR 0012 y 0025).
 * - Ficha de atributos: qué datos se capturan, campos solicitados y oficiales (ADR 0019, 0029 y 0030).
 */
import type { Estado, Panorama } from '@nexo/api-client';

import { numero } from '@/shared/formato';

import { centro, Decision, Evento, Flujo, Lienzo, Nota, Tarea, type Carril } from './bpmn';

const COLOR: Record<Estado, string> = {
  PENDIENTE: 'var(--color-pendiente)',
  POR_VALIDAR: 'var(--color-por-validar)',
  RECHAZADO: 'var(--color-rechazado)',
  VALIDADO: 'var(--color-validado)',
  SINCRONIZADO: 'var(--color-sincronizado)',
};
const NOMBRE: Record<Estado, string> = {
  PENDIENTE: 'Pendiente',
  POR_VALIDAR: 'Por validar',
  RECHAZADO: 'Rechazado',
  VALIDADO: 'Validado',
  SINCRONIZADO: 'Sincronizado',
};

export type Proceso = 'articulo' | 'ficha';
export const PROCESOS: { id: Proceso; nombre: string; resumen: string; nota: string }[] = [
  {
    id: 'articulo',
    nombre: 'Artículo',
    resumen: 'De SAP a SAP, con doble control.',
    nota: 'Para enviar a revisión hacen falta el tipo de parte, el vehículo principal confirmado y los atributos obligatorios.',
  },
  {
    id: 'ficha',
    nombre: 'Ficha de atributos',
    resumen: 'Qué datos se capturan: campos solicitados y oficiales.',
    nota: 'Revisar y aprobar requiere el permiso «Configurar la ficha de atributos». Un campo propuesto nunca es obligatorio.',
  },
];

// ---------------------------------------------------------------------------------------------------------------------
// Artículo
// ---------------------------------------------------------------------------------------------------------------------
const C_ARTICULO: Carril[] = ['SAP · ETL', 'Operador', 'Supervisor', 'Salida a SAP'].map((nombre) => ({
  nombre,
  alto: 130,
}));

function ProcesoArticulo({ d }: { d: Panorama }) {
  const y = (k: number) => centro(C_ARTICULO, k);
  const n = (e: Estado) => d.por_estado[e] ?? 0;
  const estado = (e: Estado) => ({ texto: NOMBRE[e], cantidad: n(e), color: COLOR[e] });
  return (
    <Lienzo carriles={C_ARTICULO} titulo="Proceso del artículo en BPMN: SAP, operador, supervisor y salida a SAP">
      {/* SAP · ETL */}
      <Evento x={95} cy={y(0)} lineas={['Artículo nuevo o', 'cambia en SAP']} />
      <Flujo
        puntos={[
          [111, y(0)],
          [180, y(0)],
        ]}
      />
      <Tarea x={260} cy={y(0)} lineas={['ETL diario:', 'foto completa de SAP']} />
      <Flujo
        puntos={[
          [335, y(0)],
          [393, y(0)],
        ]}
      />
      <Decision x={415} cy={y(0)} pregunta="¿Nuevo o cambió?" />
      <Flujo
        puntos={[
          [437, y(0)],
          [520, y(0)],
        ]}
        etiqueta="sin cambios"
        dx={8}
      />
      <Nota x={528} y={y(0) + 4} lineas={['nada que hacer']} />

      {/* Operador */}
      <Flujo
        puntos={[
          [415, y(0) + 22],
          [415, y(1) - 29],
        ]}
        etiqueta="sí"
        dx={-18}
        dy={14}
      />
      <Nota
        x={425}
        y={y(0) + 40}
        tono="aviso"
        lineas={['nuevo, o cambió algo que importa:', 'va a Pendiente (lo hecho se conserva)']}
      />
      <Tarea
        x={415}
        cy={y(1)}
        lineas={['Tomar con «Siguiente»', '(se reserva 30 min)']}
        insignia={estado('PENDIENTE')}
        ancho={168}
      />
      <Flujo
        puntos={[
          [499, y(1)],
          [548, y(1)],
        ]}
      />
      <Tarea x={640} cy={y(1)} lineas={['Ficha, aplicaciones', 'y ★ vehículo principal']} ancho={184} />
      {/* Lo que falta en la ficha se pide aparte (proceso Ficha de atributos) */}
      <Flujo
        puntos={[
          [700, y(1) + 29],
          [700, y(1) + 44],
        ]}
        punteado
      />
      <Nota x={708} y={y(1) + 46} tono="aviso" lineas={['¿falta un dato?', '→ solicitar campo']} />
      <Flujo
        puntos={[
          [732, y(1)],
          [783, y(1)],
        ]}
      />
      <Tarea x={850} cy={y(1)} lineas={['Enviar a revisión']} ancho={134} />

      {/* Supervisor */}
      <Flujo
        puntos={[
          [850, y(1) + 29],
          [850, y(2) - 29],
        ]}
      />
      <Tarea x={850} cy={y(2)} lineas={['Revisar', '(otro supervisor)']} insignia={estado('POR_VALIDAR')} ancho={134} />
      <Flujo
        puntos={[
          [917, y(2)],
          [968, y(2)],
        ]}
      />
      <Decision x={990} cy={y(2)} pregunta="¿Correcto?" abajo />
      <Flujo
        puntos={[
          [990, y(2) - 22],
          [990, y(1) + 4],
          [917, y(1) + 4],
        ]}
      />
      <Nota x={998} y={y(1) + 34} lineas={['no: rechazar con motivo;', 'el operador corrige y reenvía']} />
      <Nota x={998} y={y(1) - 4} tono="rechazado" lineas={[`Rechazado · ${numero(n('RECHAZADO'))}`]} />
      <Flujo
        puntos={[
          [1012, y(2)],
          [1062, y(2)],
        ]}
        etiqueta="sí"
        dx={8}
      />
      <Tarea x={1110} cy={y(2)} lineas={['Validar']} insignia={estado('VALIDADO')} ancho={128} />

      {/* Salida a SAP */}
      <Flujo
        puntos={[
          [1110, y(2) + 51],
          [1110, y(3) - 29],
        ]}
      />
      <Tarea x={1110} cy={y(3)} lineas={['Actualizar SAP', '(proceso externo)']} ancho={128} />
      <Flujo
        puntos={[
          [1046, y(3)],
          [960, y(3)],
        ]}
      />
      <Evento x={942} cy={y(3)} fin lineas={['Sincronizado', numero(n('SINCRONIZADO'))]} />

      {/* Verificación (la resuelve un supervisor): lo validado se vuelve a mirar; con hallazgo, vuelve a Pendiente */}
      <Tarea x={560} cy={y(2)} lineas={['Verificación: foto nueva,', 'muestreo o cambio de catálogo']} ancho={210} />
      <Flujo
        puntos={[
          [924, y(3)],
          [560, y(3)],
          [560, y(2) + 31],
        ]}
        punteado
      />
      <Flujo
        puntos={[
          [455, y(2)],
          [415, y(2)],
          [415, y(1) + 52],
        ]}
        punteado
      />
      <Nota x={405} y={y(2) + 16} ancla="end" tono="aviso" lineas={['con hallazgo', '→ Pendiente']} />
    </Lienzo>
  );
}

// ---------------------------------------------------------------------------------------------------------------------
// Ficha de atributos
// ---------------------------------------------------------------------------------------------------------------------
const C_FICHA: Carril[] = [
  { nombre: 'Operador', alto: 130 },
  { nombre: 'Configura la ficha', alto: 190 },
  { nombre: 'AutoCare', alto: 130 },
];

function ProcesoFicha({ d }: { d: Panorama }) {
  const op = centro(C_FICHA, 0);
  const cfg = 190; // fila principal del carril «Configura la ficha» (de 130 a 320)
  const rech = 275; // fila del rechazo
  const ac = centro(C_FICHA, 2);
  return (
    <Lienzo
      carriles={C_FICHA}
      titulo="Proceso de la ficha de atributos en BPMN: el operador solicita campos, quien configura la ficha los aprueba o rechaza"
    >
      {/* Operador: pide lo que falta; queda propuesto y ya se puede llenar */}
      <Evento x={95} cy={op} lineas={['Falta un dato', 'en la ficha']} />
      <Flujo
        puntos={[
          [111, op],
          [185, op],
        ]}
      />
      <Tarea x={270} cy={op} lineas={['Solicitar un campo', '(nombre, tipo y para qué)']} ancho={170} />
      <Flujo
        puntos={[
          [355, op],
          [425, op],
        ]}
      />
      <Tarea
        x={530}
        cy={op}
        lineas={['Propuesto: ya se llena,', 'pero no es obligatorio']}
        insignia={{ texto: 'Propuestos', cantidad: d.atencion.campos_propuestos, color: 'var(--color-por-validar)' }}
        ancho={210}
      />
      <Flujo
        puntos={[
          [635, op],
          [760, op],
          [760, cfg - 29],
        ]}
      />

      {/* Configura la ficha: lo oficial directo, y la revisión de lo solicitado */}
      <Evento x={95} cy={cfg} lineas={['Dato nuevo', 'para todos']} />
      <Flujo
        puntos={[
          [111, cfg],
          [185, cfg],
        ]}
      />
      <Tarea x={270} cy={cfg} lineas={['Crear campo propio', 'o agregar de AutoCare']} ancho={170} />
      <Flujo
        puntos={[
          [355, cfg],
          [414, cfg],
        ]}
      />
      <Evento x={430} cy={cfg} fin lineas={['Oficial']} />

      <Tarea x={760} cy={cfg} lineas={['Revisar la solicitud', '(ajustar si hace falta)']} ancho={170} />
      <Flujo
        puntos={[
          [845, cfg],
          [878, cfg],
        ]}
      />
      <Decision x={900} cy={cfg} pregunta="¿Se aprueba?" />
      <Flujo
        puntos={[
          [922, cfg],
          [965, cfg],
        ]}
        etiqueta="sí"
        dx={8}
      />
      <Tarea x={1030} cy={cfg} lineas={['Oficial: ya puede', 'ser obligatorio']} ancho={130} />
      <Flujo
        puntos={[
          [1095, cfg],
          [1124, cfg],
        ]}
      />
      <Evento x={1140} cy={cfg} fin lineas={['En la ficha']} />
      <Flujo
        puntos={[
          [900, cfg + 22],
          [900, rech],
          [955, rech],
        ]}
        etiqueta="no"
        dx={8}
        dy={30}
      />
      <Tarea x={1030} cy={rech} lineas={['Rechazar con motivo:', 'sale de la ficha']} ancho={150} />
      <Nota x={945} y={rech + 18} ancla="end" lineas={['lo capturado', 'se conserva']} />
      <Flujo
        puntos={[
          [1075, rech - 29],
          [1075, cfg + 29],
        ]}
        punteado
      />
      <Nota x={1083} y={cfg + 48} tono="aviso" lineas={['reconsiderar']} />

      {/* AutoCare: la carga trae los atributos que admite cada tipo de parte */}
      <Evento x={95} cy={ac} lineas={['Nueva versión', 'de AutoCare']} />
      <Flujo
        puntos={[
          [111, ac],
          [185, ac],
        ]}
      />
      <Tarea x={270} cy={ac} lineas={['Cargar el catálogo', 'de atributos']} ancho={170} />
      <Flujo
        puntos={[
          [270, ac - 29],
          [270, cfg + 29],
        ]}
        etiqueta="nuevos: disponibles, fuera de la ficha"
        dx={8}
        dy={-14}
      />
      <Flujo
        puntos={[
          [355, ac],
          [425, ac],
        ]}
      />
      <Tarea x={555} cy={ac} lineas={['Lo que AutoCare retira:', 'obsoleto (se conserva)']} ancho={260} />
      <Nota
        x={710}
        y={ac - 4}
        lineas={['Los campos propios no son de AutoCare:', 'la carga nunca los toca (solo viven en Nexo).']}
      />
    </Lienzo>
  );
}

export function DibujoProceso({ proceso, d }: { proceso: Proceso; d: Panorama }) {
  if (proceso === 'ficha') return <ProcesoFicha d={d} />;
  return <ProcesoArticulo d={d} />;
}
