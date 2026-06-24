# Workflow: Sync Calendar Earnings

## Cuándo Usar
- Después de añadir una nueva compañía
- Periódicamente para actualizar fechas de earnings

## Pasos

1. **Cierra la aplicación** (importante - evita conflictos de DB)

2. **Ejecuta el script:**
```bash
python sync_calendar_earnings.py
```

3. **Espera** - Puede tomar 1-2 minutos dependiendo del número de compañías

4. **Revisa resultados:**
   - Verás cuántas compañías se actualizaron
   - Algunas pueden fallar (delisted, non-US tickers) - es normal

5. **Abre la aplicación** - Las fechas estarán actualizadas en el calendario

## Notas
- El script NO crashea (no usa threading)
- Se puede ejecutar las veces que necesites
- Solo actualiza compañías que ya existen en el calendar DB
