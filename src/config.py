
import os
import sys
import json
from pathlib import Path

# --- PORTABILITY & PRIVACY CONFIGURATION ---

# 1. Prevent Python from writing __pycache__ (Zero-Trace)
sys.dont_write_bytecode = True
os.environ["PYTHONDONTWRITEBYTECODE"] = "1"

# 2. Define Base Paths relative to the executable/script location
#    This ensures the app finds files whether on C: or a USB drive E:
BASE_DIR = Path(__file__).parent.parent.resolve()
SRC_DIR = BASE_DIR / "src"
MODELS_DIR = BASE_DIR / "models"
OUTPUT_DIR = BASE_DIR / "output_pdf"
MEMORY_FILE = BASE_DIR / "global_memory.json"
IGNORE_FILE = BASE_DIR / "global_ignore.json"
PROVINCE_FILE = BASE_DIR / "sigle_province_italiane.json"
SETTINGS_FILE = BASE_DIR / "settings.json"

# 3. Default Settings
DEFAULT_SETTINGS = {
    "use_gpu": True,          # Auto-detect if possible
    "manual_mode": False,     # Force manual mode (no AI)
    "ephemeral_session": False, # Incognito mode (don't save memory to disk)
    "custom_staging_path": "" # Optional C:\ path for strict Hospital compliance (One-Way Valve)
}

def load_settings():
    if SETTINGS_FILE.exists():
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                settings = json.load(f)
                return {**DEFAULT_SETTINGS, **settings} # Merge with defaults
        except Exception as e:
            print(f"Error loading settings: {e}")
            return DEFAULT_SETTINGS
    return DEFAULT_SETTINGS

def save_settings(settings):
    try:
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")

# Global Config Object (Singleton-ish)
SETTINGS = load_settings()

# STAGING_DIR configuration (Dynamic for Security Level 2)
if SETTINGS.get("custom_staging_path", "").strip():
    STAGING_DIR = Path(SETTINGS["custom_staging_path"].strip())
else:
    STAGING_DIR = BASE_DIR / "staging_pazienti"

# Ensure directories exist
OUTPUT_DIR.mkdir(exist_ok=True)
MODELS_DIR.mkdir(exist_ok=True)

try:
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
except PermissionError:
    # Fallback to local if custom path is totally inaccessible
    STAGING_DIR = BASE_DIR / "staging_pazienti"
    STAGING_DIR.mkdir(parents=True, exist_ok=True)
