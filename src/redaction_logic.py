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
        
        from regex_rules_manager import RegexRulesManager
        manager = RegexRulesManager()
        
        for rule_name, rule in manager.rules.items():
            if not rule.get("active", True):
                continue
                
            try:
                pattern = rule["pattern"]
                group_logic = rule.get("group", 0)
                
                # Special skip for dates in DATI_STRUTTURATI
                if group_logic == "date_logic" and category == "DATI_STRUTTURATI":
                    continue
                if group_logic == "dob_logic" and category != "DATI_STRUTTURATI":
                    continue
                    
                for match in re.finditer(pattern, text):
                    # Evaluate custom grouping logic
                    if group_logic == 0:
                        patterns.add(match.group())
                    elif group_logic == 1:
                        patterns.add(match.group(1).upper())
                    elif group_logic == "both":
                        patterns.add(match.group())
                        if len(match.groups()) > 0:
                            patterns.add(match.group(1))
                    elif group_logic == "prepend_ao":
                        patterns.add(f"A.O. {match.group(1).strip()}")
                    elif group_logic == "phone":
                        clean_phone = re.sub(r'[\s\-+]', '', match.group())
                        if len(clean_phone) >= 8:
                            patterns.add(match.group().strip())
                    elif group_logic == "province":
                        if match.group() in self.provinces:
                            patterns.add(match.group())
                    elif group_logic == "date_logic" or group_logic == "dob_logic":
                        if len(match.groups()) > 0:
                            patterns.add(match.group(1).strip())
                        else:
                            patterns.add(match.group())
            except Exception as e:
                logger.error(f"Error applying regex rule '{rule_name}': {e}")
                
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
            # Escape term (special chars like dots or parens) and add word boundaries via lookarounds
            pattern = r'(?i)(?<!\w)' + re.escape(term.strip()) + r'(?!\w)'
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

def classify_redacted_term(term):
    import re
    term = term.strip()
    term_lower = term.lower()
    
    # 1. Codice Fiscale / Tessera Sanitaria / UK NHS
    cf_pattern = r'^[A-Z]{6}[0-9LMNPQRSTUV]{2}[ABCDEHLMPRST][0-9LMNPQRSTUV]{2}[A-Z][0-9LMNPQRSTUV]{3}[A-Z]$'
    ts_pattern = r'^\d{20}$'
    nhs_pattern = r'^\d{3}\s?-?\s?\d{3}\s?-?\s?\d{4}$|^\d{10}$'
    if re.match(cf_pattern, term, re.IGNORECASE) or re.match(ts_pattern, term) or re.match(nhs_pattern, term):
        return "SSN / National ID / Tax Codes"
        
    # 2. Email / URL / IP
    email_pattern = r'^[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}$'
    url_pattern = r'^(?:https?://|www\.)[a-z0-9-]+(?:\.[a-z0-9-]+)+(?:[/?#][^\s]*)?$'
    ip_pattern = r'^(?:[0-9]{1,3}\.){3}[0-9]{1,3}$'
    if re.match(email_pattern, term, re.IGNORECASE) or re.match(url_pattern, term, re.IGNORECASE) or re.match(ip_pattern, term):
        return "Digital Contacts (Email/URL/IP)"
        
    # 3. Dates
    date_pattern = r'^(?:0[1-9]|[12][0-9]|3[01])[-/./](?:0[1-9]|1[012])[-/./]\d{1,4}$'
    if re.match(date_pattern, term):
        return "Dates (Birth/Admission/Discharge)"
        
    # 4. Phone numbers / Fax
    phone_pattern = r'^\+?[0-9\s.\-\(\)]{6,20}$'
    if re.match(phone_pattern, term) and any(c.isdigit() for c in term):
        if sum(c.isdigit() for c in term) >= 6:
            return "Phone Numbers / Contacts"
            
    # 5. CAP (Zip Codes)
    if term.isdigit() and len(term) == 5:
        return "Addresses / ZIP Codes"

    # 6. Cartella Clinica / Codice Paziente
    code_pattern = r'^[A-Za-z0-9\-/_]{5,15}$'
    if re.match(code_pattern, term) and any(c.isdigit() for c in term) and any(c.isalpha() for c in term):
        return "ID Codes (Record/Patient)"
    if term.isdigit() and 4 <= len(term) <= 12:
        return "ID Codes (Record/Patient)"
        
    # 7. Hospitals / Medical centers
    hospital_keywords = ["ospedale", "policlinico", "clinica", "asl", "ausl", "presidio", "azienda ospedaliera"]
    if any(k in term_lower for k in hospital_keywords):
        return "Healthcare Facilities (Hospitals/Clinics)"
        
    # 8. Prefixes of doctors/names
    prefixes = ["dr.", "dott.", "dott.ssa", "prof.", "medico", "dr", "dottore", "sig.", "sig.ra"]
    if any(term_lower.startswith(p) for p in prefixes) or any(term_lower.startswith(p + " ") for p in prefixes):
        return "Personal Names (Doctors/Patients)"
        
    # 9. Name heuristics
    if term.replace(" ", "").isalpha():
        words = term.split()
        if 1 <= len(words) <= 4:
            if all(w[0].isupper() or w.isupper() for w in words):
                return "Personal Names (Doctors/Patients)"
                
    return "Other Sensitive Information"
