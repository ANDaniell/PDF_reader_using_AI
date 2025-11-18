import os
import re

import pytest

from reader import (
    read_pdf_text_pypdf,
    read_pdf_text_pdfplumber,
    read_pdf_text_pymupdf,
)

# === НАСТРОЙКА ПУТИ К PDF ===
# Предположим, что DTQ1.pdf лежит в корне проекта, рядом с main.py и reader.py.
# Если у тебя другая структура, поправь только эту константу.

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), os.pardir))
PDF_PATH = os.path.join(PROJECT_ROOT, "input_files", "DTQ1.pdf")


def normalize_ws(text: str) -> str:
    """
    Нормализует пробелы и переводы строк:
    все виды whitespace -> один пробел.
    Нужно, потому что разные библиотеки по-разному
    обращаются с табами/переносами.
    """
    return re.sub(r"\s+", " ", text).strip()


@pytest.mark.parametrize(
    "reader_func",
    [
        read_pdf_text_pypdf,
        read_pdf_text_pdfplumber,
        read_pdf_text_pymupdf,
    ],
)
def test_reader_returns_non_empty_string(reader_func):
    """
    Базовый sanity-check: каждая функция чтения должна вернуть ненулевую строку.
    """
    assert os.path.exists(PDF_PATH), f"PDF-файл не найден по пути: {PDF_PATH}"

    text = reader_func(PDF_PATH)

    assert isinstance(text, str), "Функция должна возвращать строку"
    assert text.strip() != "", f"{reader_func.__name__} вернула пустой текст"


def test_pdfplumber_contains_key_phrases():
    """
    Проверяем, что pdfplumber-ридер вытаскивает ключевые элементы формы PHQ.
    Эту функцию можно считать "основной" для семантической проверки.
    """
    raw_text = read_pdf_text_pdfplumber(PDF_PATH)
    text = normalize_ws(raw_text)

    # Заголовок формы
    assert "Personal Health Questionnaire (PHQ)" in text, \
        "Не найден заголовок 'Personal Health Questionnaire (PHQ)'"

    # Раздел I
    assert "Demographic Build and Tobacco Use" in text, \
        "Не найден раздел 'Demographic Build and Tobacco Use'"

    # Раздел II
    assert "Medical Conditions & Treatments" in text, \
        "Не найден раздел 'Medical Conditions & Treatments'"

    # Раздел III
    assert "Pregnancy and Childbirth" in text, \
        "Не найден раздел 'Pregnancy and Childbirth'"

    # Additional Details
    assert "Additional Details" in text, \
        "Не найден блок 'Additional Details'"


def test_all_extractors_see_main_title():
    """
    Все три реализации должны извлекать основной заголовок формы PHQ.
    Это проверка, что файл читается корректно любым из ридеров.
    """
    funcs = [
        read_pdf_text_pypdf,
        read_pdf_text_pdfplumber,
        read_pdf_text_pymupdf,
    ]

    for func in funcs:
        raw = func(PDF_PATH)
        text = normalize_ws(raw)
        assert "Personal Health Questionnaire (PHQ)" in text, \
            f"{func.__name__} не извлёк основной заголовок формы"


def test_extractors_have_similar_length():
    """
    Три библиотеки могут по-разному обращаться с пробелами/переносами,
    но общий объём текста должен быть сопоставим.
    Проверяем, что длины текстов не отличаются более чем на 20%.
    """
    texts = {
        "pypdf": read_pdf_text_pypdf(PDF_PATH),
        "pdfplumber": read_pdf_text_pdfplumber(PDF_PATH),
        "pymupdf": read_pdf_text_pymupdf(PDF_PATH),
    }

    lengths = {name: len(t) for name, t in texts.items()}
    max_len = max(lengths.values())
    min_len = min(lengths.values())

    assert min_len > 0, "Какая-то из библиотек вернула пустой текст"
    assert min_len / max_len > 0.8, (
        f"Слишком большая разница в длине текста между библиотеками: {lengths}"
    )


def test_section_order_with_pdfplumber():
    """
    Проверяем, что ключевые разделы формы идут в правильном порядке:
    PHQ -> Demographic -> Medical -> Pregnancy -> Additional Details.
    Это даёт уверенность, что порядок блоков при извлечении не сломан.
    """
    raw_text = read_pdf_text_pdfplumber(PDF_PATH)
    text = normalize_ws(raw_text)

    idx_phq = text.find("Personal Health Questionnaire (PHQ)")
    idx_demographic = text.find("Demographic Build and Tobacco Use")
    idx_medical = text.find("Medical Conditions & Treatments")
    idx_pregnancy = text.find("Pregnancy and Childbirth")
    idx_additional = text.find("Additional Details")

    assert idx_phq != -1, "Не найден заголовок PHQ"
    assert idx_demographic != -1, "Не найден раздел Demographic Build and Tobacco Use"
    assert idx_medical != -1, "Не найден раздел Medical Conditions & Treatments"
    assert idx_pregnancy != -1, "Не найден раздел Pregnancy and Childbirth"
    assert idx_additional != -1, "Не найден раздел Additional Details"

    assert idx_phq < idx_demographic < idx_medical < idx_pregnancy < idx_additional, (
        "Разделы PHQ → Demographic → Medical → Pregnancy → Additional Details "
        "идут в неправильном порядке"
    )
