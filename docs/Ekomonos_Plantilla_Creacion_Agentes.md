# Guía de Ingeniería Digital: Creación de Agentes (v.2.0)

Este documento define la estructura técnica obligatoria (Blueprint) y el proceso de creación interactivo para dar de alta nuevos **empleados (agentes de IA)** en el ecosistema **Ekomonos**.

Esta guía es utilizada exclusivamente por el **CTO** para realizar la contratación y desplegar al agente en la carpeta `.agents/personas/` que corresponda.

---

## 1. Proceso Guiado de Contratación (Paso a Paso)

Cuando el CEO indique que desea **"contratar"** o **"crear"** un nuevo empleado en cualquier área, el CTO iniciará este protocolo interactivo:

1. **Preguntas Secuenciales (Una a la vez):**
   * **Paso 1 (Objetivos):** *"¿Cuál será el objetivo principal de este nuevo empleado y qué carpetas o archivos específicos del sistema tendrá permitido gestionar?"*
   * **Paso 2 (Rol e Identidad):** *"¿Cuál será su personalidad, su tono y su estilo de comunicación (ej. técnico, inquisitivo, socrático)?"*
   * **Paso 3 (Instrucciones Concretas):** *"¿Qué tareas concretas o pasos estructurados debe seguir cuando le encomendemos un trabajo?"*
   * **Paso 4 (Formato de Salida):** *"¿Cómo debe entregar sus respuestas? ¿Necesitamos tablas, listas o citas de fuentes específicas?"*
   * **Paso 5 (Protecciones):** *"¿Qué cosas tiene estrictamente prohibido hacer o decir? ¿Qué debe hacer si le falta información?"*
2. **Generación del Borrador:** Una vez recopiladas las respuestas, redacta el borrador del archivo `.md` estructurado según el **Blueprint de Empleado** (ver Sección 2).
3. **Validación:** Solicita la aprobación de Rafa. Si se requieren cambios, ajusta la sección indicada.
4. **Despliegue Físico:** Tras la confirmación final, guarda el archivo en la subcarpeta `.agents/personas/` del Workspace objetivo (ej. `D:\00_EKOSISTEMA_OS\.agents\personas/` o `D:\00_EKOSISTEMA_OS\03_DINERO\.agents\personas/`) asignándole el número correlativo que corresponda.

---

## 2. Blueprint de Empleado (Estructura XML Obligatoria)

Todo archivo de agente debe llamarse `[Número]_[nombre_del_empleado].md` (ej. `03_asesor_fiscal.md`) y respetar esta plantilla exacta:

```markdown
# Empleado: [Nombre del Empleado] (v.X.X)

Este empleado ha sido contratado para [describir brevemente su función].

---

## 1. OBJETIVOS Y ALCANCE
<scope>
- [Meta principal del empleado]
- [Límites: carpetas que tiene permitido leer/escribir]
</scope>

## 2. ROL E IDENTIDAD
<role>
- [Identidad profesional y área de especialización]
- [Tono, voz y estilo de comunicación]
</role>

## 3. INSTRUCCIONES CONCRETAS Y FLUJO (Workflow)
<workflow>
- [Pasos ordenados a seguir para completar las tareas]
- [Protocolo de interacción en el chat]
</workflow>

## 4. FORMATO DE SALIDA
<output_format>
- [Estructura de las respuestas: tablas, diagramas Mermaid, listas]
- [Anclaje a fuentes: citas exactas si aplica]
</output_format>

## 5. PROTECCIONES Y LIMITACIONES (Constraints)
<constraints>
- [Acciones prohibidas y límites]
- [Abstenciones: qué responder ante falta de información]
- [Reglas de privacidad y fugas de datos]
</constraints>

## 6. REFUERZOS Y PRINCIPIOS GUÍA (Reinforcements)
<reinforcements>
- [Principios innegociables que debe recordar siempre]
</reinforcements>
```
