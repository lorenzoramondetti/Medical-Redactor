import json
import re
from pathlib import Path
from config import MEMORY_FILE, IGNORE_FILE, SETTINGS, PROVINCE_FILE
from utils import logger

class RedactionMemory:
    def __init__(self, ephemeral=False):
        self.whitelist = set()
        self.blacklist = set()
        self.blacklist_lower = set()
        self.ephemeral = ephemeral
        self.load_memory()

    def load_memory(self):
        """Loads memory from JSON files unless files don't exist."""
        self.whitelist = self._load_json_set(MEMORY_FILE)
        self.blacklist = self._load_json_set(IGNORE_FILE)
        self.blacklist_lower = {t.lower() for t in self.blacklist}
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
            # Sort and filter empty strings and multi-line garbage
            clean_list = sorted([t for t in data_set if t and len(t.strip()) > 1 and '\n' not in t])
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(clean_list, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving {filepath}: {e}")

    def add_to_whitelist(self, terms):
        clean = {t.strip() for t in terms if t.strip() and '\n' not in t}
        self.whitelist.update(clean)
        # If it's in whitelist, remove from blacklist to avoid conflicts
        self.blacklist.difference_update(clean)
        self.blacklist_lower = {t.lower() for t in self.blacklist}

    def add_to_blacklist(self, terms):
        clean = {t.strip() for t in terms if t.strip()}
        self.blacklist.update(clean)
        self.blacklist_lower = {t.lower() for t in self.blacklist}
        # If it's in blacklist, remove from whitelist
        self.whitelist.difference_update(clean)

    def filter_terms(self, sensitive_terms, is_pii=False):
        """
        Returns terms that should be redacted. 
        If is_pii is True, we are extremely permissive.
        """
        valid = set()
        # Word boundaries prevent 'pg' matching 'impegnativa'
        lab_unit_pattern = r'(?i)\b(?:mg/dL|mmol/L|g/dL|U/L|pg|fL|mEq/L|mol/L|mmol)\b'
        ui_labels = {"paziente", "nato il", "data", "scadenza", "firma", "sig.", "informazioni", "paziente:"}
        
        for term in sensitive_terms:
            t = term.strip()
            # Remove trailing dots or punctuation that might be captured
            t = t.rstrip('.,;:')
            t_lower = t.lower()
            
            # 1. Essential checks (MUST apply even to PII)
            if len(t) <= 1: continue
            if '\n' in t: continue
            
            # 2. Blacklist check (Crucial: even for PII)
            if t_lower in self.blacklist_lower:
                continue
                
            # 3. Lab Unit check
            if re.search(lab_unit_pattern, t):
                continue
            
            # 4. Noise/Partial Date check (e.g., 01/01/1)
            # If it looks like a date, we allow it even if potentially truncated,
            # as medical records often cut off the year (e.g. 01/01/198).
            date_match = re.match(r'^(\d{1,2})[-/.](\d{1,2})[-/.](\d{1,4})$', t)
            if date_match:
                # We only skip if the string is extremely short and contextless,
                # but 01/01/1 is 7 chars, which is identifying enough.
                if len(t) < 6:
                    continue

            # 5. Clinical Acronym check (e.g., M.C., E.C.G., F.A.)
            # High-recall protection for common 2-4 letter medical acronyms with dots.
            # Handle both with and without trailing dot (since it might have been stripped above).
            if re.match(r'^[A-Z]\.(?:[A-Z]\.?){1,3}$', t):
                 continue

            # PII OVERRIDE: If the system tagged this as PII (Regex/AI), 
            # we are more permissive after the basic security/noise checks above.
            if is_pii:
                valid.add(t)
                continue
                
            # 6. Generic/Memory filtering (Only if NOT already tagged as PII)
            if t.endswith(":") or t_lower in ui_labels: continue
            
            valid.add(t)
        return valid

class TextAnalyzer:
    def __init__(self, memory: RedactionMemory, llm_engine=None):
        self.memory = memory
        self.llm_engine = llm_engine
        self.provinces = self._load_provinces()
        self.common_hospitals = {"OSPEDALE CIVILE", "OSPEDALE MAGGIORE", "POLICLINICO"}

    def _load_provinces(self):
        if PROVINCE_FILE.exists():
            try:
                with open(PROVINCE_FILE, "r", encoding="utf-8") as f:
                    return set(json.load(f))
            except Exception as e:
                logger.error(f"Error loading {PROVINCE_FILE}: {e}")
        return set()

    def extract_regex_patterns(self, text, category="GENERIC"):
        patterns = set()
        
        # 1. Codice Fiscale
        cf_pattern = r'\b[A-Z]{6}[0-9LMNPQRSTUV]{2}[ABCDEHLMPRST][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]\b'
        for match in re.finditer(cf_pattern, text):
            patterns.add(match.group())
            
        cf_prefix_pattern = r'(?i)\b(?:c\.f\.|cf|codice fiscale)\s*[:\-]?\s*([A-Z0-9]{16})\b'
        for match in re.finditer(cf_prefix_pattern, text):
            patterns.add(match.group(1).upper())

        # 2. Cartella Clinica
        cartella_pattern = r'(?i)\b(?:n[°º]|numero|cart|cartella)\s*(?:cart|clinica)?\s*[:\-]?\s*(\d{5,15})\b'
        for match in re.finditer(cartella_pattern, text):
            patterns.add(match.group())
            patterns.add(match.group(1))

        # 3. Doctor/Staff Names based on prefixes. 
        # We use a non-greedy name part to avoid capturing conjunctions like 'e' or 'dalla'.
        # Prefixes are case-insensitive, but name components must be Title Case or ALL CAPS.
        prefixes = r'(?i:dr\.|dott\.|dott\.ssa|prof\.|medico|dottore)'
        name_comp = r'(?:[A-Z][a-z]+|[A-Z]{2,})'
        dr_pattern = fr'\b{prefixes}\s+({name_comp}(?:\s+{name_comp})*)\b'
        
        for match in re.finditer(dr_pattern, text):
            name = match.group(1).strip()
            if len(name) > 2:
                patterns.add(match.group())
                patterns.add(name)
            
        # Signature blocks
        signature_pattern = r'\b[A-Z]\.\s+([A-Z]{3,})\b'
        for match in re.finditer(signature_pattern, text):
            patterns.add(match.group())
            patterns.add(match.group(1))

        # 4. Hospital / Institution Names
        hospital_pattern = r'(?i)\b(?:a\.o\.|ospedale|azienda ospedaliera(?: universitaria)?|presidio ospedaliero|asl|ausl)\s+([A-Z][a-z]+(?:\s+[A-Za-z]+){0,4})\b'
        for match in re.finditer(hospital_pattern, text):
            patterns.add(match.group())
            
        capitalized_hospital_pattern = r'(?i)\b(?:a\.o\.)\s+([A-Z\s]+)(?:$|\n|\s\s)'
        for match in re.finditer(capitalized_hospital_pattern, text):
             patterns.add(f"A.O. {match.group(1).strip()}")

        # 5. IP Addresses
        ip_pattern = r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b'
        for match in re.finditer(ip_pattern, text):
            patterns.add(match.group())

        # 6. URLs
        url_pattern = r'(?i)\b(?:https?://|www\.)[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:[/?#][^\s]*)?\b'
        for match in re.finditer(url_pattern, text):
            patterns.add(match.group())

        # 7. Email Addresses
        email_pattern = r'(?i)\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b'
        for match in re.finditer(email_pattern, text):
            patterns.add(match.group())
            
        # 8. Dates (Supports partial/truncated years)
        date_pattern = r'\b(?:0[1-9]|[12][0-9]|3[01])[-/./](?:0[1-9]|1[012])[-/./]\d{1,4}\b'
        if category == "DATI_STRUTTURATI":
            dob_pattern = r'(?i)\b(?:nat[oa]\s+il|data\s*(?:di\s*)?nascita|dob)\s*[:\-]?\s*(' + date_pattern + r')'
            for match in re.finditer(dob_pattern, text):
                patterns.add(match.group(1).strip())
        else:
            for match in re.finditer(date_pattern, text):
                patterns.add(match.group())

        # 9. Phone/Fax Numbers
        phone_pattern = r'\b(?:\+39\s?)?(?:0\d{1,3}\s?[\d\s-]{5,10}|3\d{2}\s?[\d\s-]{6,8})\b'
        for match in re.finditer(phone_pattern, text):
            clean_phone = re.sub(r'[\s\-+]', '', match.group())
            if len(clean_phone) >= 8:
                patterns.add(match.group().strip())

        # 10. Province Abbreviations
        province_pattern = r'\([A-Z]{2}\)'
        for match in re.finditer(province_pattern, text):
            if match.group() in self.provinces:
                patterns.add(match.group())

        return patterns

    def analyze_text(self, text, category="GENERIC"):
        if not text.strip():
            return []

        found_terms = set()
        
        # 1. Regex Patterns
        regex_terms = self.extract_regex_patterns(text, category=category)
        found_terms.update(self.memory.filter_terms(regex_terms, is_pii=True))

        # 2. Whitelisted terms (Regex Word Boundary Search)
        # This prevents "CORSO" from matching "SOCCORSO" or "VIA" matching "INVIA"
        whitelist_found = set()
        for term in self.memory.whitelist:
            if not term.strip(): continue
            # Escape term (special chars like dots or parens) and add word boundaries
            pattern = r'(?i)\b' + re.escape(term.strip()) + r'\b'
            for match in re.finditer(pattern, text):
                whitelist_found.add(match.group())
        
        # Apply filters to whitelisted terms as well (Consistency)
        found_terms.update(self.memory.filter_terms(whitelist_found, is_pii=True))
        
        # 3. AI Extraction
        if self.llm_engine and self.llm_engine.is_ready():
            llm_terms = self.llm_engine.extract_pii(text, category=category)
            filtered_llm = self.memory.filter_terms(llm_terms, is_pii=True)
            found_terms.update(filtered_llm)
        
        return sorted(list(found_terms))
