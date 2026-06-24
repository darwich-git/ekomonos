# Special Situations V2 — Plan de Implementación
# Versión objetivo: V.7.50
# Fecha: 2026-02-22

---

## RESUMEN EJECUTIVO

Refactor profundo del módulo de Situaciones Especiales alineado con el marco Hielco.
Afecta a 7 archivos. Requiere migración de datos de 3 situaciones existentes.
Implementación en 6 fases, de menor a mayor riesgo.

---

## FASE 0 — MIGRACIÓN DE DATOS EXISTENTES (CRÍTICO: HACER PRIMERO)

### Situaciones a preservar:
- Frontera Energy Corporation (FEC.TO) — Active
- Elme Communities (ELME) — Active
- Workspace Group Plc (WKP.L) — Active

### Campos nuevos a añadir en specific_data con defaults seguros:
- close_probability: 90
- outside_date: null
- break_fee_pct: 0.0
- downside_price: 0.0
- reinforce_price: 0.0
- reduce_price: 0.0
- checklist_global: {}
- checklist_specific: {}
- scenario_bear: {price: 0, prob: 20}
- scenario_base: {price: 0, prob: 65}
- scenario_bull: {price: 0, prob: 15}

### Acción: Crear scripts/migrate_ss_v2.py
1. Backup de la BD antes de modificar
2. Lee las 3 situaciones
3. Añade campos nuevos preservando todos los datos existentes

---

## FASE 1 — TIPOS Y CATEGORÍAS SIMPLIFICADOS
**Archivo: core/special_definitions.py**

### Nueva SITUATION_CATEGORIES (7 cats, 16 tipos):

M&A Arbitrage:
  - Merger Arbitrage (Cash)
  - Merger Arbitrage (Stock)
  - Going Private (LBO)
  - Tender Offer / Dutch Auction   [FUSIÓN de Dutch Auction]

Contingent Rights:
  - Contingent Value Rights (CVR)
  - Litigation Arbitrage

Restructuring & Spinoffs:
  - Spin-off
  - Split-off
  - Equity Carve-out

Capital Events:
  - Rights Offering
  - Odd Lot Tender
  - Special Dividend / Asset Sale

Distress & Liquidation:
  - Liquidations   [+ soporte XIRR]
  - Post-Bankruptcy (Emergence)   [renombrado]

Activist & Catalyst:
  - Holding Discount / SOTP   [NUEVO]
  - Index Inclusion/Exclusion  [NUEVO, de Macro&Technical]

Other:
  - Generic                    [comodín universal]
  [Resto de Macro&Technical fusionados aquí]

### Cambios en calculate_global_core():
Nuevos parámetros: close_probability (float 0-1), break_fee_pct (float)
Nuevas métricas:
  - ev_weighted = p*spread + (1-p)*downside_pct
  - ev_price = p*target + (1-p)*downside_price
  - irr_no_deal = IRR anualizada si se cobra downside_price
  - break_fee_signal = break_fee_pct / spread

### Nuevo: calculate_xirr(cashflows, dates)
Para Liquidaciones con pagos múltiples.
Newton-Raphson sin dependencias externas.

### CHECKLIST_GLOBAL (10 items universales):
- tesis_catalizador: "Tesis y catalizador claros y fechados"
- doc_oficial: "Documentación oficial verificada"
- estructura_evento: "Estructura del evento clara (cash/stock/collar)"
- financiacion: "Financiación asegurada y contrapartes creíbles"
- alineacion_accionarial: "Alineación accionarial y gobernanza"
- valoracion_downside: "Valoración y downside modelizado"
- cronograma: "Cronograma y riesgo de tiempo calculado"
- prob_cierre: "Probabilidad de cierre con precedentes"
- liquidez_operativa: "Liquidez, operativa y costes calculados"
- plan_salida: "Plan de posición y reglas de salida"

### CHECKLIST_BY_TYPE (específicos por tipo):
Merger Arbitrage (Cash): 5 items (oferta firme, break fees, aprobaciones, outside date, downside)
Merger Arbitrage (Stock): 3 items (collar, riesgo adquirente, hedge)
CVR: 4 items (trigger, ventana, garantía, reporting)
Spin-off: 5 items (motivación, incentivos mgmt, deuda, presión técnica, SOTP)
Liquidations: 5 items (inventario, costes, pasivos, calendario pagos, incentivos gestor)
Rights Offering: 4 items (necesidad capital, aseguramiento, TERP, uso fondos)
Odd Lot Tender: 3 items (prioridad, elegibilidad, fechas/custodios)
Post-Bankruptcy: 4 items (plan, estructura, overhang, covenants)
Generic: 0 items adicionales

---

## FASE 2 — MOTOR DE CÁLCULO Y WIZARD

### 2A — Wizard: nuevos campos

Sección Financials (ampliar):
  - Entry Price (Avg)      [existente]
  - Deal / Target Price    [existente]
  - Downside Price         [NUEVO, universal]
  - Break Fee (%)          [NUEVO]
  - Capital Allocated      [existente]

Sección Timeline (ampliar):
  - Start Date             [existente]
  - Expected Close Date    [renombrar Target Date]
  - Outside Date           [NUEVO — hard deadline]

Sección Deal Parameters (nueva):
  - Close Probability (%)  [slider visual 0-100, default 90]

Comportamiento al cambiar tipo (G1):
  - Popup de aviso antes de cambiar
  - Se conservan: entry_price, deal_value, downside_price, close_probability,
    outside_date, break_fee_pct, notas, archivos
  - Se resetea: checklist_specific, custom_attributes

### 2B — Panel Analysis renovado

Columna izquierda (INPUTS):
  - Inputs dinámicos por tipo [existente]
  - + Downside Price [universal, siempre visible]
  - + Slider Close Probability (%) con valor numérico en tiempo real
  - + Reinforce Price (umbral compra para F2)
  - + Reduce Price (umbral venta para F2)

Columna derecha (CALCULOS) — 3 secciones:

  Sección 1 — Métricas clave (6 labels expandidos):
    Spread: X.XX%
    IRR (entrada): X.XX% anual
    IRR (actual):  X.XX% anual
    EV Ponderado %: X.XX%
    EV Precio: X.XX currency
    Days to Close: NN días
    Risk/Reward: X.X : 1
    IRR si No-Deal: -X.XX%
    Break Fee Signal: X.Xx (spread)

  Sección 2 — Escenarios (tabla editable inline):
    Columnas: BEAR | BASE | BULL
    Filas: Precio | Prob% | IRR%
    Editable: precio y prob; IRR calculado automáticamente

  Sección 3 — Outside Date:
    "Quedan NN días — [fecha]"
    Barra de urgencia (roja si <30 días, naranja si <60, verde si >90)

---

## FASE 3 — PESTAÑA CHECKLIST HIELCO

Nueva tab insertada después de Analysis, antes de Timeline.
Nombre dinámico: "Checklist N/M" donde N=marcados, M=total.
Color del tab: rojo(0-4), naranja(5-6), amarillo(7-8), verde(9+).

### Layout de cada item:
Opción C del usuario:
  [checkbox] Título corto                              [▼ expandir]
             └── QTextEdit (aparece al hacer click ▼)
                 [Escribe tu respuesta aquí...]

### Comportamiento:
  - Al escribir texto en el QTextEdit: el checkbox se activa automáticamente
  - Se puede marcar el checkbox sin texto
  - Collapse/expand independiente por item
  - Auto-guardado en specific_data['checklist_global'] y ['checklist_specific']

### Estructura del guardado en specific_data:
checklist_global: {
  "tesis_catalizador": {"checked": true, "notes": "El deal es a..."},
  "doc_oficial": {"checked": false, "notes": ""},
  ...
}
checklist_specific: {
  "oferta_firme": {"checked": true, "notes": "Acuerdo firmado el..."},
  ...
}

---

## FASE 4 — PROGRESO COMPUESTO

### Fórmula (100% total):

Checklist (40%):
  - 10 globales: 2% por check = 20% max
  - N específicos según tipo: prorrateado = 20% max
    (ej: Merger Cash tiene 5 específicos → 4% por check)

Archivos leídos (25%):
  - 1er archivo marcado "leído" = 12.5%
  - 2do archivo marcado "leído" = 12.5%
  - Cap en 25%

Tiempo Pomodoro (25%):
  - tiempo_registrado_en_horas / 10 * 25
  - Cap en 25% (≥10h = 25%)

Notas (10%):
  - ≥1 nota cualquiera = 5%
  - ≥3 notas en total = 10%

### Cálculo en special_manager.py:
Nuevo método: calculate_progress_score(situation_data, pomodoro_hours) -> float (0-100)

### Columnas F2 Special Situations (nuevo orden):
Ticker | Status | Price | IRR(E) | IRR(M) | EV% | Days | Reinforce | Reduce | Progress

Reinforce y Reduce: sacados de specific_data donde el usuario los define en Analysis.

---

## FASE 5 — NOTAS, ARCHIVOS Y TABS RESTANTES

### E1 — Orden invertido notas (newest first):
En situation_notes.py -> SituationNotesWidget.load_notes():
  notes_list.sort(key=lambda x: x['timestamp'], reverse=True)

Aplicar también en Library (F3) si usa el mismo widget.

### E1b — Tablas HTML en notas:
NoteEntryWidget:
  - Visualización: QTextBrowser (soporta HTML: tablas, bold, listas)
  - Edición: QTextEdit con setAcceptRichText(True)
  - Guardado: .toHtml() si contains("<"), else plain text
  - Carga: detectar "<!DOCTYPE" o "<table" → cargar como HTML

### E2 — Clasificación de archivos (Tab Files):
Categorías: Filing | Folleto | Regulatorio | Análisis-Propio | Modelo | Prensa | Otro
Cada fila: [Nombre] [Categoría-badge] [Fecha] [Leído ✓] [Abrir] [Eliminar]
Añadir referencia manual: botón "+ Sin archivo (URL/nombre)"
Estado "Leído" conectado al cálculo de progreso (Fase 4)

### E3 — Tabs Riesgos y Shareholders:
Mismo SituationNotesWidget reutilizado.
Newest first.
Soporte HTML.

---

## FASE 6 — COLUMNAS F2 Y DUAL IRR

### special_manager.py — get_all_situations_summary():
Añadir al dict de retorno:
  - downside_price (de specific_data, default 0)
  - close_probability (de specific_data, default 0.90)
  - reinforce_price (de specific_data, default 0)
  - reduce_price (de specific_data, default 0)
  - outside_date (de specific_data, default None)
  - progress_score (llamar calculate_progress_score)

### companies_view.py — populate_table() para Special Situations:
IRR(E): calculate_global_core(entry_price, deal_value, downside_price, target_date, prob)
IRR(M): calculate_global_core(current_market_price, deal_value, downside_price, target_date, prob)
current_market_price: del price cache (self.price_cache o similar)
Si no hay precio de mercado: IRR(M) = "--"

---

## ARCHIVOS AFECTADOS

scripts/migrate_ss_v2.py          NUEVO       Riesgo: Bajo
core/special_definitions.py       REFACTOR    Riesgo: Medio
core/special_manager.py           AMPLIAR     Riesgo: Bajo
ui/widgets/special_situations.py  REFACTOR    Riesgo: Alto
ui/widgets/situation_notes.py     AMPLIAR     Riesgo: Bajo
ui/views/companies_view.py        AMPLIAR     Riesgo: Medio
version.py                        V.7.50      Riesgo: Trivial

---

## REGLAS DE NO ROMPER

1. Las 3 situaciones existentes NUNCA pierden datos
2. Script de migración hace backup ANTES de tocar la BD
3. Campos nuevos siempre tienen defaults seguros (no null que rompa calculos)
4. Al cambiar tipo en wizard: popup + preservar campos comunes
5. IRR(M) = "--" si no hay precio de mercado (no crash)
6. Progreso formula nueva: datos nuevos a 0 por defecto = 0% progreso (no crash)
7. XIRR: si hay error de convergencia, devolver IRR simple como fallback
