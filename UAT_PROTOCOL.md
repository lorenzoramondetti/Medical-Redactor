# 📝 User Acceptance Testing (UAT) Protocol
## Project: Medical Redactor v1.0

This document defines the manual testing procedures to validate the security, privacy, and functional accuracy of the **Medical Redactor** software. Passing these tests certifies that the software is ready for use in a hospital environment compliant with GDPR and HIPAA.

---

### 📋 Testing Prerequisites
1.  **Hardware**: USB drive containing the `Medical_Redactor` folder.
2.  **Environment**: Windows PC (even without administrator privileges).
3.  **Test Data**: Use only the files in the `test_data/` folder. **DO NOT use real patient data during the initial testing.**

---

### 🟢 PHASE 1: Installation and Portability (Zero-Trace)
**Goal**: Verify that the software is "Plug & Play" and leaves no traces on the hospital system.

| Test ID | Action | Expected Result | Result (P/F) |
| :--- | :--- | :--- | :--- |
| **1.1** | Insert USB and launch `start_portable.bat`. | The software starts in the default browser. No installation or Admin privileges requested. | [ ] |
| **1.2** | Close the software and press the `Wipe & Exit` button. | The terminal window closes. The `tmp/` folder on the USB is emptied. | [ ] |

---

### 🔒 PHASE 2: Privacy and Security (One-Way Valve)
**Goal**: Ensure sensitive data (PHI) remains isolated and protected.

| Test ID | Action | Expected Result | Result (P/F) |
| :--- | :--- | :--- | :--- |
| **2.1** | In the Sidebar settings, set a local path (e.g., `C:\Temp\Staging`) as the "Staging Folder". | The folder is correctly identified by the system. | [ ] |
| **2.2** | Use the Acquisition Wizard to load `diario_clinico_lungo.pdf`. | The original file must be located only in `C:\Temp\Staging` and NOT in the `output_pdf` folder on the USB. | [ ] |
| **2.3** | Enable "Incognito Session" and add a word to the Whitelist. Close and reopen the software. | The added word must no longer be in the Whitelist (confirms ephemeral memory). | [ ] |

---

### 🧠 PHASE 3: AI Precision and Medical Rules
**Goal**: Verify that AI and Regex correctly identify sensitive data.

| Test ID | Action | Expected Result | Result (P/F) |
| :--- | :--- | :--- | :--- |
| **3.1** | Load `finto_referto_clinico.pdf` in **Clinical Documents** mode. | The Fiscal Code and dates in the text must be automatically highlighted. | [ ] |
| **3.2** | Load `dati_laboratorio_test.pdf` in **Structured Data** mode. | Only the "Date of Birth" must be redacted. Lab test dates must remain visible (scientific validity). | [ ] |
| **3.3** | On `diario_clinico_lungo.pdf` (Page 1), select a term and activate **Correct and Propagate**. | Scrolling to Page 5, the same term must be automatically pre-selected. | [ ] |

---

### 🎨 PHASE 4: Manual Review and Final Export
**Goal**: Validate the physical removal (Incineration) of data.

| Test ID | Action | Expected Result | Result (P/F) |
| :--- | :--- | :--- | :--- |
| **4.1** | On `scansione_fotocopia.pdf`, draw a manual rectangle over a hospital logo. | The rectangle appears in the preview. | [ ] |
| **4.2** | Click on **Export Patient Data**. | A UUID folder is generated in `output_pdf` on the USB. | [ ] |
| **4.3** | Open the exported PDF and try to select the text under the black rectangles. | The text is removed or replaced. It is impossible to recover the original data even with a PDF editor. | [ ] |

---

### 🏆 Final Approval (Sign-off)

*The Medical Redactor software complies with the technical and privacy requirements defined in the Technical Specifications.*

**Test Date:** ____________________

**Evaluator Signature:** ____________________

**Privacy Officer Signature:** ____________________

<br>
<hr>
<br>

# 📝 Protocollo di Collaudo (User Acceptance Testing - UAT)
## Progetto: Medical Redactor v1.0

Questo documento definisce le procedure di test manuali per convalidare la sicurezza, la privacy e l'accuratezza funzionale del software **Medical Redactor**. Il superamento di questi test certifica che il software è pronto per l'uso in ambiente ospedaliero conforme a GDPR e HIPAA.

---

### 📋 Prerequisiti per il Collaudo
1.  **Hardware**: Chiavetta USB contenente la cartella `Medical_Redactor`.
2.  **Ambiente**: PC Windows (anche senza permessi di amministratore).
3.  **Dati di Test**: Utilizzare esclusivamente i file contenuti nella cartella `test_data/`. **NON utilizzare dati reali di pazienti durante il collaudo iniziale.**

---

### 🟢 FASE 1: Installazione e Portabilità (Zero-Trace)
**Obiettivo**: Verificare che il software sia "Plug & Play" e non lasci tracce sul sistema ospedaliero.

| Test ID | Azione | Risultato Atteso | Esito (P/F) |
| :--- | :--- | :--- | :--- |
| **1.1** | Inserire la USB e lanciare `start_portable.bat`. | Il software si avvia nel browser predefinito. Nessuna richiesta di installazione o privilegi Admin. | [ ] |
| **1.2** | Chiudere il software e premere il tasto `Wipe & Exit`. | La finestra di terminale si chiude. La cartella `tmp/` nella USB viene svuotata. | [ ] |

---

### 🔒 FASE 2: Privacy e Sicurezza (One-Way Valve)
**Obiettivo**: Garantire che i dati sensibili (PHI) rimangano isolati e protetti.

| Test ID | Azione | Risultato Atteso | Esito (P/F) |
| :--- | :--- | :--- | :--- |
| **2.1** | Nelle impostazioni (Sidebar), impostare un percorso locale (es. `C:\Temp\Staging`) come "Staging Folder". | La cartella viene correttamente identificata dal sistema. | [ ] |
| **2.2** | Usare l'Acquisition Wizard per caricare `diario_clinico_lungo.pdf`. | Il file originale deve trovarsi solo in `C:\Temp\Staging` e NON nella cartella `output_pdf` della USB. | [ ] |
| **2.3** | Abilitare "Incognito Session" ed aggiungere una parola alla Whitelist. Chiudere e riaprire il software. | La parola aggiunta non deve essere più presente nella Whitelist (conferma memoria effimera). | [ ] |

---

### 🧠 FASE 3: Precisione AI e Regole Mediche
**Obiettivo**: Verificare che l'IA e le Regex identifichino correttamente i dati sensibili.

| Test ID | Azione | Risultato Atteso | Esito (P/F) |
| :--- | :--- | :--- | :--- |
| **3.1** | Caricare `finto_referto_clinico.pdf` in modalità **Clinical Documents**. | Il Codice Fiscale e le date nel testo devono essere evidenziati automaticamente. | [ ] |
| **3.2** | Caricare `dati_laboratorio_test.pdf` in modalità **Structured Data**. | Deve essere oscurata solo la "Data di Nascita". Le date dei prelievi devono rimanere visibili (validità scientifica). | [ ] |
| **3.3** | Su `diario_clinico_lungo.pdf` (Pagina 1), selezionare un termine e attivare **Correct and Propagate**. | Scorrendo verso Pagina 5, lo stesso termine deve essere pre-selezionato automaticamente. | [ ] |

---

### 🎨 FASE 4: Revisione Manuale ed Esportazione Finale
**Obiettivo**: Convalidare la rimozione fisica (Incenerimento) dei dati.

| Test ID | Azione | Risultato Atteso | Esito (P/F) |
| :--- | :--- | :--- | :--- |
| **4.1** | Su `scansione_fotocopia.pdf`, disegnare un rettangolo manuale sopra un logo ospedaliero. | Il rettangolo appare nell'anteprima. | [ ] |
| **4.2** | Cliccare su **Export Patient Data**. | Viene generata una cartella UUID in `output_pdf` sulla USB. | [ ] |
| **4.3** | Aprire il PDF esportato e provare a selezionare il testo sotto i rettangoli neri. | Il testo è rimosso o sostituito. Non è possibile ripristinare i dati originali neanche con editor PDF. | [ ] |

---

### 🏆 Approvazione Finale (Sign-off)

*Il software Medical Redactor è conforme ai requisiti tecnici e di privacy definiti nel Capitolato Tecnico.*

**Data del Collaudo:** ____________________

**Firma del Valutatore:** ____________________

**Firma Responsabile Privacy:** ____________________
