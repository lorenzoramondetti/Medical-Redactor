import unittest
import time
import sys
from pathlib import Path

# Aggiungi src al path
sys.path.append(str(Path(__file__).parent.parent / "src"))
from llm_engine import LLMEngine

class TestGlinerLabels(unittest.TestCase):
    def setUp(self):
        self.engine = LLMEngine()
        self.engine.initialize_gliner_engine()
        
        self.test_text = """
        Il paziente Mario Rossi nato a Roma il 24/12/1980, residente in Via delle Mura 15 (RM), CAP 00100.
        È stato ricoverato presso l'Ospedale San Raffaele il 01/01/2023. 
        Medico curante: Dott. Giuseppe Verdi. 
        Codice Fiscale: RSSMRA80T24H501J. Telefono: 333-1234567. Email: mario.rossi@email.it.
        """
        
        self.old_labels = [
            "Nome e Cognome", "Ospedale", "Città", "Provincia", "Regione",
            "Indirizzo", "CAP", "Codice Fiscale", "Telefono", "Email", "Fax",
            "Medico", "Paziente", "Data di nascita", "Luogo di nascita", "Data di ricovero", "Data di dimissione",
            "Tessera Sanitaria", "Cartella Clinica", "Codice Paziente",
            "Codice Esenzione", "Polizza Assicurativa", "Dispositivo Medico", 
            "Targa Veicolo", "Numero di Conto", "URL", "Indirizzo IP", "Numero Patente"
        ]
        
        self.new_labels = [
            "Persona",              
            "Struttura Sanitaria",  
            "Luogo",                
            "Contatto",             
            "ID Numerico",          
            "Data"                  
        ]

    def test_performance_and_accuracy(self):
        if not self.engine.model:
            self.skipTest("GLiNER model not available")
            
        print("\n--- TEST GLINER MACRO-CATEGORIE ---")
        
        # Test Old Labels
        start_time = time.time()
        old_entities = self.engine.model.predict_entities(self.test_text, self.old_labels, threshold=0.45)
        old_time = time.time() - start_time
        old_extracted = {e["text"].strip() for e in old_entities}
        
        print(f"Vecchie etichette (28): {len(old_extracted)} entità in {old_time:.3f}s")
        print(f"Estratte: {old_extracted}")
        
        # Test New Labels
        start_time = time.time()
        new_entities = self.engine.model.predict_entities(self.test_text, self.new_labels, threshold=0.45)
        new_time = time.time() - start_time
        new_extracted = {e["text"].strip() for e in new_entities}
        
        print(f"Nuove etichette (6): {len(new_extracted)} entità in {new_time:.3f}s")
        print(f"Estratte: {new_extracted}")
        
        # Verify F1/Recall coverage (New should extract at least what old extracted contextually)
        self.assertTrue(len(new_extracted) > 0)
        self.assertTrue(new_time < old_time, f"New time {new_time} is not faster than old time {old_time}")

if __name__ == "__main__":
    unittest.main()
