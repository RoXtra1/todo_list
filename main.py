import sys
import os
from datetime import timedelta
from PySide6.QtCore import (
    QPropertyAnimation, QEasingCurve, QTimer, QTime, Qt, Signal, Property, QEvent
)
from PySide6.QtGui import QPainter
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame, QHBoxLayout, QVBoxLayout, QCheckBox,
    QLineEdit, QLabel, QPushButton, QListWidgetItem, QTimeEdit, QAbstractSpinBox,
    QToolButton, QStyleOptionToolButton, QStyle
)
from PySide6.QtUiTools import QUiLoader


class RotatableToolButton(QToolButton):
    def __init__(self, text="", parent=None):
        super().__init__(parent)
        self.setText(text)
        self._rotation = 0.0
        self.setStyleSheet("QToolButton { border: none; background: transparent; font-size: 16px; }")

    def get_rotation(self):
        return self._rotation

    def set_rotation(self, angle):
        self._rotation = angle
        self.update()

    rotation = Property(float, get_rotation, set_rotation)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.save()
        try:
            painter.translate(self.width() / 2, self.height() / 2)
            painter.rotate(self._rotation)
            painter.translate(-self.width() / 2, -self.height() / 2)

            opt = QStyleOptionToolButton()
            self.initStyleOption(opt)
            self.style().drawComplexControl(QStyle.CC_ToolButton, opt, painter, self)
        finally:
            painter.restore()
            painter.end()

class NewTaskWidget(QFrame):
    task_submitted = Signal(str, QTime)

    def __init__(self):
        super().__init__()
        self.setFrameShape(QFrame.NoFrame)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        self.cb_done = QCheckBox()
        self.cb_done.setFixedWidth(20)
        self.cb_done.hide()

        self.le_title = QLineEdit()
        self.le_title.setPlaceholderText("Новая задача...")
        self.le_title.setFrame(False)
        self.le_title.setStyleSheet("QLineEdit { border-bottom: 1px solid gray; }")
        self.le_title.returnPressed.connect(self.submit)

        self.te_time = QTimeEdit()
        self.te_time.setDisplayFormat("H:mm:ss")
        self.te_time.setTime(QTime(0, 0))
        self.te_time.hide()

        layout.addWidget(self.cb_done)
        layout.addWidget(self.le_title)
        layout.addWidget(self.te_time)

        self.le_title.textChanged.connect(self.on_text_changed)
        self.le_title.installEventFilter(self)

    def eventFilter(self, obj, event):
        if obj == self.le_title:
            if event.type() == QEvent.Type.FocusIn:
                self.show_extras(True)
            elif event.type() == QEvent.Type.FocusOut:
                if not self.le_title.text().strip():
                    self.show_extras(False)
        return super().eventFilter(obj, event)

    def on_text_changed(self, text):
        if text:
            self.show_extras(True)

    def show_extras(self, visible):
        self.cb_done.setVisible(visible)
        self.te_time.setVisible(visible)

    def submit(self):
        title = self.le_title.text().strip()
        if title:
            self.task_submitted.emit(title, self.te_time.time())
            self.reset()

    def reset(self):
        self.le_title.clear()
        self.show_extras(False)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Загрузка UI
        loader = QUiLoader()
        ui_path = os.path.join(os.path.dirname(__file__), "mainwindow.ui")
        self.ui = loader.load(ui_path)  # не передаём self как родителя!
        if self.ui is None:
            raise RuntimeError("Не удалось загрузить UI")

        # Устанавливаем загруженный виджет как центральный
        self.setCentralWidget(self.ui)

        # --- Замена кнопки на RotatableToolButton ---
        old_btn = self.ui.TBT_open_clnd
        old_font = old_btn.font()
        layout = self.ui.

        # Удаляем старую кнопку
        layout.removeWidget(old_btn)
        old_btn.deleteLater()

        # Создаём новую
        self.ui.TBT_open_clnd = RotatableToolButton(">")
        self.ui.TBT_open_clnd.setFont(old_font)

        # Добавляем на то же место (row=0, col=1)
        layout.addWidget(self.ui.TBT_open_clnd, 0, 1, 1, 1)
        # -------------------------------------------

        # Настройка кнопки-стрелки
        self.ui.TBT_open_clnd.setStyleSheet("QToolButton { border: none; background: transparent; font-size: 16px; }")

        # Анимация панели календаря
        self.calendar_animation = QPropertyAnimation(self.ui.clnd_panel, b"maximumWidth")
        self.calendar_animation.setDuration(250)
        self.calendar_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Анимация поворота кнопки
        self.btn_rotation_animation = QPropertyAnimation(self.ui.TBT_open_clnd, b"rotation")
        self.btn_rotation_animation.setDuration(250)
        self.btn_rotation_animation.setEasingCurve(QEasingCurve.InOutQuad)

        self.window_animation = QPropertyAnimation(self, b"geometry")
        self.window_animation.setDuration(250)
        self.window_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Виджет для новой задачи
        self.new_task_widget = NewTaskWidget()
        self.ui.gridLayout_2.addWidget(self.new_task_widget, 3, 0, 1, 2)
        self.new_task_widget.task_submitted.connect(self.on_new_task_submitted)

        # Таймер
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_display)
        self.remaining_seconds = 0
        self.active_task_row = None

        # Сигналы
        self.ui.clnd.clicked.connect(self.on_calendar_date_clicked)
        self.ui.bt_start_stop.clicked.connect(self.toggle_timer)
        self.ui.TBT_open_clnd.clicked.connect(self.toggle_calendar)
        self.ui.lwdg_tasks.itemClicked.connect(self.on_task_item_clicked)

        # Начальная ширина панели = 0
        self.ui.clnd_panel.setMaximumWidth(0)
        self.ui.clnd_panel.setMinimumWidth(0)

        # Пример задачи
        self.add_task("Пример задачи", "00:25:00")

    # ===== Календарь =====
    def toggle_calendar(self):
        panel = self.ui.clnd_panel
        if panel.width() == 0:
            # Открываем
            # Анимация панели
            self.calendar_animation.setStartValue(0)
            self.calendar_animation.setEndValue(250)

            # Анимация поворота кнопки
            self.btn_rotation_animation.setStartValue(0)
            self.btn_rotation_animation.setEndValue(180)

            # Анимация окна (увеличиваем ширину на 250)
            start_geom = self.geometry()
            end_geom = start_geom.adjusted(0, 0, 250, 0)
            self.window_animation.setStartValue(start_geom)
            self.window_animation.setEndValue(end_geom)
        else:
            # Закрываем
            self.calendar_animation.setStartValue(panel.width())
            self.calendar_animation.setEndValue(0)

            self.btn_rotation_animation.setStartValue(180)
            self.btn_rotation_animation.setEndValue(0)

            # Анимация окна (уменьшаем ширину на 250)
            start_geom = self.geometry()
            end_geom = start_geom.adjusted(0, 0, -250, 0)
            self.window_animation.setStartValue(start_geom)
            self.window_animation.setEndValue(end_geom)

        # Запускаем все анимации одновременно
        self.calendar_animation.start()
        self.btn_rotation_animation.start()
        self.window_animation.start()

    def on_calendar_date_clicked(self, date):
        self.ui.de_slct_date.setDate(date)

    # ===== Список задач =====
    def on_new_task_submitted(self, title, time):
        time_str = time.toString("H:mm:ss")
        self.add_task(title, time_str)

    def add_task(self, title, time_str="00:00:00"):
        row_widget = QFrame()
        row_widget.setFrameShape(QFrame.Panel)
        row_widget.setFrameShadow(QFrame.Raised)

        layout = QHBoxLayout(row_widget)
        cb_done = QCheckBox()
        le_title = QLineEdit()
        le_title.setText(title)
        le_title.setFrame(False)
        lb_timer = QLabel(time_str)
        lb_timer.setMinimumWidth(70)
        lb_timer.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        bt_delete = QPushButton("X")
        bt_delete.setFixedWidth(20)

        layout.addWidget(cb_done)
        layout.addWidget(le_title)
        layout.addWidget(lb_timer)
        layout.addWidget(bt_delete)

        item = QListWidgetItem()
        item.setSizeHint(row_widget.sizeHint())
        self.ui.lwdg_tasks.addItem(item)
        self.ui.lwdg_tasks.setItemWidget(item, row_widget)

        item.setData(Qt.UserRole, {
            'widget': row_widget,
            'cb_done': cb_done,
            'le_title': le_title,
            'lb_timer': lb_timer,
            'bt_delete': bt_delete
        })

        cb_done.stateChanged.connect(lambda state, it=item: self.on_task_checked(it, state))
        bt_delete.clicked.connect(lambda _, it=item: self.delete_task(it))
        le_title.editingFinished.connect(lambda it=item: self.on_task_title_edited(it))

        return item

    def on_task_item_clicked(self, item):
        self.set_active_task(item)

    def delete_task(self, item):
        row = self.ui.lwdg_tasks.row(item)
        self.ui.lwdg_tasks.takeItem(row)

    def on_task_checked(self, item, state):
        data = item.data(Qt.UserRole)
        le_title = data['le_title']
        font = le_title.font()
        font.setStrikeOut(state == Qt.Checked)
        le_title.setFont(font)

    def on_task_title_edited(self, item):
        data = item.data(Qt.UserRole)
        new_title = data['le_title'].text()
        print(f"Задача переименована: {new_title}")

    def set_active_task(self, item):
        self.active_task_row = item
        data = item.data(Qt.UserRole)
        time_text = data['lb_timer'].text()
        h, m, s = map(int, time_text.split(':'))
        self.ui.te_task_time.setTime(QTime(h, m, s))
        self.stop_timer()

    # ===== Таймер =====
    def toggle_timer(self):
        if self.timer.isActive():
            self.stop_timer()
        else:
            self.start_timer()

    def start_timer(self):
        if self.active_task_row is None:
            return
        time = self.ui.te_task_time.time()
        self.remaining_seconds = time.hour() * 3600 + time.minute() * 60 + time.second()
        self.timer.start(1000)
        self.ui.bt_start_stop.setText("II")

    def stop_timer(self):
        self.timer.stop()
        self.ui.bt_start_stop.setText("▶")
        if self.active_task_row is not None:
            data = self.active_task_row.data(Qt.UserRole)
            td = timedelta(seconds=self.remaining_seconds)
            data['lb_timer'].setText(str(td))
            self.ui.te_task_time.setTime(QTime(0, 0).addSecs(self.remaining_seconds))

    def update_time_display(self):
        self.remaining_seconds -= 1
        if self.remaining_seconds <= 0:
            self.remaining_seconds = 0
            self.stop_timer()
        self.ui.te_task_time.setTime(QTime(0, 0).addSecs(self.remaining_seconds))
        if self.active_task_row is not None:
            data = self.active_task_row.data(Qt.UserRole)
            data['lb_timer'].setText(str(timedelta(seconds=self.remaining_seconds)))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())