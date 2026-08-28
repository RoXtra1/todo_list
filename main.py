import sys
from datetime import timedelta
from PySide6.QtCore import QPropertyAnimation, QEasingCurve, QTimer, QTime, Qt
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QFrame,
    QHBoxLayout, QVBoxLayout, QCheckBox, QLineEdit,
    QLabel, QPushButton, QListWidgetItem,
    QAbstractSpinBox)
from PySide6.QtUiTools import QUiLoader


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        # Загружаем UI
        loader = QUiLoader()
        self.ui = loader.load("mainwindow.ui", self)

        # Скрываем прототип строки задачи (он был в layout, но мы не хотим его видеть)
        self.ui.frm_task.hide()

        # Настройка QDateEdit: без кнопок-стрелок и без всплывающего календаря
        self.ui.de_slct_date.setCalendarPopup(False)
        self.ui.de_slct_date.setButtonSymbols(QAbstractSpinBox.NoButtons)
        # Можно сделать его доступным для ручного ввода даты, если нужно

        # Анимация панели календаря
        self.calendar_animation = QPropertyAnimation(self.ui.clnd_panel, b"maximumWidth")
        self.calendar_animation.setDuration(250)
        self.calendar_animation.setEasingCurve(QEasingCurve.InOutQuad)

        # Переменные таймера
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_time_display)
        self.remaining_seconds = 0
        self.active_task_row = None  # ссылка на виджет-строку активной задачи

        # Синхронизация дат: календарь <-> QDateEdit
        self.ui.clnd.clicked.connect(self.on_calendar_date_clicked)
        self.ui.de_slct_date.dateChanged.connect(self.on_dateedit_changed)

        # Кнопка старт/стоп
        self.ui.bt_start_stop.clicked.connect(self.toggle_timer)

        # Кнопка-стрелка для открытия/закрытия календаря
        # В UI такой кнопки нет, поэтому создадим её программно и добавим в нужное место.
        # Например, разместим слева от QDateEdit в той же строке (row 0, col 0).
        self.btn_toggle_calendar = QPushButton("▶")  # символ можно заменить на иконку
        self.btn_toggle_calendar.setFixedWidth(30)
        self.btn_toggle_calendar.clicked.connect(self.toggle_calendar)
        # Добавляем в gridLayout_2 в row=0, col=0
        self.ui.gridLayout_2.addWidget(self.btn_toggle_calendar, 0, 0)

        # Загружаем пример задачи (для теста)
        self.add_task("Пример задачи", "00:25:00")

    # ---------- Календарь ----------
    def toggle_calendar(self):
        """Плавно открыть/закрыть панель календаря."""
        panel = self.ui.clnd_panel
        if panel.width() == 0:
            self.calendar_animation.setStartValue(0)
            self.calendar_animation.setEndValue(250)  # ширина панели
        else:
            self.calendar_animation.setStartValue(panel.width())
            self.calendar_animation.setEndValue(0)
        self.calendar_animation.start()

    def on_calendar_date_clicked(self, date):
        """Когда пользователь кликает по дате в календаре, обновляем QDateEdit."""
        self.ui.de_slct_date.setDate(date)

    def on_dateedit_changed(self, date):
        """Когда дата меняется в QDateEdit, обновляем календарь."""
        self.ui.clnd.setSelectedDate(date)

    # ---------- Список задач ----------
    def add_task(self, title, time_str="00:00:00"):
        """Добавляет новую строку задачи в QListWidget."""
        # Создаём виджет строки
        row_widget = QFrame()
        row_widget.setFrameShape(QFrame.Panel)
        row_widget.setFrameShadow(QFrame.Raised)

        layout = QHBoxLayout(row_widget)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        cb_done = QCheckBox()
        cb_done.setFixedWidth(20)

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

        # Создаём элемент списка
        item = QListWidgetItem()
        item.setSizeHint(row_widget.sizeHint())
        self.ui.lwdg_tasks.addItem(item)
        self.ui.lwdg_tasks.setItemWidget(item, row_widget)

        # Сохраняем ссылки на виджеты в самом item (через data)
        item.setData(Qt.UserRole, {
            'widget': row_widget,
            'cb_done': cb_done,
            'le_title': le_title,
            'lb_timer': lb_timer,
            'bt_delete': bt_delete
        })

        # Подключаем сигналы
        cb_done.stateChanged.connect(lambda state, it=item: self.on_task_checked(it, state))
        bt_delete.clicked.connect(lambda _, it=item: self.delete_task(it))
        le_title.editingFinished.connect(lambda it=item: self.on_task_title_edited(it))
        # Клик по строке делает задачу активной
        row_widget.mousePressEvent = lambda event, it=item: self.set_active_task(it)

        return item

    def delete_task(self, item):
        """Удаляет задачу из списка."""
        row = self.ui.lwdg_tasks.row(item)
        self.ui.lwdg_tasks.takeItem(row)

    def on_task_checked(self, item, state):
        # Здесь можно обработать отметку выполнения (например, зачеркнуть текст)
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
        """Устанавливает активную задачу для большого таймера."""
        self.active_task_row = item
        data = item.data(Qt.UserRole)
        time_text = data['lb_timer'].text()
        # Парсим время в QTime и выставляем в QTimeEdit
        h, m, s = map(int, time_text.split(':'))
        self.ui.te_task_time.setTime(QTime(h, m, s))
        # Останавливаем текущий таймер
        self.stop_timer()

    # ---------- Таймер ----------
    def toggle_timer(self):
        if self.timer.isActive():
            self.stop_timer()
        else:
            self.start_timer()

    def start_timer(self):
        if self.active_task_row is None:
            return
        # Берём время из QTimeEdit
        time = self.ui.te_task_time.time()
        self.remaining_seconds = time.hour() * 3600 + time.minute() * 60 + time.second()
        self.timer.start(1000)  # обновление каждую секунду
        self.ui.bt_start_stop.setText("II")
        # Можно скрыть QTimeEdit и показать QLabel (если нужно)
        # Здесь для простоты оставим QTimeEdit, но будем обновлять его значение

    def stop_timer(self):
        self.timer.stop()
        self.ui.bt_start_stop.setText("▶")
        # Сохраняем оставшееся время в активной задаче
        if self.active_task_row is not None:
            data = self.active_task_row.data(Qt.UserRole)
            td = timedelta(seconds=self.remaining_seconds)
            data['lb_timer'].setText(str(td))
            # Также обновим QTimeEdit
            self.ui.te_task_time.setTime(QTime(0, 0).addSecs(self.remaining_seconds))

    def update_time_display(self):
        self.remaining_seconds -= 1
        if self.remaining_seconds <= 0:
            self.remaining_seconds = 0
            self.stop_timer()
        # Обновляем QTimeEdit
        self.ui.te_task_time.setTime(QTime(0, 0).addSecs(self.remaining_seconds))
        # Обновляем QLabel внутри активной строки (если есть)
        if self.active_task_row is not None:
            data = self.active_task_row.data(Qt.UserRole)
            data['lb_timer'].setText(str(timedelta(seconds=self.remaining_seconds)))
        # Обновляем прогрессбар (если нужно)
        # ...


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())