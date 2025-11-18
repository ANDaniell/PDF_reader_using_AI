from pypdf import PdfReader
from openai import OpenAI
import os, sys, json
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

def process_pdf(pdf_path: str, client: OpenAI, output_dir: str):
    """
    Обрабатывает один PDF-файл:
    - читает текст
    - генерирует промпт
    - отправляет в ChatGPT
    - получает JSON-ответ
    - сохраняет ответ в .json
    """

    if not os.path.exists(pdf_path):
        print(f"Файл не найден: {pdf_path}")
        return

    base_name = os.path.splitext(os.path.basename(pdf_path))[0]

    print(f"\n=== Обрабатываем PDF через pdfplumber: {pdf_path} ===")


    pdf_text = read_pdf_text_pdfplumber(pdf_path) # Читаем PDF
    prompt_text = build_prompt(pdf_text) # Строим промпт

    # Сохраняем промпт (для отладки)
    prompt_output_path = os.path.join(output_dir, f"{base_name}_prompt.txt")
    with open(prompt_output_path, "w", encoding="utf-8") as f:
        f.write(prompt_text)
    print(f"Промпт сохранён в: {prompt_output_path}")

    # Отправляем запрос в модель
    print("Отправляем запрос в OpenAI...")
    json_str = run_extraction_prompt(prompt_text, client)

    # Конвертируем строку → JSON (dict)
    try:
        json_obj = json.loads(json_str)
    except json.JSONDecodeError:
        print("модель вернула невалидный JSON.")
        print("Сохраняю как raw-response.txt для отладки.")
        bad_path = os.path.join(output_dir, f"{base_name}_BAD_RESPONSE.txt")
        with open(bad_path, "w", encoding="utf-8") as f:
            f.write(json_str)
        return

    # Сохраняем красивый JSON
    response_output_path = os.path.join(output_dir, f"{base_name}_response.json")
    with open(response_output_path, "w", encoding="utf-8") as f:
        json.dump(json_obj, f, ensure_ascii=False, indent=2)

    print(f"JSON сохранён в: {response_output_path}")
    return json_obj



def main():
    load_dotenv() # Загружаем переменные окружения (.env)

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY не указан в .env")

    client = OpenAI(api_key=api_key)

    input_dir = os.getenv("PDF_INPUT_DIR", "input_files")
    output_dir = os.getenv("OUTPUT_DIR", "output_files")
    os.makedirs(output_dir, exist_ok=True)

    # Собираем список PDF из папки
    if len(sys.argv) > 1:
        # Если передали конкретный файл в аргумент — обрабатываем только его
        pdf_paths = [sys.argv[1]]
    else:
        # Иначе берём все PDF из input_dir
        pdf_paths = [os.path.join(input_dir, f) for f in os.listdir(input_dir) if f.lower().endswith(".pdf")]

    if not pdf_paths:
        raise FileNotFoundError(f"Не найдено ни одного PDF в {input_dir}")

    print("Найдены PDF:")
    for p in pdf_paths:
        print("  -", p)

    # Обрабатываем каждый PDF
    for pdf_path in pdf_paths:
        process_pdf(pdf_path, client, output_dir)



if __name__ == "__main__":
    main()


