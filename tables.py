import json
from typing import Tuple, Dict, Any, List
import os
import pandas as pd
import re
from logging_config import setup_logging, get_logger

logger = get_logger(__name__)

# Имена общих таблиц
MAIN_TABLE_FILENAME = "applications.csv"
MEDS_TABLE_FILENAME = "medications.csv"


def safe_join(values, placeholder="NaN"):
    """
    Собирает значения через '|', сохраняя структуру
    """

    cleaned = []
    has_real_value = False

    for v in values:
        s = "" if pd.isna(v) else str(v).strip()

        if not s or s == " | ":
            cleaned.append(placeholder)
        else:
            cleaned.append(s)
            has_real_value = True

    return " | ".join(cleaned) if has_real_value else pd.NA

# ----------------- нормализация дозировки ----------------- #

def normalize_dosage_value(dosage: str, dosage_unit: str):
    """
    Преобразует дозу в стандартный формат (mg или mg/ml).
    Возвращает (standardized_dose: float | None, standardized_unit: str | None)
    """

    logger.debug(f"Нормализация дозировки: dosage='{dosage}', unit='{dosage_unit}'")

    if not dosage or not dosage_unit:
        logger.warning("normalize_dosage_value: dosage или dosage_unit отсутствуют")
        return None, None

    dosage_unit = dosage_unit.lower().strip()
    m = re.search(r"([\d\.]+)", dosage)
    if not m:
        logger.warning(f"normalize_dosage_value: не найдено численное значение в '{dosage}'")
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

    logger.warning(f"normalize_dosage_value: неизвестная единица '{dosage_unit}'")
    return None, None


# ----------------- преобразование JSON -> записи ----------------- #

def build_main_records(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Строит строки для общей таблицы заявки по каждому аппликанту.
    """

    logger.info(f"Формирование main-records для uid={data.get('uid')}")

    uid = data.get("uid", "")
    check_it = data.get("check_it", False)
    reason_checking = data.get("reason_checking", "")

    # в JSON статус и true_tier нет — заполняем пустыми
    status = data.get("status", "")
    true_tier = data.get("true_tier", "")

    applicants = data.get("applicants", [])
    if not applicants:
        logger.warning(f"JSON не содержит списка applicants для uid={uid}, создаю пустого applicant")
        applicants = [{}]

    # медикаменты внутри phq.medications
    phq = data.get("phq", {})
    meds = phq.get("medications", [])
    logger.debug(f"build_main_records: найдено медикаментов={len(meds)} для uid={uid}")

    # applicant поля в medications могут отсутствовать, поэтому берём id главного
    default_applicant_id = applicants[0].get("applicant", 0) if applicants else 0

    # reason_checking_logs / _med / _dosage_unit сейчас отсутствуют в JSON
    reason_checking_logs = data.get("reason_checking_logs", "")
    reason_checking_med = data.get("reason_checking_med", "")
    reason_checking_dosage_unit = data.get("reason_checking_dosage_unit", "")

    records: List[Dict[str, Any]] = []

    for idx, applicant in enumerate(applicants):
        applicant_id = applicant.get("applicant")
        if applicant_id is None:
            applicant_id = idx

        logger.debug(
            f"Обрабатываем applicant #{idx} → applicant_id={applicant_id}, uid={uid}"
        )

        applicant_meds = [
            med
            for med in meds
            if med.get("applicant", default_applicant_id) == applicant_id
        ]

        logger.debug(
            f"Для applicant_id={applicant_id} найдено медикаментов: {len(applicant_meds)}"
        )

        medications = safe_join([m.get("name", "") for m in applicant_meds])
        dosages = safe_join([m.get("dosage", "") for m in applicant_meds])
        dosage_units = safe_join([m.get("dosage_unit", "") for m in applicant_meds])
        frequencies = safe_join([m.get("frequency", "") for m in applicant_meds])
        descriptions = safe_join([m.get("description", "") for m in applicant_meds])

        records.append(
            {
                "uid": uid,
                "check_it": check_it,
                "reason_checking": reason_checking,
                "status": status,
                "true_tier": true_tier,
                "applicant_id": applicant_id,
                "is_main_applicant": applicant.get("is_main_applicant", idx == 0),
                "firstName": applicant.get("firstName", ""),
                "lastName": applicant.get("lastName", ""),
                "midName": applicant.get("midName", ""),
                "phone": applicant.get("phone", ""),
                "gender": applicant.get("gender", ""),
                "dob": applicant.get("dob", ""),
                "nicotine": applicant.get("nicotine", False),
                "weight": applicant.get("weight", 0),
                "height": applicant.get("height", 0),
                "heightFt": applicant.get("heightFt", 0),
                "heightIn": applicant.get("heightIn", 0),
                "medications": medications,
                "dosages": dosages,
                "dosage_unit": dosage_units,
                "frequencies": frequencies,
                "descriptions": descriptions,
                "reason_checking_logs": reason_checking_logs,
                "reason_checking_med": reason_checking_med,
                "reason_checking_dosage_unit": reason_checking_dosage_unit,
            }
        )

    logger.info(f"build_main_records: для uid={uid} сформировано записей={len(records)}")
    return records


def build_medication_records(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Строит список строк для таблицы медикаментов.
    """
    uid = data.get("uid", "")
    logger.info(f"build_medication_records: начало обработки uid={uid}")

    applicants = data.get("applicants", [])
    phq = data.get("phq", {})
    meds = phq.get("medications", [])
    logger.debug(f"build_medication_records: найдено meds={len(meds)} для uid={uid}")

    # по умолчанию считаем, что все meds относятся к main applicant (0)
    main_applicant_id = applicants[0].get("applicant", 0) if applicants else 0

    # records = []
    records: List[Dict[str, Any]] = []

    for med in meds:
        applicant_id = med.get("applicant", main_applicant_id)
        name = med.get("name", "")
        dosage = med.get("dosage", "")
        dosage_unit = med.get("dosage_unit", "")
        freq = med.get("frequency", "")
        descr = med.get("description", "")

        std_dose = dosage
        std_unit = dosage_unit
        #std_dose, std_unit = normalize_dosage_value(dosage, dosage_unit)

        # пока check_it и reason_checking для строки медикамента
        # просто копируем из верхнего уровня;
        # при необходимости можно расширить логикой
        check_it = data.get("check_it", False)
        reason_checking = data.get("reason_checking", "")
        reason_checking_dosage_unit = data.get("reason_checking_dosage_unit", "")

        logger.debug(
            f"build_medication_records: uid={uid}, med_name={name!r}, "
            f"applicant_id={applicant_id}, dosage={dosage!r}, dosage_unit={dosage_unit!r}"
        )


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
                "frequency": freq,
                "description": descr,
            }
        )

    logger.info(f"build_medication_records: для uid={uid} записей={len(records)}")
    return records


def json_to_tables_from_dict(data: Dict[str, Any]) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Принимает dict (JSON уже загружен) и возвращает
    два DataFrame: main_df, meds_df.
    """
    main_records = build_main_records(data)
    meds_records = build_medication_records(data)

    main_df = pd.DataFrame(main_records)
    meds_df = pd.DataFrame(meds_records)

    uid = data.get("uid", "")
    logger.info(
        f"json_to_tables_from_dict: для uid={uid} main_rows={len(main_df)}, meds_rows={len(meds_df)}"
    )

    return main_df, meds_df


def json_to_tables_from_file(path: str) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """
    Загружает JSON из файла и возвращает
    два DataFrame: main_df, meds_df.
    """
    logger.info(f"json_to_tables_from_file: чтение JSON из файла {path}")

    # проверяем, что файл вообще существует
    if not os.path.exists(path):
        logger.error(f"json_to_tables_from_file: файл не найден: {path}")
        raise FileNotFoundError(f"JSON-файл не найден: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        logger.exception(f"json_to_tables_from_file: невалидный JSON в файле {path}: {e}")
        raise ValueError(f"Невалидный JSON в файле {path}: {e}")
    except Exception as e:
        logger.exception(f"json_to_tables_from_file: ошибка чтения файла {path}: {e}")
        raise

    if not isinstance(data, dict):
        logger.error(
            f"json_to_tables_from_file: корень JSON не объект (dict), а {type(data)} в файле {path}"
        )
        raise ValueError(f"Ожидался JSON-объект (dict) в файле {path}, получено {type(data)}")

    logger.info(f"json_to_tables_from_file: JSON успешно загружен, uid={data.get('uid', '')}")
    return json_to_tables_from_dict(data)


def append_to_global_tables(main_df_new: pd.DataFrame,
    meds_df_new: pd.DataFrame,output_dir: str,) -> None:
    """
    Добавляет новые записи в общие таблицы (applications.csv и medications.csv),
    не пересоздавая их и убирая дубли.

    "Такая же запись" = строка, совпадающая по всем колонкам.
    """
    logger.info(f"append_to_global_tables: output_dir={output_dir}")
    os.makedirs(output_dir, exist_ok=True)

    main_path = os.path.join(output_dir, MAIN_TABLE_FILENAME)
    meds_path = os.path.join(output_dir, MEDS_TABLE_FILENAME)

    # ---- общая таблица заявок ----
    if os.path.exists(main_path):
        logger.info(f"append_to_global_tables: читаю существующую {main_path}")
        main_df_old = pd.read_csv(main_path)
        main_df_all = pd.concat([main_df_old, main_df_new], ignore_index=True)
        main_df_all = main_df_all.drop_duplicates()
    else:
        logger.info(f"append_to_global_tables: {main_path} не существует, создаю новую")
        main_df_all = main_df_new.copy()

    main_df_all.to_csv(main_path, index=False)
    logger.info(f"append_to_global_tables: основная таблица обновлена → {main_path}")

    # ---- общая таблица медикаментов ----
    if os.path.exists(meds_path):
        logger.info(f"append_to_global_tables: читаю существующую {meds_path}")
        meds_df_old = pd.read_csv(meds_path)
        meds_df_all = pd.concat([meds_df_old, meds_df_new], ignore_index=True)
        meds_df_all = meds_df_all.drop_duplicates()
    else:
        logger.info(f"append_to_global_tables: {meds_path} не существует, создаем новую")
        meds_df_all = meds_df_new.copy()

    meds_df_all.to_csv(meds_path, index=False)
    logger.info(f"append_to_global_tables: таблица медикаментов обновлена → {meds_path}")


def main():
    # Ищем все JSON-ответы вида *_response.json в папке OUTPUT_DIR
    if not os.path.isdir(OUTPUT_DIR):
        logger.error(f"Директория с JSON не найдена: {OUTPUT_DIR}")
        raise FileNotFoundError(f"Директория с JSON не найдена: {OUTPUT_DIR}")

    json_files = [
        f for f in os.listdir(OUTPUT_DIR)
        if f.lower().endswith("_response.json")
    ]

    logger.info(f"Найдены JSON-ответы: {len(json_files)} шт. в {OUTPUT_DIR}")

    if not json_files:
        logger.error(f"В {OUTPUT_DIR} не найдено ни одного *_response.json")
        raise FileNotFoundError(f"В {OUTPUT_DIR} не найдено ни одного *_response.json")

    all_main_dfs: List[pd.DataFrame] = []
    all_meds_dfs: List[pd.DataFrame] = []

    print("Найдены JSON-ответы:")
    for fname in json_files:
        logger.info(f"Обработка JSON-файла: {fname}")
        json_path = os.path.join(OUTPUT_DIR, fname)

        main_df, meds_df = json_to_tables_from_file(json_path)
        all_main_dfs.append(main_df)
        all_meds_dfs.append(meds_df)

    # Объединяем всё в один DataFrame по заявкам и один по медикаментам
    combined_main_df = pd.concat(all_main_dfs, ignore_index=True)
    combined_meds_df = pd.concat(all_meds_dfs, ignore_index=True)

    # Дописываем в общие таблицы (или создаём, если их ещё нет),
    # удаляя дубли
    append_to_global_tables(combined_main_df, combined_meds_df, OUTPUT_DIR)

    print("Записи из всех JSON добавлены в общие таблицы:")
    print(f"- {os.path.join(OUTPUT_DIR, MAIN_TABLE_FILENAME)}")
    print(f"- {os.path.join(OUTPUT_DIR, MEDS_TABLE_FILENAME)}")


# ----------------- пример использования как скрипта ----------------- #

OUTPUT_DIR = os.getenv("OUTPUT_DIR", "output_files")

if __name__ == "__main__":
    setup_logging()
    logger = get_logger(__name__)

    logger.info("Приложение запущено (tab)")

    main()