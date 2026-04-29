#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import psutil
import math
import subprocess
import re
from datetime import datetime
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *
from PyQt5.QtGui import *
import pyqtgraph as pg

# Настройка pyqtgraph
pg.setConfigOptions(antialias=True)
pg.setConfigOption('background', '#1e1e1e')
pg.setConfigOption('foreground', '#d4d4d4')


class CPUMonitor(QThread):
    """Мониторинг CPU"""
    data_updated = pyqtSignal(float, float, float, float, float)
    test_finished = pyqtSignal()

    def __init__(self, duration_minutes=5, interval=1):
        super().__init__()
        self.duration = duration_minutes * 60
        self.interval = interval
        self.running = True
        self.start_time = 0

    def get_cpu_temperature(self):
        """Получение температуры CPU"""
        try:
            result = subprocess.run(['sensors'], capture_output=True, text=True, timeout=2)
            if result.returncode == 0:
                temperatures = []

                for line in result.stdout.split('\n'):
                    if 'Package' in line or 'Tctl' in line or 'CPU Temperature' in line or 'CPU' in line:
                        temps = re.findall(r'\+(\d+\.\d+)°C', line)
                        if temps:
                            return float(temps[0])

                    if 'Core 0' in line or 'Core0' in line:
                        temps = re.findall(r'\+(\d+\.\d+)°C', line)
                        if temps:
                            return float(temps[0])

                for line in result.stdout.split('\n'):
                    if '°C' in line:
                        temps = re.findall(r'\+(\d+\.\d+)°C', line)
                        if temps:
                            temperatures.extend([float(t) for t in temps])

                if temperatures:
                    return max(temperatures)

            import glob
            for zone in glob.glob('/sys/class/thermal/thermal_zone*/temp'):
                with open(zone, 'r') as f:
                    temp = int(f.read().strip()) / 1000.0
                    if 20 < temp < 120:
                        return temp

        except Exception as e:
            pass
        return 0.0

    def measure_performance(self):
        """Измерение производительности"""
        start = time.time()
        counter = 0

        while time.time() - start < self.interval:
            for i in range(50000):
                counter += i * i / (i + 1)
            counter += 1

        elapsed = time.time() - start
        return counter / elapsed if elapsed > 0 else 0

    def run(self):
        self.start_time = time.time()

        while self.running and (time.time() - self.start_time) < self.duration:
            cpu_percent = psutil.cpu_percent(interval=0.3)

            try:
                freq = psutil.cpu_freq().current if psutil.cpu_freq() else 0
            except:
                freq = 0

            temperature = self.get_cpu_temperature()
            performance = self.measure_performance()
            elapsed = time.time() - self.start_time

            self.data_updated.emit(cpu_percent, freq, performance, elapsed, temperature)
            time.sleep(0.5)

        self.test_finished.emit()

    def stop(self):
        self.running = False


class GaugeWidget(QWidget):
    """Круговой индикатор (Gauge) с автоматической настройкой"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.max_value = 1  # Начальное значение, будет自動 обновляться
        self.setMinimumSize(200, 200)

    def setValue(self, value, max_value=None):
        """Установка значения и опционально максимального"""
        self.value = value
        if max_value is not None and max_value > self.max_value:
            self.max_value = max_value
            # Обновляем max_value плавно
            self.max_value = max_value
        self.update()

    def paintEvent(self, event):
        """Отрисовка индикатора"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        # Размеры
        width = self.width()
        height = self.height()
        size = min(width, height)
        rect = QRectF(5, 5, size - 10, size - 10)

        # Углы для кругового индикатора
        angle_start = 90
        angle_span = 360

        # Вычисляем процент
        percent = (self.value / self.max_value) * 100 if self.max_value > 0 else 0
        percent = min(percent, 100)

        # Угол заполнения
        fill_angle = int((percent / 100) * angle_span)

        # Определяем цвет в зависимости от значения
        if percent < 30:
            color = QColor(78, 201, 176)  # зеленый
        elif percent < 60:
            color = QColor(220, 220, 170)  # желтый
        elif percent < 85:
            color = QColor(244, 135, 113)  # оранжевый
        else:
            color = QColor(244, 135, 113)  # красный

        # Рисуем фон (серый круг)
        painter.setPen(QPen(QColor(60, 60, 60), 10))
        painter.drawArc(rect, angle_start * 16, -angle_span * 16)

        # Рисуем заполнение
        painter.setPen(QPen(color, 10))
        painter.drawArc(rect, angle_start * 16, -fill_angle * 16)

        # Рисуем текст в центре
        painter.setPen(QPen(QColor(255, 255, 255), 1))

        # Форматируем значение (в млн или млрд)
        if self.value >= 1000000000:
            text = f"{self.value / 1000000000:.1f} млрд"
        elif self.value >= 1000000:
            text = f"{self.value / 1000000:.1f} млн"
        elif self.value >= 1000:
            text = f"{self.value / 1000:.1f} тыс"
        else:
            text = f"{self.value:.0f}"

        # Рисуем значение
        font = QFont('Arial', 16, QFont.Bold)
        painter.setFont(font)
        painter.drawText(rect, Qt.AlignCenter, text)

        # Рисуем подпись и процент
        font = QFont('Arial', 10)
        painter.setFont(font)
        painter.drawText(rect.adjusted(0, 30, 0, 0), Qt.AlignCenter, f"{percent:.0f}%")

        # Рисуем единицы измерения
        font = QFont('Arial', 8)
        painter.setFont(font)
        painter.drawText(rect.adjusted(0, 45, 0, 0), Qt.AlignCenter, "оп/сек")


class CPUTrottlingTest(QMainWindow):
    """Главное окно"""

    def __init__(self):
        super().__init__()
        self.test_running = False
        self.stress_process = None
        self.monitor_thread = None
        self.max_performance = 1  # Для отслеживания максимума

        # Данные для графиков
        self.time_data = []
        self.cpu_data = []
        self.freq_data = []
        self.perf_data = []
        self.temp_data = []

        self.init_ui()

        # Таймер для обновления текущей температуры
        self.temp_timer = QTimer()
        self.temp_timer.timeout.connect(self.update_current_temp)
        self.temp_timer.start(2000)

    def init_ui(self):
        """Интерфейс"""
        self.setWindowTitle("🔥 Троттлинг Тест Процессора с мониторингом температуры")
        self.setGeometry(100, 100, 1400, 900)

        self.setStyleSheet("""
            QMainWindow {
                background-color: #1e1e1e;
            }
            QLabel {
                color: white;
            }
            QGroupBox {
                color: white;
                font-weight: bold;
            }
            QGroupBox::title {
                color: #4ec9b0;
            }
            QPushButton {
                color: white;
            }
            QSpinBox, QDoubleSpinBox {
                color: white;
                background-color: #3e3e3e;
            }
            QProgressBar {
                color: white;
            }
        """)

        central = QWidget()
        self.setCentralWidget(central)
        layout = QHBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Левая панель
        left = self.create_control_panel()
        layout.addWidget(left)

        # Правая панель
        right = self.create_graph_panel()
        layout.addWidget(right, stretch=2)

        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("✅ Готов к тестированию")

    def create_control_panel(self):
        """Панель управления"""
        panel = QFrame()
        panel.setFixedWidth(350)
        panel.setStyleSheet("""
            QFrame {
                background-color: #2d2d2d;
                border-radius: 10px;
            }
            QLabel {
                color: white;
            }
        """)

        layout = QVBoxLayout(panel)
        layout.setSpacing(15)
        layout.setContentsMargins(15, 15, 15, 15)

        # Заголовок
        title = QLabel("⚙️ Управление")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: #4ec9b0;")
        layout.addWidget(title)

        # Настройки
        settings = QGroupBox("Настройки")
        settings.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3e3e3e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #4ec9b0;
            }
            QLabel {
                color: white;
            }
        """)

        s_layout = QFormLayout(settings)

        self.duration_spin = QSpinBox()
        self.duration_spin.setRange(1, 30)
        self.duration_spin.setValue(5)
        self.duration_spin.setSuffix(" мин")
        s_layout.addRow("⏱️ Длительность:", self.duration_spin)

        self.interval_spin = QDoubleSpinBox()
        self.interval_spin.setRange(0.5, 5)
        self.interval_spin.setValue(1)
        self.interval_spin.setSuffix(" сек")
        s_layout.addRow("📊 Интервал:", self.interval_spin)

        layout.addWidget(settings)

        # Кнопки
        btn_layout = QHBoxLayout()

        self.start_btn = QPushButton("▶ СТАРТ")
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #4ec9b0;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #5fd9c0; }
            QPushButton:disabled { background-color: #555; }
        """)
        self.start_btn.clicked.connect(self.start_test)
        btn_layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏹ СТОП")
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #f48771;
                color: white;
                font-size: 14px;
                font-weight: bold;
                padding: 12px;
                border-radius: 8px;
            }
            QPushButton:hover { background-color: #ff9b85; }
            QPushButton:disabled { background-color: #555; }
        """)
        self.stop_btn.clicked.connect(self.stop_test)
        self.stop_btn.setEnabled(False)
        btn_layout.addWidget(self.stop_btn)

        layout.addLayout(btn_layout)

        # Gauge индикатор производительности
        gauge_group = QGroupBox("🎯 Производительность (Gauge)")
        gauge_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3e3e3e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                color: white;
            }
            QGroupBox::title {
                color: #4ec9b0;
            }
        """)

        gauge_layout = QVBoxLayout(gauge_group)
        self.gauge = GaugeWidget()
        gauge_layout.addWidget(self.gauge, alignment=Qt.AlignCenter)
        layout.addWidget(gauge_group)

        # Система
        sys_group = QGroupBox("💻 Система")
        sys_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3e3e3e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                color: white;
            }
            QGroupBox::title {
                color: #4ec9b0;
            }
            QLabel {
                color: white;
            }
        """)

        sys_layout = QFormLayout(sys_group)

        cpu_count = psutil.cpu_count(logical=True)
        sys_layout.addRow("🖥️ Ядра:", QLabel(str(cpu_count)))

        try:
            freq = psutil.cpu_freq()
            if freq:
                sys_layout.addRow("⚡ Макс частота:", QLabel(f"{freq.max:.0f} МГц"))
                self.freq_label = QLabel("0 МГц")
                sys_layout.addRow("📊 Тек частота:", self.freq_label)
        except:
            pass

        layout.addWidget(sys_group)

        # Показатели
        stats_group = QGroupBox("📈 Показатели")
        stats_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3e3e3e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                color: white;
            }
            QGroupBox::title {
                color: #4ec9b0;
            }
            QLabel {
                color: white;
            }
        """)

        stats_layout = QFormLayout(stats_group)

        self.time_label = QLabel("0 сек")
        stats_layout.addRow("⏱️ Время:", self.time_label)

        self.load_label = QLabel("0%")
        self.load_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        stats_layout.addRow("📊 Загрузка:", self.load_label)

        self.temp_label = QLabel("0°C")
        self.temp_label.setStyleSheet("font-size: 16px; font-weight: bold; color: white;")
        stats_layout.addRow("🌡️ Температура:", self.temp_label)

        self.throttle_label = QLabel("✅ Нет")
        stats_layout.addRow("⚠️ Троттлинг:", self.throttle_label)

        layout.addWidget(stats_group)

        # Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3e3e3e;
                border-radius: 5px;
                text-align: center;
                height: 25px;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4ec9b0;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.progress_bar)

        # Температурный индикатор
        temp_indicator_group = QGroupBox("🌡️ Индикатор температуры")
        temp_indicator_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3e3e3e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                color: white;
            }
            QGroupBox::title {
                color: #4ec9b0;
            }
            QLabel {
                color: white;
            }
        """)

        temp_layout = QVBoxLayout(temp_indicator_group)

        self.temp_bar = QProgressBar()
        self.temp_bar.setRange(0, 100)
        self.temp_bar.setFormat("%v°C")
        self.temp_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #3e3e3e;
                border-radius: 5px;
                text-align: center;
                height: 30px;
                color: white;
            }
            QProgressBar::chunk {
                background-color: #4ec9b0;
                border-radius: 5px;
            }
        """)
        temp_layout.addWidget(self.temp_bar)

        self.temp_warning = QLabel("✅ Температура в норме")
        self.temp_warning.setStyleSheet("color: #4ec9b0;")
        temp_layout.addWidget(self.temp_warning)

        layout.addWidget(temp_indicator_group)

        layout.addStretch()

        return panel

    def create_graph_panel(self):
        """Графики"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(10)

        # График производительности
        perf_group = QGroupBox("Производительность")
        perf_group.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                border: 2px solid #3e3e3e;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #4ec9b0;
            }
        """)

        perf_layout = QVBoxLayout(perf_group)

        self.perf_plot = pg.PlotWidget()
        self.perf_plot.setLabel('left', 'Производительность', units='оп/сек')
        self.perf_plot.setLabel('bottom', 'Время', units='сек')
        self.perf_plot.showGrid(x=True, y=True, alpha=0.3)
        self.perf_curve = self.perf_plot.plot(pen=pg.mkPen(color='#4ec9b0', width=2))
        perf_layout.addWidget(self.perf_plot)

        layout.addWidget(perf_group)

        # График температуры
        temp_group = QGroupBox("Температура CPU")
        temp_group.setStyleSheet(perf_group.styleSheet())

        temp_layout = QVBoxLayout(temp_group)

        self.temp_plot = pg.PlotWidget()
        self.temp_plot.setLabel('left', 'Температура', units='°C')
        self.temp_plot.setLabel('bottom', 'Время', units='сек')
        self.temp_plot.showGrid(x=True, y=True, alpha=0.3)

        self.temp_plot.addLine(y=80, pen=pg.mkPen(color='#dcdcaa', width=1, style=Qt.DashLine))
        self.temp_plot.addLine(y=90, pen=pg.mkPen(color='#f48771', width=1, style=Qt.DashLine))
        self.temp_plot.addLine(y=100, pen=pg.mkPen(color='#ff0000', width=2, style=Qt.DashLine))

        self.temp_curve = self.temp_plot.plot(pen=pg.mkPen(color='#ff6b35', width=2))
        temp_layout.addWidget(self.temp_plot)

        layout.addWidget(temp_group)

        # График загрузки и частоты
        cpu_group = QGroupBox("Загрузка и частота")
        cpu_group.setStyleSheet(perf_group.styleSheet())

        cpu_layout = QVBoxLayout(cpu_group)

        self.cpu_plot = pg.PlotWidget()
        self.cpu_plot.setLabel('bottom', 'Время', units='сек')
        self.cpu_plot.showGrid(x=True, y=True, alpha=0.3)

        self.cpu_curve = self.cpu_plot.plot(pen=pg.mkPen(color='#dcdcaa', width=2), name='Загрузка %')
        self.cpu_plot.setLabel('left', 'Загрузка', units='%')

        self.freq_curve = self.cpu_plot.plot(pen=pg.mkPen(color='#f48771', width=2), name='Частота')
        self.cpu_plot.getAxis('right').setLabel('Частота', units='МГц')
        self.cpu_plot.getAxis('right').setPen('r')
        self.cpu_plot.addLegend()

        cpu_layout.addWidget(self.cpu_plot)

        layout.addWidget(cpu_group)

        # Лог
        log_group = QGroupBox("Журнал")
        log_group.setStyleSheet(perf_group.styleSheet())

        log_layout = QVBoxLayout(log_group)

        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        self.log_text.setMaximumHeight(150)
        self.log_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: white;
                font-family: 'Courier New', monospace;
                font-size: 11px;
            }
        """)
        log_layout.addWidget(self.log_text)

        layout.addWidget(log_group)

        return panel

    def log(self, message, level="INFO"):
        """Логирование"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        colors = {"INFO": "#4ec9b0", "WARNING": "#dcdcaa", "ERROR": "#f48771", "SUCCESS": "#4ec9b0"}
        self.log_text.append(f'<font color="{colors.get(level, "#4ec9b0")}">[{timestamp}] {message}</font>')
        scroll = self.log_text.verticalScrollBar()
        scroll.setValue(scroll.maximum())

    def start_stress_load(self):
        """Запуск нагрузки через stress"""
        cpu_count = psutil.cpu_count(logical=True)

        import shutil
        if not shutil.which('stress'):
            self.log("Утилита 'stress' не найдена. Установите: sudo apt install stress", "ERROR")
            return False

        self.log(f"Запуск stress с {cpu_count} ядрами...", "INFO")

        self.stress_process = QProcess()
        self.stress_process.start('stress', ['--cpu', str(cpu_count), '--timeout', '3600'])

        time.sleep(2)

        load = psutil.cpu_percent(interval=2)
        self.log(f"Загрузка CPU после запуска stress: {load}%", "SUCCESS" if load > 80 else "WARNING")

        return load > 50

    def stop_stress_load(self):
        """Остановка stress"""
        if self.stress_process:
            self.stress_process.terminate()
            self.stress_process.waitForFinished(2000)
            self.stress_process = None
            self.log("Нагрузка stress остановлена", "INFO")

    def update_current_temp(self):
        """Обновление текущей температуры в реальном времени"""
        try:
            monitor = CPUMonitor()
            temp = monitor.get_cpu_temperature()
            if temp > 0:
                self.temp_label.setText(f"{temp:.1f}°C")
                self.update_temp_indicator(temp)
        except:
            pass

    def update_temp_indicator(self, temp):
        """Обновление температурного индикатора"""
        self.temp_bar.setValue(int(temp))

        if temp >= 90:
            self.temp_bar.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #ff0000;
                    border-radius: 5px;
                }
            """)
            self.temp_warning.setText("🔥 КРИТИЧЕСКАЯ ТЕМПЕРАТУРА! Троттлинг неизбежен!")
            self.temp_warning.setStyleSheet("color: #ff0000; font-weight: bold;")
        elif temp >= 80:
            self.temp_bar.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #f48771;
                    border-radius: 5px;
                }
            """)
            self.temp_warning.setText("⚠️ ВЫСОКАЯ ТЕМПЕРАТУРА! Возможен троттлинг")
            self.temp_warning.setStyleSheet("color: #f48771; font-weight: bold;")
        elif temp >= 70:
            self.temp_bar.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #dcdcaa;
                    border-radius: 5px;
                }
            """)
            self.temp_warning.setText("⚠️ Повышенная температура")
            self.temp_warning.setStyleSheet("color: #dcdcaa;")
        else:
            self.temp_bar.setStyleSheet("""
                QProgressBar::chunk {
                    background-color: #4ec9b0;
                    border-radius: 5px;
                }
            """)
            self.temp_warning.setText("✅ Температура в норме")
            self.temp_warning.setStyleSheet("color: #4ec9b0;")

    def update_monitoring(self, cpu_percent, frequency, performance, elapsed, temperature):
        """Обновление данных мониторинга"""
        self.time_data.append(elapsed)
        self.cpu_data.append(cpu_percent)
        self.freq_data.append(frequency)
        self.perf_data.append(performance)
        self.temp_data.append(temperature)

        # Обновляем максимальную производительность для Gauge
        if performance > self.max_performance:
            self.max_performance = performance

        # Обновляем Gauge индикатор с текущим максимумом
        self.gauge.setValue(performance, self.max_performance)

        # Обновляем метки
        self.time_label.setText(f"{elapsed:.0f} сек")
        self.load_label.setText(f"{cpu_percent:.0f}%")
        self.temp_label.setText(f"{temperature:.1f}°C")

        self.update_temp_indicator(temperature)

        try:
            self.freq_label.setText(f"{frequency:.0f} МГц")
        except:
            pass

        # Прогресс
        total = self.duration_spin.value() * 60
        progress = int((elapsed / total) * 100)
        self.progress_bar.setValue(min(progress, 100))

        # Статус
        if cpu_percent > 80:
            self.status_bar.showMessage(f"🔥 Тест | Загрузка: {cpu_percent}% | Температура: {temperature:.1f}°C | Производительность: {performance:.0f}")
            self.load_label.setStyleSheet("color: #4ec9b0; font-size: 16px; font-weight: bold;")
        else:
            self.load_label.setStyleSheet("color: #f48771; font-size: 16px; font-weight: bold;")

        # Проверка троттлинга
        if len(self.perf_data) > 5:
            max_perf = max(self.perf_data)
            recent_avg = sum(self.perf_data[-5:]) / 5
            drop = (max_perf - recent_avg) / max_perf * 100 if max_perf > 0 else 0

            if drop > 20:
                self.throttle_label.setText(f"⚠️ {drop:.0f}%")
                self.throttle_label.setStyleSheet("color: #f48771; font-weight: bold;")
            elif drop > 10:
                self.throttle_label.setText(f"⚠️ {drop:.0f}%")
                self.throttle_label.setStyleSheet("color: #dcdcaa; font-weight: bold;")
            else:
                self.throttle_label.setText("✅ Нет")
                self.throttle_label.setStyleSheet("color: #4ec9b0;")

        # Графики
        if len(self.time_data) > 1:
            self.perf_curve.setData(self.time_data, self.perf_data)
            self.cpu_curve.setData(self.time_data, self.cpu_data)
            self.freq_curve.setData(self.time_data, self.freq_data)
            self.temp_curve.setData(self.time_data, self.temp_data)

        # Логирование при критической температуре
        if temperature >= 90 and temperature < 95:
            self.log(f"🌡️ Критическая температура: {temperature:.1f}°C", "WARNING")
        elif temperature >= 95:
            self.log(f"🔥 ОПАСНО! Температура CPU: {temperature:.1f}°C", "ERROR")
            self.status_bar.showMessage(f"🔥 КРИТИЧЕСКАЯ ТЕМПЕРАТУРА {temperature:.1f}°C! Срочно проверьте охлаждение!")

    def start_test(self):
        """Запуск теста"""
        # Сбрасываем максимум производительности
        self.max_performance = 1
        self.time_data.clear()
        self.cpu_data.clear()
        self.freq_data.clear()
        self.perf_data.clear()
        self.temp_data.clear()

        # Запускаем нагрузку через stress
        if not self.start_stress_load():
            QMessageBox.critical(self, "Ошибка", "Не удалось запустить нагрузку!\nУстановите stress: sudo apt install stress")
            return

        # Запускаем мониторинг
        self.monitor_thread = CPUMonitor(
            duration_minutes=self.duration_spin.value(),
            interval=self.interval_spin.value()
        )
        self.monitor_thread.data_updated.connect(self.update_monitoring)
        self.monitor_thread.test_finished.connect(self.finish_test)
        self.monitor_thread.start()

        # Обновляем UI
        self.test_running = True
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.duration_spin.setEnabled(False)
        self.interval_spin.setEnabled(False)

        self.log(f"🚀 Запуск теста на {self.duration_spin.value()} минут", "SUCCESS")

    def finish_test(self):
        """Завершение теста"""
        self.test_running = False
        self.stop_stress_load()

        if self.perf_data:
            max_perf = max(self.perf_data)
            min_perf = min(self.perf_data)
            avg_perf = sum(self.perf_data) / len(self.perf_data)
            avg_cpu = sum(self.cpu_data) / len(self.cpu_data)
            avg_temp = sum(self.temp_data) / len(self.temp_data) if self.temp_data else 0
            max_temp = max(self.temp_data) if self.temp_data else 0
            perf_drop = (max_perf - min_perf) / max_perf * 100 if max_perf > 0 else 0

            self.log("=" * 50, "INFO")
            self.log("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ", "SUCCESS")
            self.log(f"📈 Средняя загрузка CPU: {avg_cpu:.1f}%", "INFO")
            self.log(f"🌡️ Средняя температура: {avg_temp:.1f}°C", "INFO")
            self.log(f"🌡️ Максимальная температура: {max_temp:.1f}°C", "INFO")
            self.log(f"🚀 Макс производительность: {max_perf:.0f}", "INFO")
            self.log(f"🐢 Мин производительность: {min_perf:.0f}", "INFO")
            self.log(f"📉 Падение производительности: {perf_drop:.1f}%", "INFO")

            # Диагностика по температуре
            if max_temp > 95:
                self.log("🔥 КРИТИЧЕСКИЙ ПЕРЕГРЕВ! Немедленно проверьте охлаждение!", "ERROR")
                self.status_bar.showMessage("🔥 КРИТИЧЕСКИЙ ПЕРЕГРЕВ!")
            elif max_temp > 85:
                self.log("⚠️ СИЛЬНЫЙ ПЕРЕГРЕВ! Требуется улучшение охлаждения", "WARNING")
            elif max_temp > 75:
                self.log("⚠️ Повышенная температура. Рекомендуется проверка охлаждения", "WARNING")
            else:
                self.log("✅ Температура в норме", "SUCCESS")

            if avg_cpu < 50:
                self.log("❌ ОШИБКА: Низкая загрузка CPU!", "ERROR")
            elif perf_drop > 30:
                self.log("🔥 ОБНАРУЖЕН СИЛЬНЫЙ ТРОТТЛИНГ! Причина: перегрев", "ERROR")
                self.status_bar.showMessage("🔥 Обнаружен сильный троттлинг из-за перегрева!")
            elif perf_drop > 15:
                self.log("⚠️ Обнаружен троттлинг из-за высокой температуры", "WARNING")
            else:
                self.log("✅ Троттлинг НЕ обнаружен. Система охлаждения работает нормально", "SUCCESS")
                self.status_bar.showMessage("✅ Тест завершен. Троттлинг не обнаружен")

        # Обновляем UI
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.duration_spin.setEnabled(True)
        self.interval_spin.setEnabled(True)
        self.progress_bar.setValue(0)

    def stop_test(self):
        """Остановка"""
        self.test_running = False
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        self.stop_stress_load()

        self.log("⏹️ Тест остановлен пользователем", "WARNING")

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.duration_spin.setEnabled(True)
        self.interval_spin.setEnabled(True)

    def closeEvent(self, event):
        self.stop_test()
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')

    window = CPUTrottlingTest()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
