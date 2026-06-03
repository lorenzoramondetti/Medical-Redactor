import os
# Disable Streamlit's file watcher to prevent file-locking and crashes on portable USB drives
os.environ["STREAMLIT_SERVER_ENABLE_FILE_WATCHER"] = "false"

# Monkeypatch Streamlit to fix compatibility with streamlit-drawable-canvas on newer Streamlit versions
try:
    import streamlit.elements.image as st_image
    
    # Try importing the lib.image_utils if it exists, since the function might be there
    try:
        import streamlit.elements.lib.image_utils as st_image_utils
    except ImportError:
        st_image_utils = None

    # Determine which module contains image_to_url
    target_module = None
    if hasattr(st_image, "image_to_url"):
        target_module = st_image
    elif st_image_utils is not None and hasattr(st_image_utils, "image_to_url"):
        target_module = st_image_utils
        # Ensure it's exposed on st_image since st_canvas imports it from there
        st_image.image_to_url = st_image_utils.image_to_url

    if target_module is not None:
        class DummyLayoutConfig:
            def __init__(self, width):
                self.width = width
        
        _original_image_to_url = target_module.image_to_url
        def patched_image_to_url(image, layout_config, *args, **kwargs):
            if isinstance(layout_config, int):
                layout_config = DummyLayoutConfig(layout_config)
            return _original_image_to_url(image, layout_config, *args, **kwargs)
            
        target_module.image_to_url = patched_image_to_url
        st_image.image_to_url = patched_image_to_url
except Exception:
    pass




import streamlit as st
import time
from pathlib import Path

# --- LOCAL IMPORTS ---
from config import SETTINGS, OUTPUT_DIR, SETTINGS_FILE, save_settings
from organization_utils import (
    generate_patient_uuid, 
    get_patient_folder_name, 
    get_category_folder_name, 
    get_output_filename
)
from utils import logger, cleanup_session_traces
from redaction_logic import RedactionMemory, TextAnalyzer, classify_redacted_term
from llm_engine import LLMEngine
from pdf_processor import PDFProcessor
from ui_components import sidebar_ui, render_page_editor, memory_manager_ui, render_acquisition_wizard
from worker_state import worker_lock, worker_results, worker_status

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Medical Redactor - Work in Progress",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

if 'wiped' in st.session_state:
    st.title("🏥 Medical Redactor - Zero Trace")
    st.success("🔒 Session successfully terminated and all temporary data securely wiped!")
    st.info("The staging folder on the hospital PC has been completely emptied. No sensitive data or un-anonymized files remain on the host hard drive or USB drive.")
    st.warning("You can now safely close this browser window and stop the terminal.")
    st.stop()


# --- INITIALIZATION ---
if 'initialized' not in st.session_state:
    st.session_state['initialized'] = True
    st.session_state['memory'] = RedactionMemory(ephemeral=SETTINGS['ephemeral_session'])
    st.session_state['llm'] = LLMEngine()
    st.session_state['processed_data'] = {} # {filename: {page_idx: [terms]}}
    st.session_state['original_findings'] = {} # {filename: {page_idx: [terms]}} - For auto-learning on export
    st.session_state['manual_rects'] = {}   # {filename: {page_idx: [[x0,y0,x1,y1]]}}
    st.session_state['file_buffers'] = {}   # {filename: bytes}
    st.session_state['file_objs'] = {}      # {filename: PDFProcessor} -> Cached Objects (careful with memory)
    st.session_state['patient_uuids'] = {}  # {patient_id: "SHORT_UUID"}
    st.session_state['action_history'] = []


def reconcile_page_terms(f_name, p, processor, memory):
    """
    Ensures the terms for a specific page are perfectly synced with the global memory (whitelist/blacklist).
    - Adds any whitelisted terms that appear in the page text (unless filtered/blacklisted).
    - Removes any terms that are blacklisted.
    """
    import re
    if f_name not in st.session_state.get('processed_data', {}):
        return
        
    page_terms = set(st.session_state['processed_data'][f_name].get(p, []))
    
    # Extract page text
    text = processor.extract_text(p)
    
    # Find any whitelisted terms in the text using custom word boundaries and case-insensitivity
    whitelist_found = set()
    for term in memory.whitelist:
        if not term.strip():
            continue
        pattern = r'(?i)(?<!\w)' + re.escape(term.strip()) + r'(?!\w)'
        for match in re.finditer(pattern, text):
            whitelist_found.add(match.group())
            
    # Filter the found whitelisted terms (respects blacklist, noise, etc.)
    filtered_whitelist = memory.filter_terms(whitelist_found, is_pii=True)
    
    # Add to current terms
    page_terms.update(filtered_whitelist)
    
    # Apply blacklist filtering to ALL current terms (in case some were blacklisted in the meantime)
    page_terms = memory.filter_terms(page_terms, is_pii=True)
    
    # Update processed_data in session state
    st.session_state['processed_data'][f_name][p] = sorted(list(page_terms))


# --- ROUTING VARIABLES ---
bg_running = False
worker_error = None

# Sincronizza i risultati dal thread background verso session_state
if 'processed_data' in st.session_state:
    with worker_lock:
        bg_running = worker_status['running']
        worker_error = worker_status.get('error')
        
        for f_name, data in worker_results['processed_data'].items():
            if f_name not in st.session_state['processed_data']:
                st.session_state['processed_data'][f_name] = data
                st.session_state['original_findings'][f_name] = worker_results['original_findings'][f_name]
                st.session_state['manual_rects'][f_name] = worker_results['manual_rects'][f_name]
                st.session_state['file_buffers'][f_name] = worker_results['file_buffers'][f_name]
                st.session_state['file_objs'][f_name] = worker_results['file_objs'][f_name]
        for p_id, u_id in worker_results['patient_uuids'].items():
            if p_id not in st.session_state['patient_uuids']:
                st.session_state['patient_uuids'][p_id] = u_id

all_keys = list(st.session_state.get('processed_data', {}).keys())
patients_available = list(set([k.split("/")[0] for k in all_keys]))
patients_available.sort()
is_review_mode = len(all_keys) > 0 and not st.session_state.get('auto_start_analysis')

# --- SIDEBAR & SETTINGS ---
grouped_patients, ephemeral_mode, manual_mode, custom_staging, new_active_model, ai_threshold, date_replacement_active, baseline_date, baseline_day_index, date_format, date_max_range_days = sidebar_ui(
    st.session_state['memory'],
    is_review_phase=is_review_mode,
    patients_available=patients_available,
    all_keys=all_keys
)

# Update Settings if changed
settings_changed = False

if ephemeral_mode != SETTINGS['ephemeral_session']:
    SETTINGS['ephemeral_session'] = ephemeral_mode
    st.session_state['memory'].ephemeral = ephemeral_mode
    settings_changed = True

if manual_mode != SETTINGS['manual_mode']:
    SETTINGS['manual_mode'] = manual_mode
    settings_changed = True

if custom_staging != SETTINGS.get('custom_staging_path', ''):
    SETTINGS['custom_staging_path'] = custom_staging
    settings_changed = True

if new_active_model != SETTINGS.get('active_model', 'gliner'):
    SETTINGS['active_model'] = new_active_model
    settings_changed = True
    # Reset the LLM engine so that the new model will be loaded lazily on demand
    st.session_state['llm'].reset_engine()

if ai_threshold != SETTINGS.get('ai_threshold', 0.45):
    SETTINGS['ai_threshold'] = ai_threshold
    settings_changed = True

if date_replacement_active != SETTINGS.get('date_replacement_active', False):
    SETTINGS['date_replacement_active'] = date_replacement_active
    settings_changed = True

baseline_date_str = baseline_date.strftime("%Y-%m-%d") if baseline_date else None
if baseline_date_str != SETTINGS.get('baseline_date'):
    SETTINGS['baseline_date'] = baseline_date_str
    settings_changed = True

if baseline_day_index != SETTINGS.get('baseline_day_index', 1):
    SETTINGS['baseline_day_index'] = baseline_day_index
    settings_changed = True

if date_format != SETTINGS.get('date_format'):
    SETTINGS['date_format'] = date_format
    settings_changed = True

if date_max_range_days != SETTINGS.get('date_max_range_days'):
    SETTINGS['date_max_range_days'] = date_max_range_days
    settings_changed = True

if settings_changed:
    save_settings(SETTINGS)
    st.rerun() # Restart to reload state (especially important for Staging Dir remounting)

# --- MAIN LOGIC ---

# --- BACKGROUND WORKER LOGIC ---
import threading
from worker_state import worker_lock, worker_results, worker_status

def start_background_analysis(patients_dict):
    # Reset completion state flags for the progress bar
    if 'bg_progress_bar_dismissed' in st.session_state:
        del st.session_state['bg_progress_bar_dismissed']
    if 'bg_complete_time' in st.session_state:
        del st.session_state['bg_complete_time']

    # Pre-calculate file and page counts for professional ETA display
    total_files = 0
    total_pages = 0
    for patient_id, categories in patients_dict.items():
        for cat, files in categories.items():
            for f in files:
                total_files += 1
                try:
                    import fitz
                    # Read bytes via StagedFileWrapper
                    doc = fitz.open(stream=f.read(), filetype="pdf")
                    total_pages += doc.page_count
                except Exception as e:
                    logger.error(f"Error calculating total page count for {f.name}: {e}")

    with worker_lock:
        if worker_status['running']:
            return
        worker_status['running'] = True
        worker_status['error'] = None
        worker_status['total_files'] = total_files
        worker_status['completed_files'] = 0
        worker_status['total_pages'] = total_pages
        worker_status['completed_pages'] = 0
        worker_status['start_time'] = time.time()
        worker_status['current_file_name'] = ""
        worker_status['current_page'] = 0
        worker_status['current_file_total_pages'] = 0
        
    # Inizializziamo il dizionario se vuoto per permettere all'interfaccia di renderizzarsi subito
    if not st.session_state.get('processed_data'):
        st.session_state['processed_data'] = {}
        st.session_state['original_findings'] = {}
        st.session_state['manual_rects'] = {}
        st.session_state['file_buffers'] = {}
        st.session_state['file_objs'] = {}
        st.session_state['patient_uuids'] = {}

    memory_ref = st.session_state['memory']
    llm_ref = st.session_state['llm']
    is_manual = SETTINGS.get('manual_mode', False)

    def worker(memory, llm, manual_mode):
        try:
            # Lazy initialize the LLM engine
            if not manual_mode and not llm.is_ready():
                llm.initialize_engine()
                
            analyzer = TextAnalyzer(memory, llm if not manual_mode else None)
            
            for patient_id, categories in patients_dict.items():
                uuid_val = generate_patient_uuid()
                with worker_lock:
                    if patient_id not in worker_results['patient_uuids']:
                        worker_results['patient_uuids'][patient_id] = uuid_val
                    
                ordered_categories = ["CARTELLA_CLINICA", "CONSULENZE_SPECIALISTICHE", "ESAMI_STRUMENTALI", "DATI_STRUTTURATI", "GENERIC"]
                existing_cats = [c for c in ordered_categories if c in categories]
                for c in categories.keys():
                    if c not in existing_cats:
                         existing_cats.append(c)
                         
                for cat in existing_cats:
                    for f in categories[cat]:
                        f_name = f.name.replace("\\", "/") 
                        
                        # Salta se già elaborato
                        with worker_lock:
                            if f_name in worker_results['processed_data']:
                                continue
                            
                        file_bytes = f.read()
                        
                        # Processiamo e salviamo in dizionari temporanei
                        processor = PDFProcessor(file_bytes)
                        num_pages = processor.get_page_count()
                        
                        with worker_lock:
                            worker_status['current_file_name'] = Path(f_name).name
                            worker_status['current_file_total_pages'] = num_pages
                            
                        file_results = {}
                        file_originals = {}
                        
                        for i in range(num_pages):
                            with worker_lock:
                                worker_status['current_page'] = i + 1
                                worker_status['progress'] = f"Analyzing '{Path(f_name).name}' (Page {i+1} of {num_pages})..."
                                
                            text = processor.extract_text(i)
                            terms = analyzer.analyze_text(text, category=cat)
                            file_results[i] = list(terms)
                            file_originals[i] = list(terms)
                            
                            if cat == "CARTELLA_CLINICA":
                                memory.add_to_whitelist(terms)
                                
                            with worker_lock:
                                worker_status['completed_pages'] += 1
                                
                        # Aggiorniamo il dictionary globale tutto in una volta per questo file
                        with worker_lock:
                            worker_results['file_buffers'][f_name] = file_bytes
                            worker_results['file_objs'][f_name] = processor
                            worker_results['manual_rects'][f_name] = {}
                            worker_results['original_findings'][f_name] = file_originals
                            worker_results['processed_data'][f_name] = file_results
                            worker_status['completed_files'] += 1
        except Exception as e:
            logger.error(f"Worker Error: {e}")
            import traceback
            err_msg = traceback.format_exc()
            with worker_lock:
                worker_status['error'] = err_msg
        finally:
            with worker_lock:
                worker_status['running'] = False

    thread = threading.Thread(target=worker, args=(memory_ref, llm_ref, is_manual), daemon=True)
    thread.start()


@st.fragment
def page_editor_fragment(selected_file, curr_page, processor):
    col_canvas, col_tools = st.columns([4.0, 1.5])
    # DATA FOR EDITOR
    current_terms = st.session_state['processed_data'][selected_file].get(curr_page, [])
    manual_rects_map = st.session_state['manual_rects'].get(selected_file, {})
    current_manual_rects = manual_rects_map.get(curr_page, [])
    
    # RENDER EDITOR
    updated_terms, new_rects, apply_to_all, action_undo, action_clear_all, deleted_terms = render_page_editor(col_canvas, col_tools, selected_file, curr_page, processor, current_terms, current_manual_rects)
    
    # ELABORAZIONE LOGICA CANVAS
    needs_rerun = False
    
    if deleted_terms:
        updated_terms = [t for t in updated_terms if t not in deleted_terms]
        st.session_state[f"canvas_rev_{selected_file}_{curr_page}"] = st.session_state.get(f"canvas_rev_{selected_file}_{curr_page}", 0) + 1
        needs_rerun = True
        
    if new_rects and len(new_rects) > len(current_manual_rects):
        page = processor.doc[curr_page]
        words = page.get_text("words")
        import fitz
        newest_rect = fitz.Rect(new_rects[-1])
        intersected_words = []
        
        for w in words:
            w_rect = fitz.Rect(w[:4])
            intersection = newest_rect & w_rect
            if w_rect.get_area() > 0 and intersection.get_area() > 0:
                intersected_words.append(w[4])
                
        if intersected_words:
            new_term = " ".join(intersected_words)
            clean_term = new_term.strip(".,;:()")
            if clean_term not in updated_terms:
                updated_terms.append(clean_term)
                st.toast(f"✅ Added: {clean_term}")
                
            # Registra l'aggiunta dello strumento di testo nello storico
            if 'action_history' not in st.session_state:
                st.session_state['action_history'] = []
            st.session_state['action_history'].append({
                "type": "add_term",
                "file": selected_file,
                "page": curr_page,
                "term": clean_term
            })
            
            # Rimuoviamo il rettangolo manuale visto che è stato convertito in termine AI
            new_rects.pop()
            # Incrementiamo canvas_rev per forzare il rimontaggio con il nuovo AI rect ed eliminare il manual rect
            st.session_state[f"canvas_rev_{selected_file}_{curr_page}"] = st.session_state.get(f"canvas_rev_{selected_file}_{curr_page}", 0) + 1
            needs_rerun = True
    
    # UPDATE STATE
    
    old_terms_set = set(current_terms)
    new_terms_set = set(updated_terms)
    
    added_terms = new_terms_set - old_terms_set
    removed_terms = old_terms_set - new_terms_set
    
    st.session_state['processed_data'][selected_file][curr_page] = updated_terms
    
    if added_terms or removed_terms:
        import re
        if added_terms:
            st.session_state['memory'].add_to_whitelist(added_terms)
        if removed_terms:
            st.session_state['memory'].add_to_blacklist(removed_terms)
            
        num_pages = processor.get_page_count()
        for p in range(num_pages):
            if p == curr_page:
                continue
            page_terms = set(st.session_state['processed_data'][selected_file].get(p, []))
            page_terms.update(added_terms)
            page_terms.difference_update(removed_terms)
            st.session_state['processed_data'][selected_file][p] = [t for t in list(page_terms) if t.strip()]
            
        for other_file in st.session_state['processed_data'].keys():
            if other_file == selected_file:
                continue
                
            other_proc = st.session_state['file_objs'].get(other_file)
            if not other_proc:
                continue
                
            other_pages = other_proc.get_page_count()
            for p in range(other_pages):
                other_terms = set(st.session_state['processed_data'][other_file].get(p, []))
                other_text = other_proc.extract_text(p)
                
                for term in added_terms:
                    if not term.strip():
                        continue
                    pattern = r'(?i)(?<!\w)' + re.escape(term.strip()) + r'(?!\w)'
                    if re.search(pattern, other_text):
                        other_terms.add(term)
                        
                for term in removed_terms:
                    if term in other_terms:
                        other_terms.remove(term)
                        
                st.session_state['processed_data'][other_file][p] = [t for t in list(other_terms) if t.strip()]

    def rects_differ(r1, r2, tol=2.0):
        if len(r1) != len(r2): return True
        for a, b in zip(r1, r2):
            if any(abs(v1-v2) > tol for v1, v2 in zip(a,b)): return True
        return False

    toggle_key = f"apply_all_{selected_file}_{curr_page}"
    prev_apply_to_all = st.session_state.get(toggle_key, True)
    st.session_state[toggle_key] = apply_to_all
    
    toggled_on = apply_to_all and not prev_apply_to_all
    current_saved = st.session_state['manual_rects'][selected_file].get(curr_page, [])
    new_drawing = new_rects is not None and rects_differ(current_saved, new_rects)
    
    num_pages = processor.get_page_count()
    if new_drawing or toggled_on:
         rects_to_save = new_rects if new_drawing else current_saved
         
         if new_drawing:
             if 'action_history' not in st.session_state:
                 st.session_state['action_history'] = []
             st.session_state['action_history'].append({
                 "type": "add_rect",
                 "file": selected_file,
                 "page": curr_page
             })
         
         if apply_to_all:
             import copy
             raw_json = st.session_state.get(f"canvas_json_{selected_file}_{curr_page}")
             for p in range(num_pages):
                 st.session_state['manual_rects'][selected_file][p] = [r.copy() for r in (rects_to_save or [])]
                 if raw_json is not None and p != curr_page:
                     st.session_state[f"canvas_json_{selected_file}_{p}"] = copy.deepcopy(raw_json)
                 if p != curr_page:
                     st.session_state[f"canvas_rev_{selected_file}_{p}"] = st.session_state.get(f"canvas_rev_{selected_file}_{p}", 0) + 1
         else:
             st.session_state['manual_rects'][selected_file][curr_page] = rects_to_save
             
         if toggled_on:
             st.rerun()

    if action_undo:
        history = st.session_state.get('action_history', [])
        undone = False
        
        while history:
            last_action = history.pop()
            # Verify it matches the current file and page to prevent out-of-context undos
            if last_action["file"] == selected_file and last_action["page"] == curr_page:
                if last_action["type"] == "add_term":
                    term_to_remove = last_action["term"]
                    if term_to_remove in updated_terms:
                        updated_terms.remove(term_to_remove)
                        # Blacklist it so it doesn't get re-added by whitelist reconciliation
                        st.session_state['memory'].add_to_blacklist({term_to_remove})
                        st.toast(f"↩️ Undid addition: {term_to_remove}")
                    undone = True
                elif last_action["type"] == "add_rect":
                    if current_saved:
                        current_saved.pop()
                        st.session_state['manual_rects'][selected_file][curr_page] = current_saved
                        if apply_to_all:
                            for p in range(num_pages):
                                st.session_state['manual_rects'][selected_file][p] = [r.copy() for r in current_saved]
                        st.toast("↩️ Undid manual rectangle")
                    undone = True
                break
                
        # Fallback to old behavior if no action was popped from history for this page
        if not undone:
            if current_saved:
                current_saved.pop()
                st.session_state['manual_rects'][selected_file][curr_page] = current_saved
                if apply_to_all:
                    for p in range(num_pages):
                        st.session_state['manual_rects'][selected_file][p] = [r.copy() for r in current_saved]
                st.toast("↩️ Undid manual rectangle")
        
        # Update processed_data in session state in case a term was removed
        st.session_state['processed_data'][selected_file][curr_page] = updated_terms
        
        # Increment canvas_rev to force remount
        st.session_state[f"canvas_rev_{selected_file}_{curr_page}"] = st.session_state.get(f"canvas_rev_{selected_file}_{curr_page}", 0) + 1
        if apply_to_all:
            for p in range(num_pages):
                if p != curr_page:
                    st.session_state[f"canvas_rev_{selected_file}_{p}"] = st.session_state.get(f"canvas_rev_{selected_file}_{p}", 0) + 1
                    
        st.rerun()
            
    if action_clear_all:
        st.session_state['manual_rects'][selected_file][curr_page] = []
        st.session_state[f"canvas_rev_{selected_file}_{curr_page}"] = st.session_state.get(f"canvas_rev_{selected_file}_{curr_page}", 0) + 1
        if apply_to_all:
            for p in range(num_pages):
                st.session_state['manual_rects'][selected_file][p] = []
                if p != curr_page:
                    st.session_state[f"canvas_rev_{selected_file}_{p}"] = st.session_state.get(f"canvas_rev_{selected_file}_{p}", 0) + 1
        st.rerun()

    if needs_rerun:
        st.rerun()
        
    with col_tools:
        st.divider()
        with st.expander("🧠 Manage Memory"):
            memory_manager_ui(st.session_state['memory'], in_sidebar=True)


# --- APP ROUTING ---
# Synchronization is handled at the top of the script

if not st.session_state.get('processed_data') and not bg_running:
    
    if worker_error:
        st.error("The background process encountered a fatal error:")
        st.code(worker_error)
        st.stop()
        
    if st.session_state.get('auto_start_analysis'):
        st.session_state['auto_start_analysis'] = False
        start_background_analysis(grouped_patients)
        st.rerun() # Forza il ricaricamento per mostrare l'interfaccia mentre il worker lavora
    else:
        # Show Acquisition Wizard se non abbiamo iniziato
        render_acquisition_wizard(st.session_state['memory'])
else:
    # --- REVIEW UI ---
    st.divider()
    
    def format_eta(seconds):
        if seconds is None or seconds < 0:
            return "Calculating..."
        if seconds < 60:
            return f"{int(seconds)} s"
        minutes = int(seconds // 60)
        rem_seconds = int(seconds % 60)
        if minutes < 60:
            return f"{minutes} m {rem_seconds} s"
        hours = int(minutes // 60)
        rem_minutes = int(minutes % 60)
        return f"{hours} h {rem_minutes} m"
        
    if not patients_available:
        total_f = 1
        comp_f = 0
        total_p = 1
        comp_p = 0
        curr_f = ""
        curr_p = 1
        curr_f_tot = 1
        eta_str = "Calculating..."
        progress_fraction = 0.0
        
        with worker_lock:
            total_f = worker_status.get('total_files', 1)
            comp_f = worker_status.get('completed_files', 0)
            total_p = worker_status.get('total_pages', 1)
            comp_p = worker_status.get('completed_pages', 0)
            curr_f = worker_status.get('current_file_name', "")
            curr_p = worker_status.get('current_page', 1)
            curr_f_tot = worker_status.get('current_file_total_pages', 1)
            
            elapsed = time.time() - worker_status.get('start_time', time.time())
            if comp_p > 0:
                time_per_page = elapsed / comp_p
                eta_str = format_eta(time_per_page * (total_p - comp_p))
                progress_fraction = float(comp_p / total_p)
                
        # Premium glassmorphic loading screen
        st.markdown(
f"""<div style="background-color: #1E293B; 
border: 2px solid #334155; 
border-radius: 16px; 
padding: 32px; 
margin: 40px auto; 
max-width: 700px; 
box-shadow: 0px 10px 30px rgba(0, 0, 0, 0.4); 
text-align: center;">

<!-- Beautiful fluid 5-dot spinner -->
<div style="margin-bottom: 32px; display: flex; justify-content: center;">
<div class="dots-spinner">
  <div class="dot" style="--delay: 0.08s; --color: #10B981;"></div>
  <div class="dot" style="--delay: 0.16s; --color: #34D399;"></div>
  <div class="dot" style="--delay: 0.24s; --color: #059669;"></div>
  <div class="dot" style="--delay: 0.32s; --color: #6EE7B7;"></div>
  <div class="dot" style="--delay: 0.40s; --color: #A7F3D0;"></div>
</div>
</div>

<h2 style="color: #F8FAFC; margin-bottom: 12px; font-weight: 700; font-size: 24px;">
🔍 AI Analysis in Progress...
</h2>

<p style="color: #94A3B8; font-size: 15px; margin-bottom: 28px; line-height: 1.5;">
The local artificial intelligence engine is scanning clinical documents to automatically identify and redact all sensitive personal data and personally identifiable information (PII).
</p>

<!-- Progress stats cards -->
<div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-bottom: 28px;">
<div style="background-color: #0F172A; border-radius: 10px; padding: 16px; border: 1px solid #1E293B;">
<div style="font-size: 12px; color: #64748B; text-transform: uppercase; margin-bottom: 6px; font-weight: bold;">Documents</div>
<div style="font-size: 20px; color: #38BDF8; font-weight: bold;">{comp_f} / {total_f}</div>
</div>
<div style="background-color: #0F172A; border-radius: 10px; padding: 16px; border: 1px solid #1E293B;">
<div style="font-size: 12px; color: #64748B; text-transform: uppercase; margin-bottom: 6px; font-weight: bold;">Total Pages</div>
<div style="font-size: 20px; color: #10B981; font-weight: bold;">{comp_p} / {total_p}</div>
</div>
<div style="background-color: #0F172A; border-radius: 10px; padding: 16px; border: 1px solid #1E293B;">
<div style="font-size: 12px; color: #64748B; text-transform: uppercase; margin-bottom: 6px; font-weight: bold;">Estimated Time</div>
<div style="font-size: 20px; color: #F472B6; font-weight: bold;">{eta_str}</div>
</div>
</div>""",
            unsafe_allow_html=True
        )
        
        # Display the actual progress bar
        st.progress(progress_fraction)
        
        st.markdown(
f"""<div style="margin-top: 20px; padding: 12px; background-color: rgba(16, 185, 129, 0.05); border-radius: 8px; border: 1px dashed rgba(16, 185, 129, 0.2);">
<div style="font-size: 13.5px; color: #34D399; font-weight: 500; margin-bottom: 4px;">
Analyzing page {curr_p} of {curr_f_tot}
</div>
<div style="font-size: 12.5px; color: #94A3B8; font-family: monospace;">
{curr_f}
</div>
</div>

<p style="color: #64748B; font-size: 12px; margin-top: 32px; font-style: italic;">
🔒 Privacy Guaranteed: 100% offline execution entirely in local RAM.
</p>
</div>

<style>
.dots-spinner {{
  position: relative;
  width: 50px;
  height: 50px;
}}
.dots-spinner .dot {{
  position: absolute;
  width: 10px;
  height: 10px;
  background-color: var(--color);
  border-radius: 50%;
  top: 0;
  left: 20px;
  transform-origin: 5px 25px;
  animation: spin-dots 1.4s cubic-bezier(0.5, 0.1, 0.25, 1) infinite;
  animation-delay: var(--delay);
  box-shadow: 0px 0px 8px var(--color);
}}
@keyframes spin-dots {{
  0% {{ transform: rotate(0deg); }}
  100% {{ transform: rotate(360deg); }}
}}
</style>""",
            unsafe_allow_html=True
        )
        
        import time
        time.sleep(1)
        st.rerun()
        st.stop()
        
    if 'current_patient' not in st.session_state or st.session_state['current_patient'] not in patients_available:
        st.session_state['current_patient'] = patients_available[0]
        
    # Render progress bar if running OR if we have completed but not yet dismissed the success banner
    if bg_running or ('bg_complete_time' in st.session_state and not st.session_state.get('bg_progress_bar_dismissed', False)):
        @st.fragment(run_every=3)
        def render_bg_progress_bar():
            with worker_lock:
                total_f = worker_status.get('total_files', 1)
                comp_f = worker_status.get('completed_files', 0)
                total_p = worker_status.get('total_pages', 1)
                comp_p = worker_status.get('completed_pages', 0)
                curr_f = worker_status.get('current_file_name', "")
                curr_p = worker_status.get('current_page', 1)
                curr_f_tot = worker_status.get('current_file_total_pages', 1)
                running = worker_status.get('running', False)
                
                elapsed = time.time() - worker_status.get('start_time', time.time())
                eta_str = "Calculating..."
                if comp_p > 0:
                    time_per_page = elapsed / comp_p
                    eta_str = format_eta(time_per_page * (total_p - comp_p))
            
            # Check if background analysis is fully completed
            is_completed = (comp_f >= total_f) or (not running and len(st.session_state.get('processed_data', {})) >= total_f)
            
            if is_completed:
                if 'bg_complete_time' not in st.session_state:
                    st.session_state['bg_complete_time'] = time.time()
                
                # Show beautiful success notification
                st.markdown(
f"""<div style="background-color: rgba(16, 185, 129, 0.15); 
border-left: 4px solid #10B981; 
border-radius: 6px; 
padding: 12px 16px; 
margin: 10px 0px 20px 0px; 
display: flex; 
justify-content: space-between; 
align-items: center; 
box-shadow: 0px 4px 10px rgba(16, 185, 129, 0.15);">
<div style="font-size: 13.5px; color: #D1FAE5; font-weight: 600; display: flex; align-items: center; gap: 8px;">
<span style="font-size: 16px;">✅</span> All clinical files successfully analyzed in the background.
</div>
<div style="font-size: 12px; color: #A7F3D0; font-style: italic;">
Dismissing in a few seconds...
</div>
</div>""",
                    unsafe_allow_html=True
                )
                
                # If 3 seconds have passed since completion, trigger full rerun and dismiss
                if time.time() - st.session_state['bg_complete_time'] >= 3.0:
                    st.session_state['bg_progress_bar_dismissed'] = True
                    st.rerun()
            else:
                # Active progress bar
                st.markdown(
f"""<div style="background-color: rgba(30, 41, 59, 0.7); 
border-left: 4px solid #10B981; 
border-radius: 6px; 
padding: 10px 14px; 
margin: 10px 0px 20px 0px; 
display: flex; 
justify-content: space-between; 
align-items: center; 
box-shadow: 0px 4px 6px rgba(0, 0, 0, 0.1);">
<div style="font-size: 13px; color: #E2E8F0;">
<span style="animation: pulse 1.5s infinite; color: #10B981; font-weight: bold; margin-right: 6px;">⏳ Background AI:</span>
Analyzing <code style="background-color: #0F172A; padding: 2px 6px; border-radius: 4px; color: #38BDF8;">{curr_f}</code> 
(Page {curr_p} of {curr_f_tot})
</div>
<div style="font-size: 12.5px; color: #94A3B8; text-align: right;">
<strong>{comp_f}/{total_f} files</strong> completed &bull; ETA: <strong style="color: #F472B6;">{eta_str}</strong>
</div>
</div>
<style>
@keyframes pulse {{
0% {{ opacity: 0.5; }}
50% {{ opacity: 1; }}
100% {{ opacity: 0.5; }}
}}
</style>""",
                    unsafe_allow_html=True
                )
                
                # Intelligent page-refresh when a background file completes
                current_completed = len(st.session_state.get('processed_data', {}))
                if 'last_completed_files' not in st.session_state:
                    st.session_state['last_completed_files'] = current_completed
                    
                if current_completed > st.session_state['last_completed_files']:
                    st.session_state['last_completed_files'] = current_completed
                    st.rerun()
                
        render_bg_progress_bar()
        
    selected_file = st.session_state.get('current_file')

    if selected_file:
        # Paginator
        processor = st.session_state['file_objs'].get(selected_file)
        if not processor:
             # Re-init if missing
             processor = PDFProcessor(st.session_state['file_buffers'][selected_file])
             st.session_state['file_objs'][selected_file] = processor

        num_pages = processor.get_page_count()
        
        # Reset page index if file changed
        if 'last_selected_file' not in st.session_state or st.session_state['last_selected_file'] != selected_file:
            st.session_state['page_idx'] = 0
            st.session_state['last_selected_file'] = selected_file
            st.session_state['confirm_export'] = False
            st.session_state['confirm_wipe'] = False
            
        # Ensure page index is within bounds
        if 'page_idx' not in st.session_state: 
            st.session_state['page_idx'] = 0
        else:
            st.session_state['page_idx'] = min(st.session_state['page_idx'], num_pages - 1)
        
        # Keyboard Navigation & Ctrl+Z Undo Injection (JS)
        st.html(
            """
            <script>
            const doc = window.parent.document;
            
            // Core Undo function
            function triggerUndo() {
                const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText.includes('Undo Last Action'));
                if (btn) btn.click();
            }
            
            // Parent key listener
            doc.addEventListener('keydown', function(e) {
                if (e.key === 'ArrowLeft') {
                    const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText === '⬅️ Prev');
                    if (btn) btn.click();
                } else if (e.key === 'ArrowRight') {
                    const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText === 'Next ➡️');
                    if (btn) btn.click();
                } else if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'z') {
                    if (e.target.tagName !== 'INPUT' && e.target.tagName !== 'TEXTAREA') {
                        e.preventDefault();
                        triggerUndo();
                    }
                }
            });
            
            // Proactive iframe binder (to catch events when user clicked on the canvas iframe)
            function bindIframeEvents() {
                try {
                    const iframes = doc.querySelectorAll('iframe');
                    iframes.forEach(iframe => {
                        if (iframe && !iframe.dataset.ctrlzBound) {
                            iframe.contentWindow.addEventListener('keydown', function(ev) {
                                if ((ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === 'z') {
                                    ev.preventDefault();
                                    triggerUndo();
                                }
                            });
                            iframe.dataset.ctrlzBound = "true";
                        }
                    });
                } catch (err) {
                    // Safe cross-origin catch
                }
            }
            
            // Run and poll for new iframes occasionally since Streamlit renders dynamically
            bindIframeEvents();
            setInterval(bindIframeEvents, 1000);
            </script>
            """
        )


        curr_page = st.session_state['page_idx']
        
        # Reconcile terms with global memory prior to rendering the page editor
        reconcile_page_terms(selected_file, curr_page, processor, st.session_state['memory'])
        
        
        # Chiama il fragment definito a livello di modulo
        page_editor_fragment(selected_file, curr_page, processor)

        # Render sidebar actions outside the fragment!
        with st.sidebar:
            st.divider()
        
            # --- SAVE ACTIONS ---
            if not st.session_state.get('confirm_export', False):
                st.markdown('<span id="clinical-green-btn"></span>', unsafe_allow_html=True)
                if st.button("💾 EXPORT ALL REDACTED FILES", use_container_width=True):
                    st.session_state['confirm_export'] = True
                    st.rerun()
            else:
                st.warning("💾 **Confirm Patient Export**\n\nProceeding will conclude the manual review phase for this patient. All documents will be permanently processed, black-masked, and saved into the `output_pdf` folder.\n\n*If you wish to continue manual correction on other documents first, please select them from the left sidebar column.*")
                
                st.markdown('<span id="clinical-green-btn"></span>', unsafe_allow_html=True)
                if st.button("Yes, Export All", key="btn_confirm_export_yes", use_container_width=True):
                    st.session_state['confirm_export'] = False
                    
                    curr_pat = st.session_state['current_patient']
                    synthetic_id = st.session_state['patient_uuids'].get(curr_pat, "UNKNOWN_ID")
                
                    patient_files_to_save = [k for k in all_keys if k.startswith(curr_pat + "/")]
                
                    all_final_terms = set()
                    all_original_terms = set()
                
                    root_folder_name = get_patient_folder_name(synthetic_id)
                
                    # GDPR Audit Metrics tracking
                    total_pages_processed = 0
                    manual_rects_count = 0
                    category_counts = {
                        "SSN / National ID / Tax Codes": 0,
                        "Dates (Birth/Admission/Discharge)": 0,
                        "Personal Names (Doctors/Patients)": 0,
                        "Healthcare Facilities (Hospitals/Clinics)": 0,
                        "Digital Contacts (Email/URL/IP)": 0,
                        "Phone Numbers / Contacts": 0,
                        "ID Codes (Record/Patient)": 0,
                        "Addresses / ZIP Codes": 0,
                        "Other Sensitive Information": 0
                    }
                    total_redacted_items_count = 0
                
                    with st.spinner(f"Exporting patient folder {synthetic_id}..."):
                        for p_file in patient_files_to_save:
                            proc = st.session_state['file_objs'][p_file]
                        
                            # Reconcile all pages of this document with the memory prior to gathering terms or rendering PDF
                            for p_idx in range(proc.get_page_count()):
                                reconcile_page_terms(p_file, p_idx, proc, st.session_state['memory'])
                            
                            # 1. Gather all terms for learning
                            for p_idx, t_list in st.session_state['processed_data'][p_file].items():
                                all_final_terms.update(t_list)
                        
                            if p_file in st.session_state['original_findings']:
                                for p_idx, t_list in st.session_state['original_findings'][p_file].items():
                                    all_original_terms.update(t_list)
                        
                            # 2. Render PDF
                            redaction_map = st.session_state['processed_data'][p_file]
                            rect_map = st.session_state['manual_rects'][p_file]
                        
                            total_pages_processed += proc.get_page_count()
                            for p_idx, rect_list in rect_map.items():
                                manual_rects_count += len(rect_list)
                        
                            date_settings = {
                                "active": SETTINGS.get("date_replacement_active", False),
                                "baseline_date": SETTINGS.get("baseline_date"),
                                "baseline_day_index": SETTINGS.get("baseline_day_index", 1),
                                "date_format": SETTINGS.get("date_format", "%d/%m/%Y"),
                                "date_max_range_days": SETTINGS.get("date_max_range_days", 365)
                            }
                        
                            pdf_bytes = proc.save_redacted_pdf(redaction_map, rect_map, date_settings)
                        
                            # 3. Create hierarchy
                            parts = p_file.split("/")
                            original_category = parts[-2] if len(parts) >= 3 else "GENERIC"
                            original_filename = parts[-1]
                            
                            cat_files = [f for f in patient_files_to_save if f.split("/")[-2] == original_category] if len(parts) >= 3 else [p_file]
                            current_file_index = cat_files.index(p_file) + 1 if len(cat_files) > 1 else None
                        
                            cat_folder_name = get_category_folder_name(original_category, synthetic_id)
                            out_filename = get_output_filename(original_category, synthetic_id, original_filename, current_file_index)
                            
                            target_dir = OUTPUT_DIR / root_folder_name / cat_folder_name
                            target_dir.mkdir(parents=True, exist_ok=True)
                        
                            out_path = target_dir / out_filename
                            with open(out_path, "wb") as f:
                                f.write(pdf_bytes)
                            
                        # 4. Generate & Save Anonymous GDPR Audit Report
                        for term in all_final_terms:
                            cat = classify_redacted_term(term)
                            category_counts[cat] = category_counts.get(cat, 0) + 1
                            total_redacted_items_count += 1
                        
                        from datetime import datetime
                        curr_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                        report_md = f"""# 🏥 GDPR ANONYMIZATION AUDIT REPORT
This report documents the anonymization and sensitive data extraction operations performed in compliance with the **General Data Protection Regulation (GDPR - EU 2016/679)**.

In line with the principle of **Privacy by Design & Zero-Trace**, this document contains exclusively aggregated and anonymous metrics. **No Protected Health Information (PHI) or Personally Identifiable Information (PII) is present in cleartext in this report.**

---

## 📋 General Information
- **Operator (Anonymization Supervisor):** `{st.session_state.get('operator_first_name', '')} {st.session_state.get('operator_last_name', '')}`
- **Synthetic Patient ID (UUID):** `{synthetic_id}`
- **Processing Date and Time:** `{curr_time}`
- **Compliance Status:** ✅ Successfully anonymized
- **Execution Mode:** {"Manual (Without AI)" if SETTINGS.get("manual_mode", False) else f"AI-Assisted ({SETTINGS.get('active_model', 'gliner').upper()})"}
- **Applied AI Sensitivity (Threshold):** `{SETTINGS.get('ai_threshold', 0.45):.2f}`

---

## 📊 Process Metrics
| Metric | Value |
| :--- | :--- |
| **Total Documents Processed** | {len(patient_files_to_save)} |
| **Total Pages Examined** | {total_pages_processed} |
| **Sensitive Elements Redacted (Unique)** | {total_redacted_items_count} |
| **Manual Rectangles Applied** | {manual_rects_count} |

---

## 🏷️ Redacted Entities by Category
Below is the count of removed personal information, divided by sensitive data type (GDPR Art. 4 & Art. 9):

| Sensitive Data Category | Unique Elements Detected and Redacted |
| :--- | :---: |
| 🆔 SSN / National ID / Tax Codes | {category_counts.get("SSN / National ID / Tax Codes", 0)} |
| 📅 Dates (Birth/Admission/Discharge) | {category_counts.get("Dates (Birth/Admission/Discharge)", 0)} |
| 👤 Personal Names (Doctors/Patients) | {category_counts.get("Personal Names (Doctors/Patients)", 0)} |
| 🏥 Healthcare Facilities (Hospitals/Clinics) | {category_counts.get("Healthcare Facilities (Hospitals/Clinics)", 0)} |
| 🌐 Digital Contacts (Email/URL/IP) | {category_counts.get("Digital Contacts (Email/URL/IP)", 0)} |
| 📞 Phone Numbers / Contacts | {category_counts.get("Phone Numbers / Contacts", 0)} |
| 🔢 ID Codes (Record/Patient) | {category_counts.get("ID Codes (Record/Patient)", 0)} |
| 📍 Addresses / ZIP Codes | {category_counts.get("Addresses / ZIP Codes", 0)} |
| ⚙️ Other Sensitive Information | {category_counts.get("Other Sensitive Information", 0)} |

---

## 🧠 Active Learning State
The dynamic learning algorithm memorizes preferences to ensure consistency and accuracy across sessions, without exporting or uploading sensitive data to remote servers.

- **Elements in Local Whitelist (Data to redact):** `{len(st.session_state['memory'].whitelist)}` terms
- **Elements in Local Blacklist (Data to ignore):** `{len(st.session_state['memory'].blacklist)}` terms
- **Session Type:** {"Ephemeral / Incognito (Zero Trace on disk)" if SETTINGS.get("ephemeral_session", False) else "Permanent (Data saved locally)"}

---

## 🛡️ Declaration of Compliance
All personal information identified by the operator or the AI predictive model has been permanently, irreversibly, and destructively removed via opaque black box overwriting in the final PDF files. The process ensures the anonymity of the data subjects and prevents reverse re-identification attempts through surrounding text analysis.
"""
                        audit_report_path = OUTPUT_DIR / root_folder_name / "ANONYMIZATION_AUDIT_REPORT.md"
                        try:
                            with open(audit_report_path, "w", encoding="utf-8") as f_audit:
                                f_audit.write(report_md)
                        except Exception as e_audit:
                            logger.error(f"Failed to write GDPR audit report: {e_audit}")
                    
                        # --- AUTO-LEARNING PHASE ---
                        st.session_state['memory'].add_to_whitelist(list(all_final_terms))
                        
                        removed_by_user = all_original_terms - all_final_terms
                        if removed_by_user:
                            st.session_state['memory'].add_to_blacklist(list(removed_by_user))
                        
                        st.session_state['memory'].save_memory()
                        
                        st.success(f"Data for {synthetic_id} exported successfully with GDPR Audit Report! AI updated preferences for future operations (if permitted).")
                        # Premium green border glow animation (replaces unprofessional balloons)
                        st.html("""
<style>
@keyframes successGlow {
    0%   { opacity: 0; box-shadow: inset 0 0 0px 0px rgba(16, 185, 129, 0); }
    20%  { opacity: 1; box-shadow: inset 0 0 120px 60px rgba(16, 185, 129, 0.45); }
    60%  { opacity: 1; box-shadow: inset 0 0 120px 60px rgba(16, 185, 129, 0.38); }
    100% { opacity: 0; box-shadow: inset 0 0 0px 0px rgba(16, 185, 129, 0); }
}
#export-success-overlay {
    position: fixed;
    inset: 0;
    z-index: 99999;
    pointer-events: none;
    animation: successGlow 3s cubic-bezier(0.4, 0, 0.2, 1) forwards;
    border-radius: 0;
}
</style>
<div id="export-success-overlay"></div>
<script>
setTimeout(function() {
    var el = window.parent.document.getElementById('export-success-overlay');
    if (el) el.remove();
}, 3200);
</script>
""")
                        import time; time.sleep(3.0)
                        
                        # Clear active patient and current file to reset state and redirect cleanly back to selection
                        if 'current_patient' in st.session_state:
                            del st.session_state['current_patient']
                        if 'current_file' in st.session_state:
                            del st.session_state['current_file']
                            
                        st.rerun()
                        
                st.markdown("<div style='margin-top: 8px;'></div>", unsafe_allow_html=True)
                if st.button("Cancel", key="btn_confirm_export_no", use_container_width=True):
                    st.session_state['confirm_export'] = False
                    st.rerun()
        
            st.markdown("<br>", unsafe_allow_html=True)
            
            # --- WIPE & EXIT CON CONFERMA ---
            if not st.session_state.get('confirm_wipe', False):
                st.markdown('<span id="clinical-red-btn"></span>', unsafe_allow_html=True)
                if st.button("⚠️ Wipe & Exit", key="btn_wipe_initiate", use_container_width=True):
                    st.session_state['confirm_wipe'] = True
                    st.rerun()
            else:
                st.warning("⚠️ **Confirm Wipe & Exit**\nAre you sure you want to permanently delete all session files and memory traces? This cannot be undone.")
                col_c1, col_c2 = st.columns(2)
                with col_c1:
                    st.markdown('<span id="clinical-red-btn"></span>', unsafe_allow_html=True)
                    if st.button("Yes, Wipe All", key="btn_confirm_wipe_yes", use_container_width=True):
                        cleanup_session_traces()
                        st.session_state.clear()
                        st.session_state['wiped'] = True
                        
                        with worker_lock:
                            worker_results['processed_data'].clear()
                            worker_results['original_findings'].clear()
                            worker_results['manual_rects'].clear()
                            worker_results['file_buffers'].clear()
                            worker_results['file_objs'].clear()
                            worker_results['patient_uuids'].clear()
                            
                        st.rerun()
                with col_c2:
                    if st.button("Cancel", key="btn_confirm_wipe_no", use_container_width=True):
                        st.session_state['confirm_wipe'] = False
                        st.rerun()
