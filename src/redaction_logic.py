
import json
import re
import os
import json
import re
import os
from config import MEMORY_FILE, IGNORE_FILE, SETTINGS, PROVINCE_FILE
from utils import logger

class RedactionMemory:
    def __init__(self, ephemeral=False):
        """
        :param ephemeral: If True, changes are NOT saved to disk (Privacy/Incognito mode).
        """
        self.ephemeral = ephemeral
        self.whitelist = set() # Terms to ALWAYS redact (e.g., Doctor names)
        self.blacklist = set() # Terms to NEVER redact (False positives)
        self.load_memory()

    def load_memory(self):
        """Loads memory from JSON files unless files don't exist."""
        self.whitelist = self._load_json_set(MEMORY_FILE)
        self.blacklist = self._load_json_set(IGNORE_FILE)
        logger.info(f"Memory loaded. Whitelist items: {len(self.whitelist)}, Blacklist items: {len(self.blacklist)}")

    def _load_json_set(self, filepath):
        if filepath.exists():
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    return set(data)
            except Exception as e:
                logger.error(f"Error loading {filepath}: {e}")
                return set()
        return set()

    def save_memory(self):
        """Saves memory to disk ONLY if not in ephemeral mode."""
        if self.ephemeral:
            logger.info("Ephemeral mode: Skipping save to disk.")
            return

        self._save_json_set(MEMORY_FILE, self.whitelist)
        self._save_json_set(IGNORE_FILE, self.blacklist)
        logger.info("Memory saved to disk.")

    def _save_json_set(self, filepath, data_set):
        try:
            # Sort and filter empty strings
            clean_list = sorted([t for t in data_set if t and len(t.strip()) > 1])
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(clean_list, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")

    def add_to_whitelist(self, terms):
        clean = {t.strip() for t in terms if t.strip()}
        self.whitelist.update(clean)
        # If it's in whitelist, remove from blacklist to avoid conflicts
        self.blacklist.difference_update(clean)

    def add_to_blacklist(self, terms):
        clean = {t.strip() for t in terms if t.strip()}
        self.blacklist.update(clean)
        # If it's in blacklist, remove from whitelist
        self.whitelist.difference_update(clean)

    def filter_terms(self, sensitive_terms):
        """
        Returns terms that should be redacted, filtering out blacklisted ones.
        """
        valid = set()
        for term in sensitive_terms:
            t = term.strip()
            if len(t) > 1 and t not in self.blacklist:
                valid.add(t)
        return valid

class TextAnalyzer:
    def __init__(self, memory: RedactionMemory, llm_engine=None):
        self.memory = memory
        self.llm_engine = llm_engine
        self.provinces = self._load_provinces()

    def _load_provinces(self):
        if PROVINCE_FILE.exists():
            try:
                with open(PROVINCE_FILE, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception as e:
                logger.error(f"Error loading {PROVINCE_FILE}: {e}")
        return set()

    def extract_regex_patterns(self, text, category="GENERIC"):
        """
        Extracts high-confidence patterns using Regular Expressions.
        Tailored for Italian Medical Records.
        """
        patterns = set()
        
        # 1. Codice Fiscale (16 uppercase alphanumeric characters)
        cf_pattern = r'\b[A-Z]{6}[0-9LMNPQRSTUV]{2}[ABCDEHLMPRST][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]\b'
        for match in re.finditer(cf_pattern, text):
            patterns.add(match.group())
            
        # Also catch occurrences like 'c.f. MRNDTL48D69L219Q' or 'C.F. XYZ' even if formatting is slightly off
        cf_prefix_pattern = r'(?i)\b(?:c\.f\.|cf|codice fiscale)\s*[:\-]?\s*([A-Z0-9]{16})\b'
        for match in re.finditer(cf_prefix_pattern, text):
            patterns.add(match.group(1).upper())

        # 2. Cartella Clinica / N° Cart / Codici numerici preceduti da "N°"
        # Example: "N°25104292" or "N° cart 2510429"
        cartella_pattern = r'(?i)\b(?:n[°º]|numero|cart|cartella)\s*(?:cart|clinica)?\s*[:\-]?\s*(\d{5,15})\b'
        for match in re.finditer(cartella_pattern, text):
            patterns.add(match.group()) # Add the whole match e.g. "N° cart 2510429"
            patterns.add(match.group(1)) # And just the number to be safe

        # 3. Doctor/Staff Names based on prefixes
        # Matches: "Dr. Rossi", "Dott.ssa Bianchi", "Prof. Verdi"
        dr_pattern = r'(?i)\b(?:dr\.|dott\.|dott\.ssa|prof\.|medico)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)*)\b'
        for match in re.finditer(dr_pattern, text):
            patterns.add(match.group())
            
        # Matches common signature blocks like "I. TARRICONE" or "M. MOLDOVANU"
        signature_pattern = r'\b[A-Z]\.\s+([A-Z]{3,})\b'
        for match in re.finditer(signature_pattern, text):
            patterns.add(match.group()) # Entire string "I. TARRICONE"
            patterns.add(match.group(1)) # Just surname "TARRICONE"

        # 4. Hospital / Institution Names
        # Matches "A.O. ORDINE MAURIZIANO", "Ospedale Mauriziano", "Azienda Ospedaliera" etc.
        hospital_pattern = r'(?i)\b(?:a\.o\.|ospedale|azienda ospedaliera(?: universitaria)?|presidio ospedaliero|asl|ausl)\s+([A-Z][a-z]+(?:\s+[A-Za-z]+){0,4})\b'
        for match in re.finditer(hospital_pattern, text):
            patterns.add(match.group())
            
        # Added specific hardcodes to catch capitalized blocks next to hospital keywords
        capitalized_hospital_pattern = r'(?i)\b(?:a\.o\.)\s+([A-Z\s]+)(?:$|\n|\s\s)'
        for match in re.finditer(capitalized_hospital_pattern, text):
             patterns.add(f"A.O. {match.group(1).strip()}")

        # 5. IP Addresses (HIPAA Element O)
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        for match in re.finditer(ip_pattern, text):
            patterns.add(match.group())

        # 6. URLs (HIPAA Element N)
        url_pattern = r'(?i)\b(?:https?://|www\.)[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:[/?#][^\s]*)?\b'
        for match in re.finditer(url_pattern, text):
            patterns.add(match.group())

        # 7. Email Addresses (HIPAA Element F)
        email_pattern = r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            patterns.add(match.group())
            
        # 8. Dates (HIPAA Element C - All elements of dates except year)
        # Matches DD/MM/YYYY, DD-MM-YYYY, DD.MM.YYYY
        date_pattern = r'\b(?:0[1-9]|[12][0-9]|3[01])[-/./](?:0[1-9]|1[012])[-/./](?:19|20)\d\d\b'
        
        if category == "DATI_STRUTTURATI":
            # For Lab Data, we MUST keep all dates/times for scientific validity.
            # We ONLY redact Date of Birth.
            # Look for dates immediately following birth keywords in Italian
            dob_pattern = r'(?i)\b(?:nat[oa]\s+il|data\s*(?:di\s*)?nascita|dob)\s*[:\-]?\s*(' + date_pattern + r')'
            for match in re.finditer(dob_pattern, text):
                patterns.add(match.group(1).strip())
        else:
            # In clinical notes, redact all exact dates to be safe
            for match in re.finditer(date_pattern, text):
                patterns.add(match.group())

        # 9. Phone/Fax Numbers (HIPAA Element D & E)
        # Basic match for numbers with optional prefixes like +39, spaces, dashes
        phone_pattern = r'\b(?:\+39\s?)?(?:0\d{1,3}\s?[\d\s-]{5,10}|3\d{2}\s?[\d\s-]{6,8})\b'
        for match in re.finditer(phone_pattern, text):
            # Only add if it's mostly digits (filter out false positives where it just matches spaces)
            clean_phone = re.sub(r'[\s\-+]', '', match.group())
            if len(clean_phone) >= 8:
                patterns.add(match.group().strip())

        # 10. Province Abbreviations e.g. (TO)
        province_pattern = r'\([A-Z]{2}\)'
        for match in re.finditer(province_pattern, text):
            if match.group() in self.provinces:
                patterns.add(match.group())

        return patterns

    def analyze_text(self, text, category="GENERIC"):
        """
        Combines Memory (Whitelist), Regex, and LLM extraction.
        """
        if not text.strip():
            return []

        found_terms = set()
        
        # 1. High-Confidence Regex Patterns (Rule-based)
        regex_terms = self.extract_regex_patterns(text, category=category)
        found_terms.update(self.memory.filter_terms(regex_terms))

        # 2. Start with known Whitelisted terms present in the text
        for term in self.memory.whitelist:
            # Simple substring check (could be improved with regex word boundaries)
            if term in text:
                found_terms.add(term)
        
        # 3. If LLM is available and enabled, ask it for more
        if self.llm_engine and self.llm_engine.is_ready():
            llm_terms = self.llm_engine.extract_pii(text, category=category)
            filtered_llm = self.memory.filter_terms(llm_terms)
            found_terms.update(filtered_llm)
        
        return sorted(list(found_terms))
