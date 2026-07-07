import os
from pathlib import Path
from config import MODELS_DIR, SETTINGS
from utils import logger

# Configure HuggingFace cache to be in the portable folder
hf_cache_dir = MODELS_DIR / "hf_cache"
hf_cache_dir.mkdir(parents=True, exist_ok=True)
os.environ["HF_HOME"] = str(hf_cache_dir)

def check_gliner_available():
    try:
        import importlib.util
        torch_spec = importlib.util.find_spec("torch")
        gliner_spec = importlib.util.find_spec("gliner")
        return torch_spec is not None and gliner_spec is not None
    except Exception:
        return False

class LLMEngine:
    def __init__(self):
        self.model = None
        self.manual_mode = SETTINGS.get("manual_mode", False)
        
        self.gliner_available = check_gliner_available()
        if not self.gliner_available:
            self.manual_mode = True

        self.labels = [
            "Nome e Cognome", "Ospedale", "Città", "Provincia", "Regione",
            "Indirizzo", "CAP", "Codice Fiscale", "Telefono", "Email", "Fax",
            "Medico", "Paziente", "Data di nascita", "Luogo di nascita", "Data di ricovero", "Data di dimissione",
            "Tessera Sanitaria", "Cartella Clinica", "Codice Paziente",
            "Codice Esenzione", "Polizza Assicurativa", "Dispositivo Medico", 
            "Targa Veicolo", "Numero di Conto", "URL", "Indirizzo IP", "Numero Patente"
        ]

    def initialize_engine(self):
        self.manual_mode = SETTINGS.get("manual_mode", False)
        if not check_gliner_available():
            self.manual_mode = True

        if self.manual_mode:
            logger.info("Manual Mode enabled. LLM Engine disabled.")
            return

        self.initialize_gliner_engine()

    def initialize_gliner_engine(self):
        try:
            logger.info("Loading GLiNER ONNX model (onnx-community/gliner_multi_pii-v1)...")
            import torch
            from gliner import GLiNER
            
            # Apply PyTorch classes path hotfix locally
            try:
                torch.classes.__path__ = []
            except:
                pass
                
            device = "cuda" if SETTINGS.get("use_gpu", True) and torch.cuda.is_available() else "cpu"
            logger.info(f"Using GLiNER device: {device} (with ONNX Runtime)")
            
            self.model = GLiNER.from_pretrained(
                "onnx-community/gliner_multi_pii-v1", 
                local_files_only=False,
                load_onnx_model=True,
                onnx_model_file="onnx/model.onnx"
            )
            self.model.to(device)
            logger.info("GLiNER ONNX model loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load GLiNER model: {e}")
            self.model = None

    def reset_engine(self):
        self.model = None
        try:
            import torch
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except:
            pass
        logger.info("LLM Engine reset. Models unloaded from memory.")

    def is_ready(self):
        return self.model is not None

    def extract_pii(self, text, category="GENERIC", custom_threshold=None):
        if not text.strip():
            return []
            
        if not self.is_ready():
            self.initialize_engine()
            
        if not self.is_ready():
            logger.warning("LLM Engine model is not initialized or failed to load.")
            return []
            
        try:
            # Labels for GLiNER
            active_labels = self.labels.copy()
            if category == "DATI_STRUTTURATI":
                labels_to_remove = ["Data"]
                active_labels = [l for l in active_labels if l not in labels_to_remove]

            threshold = custom_threshold if custom_threshold is not None else SETTINGS.get("ai_threshold", 0.45)
            entities = self.model.predict_entities(text, active_labels, threshold=threshold)
            
            sensitive_terms = set()
            # UI labels to strip from result if AI includes them
            label_prefixes = [
                "Paziente:", "Sig.", "Dott.", "Dr.", "Dr.ssa", "Prof.", "Medico:", 
                "Nome:", "Cognome:", "Medico curante:", "Curante:", "Reparto:", 
                "Hospital:", "Ospedale:", "Osp:", "Ref:"
            ]
            
            for entity in entities:
                raw_text = entity["text"].strip()
                # Clean up if AI captured the label with the name
                for prefix in label_prefixes:
                    if raw_text.lower().startswith(prefix.lower()):
                        raw_text = raw_text[len(prefix):].strip()
                
                if len(raw_text) > 1 and '\n' not in raw_text:
                    sensitive_terms.add(raw_text)
            
            return list(sensitive_terms)
            
        except Exception as e:
            logger.error(f"Inference error with GLiNER: {e}")
            return []
