import sys
from pathlib import Path
import time

sys.path.append(str(Path(__file__).parent.parent / "src"))
from llm_engine import LLMEngine

def test_hallucination():
    engine = LLMEngine()
    engine.initialize_gliner_engine()

    text_original = """
    Il paziente Mario Rossi nato a Roma il 24/12/1980.
    È stato ricoverato presso l'Ospedale San Raffaele. 
    Medico curante: Dott. Giuseppe Verdi. 
    Codice Fiscale: RSSMRA80T24H501J.
    La diagnosi riporta un quadro clinico stabile, il paziente respira autonomamente e non presenta febbre.
    """

    # Simuliamo che la Regex abbia rimosso le parole esatte sostituendole con spazi o [REDACTED]
    text_regexed_spaces = """
    Il paziente             nato a      il           .
    È stato ricoverato presso l'                     . 
    Medico curante:                      . 
    Codice Fiscale:                 .
    La diagnosi riporta un quadro clinico stabile, il paziente respira autonomamente e non presenta febbre.
    """

    print("--- TEST TESTO ORIGINALE ---")
    res_orig = engine.model.predict_entities(text_original, engine.labels, threshold=0.45)
    print("Trovato:", [r["text"] for r in res_orig])
    
    print("\n--- TEST TESTO SVUOTATO DA REGEX (Spazi bianchi) ---")
    res_spaces = engine.model.predict_entities(text_regexed_spaces, engine.labels, threshold=0.45)
    print("Trovato:", [r["text"] for r in res_spaces])

if __name__ == "__main__":
    test_hallucination()
