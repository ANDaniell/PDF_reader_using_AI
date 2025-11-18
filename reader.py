from pypdf import PdfReader
import pdfplumber
import fitz

def read_pdf_text_pypdf(path: str) -> str:
    try:
        reader = PdfReader(path)
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {path}")
    except Exception as e:
        raise ValueError(f"Cannot open PDF: {e}")

    all_text = []

    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
        except Exception as e:
            raise ValueError(f"Failed to extract text on page {i}: {e}")

        if text:
            all_text.append(text)
        else:
            all_text.append("")  # сохраняем пустую страницу, чтобы не ломать структуру

    result = "\n".join(all_text)

    if not result.strip():
        raise ValueError(f"PDF contains no readable text: {path}")

    return result


def read_pdf_text_pdfplumber(path: str) -> str:
    """
    Читает текст с помощью pdfplumber.
    Лучше восстанавливает строки и расстояния.
    """
    pages_text = []

    try:
        with pdfplumber.open(path) as pdf:
            for i, page in enumerate(pdf.pages):
                try:
                    text = page.extract_text() or ""
                except Exception as e:
                    raise ValueError(f"pdfplumber: error reading page {i}: {e}")

                pages_text.append(text)

    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {path}")
    except Exception as e:
        raise ValueError(f"pdfplumber: cannot open PDF {path}: {e}")

    result = "\n".join(pages_text)

    if not result.strip():
        raise ValueError(f"pdfplumber: PDF contains no readable text: {path}")

    return result


def read_pdf_text_pymupdf(path: str) -> str:
    """
    Извлекает текст с помощью PyMuPDF (fitz).
    Обычно лучше восстанавливает структуру формы.
    """
    try:
        doc = fitz.open(path)
    except FileNotFoundError:
        raise FileNotFoundError(f"PDF file not found: {path}")
    except Exception as e:
        raise ValueError(f"PyMuPDF: cannot open PDF {path}: {e}")

    pages_text = []

    for i, page in enumerate(doc):
        try:
            text = page.get_text("text")  # "text" = "как видит человек"
        except Exception as e:
            raise ValueError(f"PyMuPDF: error reading page {i}: {e}")

        pages_text.append(text)

    return "\n".join(pages_text)

from typing import Dict, Any
from pypdf import PdfReader


def extract_form_fields_pypdf(path: str) -> Dict[str, Any]:
    """
    Извлекает значения полей формы из PDF с помощью pypdf.
    Работает с AcroForm-полями (текст, чекбоксы и т.д.).

    Returns:
        dict: {field_name: value}
    """
    reader = PdfReader(path)

    # get_fields возвращает словарь с описанием всех полей
    fields = reader.get_fields() or {}

    result: Dict[str, Any] = {}

    for name, field in fields.items():
        # /V = Value, значение, введённое в поле
        value = field.get("/V", "")

        # Для чекбоксов /V часто бывает /Yes или /Off
        # Преобразуем их в более человеческий вид
        if isinstance(value, str):
            normalized_value = value
        else:
            # иногда это может быть объект pypdf, тогда приводим к строке
            normalized_value = str(value)

        if normalized_value in ("/Yes", "Yes", "YES", "On", "/On"):
            normalized_value = "Yes"
        elif normalized_value in ("/Off", "Off", "OFF", "No", "NO"):
            normalized_value = "No"

        result[name] = normalized_value

    return result


def compare_extractors(path: str):
    """
    Сравнивает pypdf, pdfplumber и pymupdf.
    Печатает различия в длине текста и примеры.
    """
    print("\n=== Comparing three PDF extractors ===")

    results = {}

    # pypdf
    results["pypdf"] = read_pdf_text_pypdf(path)

    # pdfplumber
    results["pdfplumber"] = read_pdf_text_pdfplumber(path)

    # pymupdf
    results["pymupdf"] = read_pdf_text_pymupdf(path)

    print("\n--- Text lengths ---")
    for name, text in results.items():
        print(f"{name}: {len(text)} chars, {text.count(chr(10))} lines")

    print("\n--- Samples (first 800 chars) ---")
    for name, text in results.items():
        print(f"\n{name.upper()}:\n{'='*40}\n{text[:800]}")

    return results

if __name__ == "__main__":
    pdf_path = "input_files/416887602.pdf"
    compare_extractors(pdf_path)