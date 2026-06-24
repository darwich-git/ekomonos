---
description: Proceso de actualización de versión tras cambios en el código
---

# Flujo de Trabajo: Actualización de Versión

Para asegurar que el usuario siempre tenga constancia de los cambios realizados, se debe seguir este proceso **después de cada fix o nueva funcionalidad**:

1. **Identificar la versión actual**: Leer el archivo `d:\Proyectos\EKKOMONOS\version.py`.
2. **Incrementar la versión**: 
   - Seguir la lógica incremental (Ej: de `V.7.34` a `V.7.35`).
   - El formato debe mantenerse como `V.X.YY`.
3. **Aplicar el cambio**: Usar la herramienta `replace_file_content` para actualizar el string `__version__`.
4. **Informar al usuario**: Incluir siempre el nuevo número de versión en el resumen final de la tarea.

> **Regla de Oro**: Ninguna tarea de código se considera terminada hasta que la versión ha sido incrementada.
