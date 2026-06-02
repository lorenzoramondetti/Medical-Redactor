import json
import re
from pathlib import Path
from config import REGEX_RULES_FILE
from utils import logger

DEFAULT_REGEX_RULES = {
    "Fiscal Code": {
        "active": True,
        "pattern": r'\b[A-Z]{6}[0-9LMNPQRSTUV]{2}[ABCDEHLMPRST][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]\b',
        "group": 0,
        "description": "Italian Fiscal Code (16 alphanumeric characters)"
    },
    "Fiscal Code Prefix": {
        "active": True,
        "pattern": r'(?i)\b(?:c\.f\.|cf|codice fiscale)\s*[:\-]?\s*([A-Z0-9]{16})\b',
        "group": 1,
        "description": "Fiscal Code with textual prefix"
    },
    "UK NHS Number": {
        "active": True,
        "pattern": r'\b\d{3}\s?-?\s?\d{3}\s?-?\s?\d{4}\b',
        "group": 0,
        "description": "British NHS Number (10 digits)"
    },
    "Health Card (Tessera Sanitaria)": {
        "active": True,
        "pattern": r'\b\d{20}\b',
        "group": 0,
        "description": "Italian Health Card (20 digits)"
    },
    "Medical Record ID": {
        "active": True,
        "pattern": r'(?i)\b(?:n[°º]|numero|cart|cartella)\s*(?:cart|clinica)?\s*[:\-]?\s*(\d{5,15})\b',
        "group": "both",
        "description": "Medical record numbers with prefixes (captures both the digits and the full block)"
    },
    "Medical Staff / Physician": {
        "active": True,
        "pattern": r'(?i:\b(?:dr\.|dott\.|dott\.ssa|prof\.|medico|dottore)\s+((?:[A-Z][a-z]+|[A-Z]{2,})(?:\s+(?:[A-Z][a-z]+|[A-Z]{2,}))*)\b)',
        "group": "both",
        "description": "Physician names with common prefixes"
    },
    "Signature": {
        "active": True,
        "pattern": r'\b[A-Z]\.\s+([A-Z]{3,})\b',
        "group": "both",
        "description": "Signatures at the bottom (e.g., M. ROSSI)"
    },
    "Healthcare Facility": {
        "active": True,
        "pattern": r'(?i)\b(?:a\.o\.|ospedale|azienda ospedaliera(?: universitaria)?|presidio ospedaliero|asl|ausl)\s+([A-Z][a-z]+(?:\s+[A-Za-z]+){0,4})\b',
        "group": 0,
        "description": "Names of hospitals and clinics (A.O., ASL, etc.)"
    },
    "Healthcare Facility (Uppercase)": {
        "active": True,
        "pattern": r'(?i)\b(?:a\.o\.)\s+([A-Z\s]+)(?:$|\n|\s\s)',
        "group": "prepend_ao",
        "description": "A.O. followed by hospital name in uppercase"
    },
    "IP Address": {
        "active": True,
        "pattern": r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b',
        "group": 0,
        "description": "IP Addresses (IPv4)"
    },
    "URL": {
        "active": True,
        "pattern": r'(?i)\b(?:https?://|www\.)[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:[/?#][^\s]*)?\b',
        "group": 0,
        "description": "Websites (URLs)"
    },
    "Email": {
        "active": True,
        "pattern": r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b',
        "group": 0,
        "description": "Email Addresses"
    },
    "Date (Standard)": {
        "active": True,
        "pattern": r'\b(?:0[1-9]|[12][0-9]|3[01])[-/./](?:0[1-9]|1[012])[-/./]\d{1,4}\b',
        "group": "date_logic",
        "description": "Dates (will be automatically excluded in STRUCTURED_DATA)"
    },
    "Structured Date of Birth": {
        "active": True,
        "pattern": r'(?i)\b(?:nat[oa]\s+il|data\s*(?:di\s*)?nascita|dob)\s*[:\-]?\s*((?:0[1-9]|[12][0-9]|3[01])[-/./](?:0[1-9]|1[012])[-/./]\d{1,4})',
        "group": "dob_logic",
        "description": "Captures date of birth even in STRUCTURED_DATA documents"
    },
    "Phone / Fax": {
        "active": True,
        "pattern": r'\b(?:\+39\s?)?(?:0\d{1,3}\s?[\d\s-]{5,10}|3\d{2}\s?[\d\s-]{6,8})\b',
        "group": "phone",
        "description": "Italian phone and fax numbers"
    },
    "Province (Italian)": {
        "active": True,
        "pattern": r'\([A-Z]{2}\)',
        "group": "province",
        "description": "Province abbreviations (2 letters in parentheses)"
    }
}

class RegexRulesManager:
    def __init__(self):
        self.rules = {}
        self.load_rules()

    def load_rules(self):
        translation_map = {
            "Codice Fiscale": "Fiscal Code",
            "Prefisso CF": "Fiscal Code Prefix",
            "Tessera Sanitaria": "Health Card (Tessera Sanitaria)",
            "Cartella Clinica": "Medical Record ID",
            "Medico / Staff": "Medical Staff / Physician",
            "Firme": "Signature",
            "Struttura Sanitaria": "Healthcare Facility",
            "Struttura Sanitaria (Maiuscolo)": "Healthcare Facility (Uppercase)",
            "Indirizzo IP": "IP Address",
            "Data (Standard)": "Date (Standard)",
            "Data di Nascita Strutturata": "Structured Date of Birth",
            "Telefono / Fax": "Phone / Fax",
            "Provincia": "Province (Italian)"
        }
        if REGEX_RULES_FILE.exists():
            try:
                with open(REGEX_RULES_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    # Start with default rules to catch any missing default keys if app was updated
                    self.rules = DEFAULT_REGEX_RULES.copy()
                    # Merge loaded rules, translating old Italian keys and preserving custom user-defined rules
                    for k, v in loaded.items():
                        if k in translation_map:
                            target_key = translation_map[k]
                            if target_key in self.rules:
                                self.rules[target_key]["active"] = v.get("active", True)
                        else:
                            self.rules[k] = v
                return
            except Exception as e:
                logger.error(f"Error loading {REGEX_RULES_FILE}: {e}")
        
        # If not exists or error, save defaults
        self.rules = DEFAULT_REGEX_RULES.copy()
        self.save_rules()

    def save_rules(self):
        try:
            with open(REGEX_RULES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.rules, f, indent=4)
        except Exception as e:
            logger.error(f"Error saving {REGEX_RULES_FILE}: {e}")

    def reset_to_defaults(self):
        self.rules = DEFAULT_REGEX_RULES.copy()
        self.save_rules()
