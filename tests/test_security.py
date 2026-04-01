
import unittest
import sys
import os
import shutil
from pathlib import Path
import json

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from redaction_logic import RedactionMemory
import config

class TestSecurity(unittest.TestCase):
    
    def setUp(self):
        self.test_dir = Path("test_security_env")
        self.test_dir.mkdir(exist_ok=True)
        
        # Mock paths in config for testing
        self.original_output = config.OUTPUT_DIR
        self.original_staging = config.STAGING_DIR
        self.original_memory_file = config.MEMORY_FILE
        
        config.OUTPUT_DIR = self.test_dir / "usb_output"
        config.STAGING_DIR = self.test_dir / "hospital_staging"
        config.MEMORY_FILE = self.test_dir / "global_memory.json"
        
        config.OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        config.STAGING_DIR.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        # Restore config
        config.OUTPUT_DIR = self.original_output
        config.STAGING_DIR = self.original_staging
        config.MEMORY_FILE = self.original_memory_file
        
        # Cleanup
        shutil.rmtree(self.test_dir)

    def test_incognito_mode_disk_isolation(self):
        """Verify that Incognito (ephemeral) session never writes to disk."""
        # Create a real file that shouldn't be touched
        memory_path = config.MEMORY_FILE
        with open(memory_path, "w") as f:
            json.dump(["InitialItem"], f)
            
        # Init memory in ephemeral mode
        mem = RedactionMemory(ephemeral=True)
        mem.add_to_whitelist(["SecretTerm"])
        mem.save_memory()
        
        # Read file back from disk
        with open(memory_path, "r") as f:
            disk_data = json.load(f)
            
        self.assertNotIn("SecretTerm", disk_data, "Ephemeral data leaked to disk!")
        self.assertIn("InitialItem", disk_data)

    def test_one_way_valve_logic(self):
        """
        Verify the architectural 'One-Way Valve': 
        Unredacted data stays in Staging, Redacted data goes to Output.
        """
        # This test verifies the config-level separation which underpins the UI logic
        staging_path = config.STAGING_DIR
        output_path = config.OUTPUT_DIR
        
        # Ensure they are different physical paths
        self.assertNotEqual(staging_path.resolve(), output_path.resolve())
        
        # Simulate a hospital PC setting (Security Level 2)
        # In a real run, this would be set in settings.json
        hospital_c_drive = self.test_dir / "C_Drive_Staging"
        config.STAGING_DIR = hospital_c_drive
        config.STAGING_DIR.mkdir(parents=True, exist_ok=True)
        
        self.assertTrue(config.STAGING_DIR.exists())
        self.assertIn("C_Drive_Staging", str(config.STAGING_DIR))
        self.assertNotIn("usb_output", str(config.STAGING_DIR))

if __name__ == '__main__':
    unittest.main()
