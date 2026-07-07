import json
import os
import random
import concurrent.futures
from typing import List, Dict

try:
    from google import genai
    from google.genai import types
except ImportError:
    genai = None

def generate_prompt(doc_type: str, complexity: str, seed_info: dict) -> str:
    complexity_desc = {
        "Bassa": "Documento breve e lineare. Contiene pochi dati sensibili (solo in intestazione) e testo standard senza frasi contorte o abbreviazioni ambigue.",
        "Media": "Documento di media lunghezza. Dati sensibili sparsi sia in intestazione che all'interno del testo narrativo (es. nome di un parente, data di un precedente ricovero). Uso moderato di acronimi medici e sigle di reparto.",
        "Alta": "Documento complesso, lungo e 'disordinato', tipico di situazioni d'urgenza o terapie intensive. Contiene tabelle testuali sformattate, refusi, molteplici date, misurazione parametri orari, numeri di telefono nel testo, nomi di più medici/infermieri mischiati, e massiccio uso di abbreviazioni gergali (pz, tp, tp.ab, apy, rx torace, r.c., ndr, vv, ega, tc)."
    }

    return f"""Sei un medico specialista italiano (infettivologo/rianimatore) di un ospedale nella regione {seed_info['regione']}.
Sei coinvolto in un progetto europeo ECDC sulla sorveglianza delle infezioni del sangue (Bloodstream Infections - BSI). Il patogeno isolato in questo caso è: {seed_info['patogeno']}.
Il paziente è un {seed_info['genere']} nato nel {seed_info['anno_nascita']}.

TIPO DI DOCUMENTO: {doc_type}
LIVELLO DI COMPLESSITÀ: {complexity} ({complexity_desc[complexity]})

ISTRUZIONI TASSATIVE:
1. VARIABILITÀ ANAGRAFICA ASSOLUTA: È VIETATO usare nomi banali come "Mario Rossi" o "Giuseppe Verdi". Usa nomi tipici della regione {seed_info['regione']}, nomi rari, o nomi stranieri.
2. GERGO MEDICO ITALIANO: Il testo deve sembrare scritto di fretta da un medico vero. Usa ampiamente abbreviazioni cliniche reali (es. pz, tp, vv, fc, pa, satO2, ega, tc, ev, im, cvc, picc, mdr), acronimi, omettendo articoli dove non necessari (stile telegrafico).
3. INSERIMENTO ENTITÀ: Inserisci deliberatamente ENTITÀ SENSIBILI:
   - Nomi e Cognomi (Paziente, Medici, Infermieri, Familiari)
   - Date esatte (ricovero, prelievo emocoltura) in vari formati (es. 12/03/24, 12 Marzo, 12.03)
   - Luoghi (Ospedale specifico di {seed_info['regione']}, via, CAP, reparti come "MI", "Rianimazione 1")
   - Codici (Codice Fiscale realistico, ID Paziente alfanumerici, Numeri di telefono di referenti)
4. TEMA BSI: Focus clinico su Sepsi/Batteriemia, {seed_info['patogeno']}, emocolture, set di prelievo, CVC/PICC e terapia antibiotica empirica/mirata.

FORMATO DI OUTPUT RIGOROSO:
Devi restituire ESCLUSIVAMENTE un oggetto JSON valido (non Markdown testuale) con questa struttura esatta:
{{
    "text": "Il testo completo del referto generato, con formattazione e andate a capo usando \\n.",
    "ground_truth_entities": [
        {{"entity_type": "PERSON", "value": "StringaEsatta1"}},
        {{"entity_type": "DATE", "value": "StringaEsatta2"}},
        {{"entity_type": "LOCATION", "value": "StringaEsatta3"}},
        {{"entity_type": "ID", "value": "StringaEsatta4"}},
        {{"entity_type": "PHONE", "value": "StringaEsatta5"}}
    ]
}}
CRITICO: I valori in 'ground_truth_entities' devono essere le SOTTO-STRINGHE ESATTE, carattere per carattere, presenti in 'text'. Se non è presente in 'text', non metterlo.
"""

def generate_single_record(client, model_id, doc_type, complexity, seed_info, file_id, output_dir):
    prompt = generate_prompt(doc_type, complexity, seed_info)
    print(f"🔄 Inizio: {file_id} ({doc_type} - {complexity} in {seed_info['regione']})")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = client.models.generate_content(
                model=model_id,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    response_mime_type="application/json"
                )
            )
            
            # FIXED: json.loads (non json.load) perché response.text è una stringa
            data = json.loads(response.text)
            data["id"] = file_id
            data["complexity"] = complexity
            data["type"] = doc_type
            
            with open(os.path.join(output_dir, "raw_txt", f"{file_id}.txt"), "w", encoding="utf-8") as f:
                f.write(data["text"])
                
            md_review = f"# Revisione Umana: {file_id}\n"
            md_review += f"**Tipo:** {doc_type} | **Complessità:** {complexity}\n\n"
            md_review += "## Testo del Referto\n"
            md_review += "--------------------------------------------------\n\n"
            md_review += data["text"] + "\n\n"
            md_review += "--------------------------------------------------\n\n"
            md_review += "## Checklist Entità Generate dall'IA (Ground Truth)\n"
            md_review += "*Istruzioni per i revisori umani: Leggete il testo sopra e spuntate le entità se sono corrette. Aggiungete a mano entità sfuggite all'LLM.*\n\n"
            
            for ent in data["ground_truth_entities"]:
                md_review += f"- [ ] **{ent['entity_type']}**: `{ent['value']}`\n"
                
            with open(os.path.join(output_dir, "revisione_umana", f"{file_id}_review.md"), "w", encoding="utf-8") as f:
                f.write(md_review)
                
            print(f"✅ Completato: {file_id}")
            return data
            
        except Exception as e:
            error_str = str(e)
            if "429" in error_str or "RESOURCE_EXHAUSTED" in error_str:
                import time
                print(f"⏳ Rate limit su {file_id}, attendo 5 secondi (Tentativo {attempt+1}/{max_retries})")
                time.sleep(5)
            else:
                print(f"❌ Errore critico su {file_id}: {e}")
                # Riprovo in caso di disconnessioni di rete
                import time
                time.sleep(3)
                
    return None

def generate_dataset(api_key: str = None, output_dir: str = "dataset_siaam"):
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(os.path.join(output_dir, "revisione_umana"), exist_ok=True)
    os.makedirs(os.path.join(output_dir, "raw_txt"), exist_ok=True)
    
    if not genai and not api_key:
        print("Installare google-genai ed eseguire passando api_key.")
        return

    client = genai.Client(api_key=api_key)
    model_id = 'gemini-3.1-pro-preview'

    doc_types = ["Diario Clinico", "Referto Emocoltura", "Consulenza Infettivologica", "Lettera di Dimissione"]
    complexities = ["Bassa", "Media", "Alta"]
    regioni = ["Lombardia", "Campania", "Veneto", "Sicilia", "Lazio", "Piemonte", "Puglia", "Toscana", "Emilia-Romagna", "Calabria"]
    patogeni = ["Klebsiella pneumoniae KPC", "Staphylococcus aureus MRSA", "Escherichia coli ESBL", "Acinetobacter baumannii CRAB", "Pseudomonas aeruginosa MDR", "Candida auris", "Enterococcus faecium VRE"]
    generi = ["uomo", "donna"]
    
    tasks = []
    record_id = 1
    
    for complexity in complexities:
        for _ in range(20):
            doc_type = random.choice(doc_types)
            seed_info = {
                "regione": random.choice(regioni),
                "patogeno": random.choice(patogeni),
                "genere": random.choice(generi),
                "anno_nascita": random.randint(1930, 2010)
            }
            file_id = f"REC_{complexity[:3].upper()}_{record_id:03d}"
            
            tasks.append({
                "client": client,
                "model_id": model_id,
                "doc_type": doc_type,
                "complexity": complexity,
                "seed_info": seed_info,
                "file_id": file_id,
                "output_dir": output_dir
            })
            record_id += 1

    print(f"🚀 Avvio generazione parallela di {len(tasks)} referti usando il piano a pagamento...")
    dataset_manifest = []
    
    # Usa un ThreadPoolExecutor per parallelizzare fino a 10 richieste contemporanee
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(generate_single_record, **task) for task in tasks]
        for future in concurrent.futures.as_completed(futures):
            res = future.result()
            if res:
                dataset_manifest.append(res)

    # Ordina il manifest per ID prima di salvare per tenerlo pulito
    dataset_manifest.sort(key=lambda x: x["id"])
    
    with open(os.path.join(output_dir, "dataset_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(dataset_manifest, f, ensure_ascii=False, indent=4)
        
    print(f"\n✅ Finito! Generati con successo {len(dataset_manifest)} referti nella cartella '{output_dir}'.")

if __name__ == "__main__":
    import sys
    api_key = os.environ.get("GEMINI_API_KEY")
    if len(sys.argv) > 1:
        api_key = sys.argv[1]
    
    if api_key:
        generate_dataset(api_key=api_key)
    else:
        print("Esegui: python generate_synthetic_records.py <TUA_API_KEY>")
