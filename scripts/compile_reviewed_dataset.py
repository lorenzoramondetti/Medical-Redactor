import os
import json
import re

def compile_dataset(dataset_dir="dataset_siaam"):
    review_dir = os.path.join(dataset_dir, "revisione_umana")
    txt_dir = os.path.join(dataset_dir, "raw_txt")
    
    if not os.path.exists(review_dir):
        print("Cartella revisione_umana non trovata.")
        return

    manifest = []
    
    for filename in os.listdir(review_dir):
        if filename.endswith("_review.md"):
            filepath = os.path.join(review_dir, filename)
            file_id = filename.replace("_review.md", "")
            
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
                
            # Estrai tipo e complessità dall'intestazione
            tipo_match = re.search(r"\*\*Tipo:\*\* (.*?) \|", content)
            comp_match = re.search(r"\*\*Complessità:\*\* (.*?)\n", content)
            
            tipo = tipo_match.group(1).strip() if tipo_match else "Sconosciuto"
            compl = comp_match.group(1).strip() if comp_match else "Sconosciuta"
            
            # Estrai il testo
            try:
                parts = content.split("--------------------------------------------------")
                text_content = parts[1].strip()
            except IndexError:
                # Fallback se le righe divisorie sono state modificate
                print(f"Formato file anomalo per {filename}, lo salto.")
                continue
                
            # Estrai le entità dalla checklist (supporta sia spuntate [x] che vuote [ ])
            # Formato atteso: - [ ] **PERSON**: `Mario Rossi` oppure - [x] **PERSON**: `Mario Rossi`
            entities = []
            for line in parts[2].split('\n'):
                # Cerca pattern lista
                if line.strip().startswith("- ["):
                    # Estrai tipo e valore
                    # Supportiamo sia il backtick `Valore` che il valore normale
                    match = re.search(r"\*\*(.*?)\*\*:\s*`?(.*?)`?$", line.strip())
                    if match:
                        ent_type = match.group(1).strip()
                        ent_val = match.group(2).strip()
                        entities.append({
                            "entity_type": ent_type,
                            "value": ent_val
                        })
                        
            manifest.append({
                "id": file_id,
                "complexity": compl,
                "type": tipo,
                "text": text_content,
                "ground_truth_entities": entities
            })
            
            # Aggiorna anche il file testuale raw per sicurezza
            with open(os.path.join(txt_dir, f"{file_id}.txt"), "w", encoding="utf-8") as f:
                f.write(text_content)
                
    with open(os.path.join(dataset_dir, "dataset_manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=4)
        
    print(f"✅ Compilazione completata! Il dataset_manifest.json ora contiene {len(manifest)} record validati umanamente.")

if __name__ == "__main__":
    compile_dataset()
