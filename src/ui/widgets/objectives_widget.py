"""
Objectives Widget v3 — F12 Objetivos Anuales (Simplified)

Three clean tabs:
  1. HOY         — Daily ONE Thing commitment + 14-day history strip
  2. MIS PILARES — 5 objective cards with monthly status (once-a-month review)
  3. LECTURA     — Book log + daily pages goal + stats

Daily popup (once per day): asks the ONE Thing via a small modal.
"""

from datetime import date, timedelta
import core.objectives_manager as om

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QLineEdit, QFrame, QScrollArea, QDialog,
    QDialogButtonBox, QSpinBox, QMessageBox, QComboBox,
    QSizePolicy, QApplication,
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

# ── Colours (matching app palette) ────────────────────────────────────────────
BG       = "#0D0D0D"
SURFACE  = "#151515"
SURFACE2 = "#1C1C1C"
SURFACE3 = "#242424"
BORDER   = "#2A2A2A"
TEXT     = "#EAEAEA"
TEXT_DIM = "#888888"
ORANGE   = "#FF9800"
GOLD     = "#FFD700"
GREEN    = "#27AE60"
YELLOW   = "#F1C40F"
RED      = "#E74C3C"
BLUE     = "#3498DB"

# Status cycle: click to rotate
STATUS_CYCLE = ["green", "yellow", "red"]
STATUS_LABEL = {"green": "En camino 🟢", "yellow": "Advertencia 🟡", "red": "En riesgo 🔴"}
STATUS_COLOR = {"green": GREEN, "yellow": YELLOW, "red": RED}

CURRENT_YEAR = date.today().year
CURRENT_MONTH = date.today().strftime("%Y-%m")

# ── Helpers ───────────────────────────────────────────────────────────────────

def _label(text, color=TEXT, size=12, bold=False, align=Qt.AlignmentFlag.AlignLeft):
    l = QLabel(text)
    l.setStyleSheet(
        f"color: {color}; font-size: {size}px;"
        f" font-weight: {'bold' if bold else 'normal'};"
        " background: transparent;"
    )
    l.setAlignment(align)
    l.setWordWrap(True)
    return l


def _hrule(color=BORDER):
    h = QFrame()
    h.setFrameShape(QFrame.Shape.HLine)
    h.setStyleSheet(f"background: {color}; border: none; max-height: 1px; margin: 4px 0;")
    return h


def _btn(text, bg=SURFACE3, fg=TEXT, bold=False, tip=""):
    b = QPushButton(text)
    b.setStyleSheet(
        f"QPushButton {{ background-color: {bg}; color: {fg}; border: 1px solid {BORDER};"
        f" border-radius: 6px; padding: 7px 14px; font-size: 12px;"
        f" font-weight: {'bold' if bold else 'normal'}; }}"
        f"QPushButton:hover {{ background-color: {ORANGE}; color: #000; }}"
    )
    if tip:
        b.setToolTip(tip)
    return b


BASE_STYLE = f"""
    QWidget {{ background-color: {BG}; color: {TEXT}; font-family: 'Segoe UI', Arial, sans-serif; }}
    QScrollArea {{ border: none; background: transparent; }}
    QScrollBar:vertical {{ background: {SURFACE2}; width: 6px; border-radius: 3px; }}
    QScrollBar::handle:vertical {{ background: {BORDER}; border-radius: 3px; }}
    QLineEdit, QTextEdit, QSpinBox {{
        background: {SURFACE2}; color: {TEXT}; border: 1px solid {BORDER};
        border-radius: 5px; padding: 6px; font-size: 12px;
    }}
    QLineEdit:focus, QTextEdit:focus {{ border-color: {ORANGE}; }}
    QComboBox {{ background: {SURFACE2}; color: {TEXT}; border: 1px solid {BORDER};
                 border-radius: 5px; padding: 5px; font-size: 12px; }}
    QComboBox QAbstractItemView {{ background: {SURFACE2}; color: {TEXT}; }}
"""


# ── Tab 1 — HOY (Daily ONE Thing) ─────────────────────────────────────────────

class TodayTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(BASE_STYLE)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 28, 32, 28)
        root.setSpacing(20)

        # Header
        hdr = _label("☀️  TU ONE THING DE HOY", GOLD, 14, bold=True)
        root.addWidget(hdr)

        sub = _label(
            "Una sola cosa. La más importante. La que hace que todo lo demás sea más fácil o innecesario.",
            TEXT_DIM, 11
        )
        root.addWidget(sub)

        root.addWidget(_hrule(ORANGE + "55"))

        # Today's input
        today_focus = om.get_today_focus()
        self.txt_focus = QTextEdit()
        self.txt_focus.setPlaceholderText(
            "¿Qué es LO ÚNICO que harás hoy que marcará la diferencia?"
        )
        if today_focus:
            self.txt_focus.setPlainText(today_focus["focus_text"])
        self.txt_focus.setFixedHeight(90)
        self.txt_focus.setStyleSheet(
            f"background: {SURFACE2}; color: {TEXT}; border: 2px solid {ORANGE}44;"
            " border-radius: 8px; padding: 10px; font-size: 14px;"
        )
        root.addWidget(self.txt_focus)

        btn_commit = _btn("✅  Comprometerse para hoy", bg=ORANGE, fg="#000", bold=True)
        btn_commit.setFixedHeight(42)
        btn_commit.clicked.connect(self._commit)
        root.addWidget(btn_commit)

        root.addWidget(_hrule())

        # 14-day history strip
        hist_hdr = _label("ÚLTIMOS 14 DÍAS", TEXT_DIM, 10, bold=True)
        root.addWidget(hist_hdr)

        self.strip_frame = QFrame()
        self.strip_layout = QVBoxLayout(self.strip_frame)
        self.strip_layout.setContentsMargins(0, 0, 0, 0)
        self.strip_layout.setSpacing(4)
        root.addWidget(self.strip_frame)

        root.addStretch()

    def _commit(self):
        text = self.txt_focus.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Sin compromiso",
                "Escribe tu ONE THING antes de comprometerte.")
            return
        om.save_today_focus(text)
        om.mark_popup_shown()
        self.refresh()

    def refresh(self):
        # Clear history
        while self.strip_layout.count():
            item = self.strip_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        focuses = om.get_recent_focuses(14)
        focus_by_date = {f["date"]: f["focus_text"] for f in focuses}

        today = date.today()
        for i in range(13, -1, -1):
            d = today - timedelta(days=i)
            ds = d.isoformat()
            text = focus_by_date.get(ds, "")
            is_today = (i == 0)

            row = QFrame()
            row.setStyleSheet(
                f"background: {'#1A1A0A' if is_today else SURFACE2};"
                f" border-radius: 6px;"
                f" border-left: 3px solid {ORANGE if is_today else (GREEN if text else BORDER)};"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 6, 10, 6)
            rl.setSpacing(10)

            day_lbl = _label(
                d.strftime("%a %d/%m") + (" ← Hoy" if is_today else ""),
                ORANGE if is_today else (TEXT if text else TEXT_DIM),
                11, bold=is_today
            )
            day_lbl.setFixedWidth(110)
            rl.addWidget(day_lbl)

            focus_lbl = _label(
                text if text else "— sin compromiso",
                TEXT if text else TEXT_DIM,
                11
            )
            rl.addWidget(focus_lbl, 1)

            self.strip_layout.addWidget(row)


# ── Tab 2 — MIS PILARES (Monthly Review) ─────────────────────────────────────

class ObjectivePillarCard(QFrame):
    """A single objective card for the monthly review."""
    def __init__(self, obj: dict, month: str, parent=None):
        super().__init__(parent)
        self.obj = obj
        self.month = month
        self.review = om.get_monthly_review(obj["id"], month) or {}
        self._current_status = self.review.get("status", "yellow")
        self._build()

    def _build(self):
        color = self.obj.get("color", ORANGE)
        is_one = bool(self.obj.get("is_the_one_thing"))

        self.setStyleSheet(
            f"QFrame {{ background: {SURFACE2}; border-radius: 10px;"
            f" border: 2px solid {GOLD if is_one else color}33; }}"
        )

        lay = QVBoxLayout(self)
        lay.setContentsMargins(16, 14, 16, 14)
        lay.setSpacing(8)

        # Title row
        crown = "⭐ " if is_one else ""
        ttl = _label(f"{crown}{self.obj['title']}", color, 13, bold=True)
        lay.addWidget(ttl)

        # Purpose (one line)
        purpose = self.obj.get("purpose", "")
        if purpose:
            p_lbl = _label(purpose[:90] + ("…" if len(purpose) > 90 else ""), TEXT_DIM, 10)
            lay.addWidget(p_lbl)

        lay.addWidget(_hrule())

        # Status button (click to cycle)
        s_color = STATUS_COLOR.get(self._current_status, YELLOW)
        self.btn_status = QPushButton(STATUS_LABEL.get(self._current_status, "🟡"))
        self.btn_status.setStyleSheet(
            f"QPushButton {{ background: {s_color}22; color: {s_color};"
            f" border: 1px solid {s_color}66; border-radius: 6px; padding: 5px 10px;"
            f" font-size: 11px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {s_color}44; }}"
        )
        self.btn_status.clicked.connect(self._cycle_status)
        lay.addWidget(self.btn_status)

        # Monthly action text
        lay.addWidget(_label("Mi foco este mes:", TEXT_DIM, 10))
        self.txt_monthly = QLineEdit()
        self.txt_monthly.setPlaceholderText("¿Qué UN paso daré este mes?")
        self.txt_monthly.setText(self.review.get("monthly_action", ""))
        self.txt_monthly.setStyleSheet(
            f"background: {SURFACE3}; color: {TEXT}; border: 1px solid {BORDER};"
            " border-radius: 5px; padding: 6px; font-size: 12px;"
        )
        self.txt_monthly.editingFinished.connect(self._save)
        lay.addWidget(self.txt_monthly)

        # Weekly action
        lay.addWidget(_label("Acción esta semana:", TEXT_DIM, 10))
        self.txt_weekly = QLineEdit()
        self.txt_weekly.setPlaceholderText("¿Qué haré esta semana concretamente?")
        self.txt_weekly.setText(self.review.get("weekly_action", ""))
        self.txt_weekly.setStyleSheet(
            f"background: {SURFACE3}; color: {TEXT}; border: 1px solid {BORDER};"
            " border-radius: 5px; padding: 6px; font-size: 12px;"
        )
        self.txt_weekly.editingFinished.connect(self._save)
        lay.addWidget(self.txt_weekly)

    def _cycle_status(self):
        idx = STATUS_CYCLE.index(self._current_status) if self._current_status in STATUS_CYCLE else 1
        self._current_status = STATUS_CYCLE[(idx + 1) % len(STATUS_CYCLE)]
        s_color = STATUS_COLOR[self._current_status]
        self.btn_status.setText(STATUS_LABEL[self._current_status])
        self.btn_status.setStyleSheet(
            f"QPushButton {{ background: {s_color}22; color: {s_color};"
            f" border: 1px solid {s_color}66; border-radius: 6px; padding: 5px 10px;"
            f" font-size: 11px; font-weight: bold; }}"
            f"QPushButton:hover {{ background: {s_color}44; }}"
        )
        self._save()

    def _save(self):
        om.save_monthly_review(
            objective_id=self.obj["id"],
            month=self.month,
            status=self._current_status,
            monthly_action=self.txt_monthly.text().strip(),
            weekly_action=self.txt_weekly.text().strip(),
        )


class PilaresTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(BASE_STYLE)
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(28, 24, 28, 24)
        root.setSpacing(16)

        # Header
        month_str = date.today().strftime("%B %Y").capitalize()
        hdr_row = QHBoxLayout()
        hdr = _label(f"🏆  MIS 5 PILARES — {month_str}", GOLD, 14, bold=True)
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()

        # Month picker
        self.combo_month = QComboBox()
        months = []
        d = date.today()
        for i in range(12):
            months.append((date(d.year, d.month, 1) - timedelta(days=30 * i)).strftime("%Y-%m"))
        for m in months:
            self.combo_month.addItem(m, m)
        self.combo_month.setCurrentText(CURRENT_MONTH)
        self.combo_month.setFixedWidth(110)
        self.combo_month.currentTextChanged.connect(self._reload_cards)
        hdr_row.addWidget(self.combo_month)
        root.addLayout(hdr_row)

        sub = _label(
            "Entra aquí una vez al mes. Revisa el estado, escribe tu foco y tu acción semanal. Sal y ejecuta.",
            TEXT_DIM, 11
        )
        root.addWidget(sub)
        root.addWidget(_hrule(ORANGE + "55"))

        # Scroll area for cards
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        inner = QWidget()
        inner.setStyleSheet("background: transparent;")
        self.cards_layout = QVBoxLayout(inner)
        self.cards_layout.setSpacing(12)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(inner)
        root.addWidget(scroll, 1)

        self._load_cards(CURRENT_MONTH)

    def _reload_cards(self, month: str):
        self._load_cards(month)

    def _load_cards(self, month: str):
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        objectives = om.get_objectives(CURRENT_YEAR)
        if not objectives:
            self.cards_layout.addWidget(
                _label("No hay objetivos para este año. Añádelos en la base de datos.", TEXT_DIM, 12)
            )
            return

        for obj in objectives:
            card = ObjectivePillarCard(obj, month)
            self.cards_layout.addWidget(card)

        self.cards_layout.addStretch()


# ── Tab 3 — LECTURA (Reading Tracker) ────────────────────────────────────────

class LecturaTab(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(BASE_STYLE)
        self._build()
        self.refresh()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(32, 24, 32, 24)
        root.setSpacing(16)

        # Header
        root.addWidget(_label("📚  HÁBITO DE LECTURA", GOLD, 14, bold=True))
        root.addWidget(_label(
            "Registra los libros que terminas. Mantén tu ritmo de páginas/día visible para motivarte.",
            TEXT_DIM, 11
        ))
        root.addWidget(_hrule(ORANGE + "55"))

        # Stats bar
        self.stats_frame = QFrame()
        self.stats_frame.setStyleSheet(
            f"background: {SURFACE2}; border-radius: 8px; border: 1px solid {BORDER};"
        )
        self.stats_row = QHBoxLayout(self.stats_frame)
        self.stats_row.setContentsMargins(16, 12, 16, 12)
        self.stats_row.setSpacing(24)
        root.addWidget(self.stats_frame)

        root.addWidget(_hrule())

        # Daily goal
        goal_row = QHBoxLayout()
        goal_row.addWidget(_label("Meta diaria:", TEXT_DIM, 12))
        self.spin_goal = QSpinBox()
        self.spin_goal.setRange(1, 500)
        self.spin_goal.setValue(int(om.get_setting("reading_daily_goal", "20")))
        self.spin_goal.setSuffix(" pág/día")
        self.spin_goal.setFixedWidth(130)
        self.spin_goal.setStyleSheet(
            f"background: {SURFACE2}; color: {TEXT}; border: 1px solid {BORDER};"
            " border-radius: 5px; padding: 5px;"
        )
        goal_row.addWidget(self.spin_goal)
        btn_save_goal = _btn("Guardar", bg=SURFACE3)
        btn_save_goal.setFixedWidth(80)
        btn_save_goal.clicked.connect(self._save_goal)
        goal_row.addWidget(btn_save_goal)
        goal_row.addStretch()
        root.addLayout(goal_row)

        root.addWidget(_hrule())

        # Add book form
        add_hdr = _label("Añadir libro terminado:", TEXT_DIM, 11, bold=True)
        root.addWidget(add_hdr)

        form_row = QHBoxLayout()
        form_row.setSpacing(8)

        self.txt_title = QLineEdit()
        self.txt_title.setPlaceholderText("Título del libro")
        form_row.addWidget(self.txt_title, 3)

        self.txt_author = QLineEdit()
        self.txt_author.setPlaceholderText("Autor (opcional)")
        form_row.addWidget(self.txt_author, 2)

        self.spin_pages = QSpinBox()
        self.spin_pages.setRange(1, 5000)
        self.spin_pages.setValue(300)
        self.spin_pages.setSuffix(" pág")
        self.spin_pages.setFixedWidth(100)
        self.spin_pages.setStyleSheet(
            f"background: {SURFACE2}; color: {TEXT}; border: 1px solid {BORDER};"
            " border-radius: 5px; padding: 5px;"
        )
        form_row.addWidget(self.spin_pages)

        self.txt_date = QLineEdit()
        self.txt_date.setPlaceholderText(date.today().isoformat())
        self.txt_date.setFixedWidth(110)
        form_row.addWidget(self.txt_date)

        btn_add = _btn("+ Añadir", bg=ORANGE, fg="#000", bold=True)
        btn_add.setFixedWidth(90)
        btn_add.clicked.connect(self._add_book)
        form_row.addWidget(btn_add)

        root.addLayout(form_row)

        root.addWidget(_hrule())

        # Book list (scroll)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background: transparent;")
        self.books_inner = QWidget()
        self.books_inner.setStyleSheet("background: transparent;")
        self.books_vbox = QVBoxLayout(self.books_inner)
        self.books_vbox.setSpacing(4)
        self.books_vbox.setContentsMargins(0, 0, 0, 0)
        self.books_vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self.books_inner)
        root.addWidget(scroll, 1)

    def _save_goal(self):
        om.set_reading_daily_goal(self.spin_goal.value())
        self.refresh()

    def _add_book(self):
        title = self.txt_title.text().strip()
        if not title:
            QMessageBox.warning(self, "Título requerido", "Escribe el título del libro.")
            return
        author = self.txt_author.text().strip()
        pages = self.spin_pages.value()
        date_fin = self.txt_date.text().strip() or date.today().isoformat()
        om.add_book(title, author, pages, date_fin)
        self.txt_title.clear()
        self.txt_author.clear()
        self.spin_pages.setValue(300)
        self.txt_date.clear()
        self.refresh()

    def refresh(self):
        # Rebuild stats bar
        while self.stats_row.count():
            item = self.stats_row.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        stats = om.get_reading_stats(CURRENT_YEAR)

        def stat_block(val, label, color=TEXT):
            f = QFrame()
            f.setStyleSheet("background: transparent;")
            col = QVBoxLayout(f)
            col.setSpacing(2)
            col.setContentsMargins(0, 0, 0, 0)
            vl = _label(str(val), color, 22, bold=True,
                        align=Qt.AlignmentFlag.AlignCenter)
            ll = _label(label, TEXT_DIM, 10, align=Qt.AlignmentFlag.AlignCenter)
            col.addWidget(vl)
            col.addWidget(ll)
            return f

        goal = stats["daily_goal"]
        avg = stats["avg_pages_day"]
        pct_color = GREEN if avg >= goal else (YELLOW if avg >= goal * 0.6 else RED)

        self.stats_row.addWidget(stat_block(stats["total_books"], f"libros en {CURRENT_YEAR}", GOLD))
        self.stats_row.addWidget(stat_block(stats["total_pages"], "páginas totales", BLUE))
        self.stats_row.addWidget(stat_block(f"{avg}", "pág/día (media)", pct_color))
        self.stats_row.addWidget(stat_block(f"{goal}", "meta pág/día", TEXT_DIM))
        self.stats_row.addWidget(stat_block(f"{stats['goal_pct']}%", "objetivo cumplido",
                                             GREEN if stats["goal_pct"] >= 100 else YELLOW))
        self.stats_row.addStretch()

        # Rebuild book list
        while self.books_vbox.count():
            item = self.books_vbox.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        books = om.get_books(CURRENT_YEAR)
        if not books:
            self.books_vbox.addWidget(
                _label("Sin libros registrados este año. ¡Añade el primero!", TEXT_DIM, 12)
            )
            return

        # Header row
        hdr_row = QFrame()
        hdr_row.setStyleSheet(f"background: {SURFACE3}; border-radius: 5px;")
        hr = QHBoxLayout(hdr_row)
        hr.setContentsMargins(10, 6, 10, 6)
        for txt, w in [("Fecha", 100), ("Título", 0), ("Autor", 150), ("Páginas", 70)]:
            lbl = _label(txt, TEXT_DIM, 10, bold=True)
            if w:
                lbl.setFixedWidth(w)
            hr.addWidget(lbl, 0 if w else 1)
        hr.addWidget(_label("", TEXT_DIM, 10, bold=True))  # delete col
        self.books_vbox.addWidget(hdr_row)

        for b in books:
            row = QFrame()
            row.setStyleSheet(
                f"background: {SURFACE2}; border-radius: 5px;"
                f" border-left: 3px solid {GREEN};"
            )
            rl = QHBoxLayout(row)
            rl.setContentsMargins(10, 6, 10, 6)
            rl.setSpacing(8)

            date_lbl = _label(b.get("date_finished", "")[:10], TEXT_DIM, 11)
            date_lbl.setFixedWidth(100)
            rl.addWidget(date_lbl)

            title_lbl = _label(b["title"], TEXT, 12, bold=True)
            rl.addWidget(title_lbl, 1)

            author_lbl = _label(b.get("author", ""), TEXT_DIM, 11)
            author_lbl.setFixedWidth(150)
            rl.addWidget(author_lbl)

            pages_lbl = _label(f"{b.get('pages', 0)} pág", GOLD, 11, bold=True)
            pages_lbl.setFixedWidth(70)
            rl.addWidget(pages_lbl)

            btn_del = QPushButton("✕")
            btn_del.setFixedSize(24, 24)
            btn_del.setStyleSheet(
                f"background: transparent; color: {RED}; border: none; font-size: 11px;"
                f" border-radius: 4px;"
                f"QPushButton:hover {{ background: {RED}22; }}"
            )
            btn_del.clicked.connect(lambda _, bid=b["id"]: self._delete_book(bid))
            rl.addWidget(btn_del)

            self.books_vbox.addWidget(row)

    def _delete_book(self, book_id: int):
        reply = QMessageBox.question(
            self, "Eliminar libro", "¿Eliminar este libro del registro?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            om.delete_book(book_id)
            self.refresh()


# ── Daily Popup ───────────────────────────────────────────────────────────────

class DailyFocusPopup(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⭐ Tu ONE THING de hoy")
        self.setMinimumWidth(480)
        self.setWindowFlags(
            Qt.WindowType.Dialog | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setStyleSheet(
            f"QDialog {{ background: {SURFACE}; }} "
            f"QLabel {{ color: {TEXT}; }}"
        )
        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)

        title = _label("⭐  ¿Cuál es tu ONE THING de hoy?", GOLD, 16, bold=True)
        lay.addWidget(title)

        sub = _label(
            "La pregunta clave: ¿Qué única cosa puedo hacer hoy tal que, "
            "haciéndola, todo lo demás se vuelva más fácil o innecesario?",
            TEXT_DIM, 11
        )
        lay.addWidget(sub)

        lay.addWidget(_hrule(ORANGE + "55"))

        self.txt = QTextEdit()
        self.txt.setPlaceholderText("Escribe aquí tu única tarea del día…")
        self.txt.setFixedHeight(80)
        self.txt.setStyleSheet(
            f"background: {SURFACE2}; color: {TEXT}; border: 2px solid {ORANGE}55;"
            " border-radius: 6px; padding: 8px; font-size: 14px;"
        )
        lay.addWidget(self.txt)

        # Show yesterday's if existed
        yesterday = (date.today() - timedelta(days=1)).isoformat()
        conn = om.get_conn()
        row = conn.execute(
            "SELECT focus_text FROM daily_focus WHERE date=?", (yesterday,)
        ).fetchone()
        conn.close()
        if row:
            hint = _label(f"Ayer: {row[0][:80]}", TEXT_DIM, 10)
            lay.addWidget(hint)

        btns = QHBoxLayout()
        btns.addStretch()
        btn_skip = _btn("Más tarde", bg=SURFACE3, fg=TEXT_DIM)
        btn_skip.clicked.connect(self._skip)
        btns.addWidget(btn_skip)

        btn_ok = _btn("✅ Comprometerse", bg=ORANGE, fg="#000", bold=True)
        btn_ok.clicked.connect(self._commit)
        btns.addWidget(btn_ok)
        lay.addLayout(btns)

    def _commit(self):
        text = self.txt.toPlainText().strip()
        if not text:
            QMessageBox.warning(self, "Vacío", "Escribe algo antes de comprometerte.")
            return
        om.save_today_focus(text)
        om.mark_popup_shown()
        self.accept()

    def _skip(self):
        om.mark_popup_shown()  # Don't show again today even if skipped
        self.reject()


# ── Top-level tab bar ──────────────────────────────────────────────────────────

class TabBar(QWidget):
    """Simple custom tab bar."""
    def __init__(self, tabs: list, on_switch):
        super().__init__()
        self.setStyleSheet("background: transparent;")
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(4)
        self._btns = []
        self._on_switch = on_switch
        for i, (icon, label) in enumerate(tabs):
            b = QPushButton(f"{icon}  {label}")
            b.setCheckable(True)
            b.setChecked(i == 0)
            b.setFixedHeight(36)
            b.setStyleSheet(f"""
                QPushButton {{
                    background: {SURFACE2}; color: {TEXT_DIM};
                    border: 1px solid {BORDER};
                    border-radius: 6px; padding: 0 18px; font-size: 12px;
                }}
                QPushButton:checked {{
                    background: {ORANGE}; color: #000; font-weight: bold;
                    border-color: {ORANGE};
                }}
                QPushButton:hover:!checked {{ color: {TEXT}; border-color: {ORANGE}55; }}
            """)
            b.clicked.connect(lambda _, idx=i: self._switch(idx))
            lay.addWidget(b)
            self._btns.append(b)
        lay.addStretch()

    def _switch(self, idx: int):
        for i, b in enumerate(self._btns):
            b.setChecked(i == idx)
        self._on_switch(idx)


# ── Main Widget ───────────────────────────────────────────────────────────────

class ObjectivesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"QWidget {{ background-color: {BG}; }}")
        self._build()
        # Show daily popup after a short delay (so the UI is fully rendered first)
        QTimer.singleShot(800, self._maybe_show_popup)

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Top bar ──────────────────────────────────────────────────────────
        top_bar = QFrame()
        top_bar.setFixedHeight(56)
        top_bar.setStyleSheet(
            f"background: {SURFACE}; border-bottom: 1px solid {BORDER};"
        )
        tb_lay = QHBoxLayout(top_bar)
        tb_lay.setContentsMargins(24, 0, 24, 0)

        flag = _label("🎯  OBJETIVOS ANUALES 2026", ORANGE, 15, bold=True)
        tb_lay.addWidget(flag)
        tb_lay.addSpacing(30)

        self.tab_bar = TabBar(
            [("☀️", "HOY"), ("🏆", "MIS PILARES"), ("📚", "LECTURA")],
            self._switch_tab
        )
        tb_lay.addWidget(self.tab_bar)
        tb_lay.addStretch()

        # Date label
        date_lbl = _label(date.today().strftime("%A, %d de %B de %Y").capitalize(),
                          TEXT_DIM, 11)
        tb_lay.addWidget(date_lbl)
        root.addWidget(top_bar)

        # ── Tab pages (stacked manually) ─────────────────────────────────────
        self.tab_today = TodayTab()
        self.tab_pilares = PilaresTab()
        self.tab_lectura = LecturaTab()

        self._tabs = [self.tab_today, self.tab_pilares, self.tab_lectura]
        for i, t in enumerate(self._tabs):
            root.addWidget(t)
            t.setVisible(i == 0)

    def _switch_tab(self, idx: int):
        for i, t in enumerate(self._tabs):
            t.setVisible(i == idx)
        # Refresh reading stats when switching to Lectura
        if idx == 2:
            self.tab_lectura.refresh()
        elif idx == 0:
            self.tab_today.refresh()

    def _maybe_show_popup(self):
        """Show the daily ONE Thing popup if not already shown today."""
        if not om.was_popup_shown_today():
            popup = DailyFocusPopup(self)
            popup.exec()
            # Refresh the Hoy tab after popup
            self.tab_today.refresh()

    def showEvent(self, event):
        super().showEvent(event)
        # Also trigger popup check when user navigates to F12
        QTimer.singleShot(300, self._maybe_show_popup)
