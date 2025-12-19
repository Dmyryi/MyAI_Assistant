import json
import os
from typing import Dict, List

class LocalizationManager:
    """
    Class for managing multilingual support in the application.
    Loads translations from JSON files.
    (Located in Infrastructure layer)
    """
    
    def __init__(self, locales_dir: str, default_lang: str = "en"):
        self.locales_dir = locales_dir
        self._current_lang = default_lang
        self.translations: Dict[str, str] = {}
        self.load_language(default_lang)

    @property
    def current_language(self) -> str:
        """Returns current language code."""
        return self._current_lang

    def get_available_languages(self) -> List[str]:
        """Scans locales folder and returns list of available language codes."""
        languages = []
        if os.path.exists(self.locales_dir):
            for filename in os.listdir(self.locales_dir):
                if filename.endswith(".json"):
                    languages.append(filename[:-5])
        return sorted(languages)

    def load_language(self, lang_code: str) -> bool:
        """Loads translation file for specified language."""
        lang_file = os.path.join(self.locales_dir, f"{lang_code}.json")
        if not os.path.exists(lang_file):
            print(f"[Localization] Warning: Language file not found: {lang_file}")
            if lang_code != "en" and lang_code != "ru" and lang_code != "uk":
                 print(f"[Localization] Falling back to default")
                 fallback_langs = self.get_available_languages()
                 if fallback_langs:
                     return self.load_language(fallback_langs[0])
            return False

        try:
            with open(lang_file, 'r', encoding='utf-8') as f:
                self.translations = json.load(f)
            self._current_lang = lang_code
            print(f"[Localization] Language switched to: {lang_code}")
            return True
        except json.JSONDecodeError as e:
             print(f"[Localization] Error parsing JSON for '{lang_code}': {e}")
             self.translations = {}
             return False
        except Exception as e:
             print(f"[Localization] Unexpected error loading '{lang_code}': {e}")
             self.translations = {}
             return False

    def get(self, key: str, **kwargs) -> str:
        """Gets translated string by key with formatting support."""
        text = self.translations.get(key, key)
        if kwargs:
            try:
                return text.format(**kwargs)
            except KeyError as e:
                return text
            except ValueError as e:
                 return text
        return text

import sys
if getattr(sys, 'frozen', False):
    _base_dir = sys._MEIPASS
else:
    _base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOCALES_PATH = os.path.join(_base_dir, "locales")

i18n = LocalizationManager(LOCALES_PATH, default_lang="en")

_ = i18n.get

