
import uuid
import re
from pathlib import Path

def generate_patient_uuid():
    """Generates an 8-character uppercase hex UUID."""
    return uuid.uuid4().hex[:8].upper()

def get_patient_folder_name(synthetic_id):
    """Returns the root folder name for a patient."""
    return f"Paziente_{synthetic_id}"

def get_category_folder_name(category, synthetic_id):
    """Maps the internal category to the final folder name."""
    # Replace sequences of non-alphanumeric chars with a single underscore
    clean_cat = re.sub(r'[^A-Z0-9]+', '_', category.upper()).strip('_')
    return f"{clean_cat}_{synthetic_id}"

def get_output_filename(category, synthetic_id, original_filename, file_index=None):
    """
    Constructs the final filename. 
    Pattern: CATEGORY_ID_original.pdf or CATEGORY_ID_N_original.pdf
    """
    # Strip extension from original
    p = Path(original_filename)
    stem = p.stem
    ext = p.suffix
    
    clean_cat = re.sub(r'[^A-Z_]', '', category.upper())
    
    if file_index is not None:
        return f"{clean_cat}_{synthetic_id}_{file_index}_{stem}{ext}"
    return f"{clean_cat}_{synthetic_id}_{stem}{ext}"

def get_full_output_path(base_output_dir, category, synthetic_id, original_filename, file_index=None):
    """Returns the full Path object for the redacted file."""
    root_folder = get_patient_folder_name(synthetic_id)
    cat_folder = get_category_folder_name(category, synthetic_id)
    filename = get_output_filename(category, synthetic_id, original_filename, file_index)
    
    return Path(base_output_dir) / root_folder / cat_folder / filename
