
import unittest
import sys
import os
import time
from io import BytesIO
import fitz

# Add src to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from pdf_processor import PDFProcessor

class TestPerformance(unittest.TestCase):
    
    def setUp(self):
        # Create a dummy PDF bytes object for reuse
        doc = fitz.open()
        p = doc.new_page()
        p.insert_text((10, 10), "Test Performance Data")
        self.dummy_pdf = doc.tobytes()
        doc.close()

    def test_bulk_processing_speed(self):
        """Simulate processing 30 files in a row and check for major regressions."""
        start_time = time.time()
        num_files = 30
        
        for i in range(num_files):
            processor = PDFProcessor(self.dummy_pdf)
            # Simulate a redaction
            redacted = processor.save_redacted_pdf({0: ["Performance"]}, {})
            processor.close()
            self.assertTrue(len(redacted) > 0)
            
        duration = time.time() - start_time
        avg_time = duration / num_files
        
        print(f"\n[PERF] Total time for {num_files} files: {duration:.2f}s (Avg: {avg_time:.4f}s/file)")
        
        # Performance threshold: 30 small files should easily process in < 5 seconds 
        # on most modern hospital machines (even with overhead)
        self.assertLess(duration, 10.0, f"Performance regression! Bulk processing took {duration:.2f}s")

    def test_memory_cleanup(self):
        """Verify that PDFProcessor doesn't leak memory and closes gracefully."""
        # Note: True memory leak testing requires external tools, 
        # but we can verify that the doc is closed.
        processor = PDFProcessor(self.dummy_pdf)
        self.assertFalse(processor.doc.is_closed)
        processor.close()
        self.assertTrue(processor.doc.is_closed)

if __name__ == '__main__':
    unittest.main()
