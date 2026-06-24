# Changelog

## [v8.2.1] - 2026-03-01
### Fixed
- **Missing Account:** Reactivated "Cuenta Formacion Rafa" so it loads properly in the wizard.
- **Excel Bridge Mappings:** Fixed the mapping for `Cuenta Ahorro (Instan saving) Cris` to tolerate nomenclature discrepancies and properly export its value. Ensured that numeric injections respect Excel's standard `#,##0` formatting to avoid visual decimal pollution.
- **Real Estate Automation:** Intercepted the manual wizard generation to automatically add a +2% annual (compounded monthly) appreciation on the real estate pre-fill value, giving the user the exact math to confirm.
- **Analytics Isolation:** Reprogrammed Analytics so it doesn't mesh "Fondo Monetario Cris" with "Fundsmith Cris". Fondo Monetario is safely categorized as Bank & Liquidity (Cash), preserving pure Fundsmith analysis.
- **Equity Aportado Logic:** Handled new custom fields (`Aportado Hipoteca Cris/Rafa`) natively in Ekomonos Database without double-counting them into the Net Worth algorithm.

## [v8.2.0] - "The Excel Bridge" - 2026-03-01
### Added
- **`core.excel_bridge` (OpenPyXL Engine):** Engineered an invisible native python bridge to write manual data from the step-wizard directly to `Master_Balance.xlsx` automatically without modifying headers or destroying layout strings. It intelligently locates 'Enero/26' and populates the right column with accurate data.
- **F7 Wealth Analytics Overhaul:** The Net Worth, Cash, IBKR, and Fundsmith cards in F7 are now tethered to the live SQL database and no longer run off dummy strings. Added logic to automatically distribute the "House Equity" exactly 50/50 among both spouses.
- **Advanced Deuda Handling:** Renamed "Deuda Interna Rafa" to "Deuda Equity Casa Cris" and integrated the financial arithmetic: deduct £13,000 from Rafa's net worth calculation into Cris's net worth safely every time Analytics computes the Dashboard.
- **Category 69:** Appended native "Gastos Variables: Amazon" capability.

## [v8.1.10] - 2026-03-01
### Changed
- **Total Clean Slate Paradigm:** Wiped the database cache of false January 2026 data. Removed internal code in `WealthWizard` that fetched historic snapshots when loading forms. Forms now start pristine with £0.00 each month, cementing the philosophy that nothing is inferred — only read from user input or Master_Balance.xlsx.

## [v8.1.9] - 2026-03-01
### Changed
- **Architecture Shift (Hybrid Excel Mode):** Removed the "Upload IBKR CSV" button from the Wealth Wizard and severed the internal profit recalculation engine. Ekomonos now respects `Master_Balance.xlsx` as the single source of truth for investment inputs. The wizard is now exclusively focused on banking cashflow and classification, awaiting the final bridge to the Excel master root.
- Cleaned up obsolete modules (`balance_sheet.py`, `wealth_exporter.py`) and various temporary CSV/log files that clotted the project directory.

## [v8.1.8] - 2026-02-28
### Added/Fixed
- **IBKR Profit & Cris Funds Bugfix:** Fixed a severe logical flaw where Cris's "Fondo Monetario" was misidentified by the wizard due to a change in the database. `cris_total` successfully evaluates to include her new CSV deposits dynamically, even if the BOF/IBKR files are uploaded in reverse order.
- Embedded "Gastos Fijos: Suscripciones" and "Inversion: Cris Fundsmith" to the Global default Categories.

## [v8.1.7] - 2026-02-28
### Added
- **Dynamic Categories Manager:** A completely new subsystem. Categorization is no longer hardcoded into the app's core algorithm. Click the new `⚙` button inside the Analytics Tab (Next to '+ Monthly Update') to modify, create, remove or re-assign shortcut numbers to ANY category you like.
- Categories are saved persistently so every future transaction analysis respects your personal shortcut keys and tags globally.

## [v8.1.6] - 2026-02-28
### Added/Fixed
- Cleaned up Transaction Review Dialog constraints: Now entire tables rows are selected dynamically instead of single cells, preventing edit-locking issues. Increased viewport vertical height by 30%.
- Interactive Combobox formatting directly embeds the Quick-key into the Text. Removed redundant top-yellow title overlays for cleaner reading.
- Radically fixed IBKR Profit allocation Math. `Nav Profit` is now analytically deduced as `(Total NAV) - (Total Cristina's Capital) - (Total Rafa's Aportaciones)`, resolving the severe double-counting issue that inflated Capital previously.

## [v8.1.5] - 2026-02-28
### Added
- Created Split "Gastos Variables" (Supermercado, Transporte, Ocio, Vestimenta) and "Gastos Fijos" (Hipoteca, Seguros).
- Re-categorized "Cuota a Familia" as a non-expense internal Transfer ("Blue-Gray" icon).
- Included secondary Incomes like "Ingreso Extra" explicitly.

## [v8.1.4] - 2026-02-28
### Added
- Rebuilt Interactive Brokers CSV parser to robustly read the new custom "Activity Statement" formats, capturing NAV from the `Account Summary` block directly, and extracting net `Deposits & Withdrawals`.

## [v8.1.3] - 2026-02-28
### Fixed
- Caught Unhandled Pandas Exceptions (`UnicodeDecodeError`, `ParserError`) that caused the UI to silently crash when selecting incorrectly formatted, blank, or wrongly exported CSV files.

## [v8.1.2] - 2026-02-28
### Added
- Expanded numeric quick-tagging keys to support two-tier groupings (e.g. `5` for Gasto -> `51` para Hipoteca, `53` para Casa, etc.). The Legend updates dynamically on prefixes.

### Fixed
- Fixed critical application crash when confirming edited transactions for personal accounts, stemming from missing account `name` attributes accessed by the UI calculation logic.

## [v8.1.1] - 2026-02-28
### Fixed
- Fixed crash when saving `Monthly Update` when parsing all accounts for multiple users simultaneously due to key overlap.
- Added numeric rapid-classification shortcuts to `TransactionReviewDialog` for faster tagging without a mouse.
- Extracted and enhanced `IncomeRecord` allocations using updated smart sub-menus.

## [v8.1.0] - 2026-02-28
### Added
- Integrated Advanced AI Parsing for Personal and Joint Bank Statements.

## [v0.2] - 2025-12-10
### Added
- **Unified Library Interface**: Merged 'Input Stock' and 'Library' into a single cohesive "Libreria" tab.
    - Added "Select Company" dropdown with auto-refresh.
    - Integrated "Company Header" with dynamic metrics (Logo, Timer, Progress).
    - New "Company Milestones" visualization.
- **Improved Pomodoro**:
    - Added "Manual Log" button.
    - Timer sessions now attribute time to specific companies.
    - Real-time updates to company "Hours Invested" in the header.
- **Company Management**:
    - Created "New Company" wizard with folders (Reference, Transcripts, Excel, Varios) and metadata.
    - Added "Edit Company" dialog to modify details (Links, Hours).
- **UI Enhancements**:
    - Reordered sidebar: Libreria is now below Portfolio.
    - Refined "Company Header" layout (Yellow Logo, Action Buttons).

### Fixed
- Fixed crash when creating a new company or selecting one in the Library.
- Fixed `AttributeError` in embedded library mode by initializing data structures correctly.
- Corrected `LIBRARY_ROOT` path referencing issue that caused empty file lists.


## [v0.1] - 2025-12-03
### Added
- Initial release of Ekkomonos v0.1.
- "Black & Orange" professional financial theme.
- Core widgets: Dashboard, Portfolio, Pomodoro, PDF Manager (Libreria).
- Sidebar navigation.

### Notes
- Reverted from experimental "Deep Space" blue theme back to this stable version.
