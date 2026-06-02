
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
class InMemoryLogHandler(logging.Handler):
    def __init__(self, capacity=200):
        super().__init__()
        self.capacity = capacity
        self.buffer = []

    def emit(self, record):
        try:
            log_entry = self.format(record)
            self.buffer.append(log_entry)
            if len(self.buffer) > self.capacity:
                self.buffer.pop(0)
        except Exception:
            self.handleError(record)

    def get_logs(self):
        return "\n".join(self.buffer)

log_capture_handler = InMemoryLogHandler()
log_capture_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
log_capture_handler.setLevel(logging.INFO)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MedicalRedactor")
logger.addHandler(log_capture_handler)


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
    
    # 1. Clean up STAGING_DIR contents
    from config import STAGING_DIR
    import stat
    
    def remove_readonly(func, path, _):
        try:
            os.chmod(path, stat.S_IWRITE)
            func(path)
        except Exception as e:
            logger.error(f"Failed to change permissions for {path}: {e}")

    if STAGING_DIR.exists():
        logger.info(f"Wiping staging directory: {STAGING_DIR}")
        try:
            for item in STAGING_DIR.iterdir():
                if item.is_dir():
                    if item.name not in [".", "..", "System Volume Information"] and not item.name.startswith('$'):
                        try:
                            shutil.rmtree(item, onerror=remove_readonly)
                        except Exception as e:
                            logger.error(f"Error deleting directory {item}: {e}")
                elif item.is_file():
                    try:
                        secure_delete_file(item)
                    except Exception as e:
                        logger.error(f"Error deleting file {item}: {e}")
            logger.info("Staging directory contents wiped.")
        except Exception as e:
            logger.error(f"Error reading/wiping staging directory {STAGING_DIR}: {e}")
            
    # 2. Clean temporary directory
    temp_dir = BASE_DIR / "tmp"
    if temp_dir.exists():
        try:
            shutil.rmtree(temp_dir, onerror=remove_readonly)
            logger.info("Temporary directory wiped.")
        except Exception as e:
            logger.error(f"Error wiping temp dir: {e}")


def get_readable_size(size_in_bytes):
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.2f} TB"


def run_diagnostic_tests():
    """
    Runs a series of advanced diagnostic tests to identify problems
    with I/O, disk space, AI libraries, and Hugging Face connectivity.
    """
    results = {}
    
    # 1. Verify Staging Folder (Write/Read/Delete)
    from config import STAGING_DIR
    try:
        STAGING_DIR.mkdir(parents=True, exist_ok=True)
        test_file = STAGING_DIR / ".diag_write_test"
        with open(test_file, "w", encoding="utf-8") as f:
            f.write("test")
        
        # Read test
        with open(test_file, "r", encoding="utf-8") as f:
            content = f.read()
            
        if content == "test":
            results["staging_io"] = {"status": "SUCCESS", "message": f"Staging folder writable/readable in `{STAGING_DIR}`"}
        else:
            results["staging_io"] = {"status": "ERROR", "message": "Write test in Staging folder returned corrupted data."}
            
        # Delete test
        test_file.unlink()
    except Exception as e:
        results["staging_io"] = {"status": "ERROR", "message": f"I/O error in Staging folder: {e}"}
        
    # 2. Disk Space (Staging & USB)
    try:
        import shutil
        total, used, free = shutil.disk_usage(STAGING_DIR)
        free_gb = free / (1024**3)
        if free_gb < 1.0:
            results["disk_space"] = {"status": "WARNING", "message": f"Insufficient free space ({free_gb:.2f} GB). Requires at least 1.0 GB."}
        else:
            results["disk_space"] = {"status": "SUCCESS", "message": f"Sufficient disk space ({free_gb:.2f} GB free)"}
    except Exception as e:
        results["disk_space"] = {"status": "UNKNOWN", "message": f"Cannot verify disk space: {e}"}
        
    # 3. AI Engine Availability (PyTorch & GLiNER)
    try:
        import importlib.util
        torch_spec = importlib.util.find_spec("torch")
        gliner_spec = importlib.util.find_spec("gliner")
        
        if torch_spec is not None and gliner_spec is not None:
            # Check actual import without loading models
            import torch
            from gliner import GLiNER
            device = "cuda" if torch.cuda.is_available() else "cpu"
            results["ai_libraries"] = {"status": "SUCCESS", "message": f"PyTorch and GLiNER ready for loading. Device: {device.upper()}"}
        else:
            results["ai_libraries"] = {"status": "WARNING", "message": "AI libraries (PyTorch/GLiNER) not found in the environment. The app will run in manual-only mode."}
    except Exception as e:
        results["ai_libraries"] = {"status": "ERROR", "message": f"Error loading AI libraries: {e}"}
        
    # 4. Hugging Face Connectivity (Short timeout to prevent blocking)
    try:
        import urllib.request
        # Test connection to HF hub with 2s timeout
        urllib.request.urlopen("https://huggingface.co", timeout=2.0)
        results["hf_connection"] = {"status": "SUCCESS", "message": "Hugging Face Hub reachable (Online mode supported)"}
    except Exception:
        results["hf_connection"] = {"status": "WARNING", "message": "Hugging Face unreachable (The app will use locally cached models only)"}
        
    # 5. System RAM
    try:
        import psutil
        ram = psutil.virtual_memory()
        free_ram_gb = ram.available / (1024**3)
        if free_ram_gb < 2.0:
            results["system_ram"] = {"status": "WARNING", "message": f"Limited available RAM ({free_ram_gb:.2f} GB free). Risk of slowdown with heavy models."}
        else:
            results["system_ram"] = {"status": "SUCCESS", "message": f"Sufficient system RAM ({free_ram_gb:.2f} GB free)"}
    except ImportError:
        results["system_ram"] = {"status": "UNKNOWN", "message": "psutil module not installed. Unable to estimate free RAM."}
    except Exception as e:
        results["system_ram"] = {"status": "UNKNOWN", "message": f"Error reading RAM: {e}"}
        
    return results
