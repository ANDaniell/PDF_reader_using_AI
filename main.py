from pypdf import PdfReader
from openai import OpenAI
import os
from dotenv import load_dotenv
"""
def run_extraction_prompt(text: str, prompt_template: str):
    msg = prompt_template.replace("{{PDF_TEXT}}", text)

    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        temperature=0.2,
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": "You extract structured data from messy medical PDFs."},
            {"role": "user", "content": msg}
        ]
    )

    return response.choices[0].message["content"]


# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    model_params = {
        "model": "gpt-4.1-mini",
        "temperature": 0.2,
        "response_format": {"type": "json_object"}
    }

    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)


    def read_pdf_text(path):
        reader = PdfReader(path)
        text = ""
        for page in reader.pages:
            text += page.extract_text() + "\n"
        return text
        
        
"""
from reader import read_pdf_text_pypdf, read_pdf_text_pdfplumber, read_pdf_text_pymupdf

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
