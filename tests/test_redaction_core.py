
import unittest
import sys
import os

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from redaction_logic import RedactionMemory, TextAnalyzer

class TestRedactionCore(unittest.TestCase):
    
    def setUp(self):
        # Always use ephemeral mode for testing to avoid disk pollution
        self.memory = RedactionMemory(ephemeral=True)
        self.analyzer = TextAnalyzer(self.memory)

    def test_cf_extraction(self):
        """Verify Italian Fiscal Code (CF) extraction."""
        text = "Il paziente RSSMRA80A01H501X è stato dimesso. Un altro CF: c.f. BRNMAR50L12F205Z"
        found = self.analyzer.extract_regex_patterns(text)
        
        self.assertIn("RSSMRA80A01H501X", found)
        self.assertIn("BRNMAR50L12F205Z", found)

    def test_doctor_extraction(self):
        """Verify extraction of Doctor names via prefixes."""
        text = "Referto firmato dal Dott. Mario Rossi e dalla Dott.ssa Bianchi. Visitato da prof. Verdi."
        found = self.analyzer.extract_regex_patterns(text)
        
        self.assertIn("Dott. Mario Rossi", found)
        self.assertIn("Dott.ssa Bianchi", found)
        self.assertIn("prof. Verdi", found)

    def test_struct_data_date_rule(self):
        """Verify lab data mode only captures DOB, not clinical dates."""
        text = "Paziente nato il 15/05/1970. Prelievo eseguito il 20/03/2024 alle ore 08:00."
        
        # In generic mode, both dates should be caught
        generic_found = self.analyzer.extract_regex_patterns(text, category="GENERIC")
        self.assertIn("15/05/1970", generic_found)
        self.assertIn("20/03/2024", generic_found)
        
        # In structured data mode, ONLY the birth date should be caught
        struct_found = self.analyzer.extract_regex_patterns(text, category="DATI_STRUTTURATI")
        self.assertIn("15/05/1970", struct_found)
        self.assertNotIn("20/03/2024", struct_found)

    def test_memory_filtering(self):
        """Verify that blacklisted terms are filtered out."""
        self.memory.add_to_blacklist(["Rossi"])
        
        terms = ["Mario", "Rossi", "Bianchi"]
        filtered = self.memory.filter_terms(terms)
        
        self.assertIn("Mario", filtered)
        self.assertIn("Bianchi", filtered)
        self.assertNotIn("Rossi", filtered)

if __name__ == '__main__':
    unittest.main()
