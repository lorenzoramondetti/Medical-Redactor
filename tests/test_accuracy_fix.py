
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from redaction_logic import RedactionMemory, TextAnalyzer

def test_accuracy():
    memory = RedactionMemory(ephemeral=True)
    analyzer = TextAnalyzer(memory)
    
    # Test 1: Whitelist "CORSO" (Address part)
    memory.add_to_whitelist(["CORSO"])
    
    text = "PRONTO SOCCORSO - CORSO VITTORIO EMANUELE"
    found = analyzer.analyze_text(text)
    
    print(f"Text: {text}")
    print(f"Found: {found}")
    
    # Should find "CORSO" (from Vittorio Emanuele) but NOT inside "SOCCORSO"
    # Actually, analyze_text returns unique strings. 
    # If "CORSO" is found once, it's in the list.
    # But wait, we want to make sure it DOES NOT identify "CORSO" as part of SOCCORSO.
    # If it highlights "SOCCORSO" or "CORSO" inside it, that's the problem.
    
    # Test 2: M.C. (Marcatori Cardiaci)
    text_mc = "Effettuato prelievo per M.C. (Marcatori Cardiaci)"
    found_mc = analyzer.analyze_text(text_mc)
    print(f"Text MC: {text_mc}")
    print(f"Found MC: {found_mc}")
    
    # Test 3: Rossi (Real person) vs M.C.
    text_mix = "Paziente A.G. visto da M. ROSSI per M.C."
    found_mix = analyzer.analyze_text(text_mix)
    print(f"Text Mix: {text_mix}")
    print(f"Found Mix: {found_mix}")

    # Test 4: Partial Date (Nato il: 01/01/1)
    text_partial = "Nato il: 01/01/1 al Presidio Ospedaliero"
    found_partial = analyzer.analyze_text(text_partial)
    print(f"Text Partial: {text_partial}")
    print(f"Found Partial: {found_partial}")
    
    assert "01/01/1" in found_partial, "Error: Partial date 01/01/1 not found!"
    
    # Test 5: Noise protection (e.g. 1/1)
    text_noise = "Valore 1/1 rilevato"
    found_noise = analyzer.analyze_text(text_noise)
    print(f"Text Noise: {text_noise}")
    print(f"Found Noise: {found_noise}")
    assert "1/1" not in found_noise, "Error: Noise 1/1 should be ignored!"

if __name__ == "__main__":
    test_accuracy()
    print("\n[OK] Verification Complete!")
