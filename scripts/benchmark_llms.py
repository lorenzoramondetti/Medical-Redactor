import json
import os
import time
from typing import List, Dict, Set
from pathlib import Path

# --- DIPENDENZE OPZIONALI ---
# pip install litellm presidio-analyzer
try:
    import litellm
except ImportError:
    litellm = None

try:
    from presidio_analyzer import AnalyzerEngine
except ImportError:
    AnalyzerEngine = None

# Assumiamo che il progetto corrente sia nel PYTHONPATH per importare i moduli interni
import sys
sys.path.append(str(Path(__file__).parent.parent / "src"))
try:
    from redaction_logic import TextAnalyzer, RedactionMemory
    from llm_engine import LLMEngine
    MEDICAL_REDACTOR_AVAILABLE = True
except ImportError:
    MEDICAL_REDACTOR_AVAILABLE = False


def calculate_metrics(ground_truth: Set[str], predictions: Set[str]) -> Dict[str, float]:
    """Calcola Precision, Recall e F1-score esatti per Named Entity Recognition."""
    tp = len(ground_truth.intersection(predictions))
    fp = len(predictions - ground_truth)
    fn = len(ground_truth - predictions)

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * (precision * recall) / (precision + recall) if (precision + recall) > 0 else 0.0

    return {"precision": precision, "recall": recall, "f1": f1, "tp": tp, "fp": fp, "fn": fn}


def run_benchmark(dataset_dir="dataset"):
    print("🚀 Inizializzazione Benchmark Anonimizzazione Clinica Italiana (GDPR-ECDC)")
    
    dataset_path = Path(dataset_dir)
    if not dataset_path.exists():
        print(f"Dataset dir '{dataset_dir}' non trovata. Genera prima i dati sintetici.")
        return

    manifest_file = dataset_path / "dataset_manifest.json"
    if not manifest_file.exists():
         print("Manifesto del dataset non trovato.")
         return
         
    with open(manifest_file, "r", encoding="utf-8") as f:
        records = json.load(f)
        
    print(f"Caricati {len(records)} documenti sintetici con Ground Truth.")

    # 1. Configura i modelli da testare
    models_to_test = {
        "Medical Redactor (GLiNER + Regex)": run_medical_redactor,
        "Microsoft Presidio": run_presidio,
        "GPT-4o (OpenAI)": lambda text: run_litellm("gpt-4o", text),
        "Claude 3.5 Sonnet (Anthropic)": lambda text: run_litellm("claude-3-5-sonnet-20240620", text),
        "Gemini 1.5 Pro (Google)": lambda text: run_litellm("gemini/gemini-1.5-pro-latest", text),
        # Aggiungi qui le altre decine di modelli open-source / API richiesti...
    }

    results = {}

    for model_name, func in models_to_test.items():
        print(f"\n--- Valutazione Modello: {model_name} ---")
        model_metrics = {"precision": [], "recall": [], "f1": [], "latency": []}
        
        for record in records:
            text = record["text"]
            ground_truth = {ent["value"].strip() for ent in record["ground_truth_entities"]}
            
            start_time = time.time()
            try:
                 predictions = func(text)
            except Exception as e:
                 print(f"Errore {model_name} su {record['id']}: {e}")
                 predictions = set()
                 
            latency = time.time() - start_time
            
            # Formattiamo/PuliAmo le predizioni per coerenza
            predictions = {p.strip() for p in predictions if p.strip()}
            
            metrics = calculate_metrics(ground_truth, predictions)
            
            model_metrics["precision"].append(metrics["precision"])
            model_metrics["recall"].append(metrics["recall"])
            model_metrics["f1"].append(metrics["f1"])
            model_metrics["latency"].append(latency)
            
        # Medie
        avg_p = sum(model_metrics["precision"]) / len(records)
        avg_r = sum(model_metrics["recall"]) / len(records)
        avg_f1 = sum(model_metrics["f1"]) / len(records)
        avg_lat = sum(model_metrics["latency"]) / len(records)
        
        results[model_name] = {"Precision": avg_p, "Recall": avg_r, "F1-Score": avg_f1, "Latency (s/doc)": avg_lat}
        print(f"Risultato: F1={avg_f1:.4f} | Recall={avg_r:.4f} | Latency={avg_lat:.2f}s")

    # Salva risultati
    with open("benchmark_results.json", "w") as f:
         json.dump(results, f, indent=4)
    print("\n✅ Benchmark completato! Risultati salvati in benchmark_results.json")


# --- RUNNERS PER I SINGOLI MODELLI ---

def run_medical_redactor(text: str) -> Set[str]:
    """Testa il nostro Medical Redactor (GLiNER onnx + espressioni regolari)"""
    if not MEDICAL_REDACTOR_AVAILABLE: return set()
    
    # Singleton o lazily loaded per le performance del test
    if not hasattr(run_medical_redactor, "engine"):
        memory = RedactionMemory(ephemeral=True)
        llm = LLMEngine()
        llm.initialize_engine()
        run_medical_redactor.engine = TextAnalyzer(memory, llm)
        
    found_list = run_medical_redactor.engine.analyze_text(text, category="GENERIC", custom_threshold=0.45)
    return set(found_list)


def run_presidio(text: str) -> Set[str]:
    """Testa Microsoft Presidio (Regex + Spacy backend)"""
    if not AnalyzerEngine: return set()
    
    if not hasattr(run_presidio, "analyzer"):
        run_presidio.analyzer = AnalyzerEngine(supported_languages=["it", "en"])
        
    results = run_presidio.analyzer.analyze(text=text, language='it')
    
    # Estrai le stringhe di testo in base agli offset rilevati
    extracted_strings = set()
    for res in results:
        extracted_strings.add(text[res.start:res.end])
        
    return extracted_strings


def run_litellm(model_id: str, text: str) -> Set[str]:
    """Esegue un qualsiasi LLM tramite l'astrazione di LiteLLM. Restituisce le entità rilevate."""
    if not litellm: return set()
    
    prompt = f"""Sei un analista dati GDPR per un ospedale italiano (Progetto ECDC).
Il tuo compito è estrarre ESATTAMENTE e in modo preciso tutte le entità sensibili (Nomi, Date, Codici Fiscali, Luoghi) dal testo clinico fornito.
Rispondi SOLO con un array JSON di stringhe, ad esempio: ["Mario Rossi", "12/03/2023", "Ospedale Niguarda"]. Niente altro testo.

TESTO:
{text}
"""
    try:
        response = litellm.completion(
            model=model_id,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0 # Temperatura a 0 per task estrattivi deterministici
        )
        content = response.choices[0].message.content
        
        # Pulizia base per estrarre l'array JSON (rimuove i markdown block ```json se presenti)
        import re
        json_match = re.search(r'\[.*\]', content, re.DOTALL)
        if json_match:
            return set(json.loads(json_match.group()))
        else:
             # Fallback manual extraction se non formatta come JSON
             return set([line.strip('- *') for line in content.split('\n') if line.strip()])
    except Exception as e:
         print(f"API Error ({model_id}): {e}")
         return set()

if __name__ == "__main__":
    run_benchmark()
