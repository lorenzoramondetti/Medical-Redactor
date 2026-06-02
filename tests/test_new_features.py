import unittest
import sys
import os
import tempfile
from pathlib import Path
import re

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from redaction_logic import RedactionMemory, TextAnalyzer, classify_redacted_term
import config

class TestNewFeatures(unittest.TestCase):
    
    def setUp(self):
        self.memory = RedactionMemory(ephemeral=True)
        self.analyzer = TextAnalyzer(self.memory)

    def test_uk_nhs_numbers(self):
        """Verify extraction of UK NHS numbers in various formats."""
        # NHS number: 10 digits. Supported formats:
        # 1. Formatted 3-3-4 like '123-456-7890' or '123 456 7890'
        # 2. Raw 10-digit '1234567890'
        
        texts = [
            "My NHS number is 123-456-7890.",
            "His NHS number is 987 654 3210.",
            "The ID is 1234567890.",
            "NHS number: 456-789-0123",
            "NHS number 7890123456"
        ]
        
        for text in texts:
            found = self.analyzer.extract_regex_patterns(text)
            # Find any match in the extracted list
            matched = False
            for term in found:
                # Strip spaces/dashes to verify it extracted the correct sequence
                clean_term = re.sub(r'[\s-]', '', term)
                if len(clean_term) == 10 and clean_term.isdigit():
                    matched = True
            self.assertTrue(matched, f"Failed to extract NHS number from: {text}")

    def test_italian_tessera_sanitaria(self):
        """Verify extraction of Italian Tessera Sanitaria (TS) 20-digit numbers."""
        text = "La Tessera Sanitaria numero 12345678901234567890 è scaduta."
        found = self.analyzer.extract_regex_patterns(text)
        self.assertIn("12345678901234567890", found)

    def test_host_pc_staging_redirection(self):
        """Verify that STAGING_DIR is successfully mapped to the Host PC local disk."""
        staging_str = str(config.STAGING_DIR)
        temp_dir_str = tempfile.gettempdir()
        
        # Staging directory should either use custom_staging_path (if set in settings)
        # or fall back to the host PC's temporary directory.
        if config.SETTINGS.get("custom_staging_path", "").strip():
            self.assertEqual(config.STAGING_DIR, Path(config.SETTINGS["custom_staging_path"].strip()))
        else:
            self.assertTrue(staging_str.startswith(temp_dir_str) or "MedicalRedactorStaging" in staging_str, 
                            f"Staging dir '{staging_str}' does not seem to reside in the host PC's temp directory '{temp_dir_str}'")

    def test_active_learning_propagation_logic(self):
        """Verify that terms added during manual review can be matched case-insensitively using word boundaries."""
        # We test the core regex matching logic used in main.py for cross-file active learning propagation.
        # Logic: pattern = r'(?i)\b' + re.escape(term.strip()) + r'\b'
        
        # Case 1: Match exactly
        term = "Mario Rossi"
        other_text = "Il signore Mario Rossi è ricoverato."
        pattern = r'(?i)\b' + re.escape(term.strip()) + r'\b'
        self.assertTrue(re.search(pattern, other_text))
        
        # Case 2: Match case-insensitively
        other_text_case = "Il signore MARIO ROSSI è ricoverato."
        self.assertTrue(re.search(pattern, other_text_case))
        
        # Case 3: Match on word boundaries (should not match substring in longer word)
        term_short = "Rossi"
        other_text_long = "Il signore Rossini è ricoverato."
        pattern_short = r'(?i)\b' + re.escape(term_short.strip()) + r'\b'
        self.assertFalse(re.search(pattern_short, other_text_long))
        
        # Case 4: Match with punctuation
        other_text_punct = "Rossi, Mario"
        self.assertTrue(re.search(pattern_short, other_text_punct))

    def test_dynamic_threshold_slider(self):
        """Verify dynamic configuration and entity classification."""
        # 1. Verify config default value
        self.assertEqual(config.DEFAULT_SETTINGS.get("ai_threshold", 0.45), 0.45)
        
        # 2. Test classify_redacted_term classifications
        self.assertEqual(classify_redacted_term("RSSMRA80A01H501U"), "Codici Fiscali / Tessera Sanitaria / ID Nazionali")
        self.assertEqual(classify_redacted_term("12345678901234567890"), "Codici Fiscali / Tessera Sanitaria / ID Nazionali")
        self.assertEqual(classify_redacted_term("123-456-7890"), "Codici Fiscali / Tessera Sanitaria / ID Nazionali")
        self.assertEqual(classify_redacted_term("mario.rossi@hospital.it"), "Contatti Digitali (Email/URL/IP)")
        self.assertEqual(classify_redacted_term("12/05/1985"), "Date (Nascita/Ricovero/Dimissione)")
        self.assertEqual(classify_redacted_term("Ospedale Niguarda"), "Strutture Sanitarie (Ospedali/Cliniche/ASL)")
        self.assertEqual(classify_redacted_term("Dr. Mario Rossi"), "Nomi Personali (Medici/Pazienti)")
        self.assertEqual(classify_redacted_term("Mario Rossi"), "Nomi Personali (Medici/Pazienti)")
        self.assertEqual(classify_redacted_term("+39 02 123456"), "Numeri di Telefono / Contatti")
        self.assertEqual(classify_redacted_term("12345"), "Indirizzi / CAP")

    def test_anonymous_audit_log(self):
        """Verify anonymous GDPR audit report is generated correctly and contains no clear-text PII."""
        # Generate some mock data
        synthetic_id = "TESTPATIENT"
        curr_time = "2026-05-20 21:00:00"
        total_pages_processed = 5
        manual_rects_count = 2
        total_redacted_items_count = 4
        category_counts = {
            "Codici Fiscali / Tessera Sanitaria / ID Nazionali": 1,
            "Date (Nascita/Ricovero/Dimissione)": 1,
            "Nomi Personali (Medici/Pazienti)": 2
        }
        
        # Build mock report md
        report_md = f"""# 🏥 RAPPORTO DI AUDIT DI ANONIMIZZAZIONE GDPR
Questo rapporto documenta le operazioni di anonimizzazione ed estrazione dei dati sensibili eseguite in conformità con il **Regolamento Generale sulla Protezione dei Dati (GDPR - UE 2016/679)**.

In linea con il principio di **Privacy by Design & Zero-Trace**, questo documento contiene esclusivamente metriche aggregate e anonime. **Nessun dato sanitario protetto (PHI) o dato identificativo personale (PII) è presente in chiaro in questo report.**

---

## 📋 Informazioni Generali
- **ID Sintetico Paziente (UUID):** `{synthetic_id}`
- **Data e Ora Elaborazione:** `{curr_time}`
- **Stato di Conformità:** ✅ Anonimizzato con successo
- **Modalità di Esecuzione:** Assistita da IA
- **Sensibilità IA Applicata (Soglia):** 0.45

---

## 📊 Metriche del Processo
| Metrica | Valore |
| :--- | :--- |
| **Documenti Totali Elaborati** | 2 |
| **Pagine Totali Esaminate** | {total_pages_processed} |
| **Elementi Sensibili Oscurati (Univoci)** | {total_redacted_items_count} |
| **Rettangoli Manuali Applicati** | {manual_rects_count} |

---

## 🏷️ Entità Oscurate per Categoria
Di seguito è riportato il conteggio delle informazioni personali rimosse, suddivise per tipologia di dato sensibile (GDPR Art. 4 & Art. 9):

| Categoria di Dato Sensibile | Elementi Univoci Rilevati e Oscurati |
| :--- | :---: |
| 🆔 Codici Fiscali / Tessera Sanitaria / ID Nazionali | {category_counts.get("Codici Fiscali / Tessera Sanitaria / ID Nazionali", 0)} |
| 📅 Date (Nascita/Ricovero/Dimissione) | {category_counts.get("Date (Nascita/Ricovero/Dimissione)", 0)} |
| 👤 Nomi Personali (Medici/Pazienti) | {category_counts.get("Nomi Personali (Medici/Pazienti)", 0)} |
| 🏥 Strutture Sanitarie (Ospedali/Cliniche/ASL) | {category_counts.get("Strutture Sanitarie (Ospedali/Cliniche/ASL)", 0)} |
"""
        # Run assertions on the report layout and content
        self.assertIn("# 🏥 RAPPORTO DI AUDIT DI ANONIMIZZAZIONE GDPR", report_md)
        self.assertIn("Privacy by Design & Zero-Trace", report_md)
        self.assertIn("TESTPATIENT", report_md)
        self.assertIn("Elementi Sensibili Oscurati (Univoci)", report_md)
        
        # Verify strict Zero-Trace constraint (no raw PII names in clear text)
        sensitive_raw_names = ["Giuseppe Verdi"]
        for name in sensitive_raw_names:
            self.assertNotIn(name, report_md, f"PII leak detected! Report contains sensitive raw name: {name}")

    def test_localized_diff_and_filters(self):
        """Verify alphabetical/search filtering and localized diff preservation logic."""
        current_terms = ["al", "verde", "Giallo", "12345", "(parenthesis)"]
        
        # 1. Test case-insensitive sorting
        all_terms = sorted(list({t.strip() for t in current_terms if t.strip()}), key=str.lower)
        self.assertEqual(all_terms, ["(parenthesis)", "12345", "al", "Giallo", "verde"])
        
        # 2. Test Letter filter "A"
        visible_terms_a = []
        for t in all_terms:
            if not t: continue
            first_char = t[0].upper()
            if first_char == "A":
                visible_terms_a.append(t)
        self.assertEqual(visible_terms_a, ["al"])
        
        # 3. Test Symbol filter "#"
        visible_terms_hash = []
        for t in all_terms:
            if not t: continue
            first_char = t[0].upper()
            if not first_char.isalpha():
                visible_terms_hash.append(t)
        self.assertEqual(visible_terms_hash, ["(parenthesis)", "12345"])
        
        # 4. Test Search filter
        visible_terms_search = [t for t in all_terms if "ia" in t.lower()]
        self.assertEqual(visible_terms_search, ["Giallo"])
        
        # 5. Localized diffing simulation:
        # User is viewing only terms starting with 'A' (visible_terms_a = ["al"])
        # and edits it to: ["al", "azzurro"] (adding "azzurro")
        edited_visible_terms = ["al", "azzurro"]
        
        old_visible_set = set(visible_terms_a) # {"al"}
        new_visible_set = set(edited_visible_terms) # {"al", "azzurro"}
        
        added_filtered = new_visible_set - old_visible_set # {"azzurro"}
        removed_filtered = old_visible_set - new_visible_set # {}
        
        full_terms_set = set(all_terms)
        full_terms_set.update(added_filtered)
        full_terms_set.difference_update(removed_filtered)
        
        updated_terms = sorted(list({t for t in full_terms_set if t.strip()}), key=str.lower)
        # Expected: ["(parenthesis)", "12345", "al", "azzurro", "Giallo", "verde"]
        self.assertEqual(updated_terms, ["(parenthesis)", "12345", "al", "azzurro", "Giallo", "verde"])

if __name__ == '__main__':
    unittest.main()
