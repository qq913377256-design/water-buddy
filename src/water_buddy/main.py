from __future__ import annotations

import math
import sys
from datetime import datetime, time, timedelta

from PySide6.QtCore import QEasingCurve, QPointF, QPropertyAnimation, QTimer, Qt, Property, Signal
from PySide6.QtGui import QAction, QColor, QFont, QIcon, QPainter, QPainterPath, QPen
from PySide6.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QSpinBox,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

from water_buddy.config import DRINK_AMOUNT_OPTIONS, DrinkEntry, load_state, now_iso, save_state, today_key, total_today_ml
from water_buddy.startup import is_startup_enabled, set_startup_enabled


BG = "#f7fbff"
INK = "#244052"
MUTED = "#7192a8"
BLUE = "#66c7f4"
BLUE_DARK = "#2f9fd6"
PINK = "#ff8fb3"
MINT = "#94e6c6"
CARD = "#ffffff"


class BubbleButton(QPushButton):
    def __init__(self, text: str) -> None:
        super().__init__(text)
        self._scale = 1.0
        self.anim = QPropertyAnimation(self, b"scale", self)
        self.anim.setDuration(360)
        self.anim.setEasingCurve(QEasingCurve.Type.OutBack)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def get_scale(self) -> float:
        return self._scale

    def set_scale(self, value: float) -> None:
        self._scale = value
        self.setStyleSheet(button_style(value))

    scale = Property(float, get_scale, set_scale)

    def mousePressEvent(self, event) -> None:
        self.anim.stop()
        self.anim.setStartValue(self._scale)
        self.anim.setEndValue(0.96)
        self.anim.setDuration(110)
        self.anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self.anim.start()
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.anim.stop()
        self.anim.setStartValue(self._scale)
        self.anim.setEndValue(1.0)
        self.anim.setDuration(420)
        self.anim.setEasingCurve(QEasingCurve.Type.OutElastic)
        self.anim.start()
        super().mouseReleaseEvent(event)


def button_style(scale: float = 1.0) -> str:
    pad_y = max(12, round(14 * scale))
    return f"""
        QPushButton {{
            background: {BLUE_DARK};
            color: white;
            border: none;
            border-radius: 22px;
            padding: {pad_y}px 22px;
            font-size: 17px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            background: #278ec0;
        }}
        QPushButton:pressed {{
            background: #1d7faa;
        }}
    """


def amount_button_style(selected: bool) -> str:
    if selected:
        return f"""
            QPushButton {{
                background: {BLUE_DARK};
                color: white;
                border: 1px solid {BLUE_DARK};
                border-radius: 16px;
                padding: 8px 10px;
                font-weight: 800;
            }}
        """
    return f"""
        QPushButton {{
            background: #f7fbff;
            color: {INK};
            border: 1px solid #d8edf6;
            border-radius: 16px;
            padding: 8px 10px;
            font-weight: 700;
        }}
        QPushButton:hover {{
            background: #edf8fc;
            border-color: #bfe8f6;
        }}
    """


class DropletWidget(QWidget):
    progressChanged = Signal(float)

    def __init__(self) -> None:
        super().__init__()
        self._progress = 0.0
        self._breath = 0.0
        self._wave = 0.0
        self.setFixedSize(170, 182)

        self.progress_anim = QPropertyAnimation(self, b"progress", self)
        self.progress_anim.setDuration(900)
        self.progress_anim.setEasingCurve(QEasingCurve.Type.OutBack)

        self.breath_timer = QTimer(self)
        self.breath_timer.setInterval(16)
        self.breath_timer.timeout.connect(self.tick)
        self.breath_timer.start()

    def tick(self) -> None:
        self._breath = (self._breath + 0.018) % (math.pi * 2)
        self._wave = (self._wave + 0.055) % (math.pi * 2)
        self.update()

    def get_progress(self) -> float:
        return self._progress

    def set_progress(self, value: float) -> None:
        self._progress = max(0.0, min(1.0, value))
        self.progressChanged.emit(self._progress)
        self.update()

    progress = Property(float, get_progress, set_progress, notify=progressChanged)

    def animate_to(self, value: float) -> None:
        self.progress_anim.stop()
        self.progress_anim.setStartValue(self._progress)
        self.progress_anim.setEndValue(max(0.0, min(1.0, value)))
        self.progress_anim.start()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w = self.width()
        h = self.height()
        bob = math.sin(self._breath) * 5
        center_x = w / 2
        top = 22 + bob
        droplet_h = h - 44
        droplet_w = min(w * 0.62, 150)

        path = QPainterPath()
        path.moveTo(center_x, top)
        path.cubicTo(center_x - droplet_w * 0.48, top + droplet_h * 0.36, center_x - droplet_w * 0.58, top + droplet_h * 0.62, center_x - droplet_w * 0.32, top + droplet_h * 0.82)
        path.cubicTo(center_x - droplet_w * 0.12, top + droplet_h * 0.98, center_x + droplet_w * 0.12, top + droplet_h * 0.98, center_x + droplet_w * 0.32, top + droplet_h * 0.82)
        path.cubicTo(center_x + droplet_w * 0.58, top + droplet_h * 0.62, center_x + droplet_w * 0.48, top + droplet_h * 0.36, center_x, top)

        shadow = QPainterPath(path)
        painter.translate(0, 8)
        painter.fillPath(shadow, QColor(154, 209, 232, 54))
        painter.translate(0, -8)

        painter.fillPath(path, QColor("#dcf5ff"))
        painter.setPen(QPen(QColor("#a8e0f7"), 3))
        painter.drawPath(path)

        painter.save()
        painter.setClipPath(path)
        water_top = top + droplet_h * (1 - self._progress)
        wave_path = QPainterPath()
        wave_path.moveTo(center_x - droplet_w, h)
        wave_path.lineTo(center_x - droplet_w, water_top)
        steps = 36
        for i in range(steps + 1):
            x = center_x - droplet_w + (droplet_w * 2) * i / steps
            y = water_top + math.sin(self._wave + i * 0.55) * 5
            wave_path.lineTo(x, y)
        wave_path.lineTo(center_x + droplet_w, h)
        wave_path.closeSubpath()
        painter.fillPath(wave_path, QColor(BLUE))
        painter.restore()

        painter.setBrush(QColor(INK))
        painter.setPen(Qt.PenStyle.NoPen)
        eye_y = top + droplet_h * 0.52 + bob * 0.2
        painter.drawEllipse(QPointF(center_x - 24, eye_y), 5.5, 7)
        painter.drawEllipse(QPointF(center_x + 24, eye_y), 5.5, 7)

        painter.setPen(QPen(QColor(INK), 3, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        smile = QPainterPath()
        smile.moveTo(center_x - 13, eye_y + 22)
        smile.cubicTo(center_x - 5, eye_y + 31, center_x + 5, eye_y + 31, center_x + 13, eye_y + 22)
        painter.drawPath(smile)

        painter.setBrush(QColor(PINK))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(center_x - 44, eye_y + 19), 7, 4)
        painter.drawEllipse(QPointF(center_x + 44, eye_y + 19), 7, 4)


class WaterBuddyWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.current_day = today_key()
        self.state = load_state()
        self.state.settings.start_on_boot = is_startup_enabled()
        self.next_reminder_at = datetime.now() + timedelta(minutes=self.state.settings.remind_every_minutes)
        self.setWindowTitle("Water Buddy")
        self.setWindowIcon(self.make_icon())
        self.setMinimumSize(430, 640)
        self.setStyleSheet(f"QMainWindow {{ background: {BG}; }}")

        self.droplet = DropletWidget()
        self.total_label = QLabel()
        self.hint_label = QLabel()
        self.progress_label = QLabel()
        self.interval_input = QSpinBox()
        self.goal_input = QSpinBox()
        self.amount_group = QButtonGroup(self)
        self.amount_buttons: list[QPushButton] = []
        self.startup_check = QCheckBox("开机自动启动")
        self.add_button = BubbleButton("喝了一杯")
        self.pause_button = QPushButton("暂停 30 分钟")

        self.setup_ui()
        self.setup_tray()
        self.setup_timer()
        self.refresh(animated=False)

    def setup_ui(self) -> None:
        root = QWidget()
        layout = QVBoxLayout(root)
        layout.setContentsMargins(28, 20, 28, 18)
        layout.setSpacing(10)

        title = QLabel("喝水小助手")
        title.setFont(QFont("Microsoft YaHei UI", 22, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {INK};")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)

        subtitle = QLabel("轻轻提醒你补一点水")
        subtitle.setFont(QFont("Microsoft YaHei UI", 11))
        subtitle.setStyleSheet(f"color: {MUTED};")
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)

        top = QVBoxLayout()
        top.setSpacing(4)
        top.addWidget(title)
        top.addWidget(subtitle)
        layout.addLayout(top)

        layout.addWidget(self.droplet, alignment=Qt.AlignmentFlag.AlignCenter)

        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setFont(QFont("Microsoft YaHei UI", 16, QFont.Weight.Bold))
        self.progress_label.setStyleSheet(f"color: {INK};")
        layout.addWidget(self.progress_label)

        self.total_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.total_label.setFont(QFont("Microsoft YaHei UI", 12))
        self.total_label.setStyleSheet(f"color: {MUTED};")
        layout.addWidget(self.total_label)

        self.add_button.setMinimumHeight(48)
        self.add_button.clicked.connect(self.add_cup)
        layout.addWidget(self.add_button)

        self.hint_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.hint_label.setFont(QFont("Microsoft YaHei UI", 10))
        self.hint_label.setStyleSheet(f"color: {MUTED};")
        layout.addWidget(self.hint_label)

        settings = self.make_card()
        settings_layout = QVBoxLayout(settings)
        settings_layout.setContentsMargins(16, 12, 16, 12)
        settings_layout.setSpacing(8)
        settings_layout.addWidget(self.row("每日目标", self.goal_input, 800, 4000, self.state.settings.daily_goal_ml, " ml"))
        settings_layout.addWidget(self.amount_selector())
        settings_layout.addWidget(self.row("提醒间隔", self.interval_input, 15, 180, self.state.settings.remind_every_minutes, " 分钟"))
        settings_layout.addWidget(self.startup_row())
        layout.addWidget(settings)

        self.pause_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.pause_button.clicked.connect(self.pause_reminders)
        self.pause_button.setStyleSheet(f"""
            QPushButton {{
                background: #e8f6fb;
                color: {BLUE_DARK};
                border: 1px solid #c9edf9;
                border-radius: 18px;
                padding: 9px 18px;
                font-weight: 700;
            }}
            QPushButton:hover {{
                background: #dff2f9;
            }}
        """)
        layout.addWidget(self.pause_button)

        for spin in (self.goal_input, self.interval_input):
            spin.valueChanged.connect(self.settings_changed)

        self.setCentralWidget(root)

    def amount_selector(self) -> QWidget:
        wrapper = QWidget()
        layout = QHBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        label = QLabel("单次喝水量")
        label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {INK};")

        buttons = QWidget()
        button_layout = QHBoxLayout(buttons)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(8)

        for index, amount in enumerate(DRINK_AMOUNT_OPTIONS):
            button = QPushButton(f"{amount} ml")
            button.setCheckable(True)
            button.setMinimumHeight(34)
            button.setCursor(Qt.CursorShape.PointingHandCursor)
            self.amount_group.addButton(button, index)
            self.amount_buttons.append(button)
            button_layout.addWidget(button)
            button.clicked.connect(lambda checked=False, value=amount: self.select_amount(value))

        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(buttons)
        self.sync_amount_buttons()
        return wrapper

    def startup_row(self) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        self.startup_check.setChecked(self.state.settings.start_on_boot)
        self.startup_check.setCursor(Qt.CursorShape.PointingHandCursor)
        self.startup_check.setStyleSheet(f"""
            QCheckBox {{
                color: {INK};
                font-weight: 700;
                spacing: 9px;
            }}
            QCheckBox::indicator {{
                width: 20px;
                height: 20px;
            }}
        """)
        self.startup_check.toggled.connect(self.startup_changed)
        note = QLabel("打开电脑后自动留在托盘")
        note.setStyleSheet(f"color: {MUTED};")
        layout.addWidget(self.startup_check)
        layout.addStretch()
        layout.addWidget(note)
        return row

    def row(self, label_text: str, spin: QSpinBox, minimum: int, maximum: int, value: int, suffix: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        label = QLabel(label_text)
        label.setFont(QFont("Microsoft YaHei UI", 11, QFont.Weight.Bold))
        label.setStyleSheet(f"color: {INK};")
        spin.setRange(minimum, maximum)
        spin.setValue(value)
        spin.setSuffix(suffix)
        spin.setMinimumHeight(34)
        spin.setStyleSheet(f"""
            QSpinBox {{
                background: #f7fbff;
                color: {INK};
                border: 1px solid #d8edf6;
                border-radius: 12px;
                padding: 5px 8px;
                min-width: 116px;
            }}
        """)
        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(spin)
        return row

    def make_card(self) -> QFrame:
        card = QFrame()
        card.setStyleSheet(f"QFrame {{ background: {CARD}; border-radius: 8px; }}")
        shadow = QGraphicsDropShadowEffect(card)
        shadow.setBlurRadius(24)
        shadow.setColor(QColor(124, 177, 205, 36))
        shadow.setOffset(0, 8)
        card.setGraphicsEffect(shadow)
        return card

    def setup_tray(self) -> None:
        self.tray = QSystemTrayIcon(self.make_icon(), self)
        self.tray.setToolTip("Water Buddy")
        menu = self.tray.contextMenu()
        if menu is None:
            from PySide6.QtWidgets import QMenu

            menu = QMenu()
            self.tray.setContextMenu(menu)
        show_action = QAction("打开", self)
        show_action.triggered.connect(self.show_normal)
        add_action = QAction("记录一杯", self)
        add_action.triggered.connect(self.add_cup)
        pause_action = QAction("暂停 30 分钟", self)
        pause_action.triggered.connect(self.pause_reminders)
        quit_action = QAction("退出", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(show_action)
        menu.addAction(add_action)
        menu.addAction(pause_action)
        menu.addSeparator()
        menu.addAction(quit_action)
        self.tray.activated.connect(self.tray_activated)
        self.tray.show()

    def setup_timer(self) -> None:
        self.reminder_timer = QTimer(self)
        self.reminder_timer.setInterval(20_000)
        self.reminder_timer.timeout.connect(self.check_reminder)
        self.reminder_timer.start()

        self.clock_timer = QTimer(self)
        self.clock_timer.setInterval(1_000)
        self.clock_timer.timeout.connect(self.refresh_hint)
        self.clock_timer.start()

    def settings_changed(self) -> None:
        self.ensure_today()
        self.state.settings.daily_goal_ml = self.goal_input.value()
        self.state.settings.remind_every_minutes = self.interval_input.value()
        save_state(self.state, self.current_day)
        self.refresh(animated=True)

    def select_amount(self, amount: int) -> None:
        self.ensure_today()
        self.state.settings.cup_size_ml = amount
        save_state(self.state, self.current_day)
        self.sync_amount_buttons()
        self.refresh(animated=False)

    def sync_amount_buttons(self) -> None:
        for button, amount in zip(self.amount_buttons, DRINK_AMOUNT_OPTIONS):
            selected = amount == self.state.settings.cup_size_ml
            button.setChecked(selected)
            button.setStyleSheet(amount_button_style(selected))

    def startup_changed(self, enabled: bool) -> None:
        applied = set_startup_enabled(enabled)
        if not applied:
            self.startup_check.blockSignals(True)
            self.startup_check.setChecked(not enabled)
            self.startup_check.blockSignals(False)
            self.hint_label.setText("开机启动设置失败")
            return
        self.state.settings.start_on_boot = enabled
        save_state(self.state, self.current_day)
        self.refresh_hint()

    def add_cup(self) -> None:
        self.ensure_today()
        self.state.entries.append(DrinkEntry(amount_ml=self.state.settings.cup_size_ml, created_at=now_iso()))
        save_state(self.state, self.current_day)
        self.next_reminder_at = datetime.now() + timedelta(minutes=self.state.settings.remind_every_minutes)
        self.refresh(animated=True)

    def pause_reminders(self) -> None:
        self.ensure_today()
        paused_until = datetime.now() + timedelta(minutes=30)
        self.state.settings.paused_until = paused_until.isoformat(timespec="seconds")
        save_state(self.state, self.current_day)
        self.refresh_hint()
        self.tray.showMessage("Water Buddy", "提醒已暂停 30 分钟。", QSystemTrayIcon.MessageIcon.Information, 2400)

    def refresh(self, animated: bool) -> None:
        self.ensure_today(refresh_after=False)
        total = total_today_ml(self.state)
        goal = max(1, self.state.settings.daily_goal_ml)
        progress = min(1.0, total / goal)
        percent = round(progress * 100)
        self.progress_label.setText(f"今日 {percent}%")
        self.total_label.setText(f"{total} / {goal} ml")
        self.add_button.setText(f"喝了 {self.state.settings.cup_size_ml} ml")
        if animated:
            self.droplet.animate_to(progress)
        else:
            self.droplet.set_progress(progress)
        self.refresh_hint()

    def refresh_hint(self) -> None:
        self.ensure_today(refresh_after=False)
        paused_until = self.get_paused_until()
        if paused_until and paused_until > datetime.now():
            minutes = max(1, math.ceil((paused_until - datetime.now()).total_seconds() / 60))
            self.hint_label.setText(f"已暂停，约 {minutes} 分钟后恢复")
            return
        if self.in_quiet_hours():
            self.hint_label.setText("现在是勿扰时段，明早再提醒")
            return
        seconds = max(0, int((self.next_reminder_at - datetime.now()).total_seconds()))
        minutes = max(1, math.ceil(seconds / 60))
        self.hint_label.setText(f"下次提醒约 {minutes} 分钟后")

    def check_reminder(self) -> None:
        self.ensure_today()
        if self.in_quiet_hours():
            return
        paused_until = self.get_paused_until()
        if paused_until and paused_until > datetime.now():
            return
        if datetime.now() < self.next_reminder_at:
            return
        self.tray.showMessage("喝点水吧", "离开杯子太久了，补一小口也算数。", QSystemTrayIcon.MessageIcon.Information, 5000)
        self.next_reminder_at = datetime.now() + timedelta(minutes=self.state.settings.remind_every_minutes)
        self.refresh_hint()

    def ensure_today(self, refresh_after: bool = True) -> None:
        active_day = today_key()
        if active_day == self.current_day:
            return
        previous_settings = self.state.settings
        self.current_day = active_day
        self.state = load_state(active_day)
        self.state.settings = previous_settings
        self.next_reminder_at = datetime.now() + timedelta(minutes=self.state.settings.remind_every_minutes)
        save_state(self.state, self.current_day)
        if refresh_after:
            self.refresh(animated=True)

    def get_paused_until(self) -> datetime | None:
        value = self.state.settings.paused_until
        if not value:
            return None
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None

    def in_quiet_hours(self) -> bool:
        start = parse_time(self.state.settings.quiet_start)
        end = parse_time(self.state.settings.quiet_end)
        current = datetime.now().time()
        if start <= end:
            return start <= current <= end
        return current >= start or current <= end

    def tray_activated(self, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            self.show_normal()

    def show_normal(self) -> None:
        self.show()
        self.raise_()
        self.activateWindow()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()
        self.tray.showMessage("Water Buddy", "我会留在托盘里轻轻提醒。", QSystemTrayIcon.MessageIcon.Information, 2200)

    def make_icon(self) -> QIcon:
        from PySide6.QtGui import QPixmap

        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.moveTo(32, 8)
        path.cubicTo(12, 30, 14, 54, 32, 58)
        path.cubicTo(50, 54, 52, 30, 32, 8)
        painter.fillPath(path, QColor(BLUE))
        painter.setPen(QPen(QColor("#ffffff"), 4, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap))
        painter.drawPoint(25, 36)
        painter.drawPoint(39, 36)
        painter.end()
        return QIcon(pixmap)


def parse_time(value: str) -> time:
    try:
        return datetime.strptime(value, "%H:%M").time()
    except ValueError:
        return time(0, 0)


def main() -> int:
    if "--smoke-test" in sys.argv:
        return 0

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    app.setFont(QFont("Microsoft YaHei UI", 10))
    window = WaterBuddyWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
