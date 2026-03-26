import os
import json
from pathlib import Path
from config import MODELS_DIR, SETTINGS
from utils import logger

# Configure HuggingFace cache to be in the portable folder
hf_cache_dir = MODELS_DIR / "hf_cache"
hf_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(hf_cache_dir)

try:
    from gliner import GLiNER
    import torch
    GLINER_AVAILABLE = True
except ImportError:
    GLINER_AVAILABLE = False
    logger.warning("gliner module not found. AI features will be disabled.")

class LLMEngine:
    def __init__(self):
        self.model = None
        self.manual_mode = SETTINGS["manual_mode"]
        
        if not GLINER_AVAILABLE:
            self.manual_mode = True

        # Define labels to extract
        self.labels = [
            "Nome e Cognome", "Ospedale", "Città", "Provincia", "Regione",
            "Indirizzo", "CAP", "Codice Fiscale", "Telefono", "Email", "Fax",
            "Medico", "Paziente", "Data di nascita", "Luogo di nascita", "Data di ricovero", "Data di dimissione",
            "Tessera Sanitaria", "Cartella Clinica", "Codice Paziente",
            "Codice Esenzione", "Polizza Assicurativa", "Dispositivo Medico", 
            "Targa Veicolo", "Numero di Conto", "URL", "Indirizzo IP", "Numero Patente"
        ]

        self.initialize_engine()

    def initialize_engine(self):
        if self.manual_mode:
            logger.info("Manual Mode enabled. LLM Engine disabled.")
            return

        try:
            logger.info("Loading GLiNER model (urchade/gliner_multi_pii-v1)...")
            # Load model. It will download the very first time (requires internet once), 
            # then cache it locally in models/hf_cache for offline portable use.
            # Force CPU usage if GPU setting is off, or use GPU if available.
            device = "cuda" if SETTINGS["use_gpu"] and torch.cuda.is_available() else "cpu"
            logger.info(f"Using device: {device}")
            
            self.model = GLiNER.from_pretrained("urchade/gliner_multi_pii-v1", local_files_only=False).to(device)
            logger.info("GLiNER model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load GLiNER model: {e}")
            self.model = None

    def is_ready(self):
        return self.model is not None

    def extract_pii(self, text, category="GENERIC"):
        if not self.is_ready():
            return []
        
        if not text.strip():
            return []
            
        try:
            # Dynamically adjust labels based on category
            active_labels = self.labels.copy()
            if category == "DATI_STRUTTURATI":
                # For Lab Results, we need to preserve dates/times for scientific validity.
                # Remove generic date labels so the AI doesn't hunt them.
                labels_to_remove = ["Data di ricovero", "Data di dimissione", "Data"]
                active_labels = [l for l in active_labels if l not in labels_to_remove]
                # Note: "Data di nascita" remains in the list!

            # Predict entities. We lower the threshold slightly to catch more potential PII, 
            # as false positives can be manually deleted by the user.
            entities = self.model.predict_entities(text, active_labels, threshold=0.45)
            
            # Extract just the text from the found entities, filtering duplicates
            sensitive_terms = list(set([entity["text"].strip() for entity in entities]))
            
            # Clean up potential multi-line artifacts
            clean_terms = [t for t in sensitive_terms if t and len(t) > 2 and '\n' not in t]
            
            return clean_terms
            
        except Exception as e:
            logger.error(f"Inference error with GLiNER: {e}")
            return []

