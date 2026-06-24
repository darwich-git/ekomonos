# Guía de Ingeniería Digital: Creación de Skills (v.1.0)

Este documento define la estructura técnica obligatoria y las normas de portabilidad para el desarrollo y despliegue de **Skills (habilidades)** en el ecosistema **Ekomonos**.

Las skills son herramientas ejecutables creadas por el **CTO** para ampliar la funcionalidad de los agentes.

---

## 1. Estructura de Carpetas de una Skill

Toda skill debe organizarse dentro de una carpeta dedicada con el nombre de la skill (ej. `eko-mi-skill/`) siguiendo esta estructura:

```plaintext
nombre-de-la-skill/
├── SKILL.md          # Manual de uso y disparador de la IA (Obligatorio)
├── scripts/          # El motor de ejecución (Scripts de Python/Bash)
├── resources/        # Plantillas de datos, CSVs vacíos o archivos estáticos
└── examples/         # Demostraciones y archivos de ejemplo
```

---

## 2. Blueprint del Archivo SKILL.md (Estructura YAML + Markdown)

El archivo `SKILL.md` debe comenzar estrictamente con una sección de metadatos YAML de tres guiones, que sirve de disparador automático para la IA:

```markdown
---
name: [identificador-unico-de-la-skill]
description: [Descripción ultra-precisa y en lenguaje natural de cuándo debe activarse esta skill]
---

# Habilidad: [Nombre Humano de la Skill]

## 1. PROTOCOLO DE EJECUCIÓN (Paso a Paso)
- [Pasos detallados que el agente de IA debe seguir al activarse la skill]
- [Llamadas a scripts de la carpeta `/scripts/` si es necesario]

## 2. REGLAS DE COMPORTAMIENTO E INTEGRIDAD
- [Medidas de seguridad específicas]
- [Qué hacer si fallan los scripts]
```

---

## 3. Normas de Portabilidad y Seguridad (Innegociables)

1.  **Cero Hardcoding de Rutas de Usuario:** Queda prohibido escribir rutas rígidas como `C:\Users\darwi.PCDARWICH\OneDrive\Desktop` o similares en el `SKILL.md` o en los scripts. Usa variables de entorno del sistema (como `%USERPROFILE%` o `$HOME`) o rutas relativas al directorio actual.
2.  **Referencia Relativa a los Scripts:** Al indicar comandos de ejecución en `SKILL.md`, indícale a la IA que localice el script de forma dinámica relativo a la ruta física de la skill en ejecución (ej. `python {ruta_de_la_skill}/scripts/mi_script.py`).
3.  **Gestión Dinámica de Scratch/Temporales:** Está estrictamente prohibido meter identificadores de conversación fijos de chats anteriores (ej. `brain/510be174-8dec...`). En su lugar, dile a la IA: *"Guarda el JSON temporal en la carpeta /scratch/ asociada al identificador del chat actual"*.
4.  **Clasificación de Riesgos (P1/P2/P3):**
    *   **P1 (Crítico):** Las claves bancarias o de brokers nunca se tocan ni se meten en variables.
    *   **P2 (Alto):** Información de identificación personal (DNI, IBAN) no se exporta ni se loguea.
    *   **P3 (Medio):** Contraseñas de desarrollo y APIs van en un archivo `.env` local, que **debe estar declarado obligatoriamente en el `.gitignore`** de la skill si se sube a GitHub.
