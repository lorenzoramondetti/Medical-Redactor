
import os
import shutil
import logging
from pathlib import Path
import os
import shutil
import logging
from pathlib import Path
from config import BASE_DIR

# Configure Logging to console only (Zero-Trace on disk unless debug requested)
# In a real scenario, we might want a log file in a temp dir on the USB, 
# but for maximum privacy, we keep it in memory/console.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MedicalRedactor")

def secure_delete_file(path: Path):
    """
    Overwrites file with zeros before deleting to prevent recovery.
    Note: SSD wear leveling makes this imperfect, but it's better than standard delete.
    """
    if not path.exists():
        return
    try:
        # Pass 1: Overwrite with zeros (simple wipe for speed on USB)
        # For higher security, multiple passes would be needed, but might arguably wear out USBs.
        with open(path, "wb") as f:
            f.write(b'\0' * path.stat().st_size)
        
        path.unlink()
        logger.info(f"Securely deleted: {path.name}")
    except Exception as e:
        logger.error(f"Failed to secure delete {path}: {e}")

def cleanup_session_traces():
    """
    Call this on application exit to clean up temp files.
    """
    logger.info("Starting session cleanup...")
    
    # Example: Clean Streamlit temp files if we can locate them and they are custom
    # Typically streamlit manages its own cache, but we can try to clear known temp dirs
    # if we configured them to be local.
    
    # In this portable setup, if we redirect temp folders to a 'tmp' dir in BASE_DIR,
    # we would wipe that here.
    temp_dir = BASE_DIR / "tmp"
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir) # Recursive delete
            logger.info("Temporary directory wiped.")
        except Exception as e:
            logger.error(f"Error wiping temp dir: {e}")

def get_readable_size(size_in_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"
