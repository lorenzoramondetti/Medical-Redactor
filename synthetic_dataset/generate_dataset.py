#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
🏥 Medical Redactor - Synthetic Clinical Dataset Generator
==========================================================
Generatore professionale di cartelle cliniche sintetiche italiane per
l'addestramento e il test di modelli Named Entity Recognition (NER) e
algoritmi di anonimizzazione PII conformi al GDPR.

Supporta due modalità di funzionamento:
1. Modalità 'offline' (Default): Generatore probabilistico ad alta fedeltà
   che costruisce prose cliniche realistiche inserendo variabili e casi limite.
2. Modalità 'llm': Generatore basato su LLM remoti (Google Gemini, OpenAI, Anthropic)
   con prompt ingegnerizzati, chain-of-thought e iniezione dinamica di variabili
   per evitare bias nei nomi.
"""

import os
import sys
import json
import random
import argparse
import urllib.request
import urllib.error
from datetime import datetime, timedelta
from pathlib import Path

# --- SEED DATA PER EVITARE BIAS (Dati Anagrafici e Clinici Italiani) ---

COGNOMI = [
    "Rossi", "Bianchi", "Esposito", "Romano", "Colombo", "Ricci", "Marino", "Greco", 
    "Bruno", "Gallo", "Conti", "De Luca", "Costa", "Giordano", "Mancini", "Rizzo", 
    "Lombardi", "Moretti", "Barbieri", "Fontana", "Santoro", "Mariani", "Rinaldi", 
    "Caruso", "Ferrara", "Gallardi", "Pellegrini", "Villa", "Gatti", "Sciarra"
]

NOMI_F = [
    "Maria", "Francesca", "Anna", "Giulia", "Silvia", "Elena", "Chiara", "Laura", 
    "Sara", "Valentina", "Alessandra", "Roberta", "Federica", "Elisa", "Alice", 
    "Sofia", "Marta", "Beatrice", "Giorgia", "Lucia", "Rosa", "Margherita", 
    "Irene", "Simona", "Paola", "Giovanna", "Ester", "Clara", "Luisa", "Carla"
]

NOMI_M = [
    "Francesco", "Alessandro", "Andrea", "Matteo", "Lorenzo", "Gabriele", "Mattia", 
    "Davide", "Riccardo", "Tommaso", "Giuseppe", "Antonio", "Marco", "Luca", 
    "Giovanni", "Roberto", "Stefano", "Mario", "Luigi", "Federico", "Paolo", 
    "Simone", "Cristian", "Claudio", "Enrico", "Alberto", "Fabio", "Vincenzo"
]

NOMI_MEDICI = [
    "Veronesi", "Dulbecco", "Montalcini", "Bassi", "Ramazzini", "Golgi", "Spallanzani", 
    "Morgagni", "Redi", "Cesalpino", "Gigli", "Fazio", "Sileri", "Galli", "Zangrillo"
]

TITOLI_MEDICI = [
    "Dott.", "Dott.ssa", "Prof.", "Prof.ssa", "Dr.", "Dr.ssa"
]

NOMI_INFERMIERI = [
    "Infermiere Bianchi", "Inf. Russo", "Caposala Marini", "Infermiere Professionale Greco", 
    "Inf. Pellegrino", "Infermiere Rizzo"
]

CITTA = [
    "Milano", "Roma", "Torino", "Napoli", "Palermo", "Genova", "Bologna", "Firenze", 
    "Bari", "Catania", "Verona", "Venezia", "Messina", "Padova", "Trieste", "Taranto", 
    "Brescia", "Parma", "Reggio Calabria", "Modena", "Perugia", "Livorno", "Piacenza", 
    "Ancona", "Udine", "Bergamo", "Novara", "Ferrara", "Sassari", "Siracusa"
]

INDIRIZZI = [
    "Via Roma", "Via Milano", "Corso Vittorio Emanuele II", "Viale dei Mille", 
    "Piazza Garibaldi", "Via Cavour", "Via Dante Alighieri", "Corso Buenos Aires", 
    "Piazza della Repubblica", "Viale Regina Margherita", "Via Mazzini", "Via Torino", 
    "Via Leopardi", "Piazza Duomo", "Corso Rosselli", "Via Garibaldi"
]

OSPEDALI = [
    "Ospedale Niguarda Ca' Granda", "Policlinico Umberto I", "Ospedale Molinette", 
    "Ospedale Cardarelli", "Ospedale Civico di Palermo", "Ospedale San Martino", 
    "Policlinico Sant'Orsola-Malpighi", "Ospedale Careggi", "Ospedale Papa Giovanni XXIII", 
    "Ospedale San Raffaele", "Clinica Humanitas", "Istituto Clinico Humanitas", 
    "Ospedale San Carlo Borromeo", "Policlinico di Milano", "Ospedale Maggiore di Bologna"
]

REPARTI = [
    "Cardiologia", "Neurologia", "Oncologia", "Gastroenterologia", "Ortopedia e Traumatologia", 
    "Pediatria", "Dermatologia", "Pneumologia", "Endocrinologia", "Urologia", 
    "Chirurgia Generale", "Medicina Interna", "Ematologia", "Geriatria", "Nefrologia"
]

PATOLOGIE = [
    {"nome": "Ipertensione Arteriosa", "acronimo": "IA", "dettagli": "in terapia medica con ACE-inibitore."},
    {"nome": "Diabete Mellito Tipo 2", "acronimo": "DMT2", "dettagli": "scompensato, in trattamento insulinico."},
    {"nome": "Broncopneumopatia Cronica Ostruttiva", "acronimo": "BPCO", "dettagli": "riacutizzata, in ossigenoterapia."},
    {"nome": "Scompenso Cardiaco Congestizio", "acronimo": "SCC", "dettagli": "in classe NYHA III, trattato con diuretici."},
    {"nome": "Fibrillazione Atriale Parossistica", "acronimo": "FAP", "dettagli": "in terapia anticoagulante orale (TAO)."},
    {"nome": "Insufficienza Renale Cronica", "acronimo": "IRC", "dettagli": "in stadio IIIb, monitorata periodicamente."},
    {"nome": "Appendicite Acuta", "acronimo": "AA", "dettagli": "trattata mediante appendicectomia laparoscopica."},
    {"nome": "Epatite Cronica C", "acronimo": "HCC", "dettagli": "in follow-up clinico-ecografico."},
    {"nome": "Morbo di Crohn", "acronimo": "MC", "dettagli": "in fase di riacutizzazione moderata, terapia steroidea."}
]

# --- FUNZIONI DI SUPPORTO GENERATIVE ---

def genera_codice_fiscale(nome, cognome, data_nascita, sesso):
    """Genera un codice fiscale italiano realistico e strutturato (simulato)."""
    def estrai_consonanti(s):
        return "".join([c.upper() for c in s if c.isalpha() and c.upper() not in "AEIOU"])
    def estrai_vocali(s):
        return "".join([c.upper() for c in s if c.isalpha() and c.upper() in "AEIOU"])
    
    # Codice cognome (3 lettere)
    cons_cog = estrai_consonanti(cognome)
    voc_cog = estrai_vocali(cognome)
    cod_cog = (cons_cog + voc_cog + "XXX")[:3]
    
    # Codice nome (3 lettere)
    cons_nom = estrai_consonanti(nome)
    voc_nom = estrai_vocali(nome)
    if len(cons_nom) >= 4:
        cod_nom = cons_nom[0] + cons_nom[2] + cons_nom[3]
    else:
        cod_nom = (cons_nom + voc_nom + "XXX")[:3]
        
    # Anno (2 cifre)
    anno = str(data_nascita.year)[-2:]
    
    # Mese (1 lettera)
    mesi_lettere = ["A", "B", "C", "D", "E", "H", "L", "M", "P", "R", "S", "T"]
    mese = mesi_lettere[data_nascita.month - 1]
    
    # Giorno (2 cifre, +40 se femmina)
    giorno = data_nascita.day
    if sesso.upper() == "F":
        giorno += 40
    cod_giorno = f"{giorno:02d}"
    
    # Comune e Check (Fissi/Simulati coerenti)
    comune = random.choice(["F205", "H501", "L219", "A794", "D612"]) # Milano, Roma, Torino, Bergamo, Firenze
    check = random.choice("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    
    return f"{cod_cog}{cod_nom}{anno}{mese}{cod_giorno}{comune}{check}"

def genera_telefono():
    prefissi = ["333", "338", "339", "347", "348", "349", "328", "329", "02", "06", "011", "081"]
    pref = random.choice(prefissi)
    num = "".join([str(random.randint(0, 9)) for _ in range(7)])
    if pref.startswith("0"):
        return f"{pref} {num[:3]} {num[3:]}"
    return f"+39 {pref} {num[:3]} {num[3:]}"

def genera_email(nome, cognome):
    domini = ["gmail.com", "outlook.it", "yahoo.it", "ospedale.it", "asl.regione.it"]
    sep = random.choice([".", "_", ""])
    return f"{nome.lower()}{sep}{cognome.lower()}@{random.choice(domini)}"

# --- MODALITÀ OFFLINE: COMPILATORE DI NOTE CLINICHE AD ALTA FEDELTÀ ---

class HighFidelityOfflineGenerator:
    """Generatore locale deterministico-probabilistico di cartelle cliniche sintetiche."""
    
    def genera_caso(self, caso_id):
        # 1. Scelta Anagrafica e Sesso
        sesso = random.choice(["M", "F"])
        nome = random.choice(NOMI_M) if sesso == "M" else random.choice(NOMI_F)
        cognome = random.choice(COGNOMI)
        
        # Scelta del medico
        titolo_med = random.choice(TITOLI_MEDICI)
        cognome_med = random.choice(NOMI_MEDICI)
        nome_med = random.choice(NOMI_M if "Prof." in titolo_med or "Dott." in titolo_med else NOMI_F)
        medico_completo = f"{titolo_med} {nome_med} {cognome_med}"
        
        # Familiari
        fam_sesso = random.choice(["M", "F"])
        fam_nome = random.choice(NOMI_M) if fam_sesso == "M" else random.choice(NOMI_F)
        fam_parentela = random.choice(["coniuge", "figlio", "figlia", "fratello", "caregiver"])
        
        # Date
        oggi = datetime.now()
        eta = random.randint(18, 92)
        data_nascita = oggi - timedelta(days=(eta * 365 + random.randint(0, 364)))
        data_ricovero = oggi - timedelta(days=random.randint(5, 30))
        data_dimissione = data_ricovero + timedelta(days=random.randint(2, 10))
        
        # Luoghi e Contatti
        citta_res = random.choice(CITTA)
        ind_res = f"{random.choice(INDIRIZZI)}, {random.randint(1, 199)}"
        ospedale = random.choice(OSPEDALI)
        reparto = random.choice(REPARTI)
        
        # Codici
        cf = genera_codice_fiscale(nome, cognome, data_nascita, sesso)
        tel_paziente = genera_telefono()
        email_paziente = genera_email(nome, cognome)
        num_cartella = f"CC-{random.randint(10000, 99999)}/{data_ricovero.year}"
        num_posto_letto = f"PL-{random.randint(1, 40)}"
        esenzione = f"0{random.randint(1, 9)}{random.randint(10, 99)}"
        
        # Patologia e parametri
        pat = random.choice(PATOLOGIE)
        pa_sis = random.randint(110, 160)
        pa_dia = random.randint(65, 95)
        fc = random.randint(60, 110)
        sat = random.randint(92, 99)
        
        # 2. Iniezione Edge Cases (Casi limite/Ambiguità richieste su X)
        edge_case = random.choice([
            "omonimia_farmaco", 
            "omonimia_ospedale", 
            "data_relativa", 
            "cognome_citta"
        ])
        
        testo_edge_case = ""
        ground_truth_aggiuntiva = []
        
        if edge_case == "omonimia_farmaco":
            # Caso 1: Farmaco "Rosa" vs Paziente o Medico di nome "Rosa"
            farmaco_ambiguo = "sciroppo di rosa"
            rosa_nome = "Rosa"
            if sesso == "F":
                nome = rosa_nome  # Forziamo il nome del paziente
                testo_edge_case = (
                    f"La paziente {nome} riferisce di aver assunto lo {farmaco_ambiguo} "
                    f"prescritto dal medico di base per lenire la tosse prima del ricovero."
                )
            else:
                testo_edge_case = (
                    f"Riferisce la figlia {rosa_nome} che il paziente ha assunto lo {farmaco_ambiguo} "
                    f"prima dell'arrivo in Pronto Soccorso."
                )
                ground_truth_aggiuntiva.append(rosa_nome)
                
        elif edge_case == "omonimia_ospedale":
            # Caso 2: Paziente Luigi ricoverato a San Luigi, o simili
            luigi_nome = "Luigi"
            nome = luigi_nome  # Forziamo il nome del paziente
            ospedale_ambiguo = "Ospedale San Luigi Gonzaga"
            ospedale = ospedale_ambiguo
            testo_edge_case = (
                f"Il paziente {nome} è stato trasferito presso l'istituto ospedaliero "
                f"{ospedale_ambiguo} per completare la diagnostica specialistica."
            )
            
        elif edge_case == "data_relativa":
            # Caso 3: Date relative non marcate come PII assolute (es. ieri, sabato scorso)
            giorni_settimana = ["lunedì", "martedì", "mercoledì", "giovedì", "venerdì", "sabato", "domenica"]
            giorno_trauma = random.choice(giorni_settimana)
            testo_edge_case = (
                f"Il paziente riferisce caduta accidentale avvenuta sabato scorso presso il proprio domicilio. "
                f"Condotto ieri da personale del 118 in PS. Verrà rivalutato dal medico curante tra due {giorno_trauma}."
            )
            
        elif edge_case == "cognome_citta":
            # Caso 4: Cognome che è anche una città (es. "Milano", "Torino", "Roma")
            cognome = random.choice(["Milano", "Torino", "Roma", "Napoli", "Pisa"])
            testo_edge_case = (
                f"Al controllo anamnestico, il sig. {cognome} (residente nella città di {citta_res}) "
                f"mostra buona aderenza alla terapia proposta."
            )

        # 3. Costruzione della tipologia documentale
        tipologia = random.choice(["Lettera di dimissione", "Diario clinico", "Verbale di pronto soccorso"])
        
        testo_clinico = ""
        
        # Formattazione date
        fmt_nascita = data_nascita.strftime("%d/%m/%Y")
        fmt_ricovero = data_ricovero.strftime("%d/%m/%Y")
        fmt_ricovero_prosa = data_ricovero.strftime(f"%d {random.choice(['Maggio', 'Giugno', 'Luglio'])} %Y")
        fmt_dimissione = data_dimissione.strftime("%d/%m/%Y")
        
        if tipologia == "Lettera di dimissione":
            testo_clinico = (
                f"{ospedale.upper()} - REPARTO DI {reparto.upper()}\n"
                f"LETTERA DI DIMISSIONE CLINICA\n\n"
                f"Identificativo Paziente: Sig./Sig.ra {nome} {cognome}, nato/a il {fmt_nascita} a {citta_res} "
                f"e residente in {ind_res}. C.F.: {cf}. Tel: {tel_paziente} (Email: {email_paziente}).\n"
                f"Riferimento Cartella Clinica: {num_cartella} - Posto Letto: {num_posto_letto} - Cod. Esenzione: {esenzione}.\n\n"
                f"Periodo di ricovero: dal {fmt_ricovero_prosa} al {fmt_dimissione}.\n"
                f"Medico dimettente: {medico_completo}.\n"
                f"Contatto di riferimento: {fam_nome} ({fam_parentela}).\n\n"
                f"DIAGNOSI D'ACCETTAZIONE: {pat['nome']} ({pat['acronimo']}), {pat['dettagli']}\n\n"
                f"ANAMNESI E DECORSO CLINICO:\n"
                f"Paziente di anni {eta} giunge nel nostro reparto inviato dal Pronto Soccorso per riacutizzazione clinica. "
                f"All'ingresso i parametri vitali mostravano: FC {fc} bpm, PA {pa_sis}/{pa_dia} mmHg, SatO2 {sat}%. "
                f"Eseguito ECG urgente che evidenzia ritmo sinusale stabile. Nel corso della degenza si è impostata "
                f"terapia infusionale mirata con progressivo miglioramento delle condizioni soggettive e oggettive. "
                f"{testo_edge_case}\n\n"
                f"TERAPIA CONSIGLIATA ALLA DIMISSIONE:\n"
                f"- Cardioaspirina 100 mg: 1 compressa a pranzo.\n"
                f"- Lasix 25 mg: 1 compressa ore 08:00.\n"
                f"- Follow-up cardiologico tra 30 giorni presso il nostro ambulatorio.\n\n"
                f"Firma del Medico Responsabile: {medico_completo}"
            )
            
        elif tipologia == "Diario clinico":
            data_diario_1 = data_ricovero.strftime("%d/%m/%Y")
            data_diario_2 = (data_ricovero + timedelta(days=1)).strftime("%d/%m/%Y")
            testo_clinico = (
                f"{ospedale}\n"
                f"DIARIO CLINICO GIORNALIERO - CARTELLA {num_cartella}\n"
                f"Paziente: {nome} {cognome} (Nato/a {fmt_nascita}). Cod. Fiscale: {cf}.\n"
                f"Medico di Guardia: {medico_completo}. Contatto familiare: {fam_nome}.\n\n"
                f"--- Data: {data_diario_1} ore 09:30 ---\n"
                f"Condizioni stabili. Riferisce riposo notturno discreto. Obiettività: Addome trattabile, non dolente. "
                f"FC {fc} bpm. PA {pa_sis}/{pa_dia} mmHg. {testo_edge_case} Si prosegue con terapia medica impostata.\n"
                f"Firmato: {medico_completo}\n\n"
                f"--- Data: {data_diario_2} ore 08:15 ---\n"
                f"Passaggio consegne. {random.choice(NOMI_INFERMIERI)} segnala picco pressorio notturno. "
                f"Rilevata PA 170/95 mmHg. Eseguito ECG di controllo: assenza di variazioni acute. "
                f"Somministrata compressa di bloccante dei canali del calcio su indicazione del {medico_completo}.\n"
                f"Firmato: {medico_completo}"
            )
            
        elif tipologia == "Verbale di pronto soccorso":
            testo_clinico = (
                f"REGIONE LAZIO / LOMBARDIA - {ospedale.upper()}\n"
                f"VERBALE DI PRONTO SOCCORSO - ACCETTAZIONE CODICE ROSSO/ARANCIONE\n"
                f"Numero Pratica: PS-{random.randint(100000, 999999)} - Letto di attesa: {num_posto_letto}\n\n"
                f"DATI ANAGRAFICI PAZIENTE:\n"
                f"Nome: {nome} {cognome} - Sesso: {sesso} - Età: {eta}\n"
                f"Data di Nascita: {fmt_nascita} - Comune Residenza: {citta_res} - Indirizzo: {ind_res}\n"
                f"Codice Fiscale: {cf} - Telefono: {tel_paziente}\n"
                f"Contatto d'Emergenza: {fam_nome} (Tel: {genera_telefono()})\n\n"
                f"DESCRIZIONE ACCETTAZIONE:\n"
                f"Il paziente viene condotto in PS alle ore {random.randint(0,23):02d}:{random.randint(0,59):02d} del {fmt_ricovero}. "
                f"Accompagnato da {fam_parentela} ({fam_nome}) per dispnea ingravescente ed ipertensione. "
                f"Triage eseguito da {random.choice(NOMI_INFERMIERI)}. Parametri vitali: PA {pa_sis}/{pa_dia} mmHg, FC {fc} bpm, SatO2 {sat}%.\n"
                f"Valutazione Medica eseguita da {medico_completo}.\n"
                f"Quesito Clinico: Sospetto {pat['nome']} ({pat['acronimo']}).\n"
                f"{testo_edge_case}\n\n"
                f"TRATTAMENTO E PROVVEDIMENTI:\n"
                f"Eseguito prelievo ematico urgente, emogasanalisi (EGA), RX Torace ed ECG. "
                f"Impostata infusione di diuretico dell'ansa. Si dispone il ricovero urgente presso il reparto di {reparto}.\n\n"
                f"Firma del Medico di Pronto Soccorso: {medico_completo}"
            )

        # 4. Compilazione Ground Truth PHI esatta per questo caso
        pazienti_list = [f"{nome} {cognome}", nome, cognome]
        pazienti_list = list(set([p for p in pazienti_list if p]))
        
        medici_list = [medico_completo, f"{titolo_med} {cognome_med}", cognome_med, f"{nome_med} {cognome_med}"]
        medici_list = list(set([m for m in medici_list if m]))
        
        date_list = [fmt_nascita, fmt_ricovero, fmt_dimissione]
        if tipologia == "Lettera di dimissione":
            date_list.append(fmt_ricovero_prosa)
        if tipologia == "Diario clinico":
            date_list.append(data_diario_1)
            date_list.append(data_diario_2)
        date_list = list(set([d for d in date_list if d]))
        
        luoghi_list = [citta_res, ind_res, ospedale, reparto]
        if ospedale_ambiguo := (edge_case == "omonimia_ospedale" and ospedale):
            luoghi_list.append(ospedale_ambiguo)
        luoghi_list = list(set([l for l in luoghi_list if l]))
        
        codici_list = [cf, tel_paziente, email_paziente, num_cartella, num_posto_letto, esenzione]
        codici_list = list(set([c for c in codici_list if c]))
        
        # Aggiunte da edge cases
        for item in ground_truth_aggiuntiva:
            if item not in pazienti_list:
                pazienti_list.append(item)

        ground_truth = {
            "PAZIENTE": sorted(pazienti_list),
            "MEDICO": sorted(medici_list),
            "DATA": sorted(date_list),
            "LUOGO": sorted(luoghi_list),
            "ID_CODICI": sorted(codici_list)
        }
        
        return {
            "id_caso": caso_id,
            "tipologia_documento": tipologia,
            "branca_medica": reparto,
            "testo_clinico": testo_clinico,
            "ground_truth_phi": ground_truth
        }

# --- MODALITÀ ONLINE: GENERAZIONE CON API LLM ESTERNE (GEMINI / OPENAI / ANTHROPIC) ---

class LLMDatasetGenerator:
    """Generatore di dataset tramite chiamate API strutturate (con supporto nativo a Gemini 3.5/2.5 Flash)."""
    
    def __init__(self, provider, api_key, model_name=None):
        self.provider = provider.lower()
        self.api_key = api_key
        
        if self.provider == "gemini":
            self.model_name = model_name or "gemini-2.5-flash"
        elif self.provider == "openai":
            self.model_name = model_name or "gpt-4o-mini"
        elif self.provider == "anthropic":
            self.model_name = model_name or "claude-3-5-sonnet-20241022"
        else:
            raise ValueError(f"Provider sconosciuto: {provider}")

    def call_gemini(self, prompt):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model_name}:generateContent?key={self.api_key}"
        
        payload = {
            "contents": [{
                "parts": [{
                    "text": prompt
                }]
            }],
            "generationConfig": {
                "responseMimeType": "application/json"
            }
        }
        
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=req_data, 
            headers={"Content-Type": "application/json"}
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                res_body = response.read().decode('utf-8')
                res_json = json.loads(res_body)
                
                # Parsing della struttura di ritorno di Gemini
                text_out = res_json['candidates'][0]['content']['parts'][0]['text']
                return json.loads(text_out)
        except urllib.error.HTTPError as e:
            print(f"[ERRORE] Errore API Gemini: {e.code} - {e.read().decode('utf-8')}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERRORE] Errore Generico durante la chiamata Gemini: {e}")
            sys.exit(1)

    def call_openai(self, prompt):
        url = "https://api.openai.com/v1/chat/completions"
        
        payload = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": "Sei un assistente di generazione dati clinici strutturati in JSON."},
                {"role": "user", "content": prompt}
            ],
            "response_format": {"type": "json_object"}
        }
        
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=req_data, 
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                res_body = response.read().decode('utf-8')
                res_json = json.loads(res_body)
                text_out = res_json['choices'][0]['message']['content']
                return json.loads(text_out)
        except urllib.error.HTTPError as e:
            print(f"[ERRORE] Errore API OpenAI: {e.code} - {e.read().decode('utf-8')}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERRORE] Errore Generico durante la chiamata OpenAI: {e}")
            sys.exit(1)

    def call_anthropic(self, prompt):
        url = "https://api.anthropic.com/v1/messages"
        
        payload = {
            "model": self.model_name,
            "max_tokens": 4000,
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }
        
        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            url, 
            data=req_data, 
            headers={
                "Content-Type": "application/json",
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01"
            }
        )
        
        try:
            with urllib.request.urlopen(req) as response:
                res_body = response.read().decode('utf-8')
                res_json = json.loads(res_body)
                text_out = res_json['content'][0]['text']
                # Pulizia manuale di eventuali blocchi ```json o testo introduttivo
                start_idx = text_out.find("{")
                end_idx = text_out.rfind("}")
                if start_idx != -1 and end_idx != -1:
                    return json.loads(text_out[start_idx:end_idx+1])
                return json.loads(text_out)
        except urllib.error.HTTPError as e:
            print(f"[ERRORE] Errore API Anthropic: {e.code} - {e.read().decode('utf-8')}")
            sys.exit(1)
        except Exception as e:
            print(f"[ERRORE] Errore Generico durante la chiamata Anthropic: {e}")
            sys.exit(1)

    def genera_caso(self, caso_id):
        """Genera un caso clinico tramite iniezione dinamica di seed-data per evitare bias."""
        
        # Scegliamo variabili a caso da iniettare nel prompt per forzare la variabilità
        sesso = random.choice(["M", "F"])
        nome = random.choice(NOMI_M if sesso == "M" else NOMI_F)
        cognome = random.choice(COGNOMI)
        citta = random.choice(CITTA)
        ospedale = random.choice(OSPEDALI)
        patologia = random.choice(PATOLOGIE)
        medico_cog = random.choice(NOMI_MEDICI)
        medico_nome = random.choice(NOMI_M)
        medico = f"{random.choice(TITOLI_MEDICI)} {medico_nome} {medico_cog}"
        
        # Edge cases specifici per questo caso
        edge_case = random.choice([
            "omonimia_farmaco", 
            "omonimia_ospedale", 
            "data_relativa", 
            "cognome_citta"
        ])
        
        prompt_edge_case = ""
        if edge_case == "omonimia_farmaco":
            prompt_edge_case = (
                f"- **Vicolo Cieco/Ambiguità (Omonimia Farmaco)**: Inserisci una persona di nome 'Rosa' (es. la figlia del paziente) "
                f"e anche una menzione all'ingrediente/farmaco clinico 'sciroppo di rosa'. Il modello NER deve mappare 'Rosa' (persona) come PAZIENTE, "
                f"ma NON deve mappare 'sciroppo di rosa' (cura clinica) come PII personale."
            )
        elif edge_case == "omonimia_ospedale":
            prompt_edge_case = (
                f"- **Vicolo Cieco/Ambiguità (Omonimia Ospedale)**: Il paziente si deve chiamare 'Luigi' e l'ospedale di ricovero "
                f"deve essere l'Ospedale 'San Luigi Gonzaga'. Mappa 'Luigi' come PAZIENTE e 'Ospedale San Luigi Gonzaga' come LUOGO."
            )
        elif edge_case == "data_relativa":
            prompt_edge_case = (
                f"- **Vicolo Cieco/Ambiguità (Date Relative)**: Inserisci espressioni di tempo relative come 'ieri', 'sabato scorso' "
                f"o 'tra due martedì'. Queste NON devono essere incluse nella ground_truth_phi sotto la chiave 'DATA' in quanto non costituiscono dati identificativi esatti."
            )
        elif edge_case == "cognome_citta":
            prompt_edge_case = (
                f"- **Vicolo Cieco/Ambiguità (Cognome-Città)**: Il paziente deve avere come cognome '{random.choice(['Milano', 'Torino', 'Pisa'])}' "
                f"mentre risiede in un'altra città (es. {citta}). Assicurati di dichiarare correttamente l'entità nella ground truth."
            )

        prompt = f"""
Sei un sistema avanzato di simulazione di dati clinici per la ricerca scientifica.
Il tuo obiettivo è generare un caso clinico sintetico e non strutturato, espresso in lingua italiana, per addestrare modelli NER di anonimizzazione.

### INIEZIONE VARIABILI D'INPUT (Obbligatorio per evitare bias di generazione)
Per questo specifico caso ({caso_id}), devi inserire fluentemente ed obbligatoriamente i seguenti dati nel testo:
- **Paziente**: {nome} {cognome} (Sesso: {sesso})
- **Residenza/Città**: {citta}
- **Ospedale di riferimento**: {ospedale}
- **Patologia principale**: {patologia['nome']} ({patologia['acronimo']})
- **Medico curante**: {medico}

{prompt_edge_case}

### REQUISITI DELLO STILE CLINICO
- Usa gergo medico reale italiano, acronimi (DMT2, BPCO, FC, PA, SatO2), refusi clinici realistici ed ellissi tipiche dei diari ospedalieri.
- Il testo clinico NON deve contenere tabelle, ma deve essere scritto come prose, note cliniche, o diario di reparto non strutturato.

### FORMATO DI OUTPUT JSON RICHIESTO (Restituisci ESCLUSIVAMENTE questo oggetto JSON)
{{
  "id_caso": "{caso_id}",
  "tipologia_documento": "Lettera di dimissione o Diario clinico o Verbale di pronto soccorso",
  "branca_medica": "{patologia['nome']}",
  "testo_clinico": "[Testo clinico non strutturato, ricco di dati sensibili inseriti fluidamente]",
  "ground_truth_phi": {{
    "PAZIENTE": ["Elenco esatto di tutte le occorrenze/varianti del nome del paziente e dei familiari presenti nel testo"],
    "MEDICO": ["Elenco esatto di tutte le occorrenze/varianti del nome del medico presenti nel testo"],
    "DATA": ["Elenco esatto di tutte le date precise es. 12/05/2024, 12 Maggio presenti nel testo"],
    "LUOGO": ["Elenco esatto di ospedali, città, indirizzi presenti nel testo"],
    "ID_CODICI": ["Elenco esatto di codici fiscali, numeri telefonici, email o ID letto presenti nel testo"]
  }}
}}
"""

        if self.provider == "gemini":
            return self.call_gemini(prompt)
        elif self.provider == "openai":
            return self.call_openai(prompt)
        elif self.provider == "anthropic":
            return self.call_anthropic(prompt)

# --- CLI INTERFACE E LOGICA DI ESPORTAZIONE ---

def main():
    parser = argparse.ArgumentParser(
        description="Generatore professionale di dataset clinici sintetici per test di anonimizzazione PII/GDPR."
    )
    parser.add_argument(
        "--count", type=int, default=3,
        help="Numero di casi clinici sintetici da generare (default: 3)."
    )
    parser.add_argument(
        "--mode", choices=["offline", "llm"], default="offline",
        help="Modalità di generazione: 'offline' (locale ad alta fedeltà) o 'llm' (tramite API remota)."
    )
    parser.add_argument(
        "--provider", choices=["gemini", "openai", "anthropic"], default="gemini",
        help="Provider LLM da utilizzare in modalità 'llm' (default: gemini)."
    )
    parser.add_argument(
        "--model", type=str, default=None,
        help="Nome specifico del modello LLM (default coerente con il provider)."
    )
    parser.add_argument(
        "--api-key", type=str, default=None,
        help="API Key per il provider selezionato. Se omessa, viene letta da variabili d'ambiente (GEMINI_API_KEY, OPENAI_API_KEY, ANTHROPIC_API_KEY)."
    )
    parser.add_argument(
        "--output", type=str, default="synthetic_dataset/synthetic_dataset_output.json",
        help="File JSON di output in cui salvare il dataset (default: synthetic_dataset/synthetic_dataset_output.json)."
    )
    
    args = parser.parse_args()

    print("[STATUS] --- MEDICAL REDACTOR - SYNTHETIC DATASET GENERATOR ---")
    print(f"[STATUS] Modalità selezionata: {args.mode.upper()}")
    print(f"[STATUS] Numero di casi da generare: {args.count}")
    
    casi_generati = []
    
    if args.mode == "offline":
        print("[STATUS] Avvio Generatore offline ad alta fedeltà...")
        gen = HighFidelityOfflineGenerator()
        for i in range(1, args.count + 1):
            caso_id = f"CASO_{i:03d}"
            print(f"  [+] Generazione locale di {caso_id}...")
            caso = gen.genera_caso(caso_id)
            casi_generati.append(caso)
    else:
        # Recupero API Key dalle variabili d'ambiente se non passata da CLI
        api_key = args.api_key
        if not api_key:
            env_var = f"{args.provider.upper()}_API_KEY"
            api_key = os.environ.get(env_var)
            
        if not api_key:
            print(f"[ERRORE] Errore: Per la modalità 'llm' è richiesta un'API Key.")
            print(f"   Forniscila tramite `--api-key` o imposta la variabile d'ambiente '{args.provider.upper()}_API_KEY'.")
            sys.exit(1)
            
        print(f"[STATUS] Connessione in corso a {args.provider.upper()} (Modello: {args.model or 'Default'})...")
        gen = LLMDatasetGenerator(args.provider, api_key, args.model)
        
        for i in range(1, args.count + 1):
            caso_id = f"CASO_{i:03d}"
            print(f"  [+] Generazione via LLM API di {caso_id}...")
            try:
                caso = gen.genera_caso(caso_id)
                # Assicuriamo che l'ID caso sia coerente
                caso["id_caso"] = caso_id
                casi_generati.append(caso)
            except Exception as e:
                print(f"  [!] Errore durante la generazione di {caso_id}: {e}")
                print("  [!] Skip e continuazione del batch...")

    # Scrittura del dataset strutturato finale
    output_path = Path(args.output)
    try:
        # Se siamo in questo script, creiamo la directory di destinazione se non esiste
        cartella_dest = os.path.dirname(args.output)
        if cartella_dest and not os.path.exists(cartella_dest):
            os.makedirs(cartella_dest, exist_ok=True)
            
        with open(args.output, "w", encoding="utf-8") as f:
            json.dump(casi_generati, f, indent=2, ensure_ascii=False)
            
        print(f"[STATUS] Generazione Completata con successo!")
        print(f"[STATUS] Dataset salvato in: '{os.path.abspath(args.output)}'")
        print(f"[STATUS] Numero totale di record scritti: {len(casi_generati)}")
        
    except Exception as e:
        print(f"[ERRORE] Errore durante il salvataggio del file: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
