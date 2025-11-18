from pypdf import PdfReader
from openai import OpenAI
import os, sys
from dotenv import load_dotenv

from reader import read_pdf_text_pdfplumber
from prompt import prompt_template, target_json_format

def build_prompt(pdf_text: str) -> str:
    """
    Подставляет JSON-схему и текст PDF в prompt_template из prompt.py.
    В prompt_template используются плейсхолдеры {target_json_format} и {pdf_text}.
    """
    return prompt_template.format(
        target_json_format=target_json_format,
        pdf_text=pdf_text,
    )


def run_extraction_prompt(pdf_text: str, client: OpenAI) -> str:
    """
    Отправляет текст PDF в модель OpenAI и возвращает JSON-строку (как текст).
    """
    prompt = build_prompt(pdf_text)

    model = os.getenv("OPENAI_MODEL", "gpt-4.1-mini") # fallback
    temperature = float(os.getenv("OPENAI_TEMPERATURE", "0.2")) # fallback

    response = client.chat.completions.create(
        model=model,
        temperature=temperature,
        response_format={"type": "json_object"},
        messages=[
            {
                "role": "system",
                "content": "You extract structured data from messy medical PDFs.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    # В новой версии клиента content — это строка
    return response.choices[0].message.content


def main():
    # Загружаем переменные окружения (.env)
    load_dotenv()

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не найден в .env")

    client = OpenAI(api_key=api_key)

    # Путь к PDF: либо из аргумента командной строки, либо дефолт
    if len(sys.argv) > 1:
        pdf_path = sys.argv[1]
    else:
        pdf_path = os.path.join("input_files", "416887602.pdf")

    if not os.path.exists(pdf_path):
        raise FileNotFoundError(f"PDF-файл не найден: {pdf_path}")

    print(f"Читаем PDF: {pdf_path}")
    pdf_text = read_pdf_text_pdfplumber(pdf_path)

    print("Отправляем текст в OpenAI API...")
    json_response = run_extraction_prompt(pdf_text, client)

    # Куда сохранять ответ
    output_dir = os.getenv("OUTPUT_DIR", "output_files")
    os.makedirs(output_dir, exist_ok=True)

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_path = os.path.join(output_dir, f"{base_name}_response.txt")

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(json_response)

    print(f"Готово. Ответ модели сохранён в: {output_path}")


if __name__ == "__main__":
    # ------------------------------------------------------------
    # Сохраняем ПРОМПТ, который отправим в OpenAI
    # ------------------------------------------------------------

    output_dir = os.getenv("OUTPUT_DIR", "output_files")
    pdf_path = os.path.join("input_files", "416887602.pdf")
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    pdf_text = read_pdf_text_pdfplumber(pdf_path)
    prompt_text = build_prompt(pdf_text)

    prompt_output_path = os.path.join(output_dir, f"{base_name}_prompt.txt")
    with open(prompt_output_path, "w", encoding="utf-8") as f:
        f.write(prompt_text)

    print(f"Промпт сохранён в: {prompt_output_path}")
#    main()


