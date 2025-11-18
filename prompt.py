# height, dosage_unit, is_main_applicant  - custom keys
#  "status": accepted/rejected,

target_json_format = '''{
  "uid": "string (optional)",
  "check_it": bool,
  "reason_checking": 'string'
  "applicants": [
    {
      "applicant": 0,
      "is_main_applicant" : bool
      "firstName": "string (optional)",
      "lastName": "string (optional)",
      "midName": "string (optional)",
      "phone": "string (optional)",
      "gender": "string (optional)",
      "dob": "YYYY-MM-DD (optional)",
      "nicotine": bool (optional),
      "weight": float (optional), (0 default)
      "height":int (optional), (0 default)
      "heightFt": int (optional), (0 default)
      "heightIn": int (optional) (0 default)
    }
  ],
  "plans": [
    {
      "id": int, (0 default)
      "priceId": int (0 default)
    }
  ],
  "phq": {
    "treatment": bool,
    "invalid": bool,
    "pregnancy": bool,
    "effectiveDate": "YYYY-MM-DD",
    "disclaimer": bool,
    "signature": "string",
    "medications": [
      {
        "applicant": int,
        "name": "string",
        "rxcui": "string",
        "dosage": "string",
        "dosage_unit": "string",
        "frequency": "string",
        "description": "string"
      }
    ],
    "issues": [
      {
        "key": "string",
        "details": [
          {
            "key": "string",
            "description": "string"
          }
        ]
      }
    ],
    "conditions": [
      {
        "key": "string",
        "description": "string"
      }
    ]
  },
  "income": float,
  "address": {
    "address1": "string (optional)",
    "address2": "string (optional)",
    "city": "string (optional)",
    "state": "string (optional)",
    "zipcode": "string (optional)"
  }
}'''



prompt_template = """  
You are an expert in processing insurance documents. Your task is to **precisely extract data** from the provided PDF and convert it into JSON.  
Key Requirements:  
1. Data Accuracy:  
   - Preserve all original values exactly as written, even if they appear incorrect.  
   - Do not correct, reformat, or infer missing data.  
   - When filling out fields and descriptions, avoid using the direct names of applicants, as this is confidential.

2. Special Field Handling:
   - Information about the primary applicant is at the very beginning of the document, for example, in the Member Information section. For them, set "is_main_applicant": True.
   - Weight: Extract numeric value only (remove "kg", "lbs" etc.) and convert to integer
   - Height: 
     * "heightFt" must be integer (feet portion only, no units)
     * "heightIn" must be integer (inches portion only, no units)
   - Gender: Must be strictly "male" or "female" (convert if needed: "m" → "male", "f" → "female")
   - Medications:
      "frequency" must be one of: ["Once daily", "Twice daily", "Three times daily", "Four times daily", "Weekly", "Monthly", "Every other day", "At bedtime", "After meals", "Before meals", "As needed"]
      "dosage": no units
      "dosage_unit": unit of measurement, eg mg  
   - Income is usually indicated in the Yearly Income section.

3. Family Members:  
   - Usually, information about additional applicants is located in the Dependent Information section. If you see that this section exists but no individuals are listed, set the flag "check_it": True.
   In the "reason_checking" field, briefly describe what is wrong and why this data needs to be checked.
   - If the PDF lists additional family members under the insurance policy, include them in the `applicants` array.  
   - Maintain their names, relationships, and other details verbatim.  

4. Medications:  
   - Extract all mentioned medications, including dosage and frequency, and map them to the `medications` field.  
   - Retain original spelling/phrasing
   - In the name field, specify only the name of the medicine

5. Missing Data:  
   - Use empty strings (`""`), `false`, or empty arrays/objects where fields are absent.  
   - Never guess or populate placeholder values.  

6. Strict Structure Compliance:  
   - Adhere **exactly** to the provided JSON schema.  
   - No additional fields, alterations, or deviations allowed.  

Target JSON Schema:  
{target_json_format}  

PDF Content:  
{pdf_text}  

Output **only the raw JSON object** without explanations or annotations.  
"""  