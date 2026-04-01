# Medical Redactor

Medical Redactor is an advanced, privacy-first, and fully portable Python application designed for healthcare professionals. It automates the ingestion, structural analysis, and text redaction of sensitive patient data (PHI/PII) from clinical records and laboratory data, allowing for seamless anonymization and data sharing.

## 🚀 Features

- **Double-Layer Data Protection**: 
  - A secure "**One-Way Valve**" architecture ensures that Protected Health Information (PHI) never resides on portable media prior to anonymization.
  - Generates inviolable Synthetic Patient IDs (`UUID`) upon ingestion, breaking the associative chain immediately.
- **AI-Powered Redaction**: Utilizes a specialized GLiNER model (`gliner_multi_pii-v1`) running fully offline (CPU/GPU) to identify and mask names, dates, and locations.
- **Rule-Based Engine**: Custom Regex algorithms tailored for Italian Medical Records instantly extract tax codes, phone numbers, emails, and exact dates (while selectively preserving dates in structured lab data for scientific validity).
- **Zero-Trace Execution**: The application runs entirely from a USB drive without installation, suppresses Python cache generation (`__pycache__`), and supports an "Incognito Session" mode where dynamic memory is wiped upon exit.
- **Interactive Review UI**: A powerful Streamlit interface allows operators to visually inspect AI decisions, draw manual redaction rectangles across the PDF, and automatically propagate corrections to all subsequent pages of a document.
- **Automated Memory Learning**: The system improves itself with every export. Confirmed redactions are added to a permanent whitelist, while removed AI suggestions are automatically blacklisted to prevent future false positives.
- **Batch Processing**: A full-screen Patient Acquisition Wizard makes it easy to drag-and-drop hundreds of patient folders and process them sequentially without errors.

## 🧪 Quality Assurance & Testing

The project includes a comprehensive test suite covering core redaction logic, security boundaries, and performance.

### 1. Automated CI/CD
A GitHub Action is configured to run the full test suite (`run_all_tests.py`) on every push to the `main` branch, ensuring that the 'One-Way Valve' and other security invariants are never compromised.

### 2. Manual Verification
You can run the tests locally at any time:
```bash
python run_all_tests.py
```

### 3. Synthetic Test Data
The repository includes a generation script (`generate_test_data.py`) that can create realistic, yet entirely synthetic, medical PDF documents for local stress testing without using real patient data.

## 📦 Architecture

- **Backend**: Python 3.12+, `PyMuPDF` (fitz) for PDF manipulation, `gliner` for local AI Named Entity Recognition (NER).
- **Frontend**: Streamlit, `streamlit-drawable-canvas` for interactive PDF review.
- **Portability**: Designed to be bundled with an embedded Python distribution and run via a single `start_portable.bat` script.

## 🛠️ Setup & Installation

To run this application, you must have an embedded or local Python environment.

### 1. Prerequisites
- Python 3.10+ (Embedded environment recommended for USB portability)
- A specialized GLiNER NER model (`urchade/gliner_multi_pii-v1`) automatically cached in the `models/` directory upon first launch.

### 2. Install Dependencies
Run the included batch script or install manually:
```bash
pip install -r requirements.txt
```

### 3. Launch the Application
Execute the application using Streamlit:
```bash
streamlit run src\main.py
```
*(Alternatively, use `start_portable.bat` if deploying via USB).*

## 📖 Usage

Please refer to the [USER_GUIDE.md](USER_GUIDE.md) for detailed, step-by-step instructions on setting up the portable USB drive, navigating the Patient Acquisition Wizard, and exporting anonymized data.

## 🛡️ Security Boundaries (Staging)

For maximum security in hospital environments, the software supports a **Custom Staging Path**. Instead of copying raw, unredacted patient PDFs directly to your USB drive, the software can ingest them into a secure `C:\` folder (e.g., `C:\Temp\Redactor`) on the host machine. The files are instantly renamed to a synthetic UUID, processed, and *only* the final, permanently redacted PDFs are exported back to the USB drive's `output_pdf` folder.

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
