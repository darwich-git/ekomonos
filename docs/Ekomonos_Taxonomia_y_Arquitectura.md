# Ekomonos Library System: Folder Taxonomy and Architecture Reference

Este documento detalla el diseño de arquitectura, la taxonomía de carpetas y los mecanismos de integración del ecosistema **Ekomonos**. Sirve como la base de conocimiento y el "plano de ingeniería" para futuras actualizaciones o migraciones de infraestructura.

---

## 1. Filosofía del Diseño

El ecosistema Ekomonos está estructurado bajo tres principios clave:
1. **Separación de Sincronización (Híbrido Nube/Local):** Evitar saturar el almacenamiento en la nube (Google Drive/Obsidian) con PDFs y transcripciones pesadas (que ocupan gigabytes de datos brutos), al tiempo que se sincronizan de forma segura en la nube las hojas de cálculo de valoración activa (`.xlsm`), las bitácoras y las tesis en formato Markdown.
2. **Taxonomía Normalizada Rigurosa:** Todas las compañías y situaciones especiales comparten exactamente la misma estructura interna de carpetas y convenciones de nombres, lo que permite que los scripts de Python y los scrapers automáticos naveguen y operen en el disco sin fallos.
3. **Única Fuente de Verdad (Single Source of Truth):** Todas las variables globales, rutas raíz de discos y parámetros de puertos se definen en un solo archivo de configuración (`config.py`) para garantizar portabilidad absoluta entre diferentes ordenadores.

---

## 2. Estructura de Directorios a Nivel Global

El ecosistema se distribuye físicamente en dos ubicaciones del almacenamiento local de disco `D:\`:

### A. Ubicación Central Sincronizada (Ekomonos Library)
* **Ruta Física:** `D:\00_EKOSISTEMA_OS\03_DINERO\03.01_Inversion\03.01_Ekomonos_Library`
* **Sincronización:** Google Drive (Nube)
* **Contenido:** Subcarpetas por ticker (STOCK y SPECIAL), modelos de valoración activos, base de datos del estado de la librería (`library.db`), y pomodoro logs.

### B. Almacenamiento Local Puro No Sincronizado
* **Ruta Física:** `D:\00_LOCAL_ARCHIVE_NO_SYNC\Ekomonos_Library`
* **Sincronización:** Ninguna (Excluido físicamente de la nube)
* **Contenido:** El almacenamiento crudo de los reportes PDF descargados, transcripciones de conferencias de resultados, y prensa.

---

## 3. Taxonomía de 4 Capas de la Compañía (`STOCK/[TICKER]/`)

Cada compañía dentro de la biblioteca central en `STOCK/[TICKER]/` se organiza bajo la siguiente taxonomía:

```
STOCK/[TICKER]/
├── 01_Directrices_y_Cerebro/      ➔ (Sincronizado en Nube)
│   ├── company_info.json         <-- Metadatos JSON (Ticker oficial, nombre, aliases, exchange)
│   └── rules_[TICKER].json       <-- Reglas de inversión y límites de precios específicos
│
├── 02_Fuentes_Inmutables/         ➔ (NTFS Junction -> Local Archive No Sync)
│   ├── 02.01_Reportes/           <-- Informes brutos de TIKR (Anuales y trimestrales)
│   ├── 02.02_Transcripciones/     <-- Transcripciones de conferencias de resultados
│   └── 02.03_Articulos_y_Prensa/ <-- Notas de brokers, noticias, PDFs externos
│
├── 03_Modelos_y_Datos/            ➔ (Sincronizado en Nube)
│   ├── [TICKER]_Modelo_Valoracion.xlsm  <-- Modelo financiero activo (Excel con Macros)
│   └── _Historico/               <-- Modelos de años pasados y backups de trabajo
│
└── 04_Sintesis_y_Analisis/        ➔ (Sincronizado en Nube / Obsidian)
    ├── [TICKER]_Tesis.md         <-- Nota central de Obsidian con la tesis de inversión
    ├── [TICKER]_Bitacora.md       <-- Bitácora viva de KPIs y eventos trimestrales
    └── [TICKER]_Checklist.md      <-- Checklist completado por la Skill local de RAG
```

---

## 4. El Mecanismo de Junctions NTFS

Para lograr la separación híbrida entre la nube y el almacenamiento físico local:
1. La carpeta `STOCK/[TICKER]/02_Fuentes_Inmutables` no es un directorio real en la ruta sincronizada. Es un **Junction NTFS** (un enlace duro de sistema de archivos a nivel de kernel de Windows).
2. Se crea utilizando el comando de Windows:
   `mklink /J "D:\00_EKOSISTEMA_OS\03_DINERO\03.01_Inversion\03.01_Ekomonos_Library\STOCK\[TICKER]\02_Fuentes_Inmutables" "D:\00_LOCAL_ARCHIVE_NO_SYNC\Ekomonos_Library\STOCK\[TICKER]\02_Fuentes_Inmutables"`
3. **Beneficio:** Tanto la GUI de Ekomonos en Python como el scraper Node.js escriben y leen de `02_Fuentes_Inmutables` de forma transparente como si fuera una subcarpeta ordinaria. Sin embargo, Google Drive detecta el Junction y no sube el contenido a la nube, ahorrando espacio y ancho de banda en la cuenta sincronizada.

---

## 5. Diseño de Base de Datos y Clasificación de Archivos

Ekomonos utiliza la base de datos `fortress_vault.db` (en `D:\01_PROJECT_CODE\EKKOMONOS\db\fortress_vault.db`) como el registro maestro de la biblioteca.

### A. Tabla `files`
Registra la ubicación física de cada PDF e informe y sus metadatos de lectura:
* `path` (TEXT UNIQUE): Ruta absoluta completa del archivo en el sistema de archivos (ej. `D:\00_LOCAL_ARCHIVE_NO_SYNC\Ekomonos_Library\STOCK\NA9\02_Fuentes_Inmutables\02.01_Reportes\2021-06-30_NAGARRO SE_INTERIM H1_EN_2021-08-13.pdf`).
* `ticker` (TEXT): Ticker de la compañía.
* `category` (TEXT): Categoría normalizada que determina en qué sección del PDF Manager de la GUI aparecerá. Las categorías son:
  * `"Annual Reports"` (Informes Anuales de cierre de ejercicio / FY)
  * `"Reportes"` (Informes trimestrales y semestrales / Q1, Q2, Q3, H1, H2)
  * `"Transcript"` (Transcripciones de llamadas de ganancias)
  * `"Excel"` (Modelos de valoración y datos numéricos)
  * `"Varios"` (Notas de prensa y artículos de mercado)
* `year` (TEXT): Año del documento.
* `quarter` (TEXT): Trimestre o periodo del documento (`"FY"`, `"Q1"`, `"Q2"`, `"Q3"`, `"Q4"`, `"H1"`, `"H2"`, `"NA"`).
* `language` (TEXT): Idioma del documento (`"EN"`, `"ES"`).
* `status` (INTEGER): Estado de revisión (`0` = Nuevo, `1` = En Proceso, `2` = Revisado).

### B. Algoritmo de Clasificación
Para estructurar los PDFs, el sistema implementa un parsing secuencial en [pdf_manager.py](file:///D:/01_PROJECT_CODE/EKKOMONOS/ui/widgets/pdf_manager.py):
1. **Detección de Carpeta:**
   * Si la ruta contiene `02.01_Reportes` o `1 REPORTS`, el archivo se marca inicialmente como informe (`Reports_Folder`).
   * Si contiene `02.02_Transcripciones` o `2 TRANSCRIPTS`, se asigna a `"Transcript"`.
   * Si contiene `03_Modelos_y_Datos` o `3 EXCEL`, se asigna a `"Excel"`.
   * Si contiene `02.03_Articulos_y_Prensa` o `4 VARIOS`, se asigna a `"Varios"`.
2. **Refinamiento por Periodo (Informes):**
   * Si el nombre del archivo cumple con la estructura estándar (`YYYY-MM-DD_[Title]_[FormName]_[Lang]_[YYYY-MM-DD].pdf`), se parsea el `FormName` y el periodo (`quarter`).
   * Si el periodo es `"FY"`, la categoría final se ajusta a `"Annual Reports"`.
   * Si el periodo es `"Q1"`, `"Q2"`, `"Q3"`, `"Q4"`, `"H1"` o `"H2"`, la categoría final se ajusta a `"Reportes"`.
   * Para archivos no estructurados, se aplica un filtro heurístico en base a palabras clave (ej: si contiene `"annual report"` o `"full_year"` se mapea como `"Annual Reports"`, en caso contrario como `"Reportes"`).

---

## 6. Integración del Scraper TIKR Harvest

El extractor de PDFs de TIKR Harvest corre en Node.js y se comunica con la base de datos de Ekomonos para evitar descargas redundantes:
1. **Consulta del Estado de la Librería:** TIKR Harvest realiza una petición `GET` a `/api/library-status`. El backend ejecuta el script [get_library_status.py](file:///D:/01_PROJECT_CODE/EKKOMONOS/scripts/get_library_status.py), el cual realiza una consulta SQL a la tabla `files` de `fortress_vault.db` y devuelve la lista completa de archivos registrados.
2. **Marcado Visual:** El frontend en React compara el nombre que TIKR va a descargar con los archivos ya presentes en local, sombreando en color gris claro los informes que ya posees en tu disco para evitar que hagas doble descarga.
3. **Escritura Directa:** Al descargar, el servidor de Node escribe el archivo directamente en `02.01_Reportes` o `02.02_Transcripciones` de la carpeta de la empresa en la librería local (sin subcarpetas de años intermedias).
4. **Disparador de Sincronización (Trigger):** Al terminar la descarga de una compañía, TIKR envía el mensaje `ACTION_TRIGGER:DOWNLOAD_FINISHED:[TICKER]` a través de la consola. El objeto `QProcess` en la GUI de Ekomonos intercepta este evento y refresca instantáneamente la lista de PDFs del gestor en pantalla sin requerir ninguna acción por tu parte.

---

## 7. Integración de la Skill de Checklist (RAG Local)

La skill interactiva de checklist RAG está diseñada para operar directamente sobre la taxonomía normalizada:
* **Ubicación de la Skill:** `C:\Users\darwi.PCDARWICH\.gemini\config\skills\checklist\SKILL.md`
* **Entrada de Datos:** El RAG procesa los archivos locales alojados en `STOCK/[TICKER]/02_Fuentes_Inmutables/02.01_Reportes/` y `02.02_Transcripciones/`. Al usar las carpetas de Junctions directas, se evitan bucles infinitos de búsqueda y se acelera el indexado semántico local de los modelos de lenguaje.
* **Salida del Análisis:** Una vez procesada la checklist fundamental de la empresa, el archivo Markdown generado se deposita de manera automática en la carpeta de Obsidian: `STOCK/[TICKER]/04_Sintesis_y_Analisis/[TICKER]_Checklist.md`.

---

## 8. Mantenimiento y Solución de Problemas de Infraestructura

Si en el futuro se realiza otra migración de disco o el sistema deja de funcionar, sigue este checklist secuencial de soporte:

1. **Conflicto de Puerto 3000:** Si TIKR Harvest muestra la pantalla roja de `ProcessError.Crashed`, significa que un proceso huérfano de `node.exe` se ha quedado bloqueando el puerto `3000`. Ekomonos ejecuta automáticamente `_kill_port_owner` en el arranque de la pestaña para solucionarlo, pero puedes forzar el limpiado en PowerShell con:
   `Stop-Process -Id (Get-NetTCPConnection -LocalPort 3000).OwningProcess -Force` (o matando todas las instancias con `taskkill /F /IM node.exe`).
2. **Re-Sincronización de Base de Datos:** Si los archivos no aparecen en TIKR Harvest pero sí están físicamente en tu disco, ejecuta el script de corrección de rutas:
   `python "C:\Users\darwi.PCDARWICH\.gemini\antigravity\brain\510be174-8dec-4a2b-84dd-0791ad6d964f\scratch\sync_and_prune_files.py"`
3. **Portabilidad de Rutas:** Si cambias la biblioteca de disco o de letra de unidad (ej: de `D:\` a `E:\`), solo debes modificar la variable `LIBRARY_ROOT` en `D:\01_PROJECT_CODE\EKKOMONOS\config.py` y volver a compilar el scraper ejecutando `npm run build` en la carpeta `tikr-harvest`.
