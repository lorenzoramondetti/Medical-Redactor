import fitz  # PyMuPDF
from PIL import Image, ImageDraw, ImageFont
import os

# Create test_data directory if it doesn't exist
test_dir = 'test_data'
if not os.path.exists(test_dir):
    os.makedirs(test_dir)

def create_text_pdf(filename, title, contentLines):
    doc = fitz.open()
    page = doc.new_page()
    
    # Title
    page.insert_text((50, 50), title, fontsize=16, color=(0, 0, 0.5))
    
    # Content
    y = 100
    for line in contentLines:
        page.insert_text((50, y), line, fontsize=12)
        y += 20
        
    doc.save(os.path.join(test_dir, filename))
    doc.close()

def create_multipage_pdf(filename, title, patientInfo, pagesContent):
    doc = fitz.open()
    
    for i, content in enumerate(pagesContent):
        page = doc.new_page()
        # Header with patient info
        header = f"{title} - Pagina {i+1} | Paziente: {patientInfo['name']} | CF: {patientInfo['cf']} | Nato il: {patientInfo['dob']}"
        page.insert_text((50, 30), header, fontsize=10, color=(0.5, 0.5, 0.5))
        
        # Main Title
        page.insert_text((50, 70), f"Diario Clinico - Giorno {i+1}", fontsize=14, color=(0, 0, 0))
        
        # Content
        y = 110
        for line in content:
            page.insert_text((50, y), line, fontsize=11)
            y += 18
            
    doc.save(os.path.join(test_dir, filename))
    doc.close()

def create_raster_pdf(filename, title, contentLines):
    # Create an image using PIL
    width, height = 595, 842  # A4 roughly
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    
    # We'll use a basic drawer since we might not have custom fonts readily available
    # Title
    draw.text((50, 50), title, fill=(0, 0, 0))
    
    # Content
    y = 100
    for line in contentLines:
        draw.text((50, y), line, fill=(0, 0, 0))
        y += 25
    
    # Save the image and convert to PDF
    img_path = os.path.join(test_dir, filename + '.png')
    img.save(img_path)
    
    doc = fitz.open()
    img_doc = fitz.open(img_path)
    pdf_bytes = img_doc.convert_to_pdf()
    img_doc.close()
    
    out_pdf = fitz.open("pdf", pdf_bytes)
    doc.insert_pdf(out_pdf)
    doc.save(os.path.join(test_dir, filename))
    doc.close()
    os.remove(img_path) # Clean up temp image

# 1. finto_referto_clinico.pdf (Standard text with abbreviations/CF)
create_text_pdf(
    "finto_referto_clinico.pdf",
    "REFERTO CLINICO - REPARTO CARDIOLOGIA",
    [
        "Paziente: MARIO ROSSI. Codice Fiscale: RSSMRA80A01H501Z.",
        "Nato il 01-01-1980 a Roma.",
        "Motivo della visita: Sospetta extrasistolia atriale.",
        "Referto: Paziente di anni 46, presenta PA (125/85 mmHg) e FC (80 bpm).",
        "Non si rilevano soffi patologici. ECG nei limiti della norma.",
        "Data Referto: 01/04/2026. Firmato: Dott. Andrea Neri."
    ]
)

# 2. dati_laboratorio_test.pdf (Lab results with "Data di Nascita")
create_text_pdf(
    "dati_laboratorio_test.pdf",
    "LABORATORIO ANALISI ALPHA",
    [
        "ESAMI DEL SANGUE",
        "Data di Nascita: 10/10/1985",
        "Paziente: FRANCESCO BIANCHI",
        "Data Prelievo: 25/03/2026",
        "Data Validazione: 26/03/2026",
        "Esame              Risultato          Unita          Rif.",
        "Glucosio           95                 mg/dL          70-110",
        "Creatinina         0.9                mg/dL          0.7-1.2",
        "Sodio              140                mmol/L         135-145"
    ]
)

# 3. documento_clinico_generico.pdf (Generic hospital document for Clinical mode)
create_text_pdf(
    "documento_clinico_generico.pdf",
    "LETTERA DI DIMISSIONE - OSPEDALE CIVILE",
    [
        "INFORMAZIONI PAZIENTE",
        "Paziente: ANNA VERDI. Nata il: 15/05/1975.",
        "Data Ricovero: 15/03/2026.",
        "Data Dimissione: 22/03/2026.",
        "Diagnosi: Faringite batterica acuta. Sottoposta a terapia antibiotica.",
        "Prossimo controllo ambulatoriale: 10/04/2026."
    ]
)

# 4. scansione_fotocopia.pdf (Rasterized scan, no OCR)
create_raster_pdf(
    "scansione_fotocopia.pdf",
    "CERTIFICATO MEDICO DI IDONEITA - (RICEVUTA SCANSIONATA)",
    [
        "SI ATTESTA CHE IL SIG. LORENZO VERDI, NATO IL 12/12/1992,",
        "E' IN BUONA SALUTE.",
        "DATA: 30/03/2026. FIRMA: DR. MARCO ROSSI (LOGOTIPO OSPEDALIERO)",
        "Questo documento e' una scansione d'immagine senza testo selezionabile.",
        "L'operatore deve usare lo strumento di disegno per oscurare i dati."
    ]
)

# 5. diario_clinico_lungo.pdf (Multi-page for "Correct and Propagate" testing)
create_multipage_pdf(
    "diario_clinico_lungo.pdf",
    "OSPEDALE RIUNITI - DIARIO CLINICO",
    {"name": "LUCA VERDI", "cf": "VRDL CU90A01H501Y", "dob": "01/01/1990"},
    [
        ["Paziente stabile. Si richiede monitoraggio parametri vitali.", "In data 15/03/2026 inizio terapia antibiotica ore 08:00."],
        ["Esami del sangue effettuati. Valori di leucociti in diminuzione.", "Paziente riferisce leggero miglioramento."],
        ["Si prosegue con il protocollo terapeutico.", "Aggiunta idratazione endovenosa."],
        ["Parametri vitali nella norma.", "Il paziente cammina autonomamente nel corridoio."],
        ["Lettera di dimissione pronta.", "Si raccomanda riposo domiciliare per 7 giorni."]
    ]
)

# 7. nomi_ambigui.pdf (Names that are also common nouns)
create_text_pdf(
    "nomi_ambigui.pdf",
    "REPARTO DI MEDICINA GENERALE",
    [
        "Medico curante: Dr. FIORINO SECONDO.",
        "Paziente: SESTO BIANCHI. Nato il: 06/06/1966.",
        "Referto: Il paziente riferisce dolore al piede destro.",
        "Si consiglia visita con la Dr.ssa BELLA VISTA.",
        "Località: FIORE (PV). Data: 01/04/2026."
    ]
)

# 8. toponimi_numerici.pdf (Addresses with numbers/dates)
create_text_pdf(
    "toponimi_numerici.pdf",
    "CERTIFICATO DI RESIDENZA PER USO CLINICO",
    [
        "Sig. MARIO VERDI, nato il 01/01/1980.",
        "Residente in: VIA 24 MAGGIO, n. 15, MILANO (MI).",
        "Domicilio temporaneo: PIAZZA 4 NOVEMBRE, 10, ROMA (RM).",
        "Data emissione: 02/04/2026."
    ]
)

# 9. abbreviazioni_medicali.pdf (Clinical acronyms vs Initials)
create_text_pdf(
    "abbreviazioni_medicali.pdf",
    "APPUNTI CLINICI - PRONTO SOCCORSO",
    [
        "Paziente: A.G. (per motivi di urgenza non identificato).",
        "Sospetta F.A. (Fibrillazione Atriale).",
        "Effettuato E.C.G. e prelievo per M.C. (Marcatori Cardiaci).",
        "Contattare il Medico di Guardia: M. ROSSI.",
        "Ore 10:30 - Somministrata terapia correttiva."
    ]
)

# 10. testo_sporco_ocr.pdf (Bad formatting/OCR simulation)
create_text_pdf(
    "testo_sporco_ocr.pdf",
    "REPORT DI LABORATORIO (ERRORI DI FORMATTAZIONE)",
    [
        "Paziente:MARIO ROSSI.Nato il:01/01/1980.CF:RSSMRA80A01H501Z",
        "Esame:Glicemia.Risultato:105mg/dl(70-110)",
        "Dottore:V.VERDI.Firmadigitale:XYZ12345",
        "DATA:20260401.TIPO:URGENTE"
    ]
)

print("Test data files generated successfully in 'test_data/' directory.")
