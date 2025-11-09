#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Скрипт для объединения отредактированных сцен Фазы 1 в один файл
ВЕРСИЯ: После ревизии (9.0/10)
"""

import os
import sys
from pathlib import Path
from datetime import datetime

# Настройка кодировки для Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Путь к каталогу с отредактированными главами
CHAPTERS_DIR = Path(r"e:\sources\book-alexa-right\acts\act-1\chapters")
OUTPUT_FILE = Path(r"e:\sources\book-alexa-right\acts\act-1\ФАЗА_1_ПОЛНЫЙ_ТЕКСТ_v2.1.md")

# Порядок сцен в правильной последовательности (после ревизии)
SCENES_ORDER = [
    "0001_Сцена 1.1 - Утро на 247 этаже.md",
    "0002_Сцена 1.2 - Редактор памяти за работой.md",
    "0003_Сцена 1.3 - Инъекция и напоминание о статусе.md",
    "0006_Сцена 1.4 - Вечернее хондрение.md",
    "0005_Переход - Ночь перед вызовом.md",  # НОВАЯ СЦЕНА
    "0004_Сцена 2.1 - Срочный вызов.md",
    "0005_Сцена 2.2 - Встреча с Лже-Реджинальдом.md",
    "0008_Сцена 2.3 - Погружение в память Лже-Реджинальда.md",
    # "0007_Сцена 2.4 - Успешное завершение и благодарность.md",  # Пока не редактировали
    # "0009_Финальный момент Фазы 1 - Переход.md"  # Пока не редактировали
]

def merge_scenes():
    """Объединяет все сцены в один файл"""

    print("Начинаю объединение сцен...")
    print(f"Каталог: {CHAPTERS_DIR}")
    print(f"Выходной файл: {OUTPUT_FILE}")
    print()

    # Создаём содержимое объединённого файла
    merged_content = []

    # Добавляем заголовок
    merged_content.append("# ФАЗА 1: ИЛЛЮЗИЯ КОНТРОЛЯ")
    merged_content.append("")
    merged_content.append("**Полный текст отредактированных сцен (версия 2.1)**")
    merged_content.append("")
    merged_content.append(f"*Дата сборки: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    merged_content.append("**Оценка качества:** 9.0/10 (было 7.8/10)")
    merged_content.append("")
    merged_content.append("---")
    merged_content.append("")

    # Проходим по всем сценам в правильном порядке
    for i, scene_file in enumerate(SCENES_ORDER, 1):
        scene_path = CHAPTERS_DIR / scene_file

        if not scene_path.exists():
            print(f"[WARNING] Файл не найден: {scene_file}")
            continue

        print(f"[OK] Добавляю сцену {i}/{len(SCENES_ORDER)}: {scene_file}")

        # Читаем содержимое сцены
        with open(scene_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Удаляем секции с метаинформацией (оставляем только художественный текст)
        lines = content.split('\n')
        filtered_lines = []
        skip_section = False

        for line in lines:
            # Начало секций с метаинформацией
            if line.startswith("## Потенциальные улучшения") or \
               line.startswith("## НОВЫЕ ЭЛЕМЕНТЫ МИРА") or \
               line.startswith("## Технические детали для мира"):
                skip_section = True
                continue

            # Если не в режиме пропуска, добавляем строку
            if not skip_section:
                filtered_lines.append(line)

        # Добавляем отфильтрованное содержимое
        merged_content.append('\n'.join(filtered_lines).strip())
        merged_content.append("")
        merged_content.append("")

        # Разделитель между сценами (кроме последней)
        if i < len(SCENES_ORDER):
            merged_content.append("---")
            merged_content.append("")

    # Записываем объединённый файл
    final_content = '\n'.join(merged_content)

    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write(final_content)

    print()
    print(f"[SUCCESS] Готово! Все сцены объединены в файл:")
    print(f"   {OUTPUT_FILE}")
    print()

    # Выводим статистику
    word_count = len(final_content.split())
    char_count = len(final_content)

    print(f"Статистика:")
    print(f"   Символов: {char_count:,}")
    print(f"   Слов: {word_count:,}")
    print(f"   Сцен: {len(SCENES_ORDER)}")

if __name__ == "__main__":
    merge_scenes()
