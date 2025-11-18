import json
from typing import Tuple, Dict, Any, List
import os
import pandas as pd
import re


# ----------------- нормализация дозировки ----------------- #

def normalize_dosage_value(dosage: str, dosage_unit: str):
    """
    Преобразует дозу в стандартный формат (mg или mg/ml).
    Возвращает (standardized_dose: float | None, standardized_unit: str | None)

    Логика простая:
    - берём ПЕРВОЕ число из строки dosage
    - конвертируем mcg, g в mg
    - если unit неизвестен — возвращаем None
    """
    if not dosage or not dosage_unit:
        return None, None

    dosage_unit = dosage_unit.lower().strip()
    # берём первое число из строки
    m = re.search(r"([\d\.]+)", dosage)
    if not m:
        return None, None

    val = float(m.group(1))

    if dosage_unit in ["mg"]:
        return val, "mg"
    if dosage_unit in ["mcg", "μg"]:
        return val / 1000.0, "mg"
    if dosage_unit in ["g", "gram", "grams"]:
        return val * 1000.0, "mg"
    if dosage_unit in ["mg/ml", "mg per ml", "mg/mL"]:
        return val, "mg/ml"

    # если единицы странные/неизвестные
    return None, None


# ----------------- преобразование JSON -> записи ----------------- #

def build_main_record(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Строит одну строку для общей таблицы заявки
    по описанной тобой структуре.
    """
    uid = data.get("uid", "")
    check_it = data.get("check_it", False)
    reason_checking = data.get("reason_checking", "")

    # в JSON статус и true_tier нет — заполняем пустыми
    status = data.get("status", "")
    true_tier = data.get("true_tier", "")

    applicants = data.get("applicants", [])
    # пока берём только главного заявителя (applicant 0)
    main_app = applicants[0] if applicants else {}

    applicant_id = main_app.get("applicant", 0)
    is_main_applicant = main_app.get("is_main_applicant", True)
    firstName = main_app.get("firstName", "")
    lastName = main_app.get("lastName", "")
    midName = main_app.get("midName", "")
    phone = main_app.get("phone", "")
    gender = main_app.get("gender", "")
    dob = main_app.get("dob", "")
    nicotine = main_app.get("nicotine", False)
    weight = main_app.get("weight", 0)
    height = main_app.get("height", 0)
    heightFt = main_app.get("heightFt", 0)
    heightIn = main_app.get("heightIn", 0)

    # медикаменты внутри phq.medications
    phq = data.get("phq", {})
    meds = phq.get("medications", [])

    # для общей таблицы — агрегируем списки через "|"
    medications = "|".join(m.get("name", "") for m in meds)
    dosages = "|".join(m.get("dosage", "") for m in meds)
    dosage_units = "|".join(m.get("dosage_unit", "") for m in meds)
    frequencies = "|".join(m.get("frequency", "") for m in meds)
    descriptions = "|".join(m.get("description", "") for m in meds)

    # reason_checking_logs / _med / _dosage_unit сейчас отсутствуют в JSON
    reason_checking_logs = data.get("reason_checking_logs", "")
    reason_checking_med = data.get("reason_checking_med", "")
    reason_checking_dosage_unit = data.get("reason_checking_dosage_unit", "")

    return {
        "uid": uid,
        "check_it": check_it,
        "reason_checking": reason_checking,
        "status": status,
        "true_tier": true_tier,
        "applicant_id": applicant_id,
        "is_main_applicant": is_main_applicant,
        "firstName": firstName,
        "lastName": lastName,
        "midName": midName,
        "phone": phone,
        "gender": gender,
        "dob": dob,
        "nicotine": nicotine,
        "weight": weight,
        "height": height,
        "heightFt": heightFt,
        "heightIn": heightIn,
        "medications": medications,
        "dosages": dosages,
        "dosage_unit": dosage_units,
        "frequencies": frequencies,
        "descriptions": descriptions,
        "reason_checking_logs": reason_checking_logs,
        "reason_checking_med": reason_checking_med,
        "reason_checking_dosage_unit": reason_checking_dosage_unit,
    }


def build_medication_records(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Строит список строк для таблицы медикаментов.
    """
    uid = data.get("uid", "")
    applicants = data.get("applicants", [])
    phq = data.get("phq", {})
    meds = phq.get("medications", [])

    # по умолчанию считаем, что все meds относятся к main applicant (0)
    main_applicant_id = applicants[0].get("applicant", 0) if applicants else 0

    records = []

    for med in meds:
        applicant_id = med.get("applicant", main_applicant_id)
        name = med.get("name", "")
        dosage = med.get("dosage", "")
        dosage_unit = med.get("dosage_unit", "")
        freq = med.get("frequency", "")
        descr = med.get("description", "")

        std_dose, std_unit = normalize_dosage_value(dosage, dosage_unit)

        # пока check_it и reason_checking для строки медикамента
        # просто копируем из верхнего уровня;
        # при необходимости можно расширить логикой
        check_it = data.get("check_it", False)
        reason_checking = data.get("reason_checking", "")
        reason_checking_dosage_unit = data.get("reason_checking_dosage_unit", "")

        records.append(
            {
                "uid": uid,
                "applicant_id": applicant_id,
                "medication": name,
                "dosage": dosage,
                "dosage_unit": dosage_unit,
                "standardized_dose": std_dose,
                "standardized_unit": std_unit,
                "check_it": check_it,
                "reason_checking": reason_checking,
                "reason_checking_dosage_unit": reason_checking_dosage_unit,
            }
        )

    return records


def json_to_tables_from_dict(data: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Принимает dict (JSON уже загружен) и возвращает
    два DataFrame: main_df, meds_df.
    """
    main_record = build_main_record(data)
    meds_records = build_medication_records(data)

    main_df = pd.DataFrame([main_record])
    meds_df = pd.DataFrame(meds_records)

    return main_df, meds_df


def json_to_tables_from_file(path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Загружает JSON из файла и возвращает
    два DataFrame: main_df, meds_df.
    """
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)

    return json_to_tables_from_dict(data)






OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output_files")

if __name__ == "__main__":
    json_path = os.path.join(OUTPUT_DIR, "416887602_response.txt")

    main_df, meds_df = json_to_tables_from_file(json_path)

    # сохраняем в CSV
    main_csv = os.path.join(OUTPUT_DIR, "416887602_main.csv")
    meds_csv = os.path.join(OUTPUT_DIR, "416887602_meds.csv")

    main_df.to_csv(main_csv, index=False)
    meds_df.to_csv(meds_csv, index=False)

    print(f"Main table saved to: {main_csv}")
    print(f"Medications table saved to: {meds_csv}")