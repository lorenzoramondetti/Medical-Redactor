
import os
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from pdf_processor import PDFProcessor
from redaction_logic import RedactionMemory, TextAnalyzer
from llm_engine import LLMEngine

def analyze_test_folder(folder_path):
    folder = Path(folder_path)
    if not folder.exists():
        print(f"Error: Folder {folder} does not exist.")
        return

    # Use ephemeral memory for testing
    memory = RedactionMemory(ephemeral=True)
    print(f"Memory Diagnostics: Blacklist items: {len(memory.blacklist_lower)}")
    print(f"Sample Blacklist: {list(memory.blacklist_lower)[:10]}")
    if "ospedale civile" in memory.blacklist_lower:
        print(f"  - 'ospedale civile' is in blacklist. Repr: {repr('ospedale civile')}")
    else:
        # Print all items starting with 'o'
        print("  - 'ospedale civile' NOT found. Items starting with 'o':")
        for item in memory.blacklist_lower:
            if item.startswith('o'):
                print(f"    * {repr(item)}")
    
    # Try to load LLM engine
    llm = LLMEngine()
    analyzer = TextAnalyzer(memory, llm_engine=llm if llm.is_ready() else None)
    
    print("\n" + "="*80)
    print(f"MEDICAL REDACTOR - TEST DATA ANALYSIS REPORT")
    print(f"AI Status: {'READY' if llm.is_ready() else 'DISABLED'}")
    print("="*80 + "\n")

    for pdf_file in folder.glob("*.pdf"):
        print(f"[{pdf_file.name}]")
        try:
            with open(pdf_file, "rb") as f:
                pdf_bytes = f.read()
            
            processor = PDFProcessor(pdf_bytes)
            num_pages = processor.get_page_count()
            
            all_found_terms = set()
            full_text = ""
            
            for i in range(num_pages):
                text = processor.extract_text(i)
                full_text += text + "\n"
                terms = analyzer.analyze_text(text)
                all_found_terms.update(terms)
            
            print(f"  - Pages: {num_pages}")
            print(f"  - Clinical Text Sample: \"{full_text[:150].replace('\n', ' ')}...\"")
            
            if all_found_terms:
                print(f"  - Identified PII ({len(all_found_terms)}):")
                for term in sorted(list(all_found_terms)):
                    print(f"    * {repr(term)}")
            else:
                print("  - No PII identified.")
            
            processor.close()
        except Exception as e:
            print(f"  - Error processing file: {e}")
        
        print("-" * 40)

if __name__ == "__main__":
    analyze_test_folder("test_data")
