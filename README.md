# 🔥 CPU Trottling Test Tool

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![Linux](https://img.shields.io/badge/platform-Linux-green.svg)](https://www.linux.org/)

## 📊 О программе

Инструмент для тестирования троттлинга процессора с визуализацией в реальном времени. Позволяет:
- Нагрузить CPU на 100% (через утилиту `stress`)
- Отслеживать температуру процессора
- Мониторить частоту и загрузку CPU
- Визуализировать производительность на круговом индикаторе (Gauge)
- Обнаруживать троттлинг автоматически
- Сохранять результаты тестирования

## 🎯 Скриншоты

![Главное окно](screenshots/main_window.png)
![Графики](screenshots/graphs.png)
![Результаты](screenshots/results.png)

## 📦 Установка

### Способ 1: DEB пакет (рекомендуется)

```bash
# Скачать последнюю версию
wget https://github.com/Wsper-hub/cpu-trottling-test/releases/download/v1.0.0/cpu-trottling-test_1.0.0_all.deb

# Установить
sudo dpkg -i cpu-trottling-test_1.0.0_all.deb
sudo apt-get install -f
