
import unittest
import sys
import os
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from organization_utils import (
    generate_patient_uuid,
    get_patient_folder_name,
    get_category_folder_name,
    get_output_filename
)

class TestOrganizationUtils(unittest.TestCase):
    
    def test_uuid_generation(self):
        """Verify UUIDs are 8-char uppercase hex strings."""
        u1 = generate_patient_uuid()
        u2 = generate_patient_uuid()
        
        self.assertEqual(len(u1), 8)
        self.assertTrue(u1.isupper())
        self.assertNotEqual(u1, u2) # Basic uniqueness check
        
        # Verify it's valid hex
        int(u1, 16) 

    def test_folder_naming(self):
        """Verify patient and category folder names."""
        self.assertEqual(get_patient_folder_name("ABC123"), "Paziente_ABC123")
        self.assertEqual(get_category_folder_name("CARTELLA_CLINICA", "XYZ"), "CARTELLA_CLINICA_XYZ")
        # Test cleaning of special chars in category
        self.assertEqual(get_category_folder_name("Cartella - Clinica!", "XYZ"), "CARTELLA_CLINICA_XYZ")

    def test_file_naming(self):
        """Verify output filename construction."""
        # Standard case
        name = get_output_filename("CARTELLA_CLINICA", "ID123", "verbale.pdf")
        self.assertEqual(name, "CARTELLA_CLINICA_ID123_verbale.pdf")
        
        # Indexed case (multiple files in same cat)
        name_idx = get_output_filename("DATI_STRUTTURATI", "ID123", "analisi.pdf", file_index=2)
        self.assertEqual(name_idx, "DATI_STRUTTURATI_ID123_2_analisi.pdf")
        
        # Directory path check in original filename
        name_path = get_output_filename("GENERIC", "ID123", "C:/User/test.pdf")
        self.assertEqual(name_path, "GENERIC_ID123_test.pdf")

if __name__ == '__main__':
    unittest.main()
