
import unittest
import sys
import os
import fitz
from io import BytesIO

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pdf_processor import PDFProcessor

class TestIntegrity(unittest.TestCase):
    
    def test_text_incineration(self):
        """Verify that redacted text is NOT retrievable from the saved PDF."""
        # 1. Create a temporary PDF with sensitive data
        doc = fitz.open()
        page = doc.new_page()
        text = "PAZIENTE: MARIO ROSSI, NATO IL 15/05/1980"
        page.insert_text((50, 50), text)
        pdf_bytes = doc.tobytes()
        doc.close()
        
        # 2. Process with PDFProcessor
        processor = PDFProcessor(pdf_bytes)
        
        # Define redactions
        redaction_map = {0: ["MARIO ROSSI", "15/05/1980"]}
        manual_rects = {}
        
        # Save redacted PDF
        redacted_bytes = processor.save_redacted_pdf(redaction_map, manual_rects)
        processor.close()
        
        # 3. Verify incineration
        doc_check = fitz.open(stream=redacted_bytes, filetype="pdf")
        page_check = doc_check[0]
        
        # Search for the original text
        self.assertEqual(len(page_check.search_for("MARIO ROSSI")), 0, "Redacted text still searchable!")
        self.assertEqual(len(page_check.search_for("15/05/1980")), 0, "Redacted date still searchable!")
        
        # Extract full text and check substrings
        full_text = page_check.get_text()
        self.assertNotIn("MARIO ROSSI", full_text)
        self.assertNotIn("ROSSI", full_text)
        self.assertNotIn("15/05/1980", full_text)
        
        # Verify the rest of the text is still there
        self.assertIn("PAZIENTE:", full_text)
        
        doc_check.close()

if __name__ == '__main__':
    unittest.main()
