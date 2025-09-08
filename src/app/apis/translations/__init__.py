# src/app/apis/translations/__init__.py
import databutton as db
import os
import re
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Dict

router = APIRouter(prefix="/translations")

# Define the path to the translations directory
TRANSLATIONS_DIR = "/app/ui/src/utils"

class TranslationUpdateRequest(BaseModel):
    language: str
    translations: Dict[str, str]

def parse_ts_file(content: str) -> Dict[str, str]:
    """
    Parses key-value pairs from a TypeScript object using a robust regex.
    It handles single or double quotes and correctly extracts keys and values.
    """
    data = {}
    # This regex looks for a key (word), colon, and a quoted string on each line.
    pattern = re.compile(r"^\s*(\w+):\s*['\"](.*?)['\"],?\s*$", re.MULTILINE)
    matches = pattern.findall(content)
    for key, value in matches:
        # Un-escape characters that might be escaped in the string, like \"
        data[key] = value.replace('\\"', '"').replace("\\'", "'")
    return data

def format_ts_file(language: str, data: Dict[str, str]) -> str:
    """Formats a dictionary of translations back into a TypeScript file string."""
    header = f"// ui/src/utils/translations.{language}.ts\nexport const {language} = {{\n"
    footer = "\n};"
    
    lines = []
    for key, value in data.items():
        # First, escape any double quotes within the value string.
        escaped_value = value.replace('"', '\\"')
        # Then, construct the line safely.
        lines.append(f'  {key}: "{escaped_value}",')
    
    return header + "\n".join(lines) + footer


@router.get("/all", tags=["translations"])
def get_all_translations():
    print("START: get_all_translations")
    """
    Scans the translations directory, reads each language file,
    and returns them as a JSON object.
    """
    all_translations = {}
    try:
        print(f"Searching for translation files in: {TRANSLATIONS_DIR}")
        files = os.listdir(TRANSLATIONS_DIR)
        print(f"Found files: {files}")
        for filename in files:
            if filename.startswith("translations.") and filename.endswith(".ts"):
                print(f"Processing file: {filename}")
                lang_match = re.search(r"translations\.(.*?)\.ts", filename)
                if lang_match:
                    lang = lang_match.group(1)
                    filepath = os.path.join(TRANSLATIONS_DIR, filename)
                    print(f"Reading translations for language '{lang}' from {filepath}")
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                        parsed_data = parse_ts_file(content)
                        print(f"Parsed data for '{lang}': {{key_count: len(parsed_data)}}")
                        all_translations[lang] = parsed_data
    except FileNotFoundError as e:
        print(f"ERROR in get_all_translations: {e}")
        raise HTTPException(status_code=404, detail="Translations directory not found.") from e
    except Exception as e:
        print(f"ERROR in get_all_translations: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to read translation files: {e}") from e
    
    print(f"END: get_all_translations - Returning {len(all_translations)} languages.")
    return all_translations

@router.post("/update", tags=["translations"])
def update_translation_file(request: TranslationUpdateRequest):
    print(f"START: update_translation_file for language: {request.language}")
    print(f"Received data: {request.dict()}")
    """
    Receives a language and a set of translations, and overwrites
    the corresponding translation file.
    """
    lang = request.language
    if not re.match("^[a-z]{2}$", lang):
        print(f"ERROR: Invalid language code '{lang}'")
        raise HTTPException(status_code=400, detail="Invalid language code format.")

    filename = f"translations.{lang}.ts"
    filepath = os.path.join(TRANSLATIONS_DIR, filename)
    print(f"Target file path: {filepath}")

    if not os.path.exists(filepath):
        print(f"ERROR: File not found at {filepath}")
        raise HTTPException(status_code=404, detail=f"Translation file for language '{lang}' not found.")

    try:
        new_content = format_ts_file(lang, request.translations)
        print(f"Formatted new content for {filename}: Truncated for brevity...")
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print(f"Successfully wrote to {filepath}")
    except Exception as e:
        print(f"ERROR: Failed to write to {filepath}: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to write translation file: {e}") from e

    print("END: update_translation_file")
    return {"status": "success", "language": lang, "message": f"Successfully updated {filename}"}
