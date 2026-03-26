
import streamlit as st
import os
import time
from pathlib import Path

# --- LOCAL IMPORTS ---
from config import SETTINGS, OUTPUT_DIR, SETTINGS_FILE, save_settings
from utils import logger, cleanup_session_traces
from redaction_logic import RedactionMemory, TextAnalyzer
from llm_engine import LLMEngine
from pdf_processor import PDFProcessor
from ui_components import sidebar_ui, render_page_editor, memory_manager_ui, render_acquisition_wizard

# --- PAGE CONFIG ---
st.set_page_config(
    page_title="Medical Redactor Ultimate",
    page_icon="🏥",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- INITIALIZATION ---
if 'initialized' not in st.session_state:
    st.session_state['initialized'] = True
    st.session_state['memory'] = RedactionMemory(ephemeral=SETTINGS['ephemeral_session'])
    st.session_state['llm'] = LLMEngine()
    st.session_state['processed_data'] = {} # {filename: {page_idx: [terms]}}
    st.session_state['manual_rects'] = {}   # {filename: {page_idx: [[x0,y0,x1,y1]]}}
    st.session_state['file_buffers'] = {}   # {filename: bytes}
    st.session_state['file_objs'] = {}      # {filename: PDFProcessor} -> Cached Objects (careful with memory)
    st.session_state['patient_uuids'] = {}  # {patient_id: "SHORT_UUID"}

# --- SIDEBAR & SETTINGS ---
grouped_patients, start_btn, ephemeral_mode, manual_mode, custom_staging = sidebar_ui(st.session_state['memory'])

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

if settings_changed:
    save_settings(SETTINGS)
    st.rerun() # Restart to reload state (especially important for Staging Dir remounting)

# --- MAIN LOGIC ---

def run_analysis(patients_dict):
    analyzer = TextAnalyzer(st.session_state['memory'], st.session_state['llm'] if not SETTINGS['manual_mode'] else None)
    import uuid
    
    # Calculate total files for progress bar
    total_files = sum(len(files) for categories in patients_dict.values() for files in categories.values())
    
    if total_files == 0:
        st.error("No files found in Staging or Direct Upload to analyze.")
        return
        
    prog_bar = st.progress(0)
    status = st.empty()
    completed_steps = 0
    total_steps = total_files * 5 # Approximation
    
    for patient_id, categories in patients_dict.items():
        # Generate Synthetic ID for this patient if not exists
        if patient_id not in st.session_state['patient_uuids']:
            st.session_state['patient_uuids'][patient_id] = uuid.uuid4().hex[:8].upper()
            
        # Strategy: Process CARTELLA_CLINICA first, then DATI_STRUTTURATI so memory learns the patient.
        ordered_categories = ["CARTELLA_CLINICA", "DATI_STRUTTURATI", "GENERIC"]
        existing_cats = [c for c in ordered_categories if c in categories]
        # Add any other unexpected subfolders at the end
        for c in categories.keys():
            if c not in existing_cats:
                 existing_cats.append(c)
                 
        for cat in existing_cats:
            for f in categories[cat]:
                file_bytes = f.read()
                # To prevent collisions, f.name is already the relative path from the upload 
                # e.g. "PAZIENTE_1/CARTELLA_CLINICA/verbale.pdf". We use this full path as the unique key.
                f_name = f.name.replace("\\", "/") 
                
                st.session_state['file_buffers'][f_name] = file_bytes
                processor = PDFProcessor(file_bytes)
                st.session_state['file_objs'][f_name] = processor
                
                num_pages = processor.get_page_count()
                file_results = {}
                st.session_state['manual_rects'][f_name] = {} # Init manual rects
                
                for i in range(num_pages):
                    status.text(f"Analyzing {patient_id} ({cat}): Page {i+1}/{num_pages}")
                    text = processor.extract_text(i)
                    
                    # ANALYZE
                    # Pass the category to allow contextual rules (e.g. keeping dates in DATI_STRUTTURATI)
                    terms = analyzer.analyze_text(text, category=cat)
                    file_results[i] = terms
                    
                    # CROSS-DOCUMENT LEARNING:
                    # If we are in the Cartella Clinica, immediately feed discovered terms
                    # into the temporary memory so subsequent Lab Results (Dati Strutturati) 
                    # catch them instantly as exact matches.
                    if cat == "CARTELLA_CLINICA":
                        st.session_state['memory'].add_to_whitelist(terms)
                    
                    completed_steps += 1
                    prog_bar.progress(min(0.95, completed_steps / max(1, total_steps)))
                    time.sleep(0.01) # UI yield
                    
                st.session_state['processed_data'][f_name] = file_results
    
    prog_bar.progress(1.0)
    status.success("Analysis Complete!")
    time.sleep(1)
    status.empty()
    st.rerun()


# --- APP ROUTING ---
if not st.session_state.get('processed_data'):
    
    if st.session_state.get('auto_start_analysis') or start_btn:
        st.session_state['auto_start_analysis'] = False
        with st.spinner("Initializing AI Engine and processing patients..."):
            run_analysis(grouped_patients)
    else:
        # Show Acquisition Wizard if no data is processed yet
        render_acquisition_wizard()
else:
    # --- REVIEW UI ---
    st.divider()
    
    # We parse the flat keys "PAZIENTE/CAT/FILE" back into a hierarchy for UI
    all_keys = list(st.session_state['processed_data'].keys())
    patients_available = list(set([k.split("/")[0] for k in all_keys]))
    patients_available.sort()
    
    if 'current_patient' not in st.session_state or st.session_state['current_patient'] not in patients_available:
        st.session_state['current_patient'] = patients_available[0]
        
    col_pat, col_file, col_mem = st.columns([1, 2, 1])
    
    with col_pat:
        st.session_state['current_patient'] = st.selectbox("Select Patient", patients_available, index=patients_available.index(st.session_state['current_patient']))
        
    patient_files = [k for k in all_keys if k.startswith(st.session_state['current_patient'] + "/")]
    
    if 'current_file' not in st.session_state or st.session_state['current_file'] not in patient_files:
        st.session_state['current_file'] = patient_files[0] if patient_files else None
        
    with col_file:
        if patient_files:
            # Display nicely (strip patient prefix for display)
            display_names = [f.replace(st.session_state['current_patient'] + "/", "") for f in patient_files]
            chosen_display = st.selectbox("Select Document", display_names, index=patient_files.index(st.session_state['current_file']) if st.session_state['current_file'] in patient_files else 0)
            selected_file = st.session_state['current_patient'] + "/" + chosen_display
            st.session_state['current_file'] = selected_file
        else:
            selected_file = None
            
    with col_mem:
        with st.expander("Manage Memory"):
            memory_manager_ui(st.session_state['memory'])

    if selected_file:
        # Paginator
        processor = st.session_state['file_objs'].get(selected_file)
        if not processor:
             # Re-init if missing
             processor = PDFProcessor(st.session_state['file_buffers'][selected_file])
             st.session_state['file_objs'][selected_file] = processor

        num_pages = processor.get_page_count()
        if 'page_idx' not in st.session_state: st.session_state['page_idx'] = 0
        
        # Keyboard Navigation Injection (JS)
        import streamlit.components.v1 as components
        components.html(
            """
            <script>
            const doc = window.parent.document;
            doc.addEventListener('keydown', function(e) {
                if (e.key === 'ArrowLeft') {
                    const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText === '⬅️ Prev');
                    if (btn) btn.click();
                } else if (e.key === 'ArrowRight') {
                    const btn = Array.from(doc.querySelectorAll('button')).find(el => el.innerText === 'Next ➡️');
                    if (btn) btn.click();
                }
            });
            </script>
            """,
            height=0,
            width=0,
        )

        # Navigation
        c1, c2, c3 = st.columns([1, 4, 1])
        with c1: 
            if st.button("⬅️ Prev", key="btn_prev_page"): 
                st.session_state['page_idx'] = max(0, st.session_state['page_idx'] - 1)
                st.rerun()
        with c3: 
            if st.button("Next ➡️", key="btn_next_page"): 
                st.session_state['page_idx'] = min(num_pages - 1, st.session_state['page_idx'] + 1)
                st.rerun()
        with c2:
            new_page = st.slider("Page", 1, num_pages, st.session_state['page_idx'] + 1) - 1
            if new_page != st.session_state['page_idx']:
                st.session_state['page_idx'] = new_page
                st.rerun()

        curr_page = st.session_state['page_idx']
        
        # DATA FOR EDITOR
        current_terms = st.session_state['processed_data'][selected_file].get(curr_page, [])
        manual_rects_map = st.session_state['manual_rects'].get(selected_file, {})
        current_manual_rects = manual_rects_map.get(curr_page, [])
        
        # RENDER EDITOR
        updated_terms, new_rects, apply_to_all, action_undo, action_clear_all = render_page_editor(selected_file, curr_page, processor, current_terms, current_manual_rects)
        
        # UPDATE STATE
        
        # Calculate diffs to auto-propagate to subsequent pages
        old_terms_set = set(current_terms)
        new_terms_set = set(updated_terms)
        
        added_terms = new_terms_set - old_terms_set
        removed_terms = old_terms_set - new_terms_set
        
        # Apply to current page
        st.session_state['processed_data'][selected_file][curr_page] = updated_terms
        
        # Auto-propagate changes to all FOLLOWING pages in this document
        if added_terms or removed_terms:
            for p in range(curr_page + 1, num_pages):
                page_terms = set(st.session_state['processed_data'][selected_file].get(p, []))
                
                # Add new terms
                page_terms.update(added_terms)
                
                # Remove deleted terms
                page_terms.difference_update(removed_terms)
                
                # Save back ensuring no empty strings
                st.session_state['processed_data'][selected_file][p] = [t for t in list(page_terms) if t.strip()]

        
        def rects_differ(r1, r2, tol=2.0):
            if len(r1) != len(r2): return True
            for a, b in zip(r1, r2):
                if any(abs(v1-v2) > tol for v1, v2 in zip(a,b)): return True
            return False

        # State tracking for the Apply to All Toggle
        toggle_key = f"apply_all_{selected_file}_{curr_page}"
        prev_apply_to_all = st.session_state.get(toggle_key, True) # Default is now True
        st.session_state[toggle_key] = apply_to_all
        
        # Did the user just turn on the checkbox? Or did they draw a new rect while it's on?
        toggled_on = apply_to_all and not prev_apply_to_all
        current_saved = st.session_state['manual_rects'][selected_file].get(curr_page, [])
        new_drawing = new_rects is not None and rects_differ(current_saved, new_rects)
        
        # Handle Manual Rects update
        if new_drawing or toggled_on:
             rects_to_save = new_rects if new_drawing else current_saved
             
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
                 st.rerun() # Force immediate refresh of other pages if we retroactively broadcasted

                 
        # --- Handle Undo / Delete Logic ---
        if action_undo:
            if st.session_state['manual_rects'][selected_file].get(curr_page):
                st.session_state['manual_rects'][selected_file][curr_page].pop()
                j_c = st.session_state.get(f"canvas_json_{selected_file}_{curr_page}")
                if j_c and j_c.get("objects"): j_c["objects"].pop()
                st.session_state[f"canvas_rev_{selected_file}_{curr_page}"] = st.session_state.get(f"canvas_rev_{selected_file}_{curr_page}", 0) + 1
                
                if apply_to_all:
                    for p in range(num_pages):
                        if p != curr_page:
                            if st.session_state['manual_rects'][selected_file].get(p):
                                st.session_state['manual_rects'][selected_file][p].pop()
                            pj_c = st.session_state.get(f"canvas_json_{selected_file}_{p}")
                            if pj_c and pj_c.get("objects"): pj_c["objects"].pop()
                            st.session_state[f"canvas_rev_{selected_file}_{p}"] = st.session_state.get(f"canvas_rev_{selected_file}_{p}", 0) + 1
                st.rerun()
                
        if action_clear_all:
            if st.session_state['manual_rects'][selected_file].get(curr_page):
                st.session_state['manual_rects'][selected_file][curr_page] = []
                j_c = st.session_state.get(f"canvas_json_{selected_file}_{curr_page}")
                if j_c: j_c["objects"] = []
                st.session_state[f"canvas_rev_{selected_file}_{curr_page}"] = st.session_state.get(f"canvas_rev_{selected_file}_{curr_page}", 0) + 1
                
                if apply_to_all:
                    for p in range(num_pages):
                        if p != curr_page:
                             st.session_state['manual_rects'][selected_file][p] = []
                             pj_c = st.session_state.get(f"canvas_json_{selected_file}_{p}")
                             if pj_c: pj_c["objects"] = []
                             st.session_state[f"canvas_rev_{selected_file}_{p}"] = st.session_state.get(f"canvas_rev_{selected_file}_{p}", 0) + 1
                st.rerun()

        st.divider()
        
        # --- SAVE ACTIONS ---
        c_save, c_wipe = st.columns([3, 1])
        with c_save:
            if st.button("💾 EXPORT ENTIRE PATIENT (Preserve Hierarchy)", type="primary"):
                curr_pat = st.session_state['current_patient']
                synthetic_id = st.session_state['patient_uuids'].get(curr_pat, "UNKNOWN_ID")
                
                patient_files_to_save = [k for k in all_keys if k.startswith(curr_pat + "/")]
                
                all_final_terms = set()
                
                with st.spinner(f"Exporting patient folder {synthetic_id}..."):
                    for p_file in patient_files_to_save:
                        # 1. Gather all terms for whitelist
                        for p_idx, t_list in st.session_state['processed_data'][p_file].items():
                            all_final_terms.update(t_list)
                        
                        # 2. Render PDF
                        redaction_map = st.session_state['processed_data'][p_file]
                        rect_map = st.session_state['manual_rects'][p_file]
                        proc = st.session_state['file_objs'][p_file]
                        
                        pdf_bytes = proc.save_redacted_pdf(redaction_map, rect_map)
                        
                        # 3. Create hierarchy
                        # Original key is "PAZIENTE_1/CARTELLA_CLINICA/verbale.pdf"
                        parts = p_file.split("/")
                        if len(parts) >= 3:
                            original_category = parts[-2]
                            original_filename = parts[-1]
                        else:
                            original_category = "GENERIC"
                            original_filename = parts[-1]
                            
                        # Format Output Names
                        root_folder_name = f"Paziente_{synthetic_id}"
                        
                        # Count how many files are in this category for this patient
                        # to decide if we need to append an index (_1, _2...)
                        cat_files = [f for f in patient_files_to_save if f.split("/")[-2] == original_category]
                        needs_index = len(cat_files) > 1
                        current_file_index = cat_files.index(p_file) + 1 if needs_index else ""
                        suffix = f"_{current_file_index}" if needs_index else ""
                        
                        if original_category == "CARTELLA_CLINICA":
                            cat_folder_name = f"Cartella_Clinica_{synthetic_id}"
                            out_filename = f"Cartella_Clinica_{synthetic_id}{suffix}.pdf"
                        elif original_category == "DATI_STRUTTURATI":
                            cat_folder_name = f"Dati_Laboratorio_{synthetic_id}"
                            out_filename = f"Dati_Laboratorio_{synthetic_id}{suffix}.pdf"
                        else:
                            cat_folder_name = original_category
                            # For unknown generic categories we keep original name logic
                            out_filename = f"{synthetic_id}{suffix}_{original_filename}"
                            
                        # Format output: OUTPUT_DIR / Paziente_4F8A9B2C / Cartella_Clinica_4F8A9B2C / Cartella_Clinica_4F8A9B2C_verbale.pdf
                        target_dir = OUTPUT_DIR / root_folder_name / cat_folder_name
                        target_dir.mkdir(parents=True, exist_ok=True)
                        
                        out_path = target_dir / out_filename
                        with open(out_path, "wb") as f:
                            f.write(pdf_bytes)
                
                st.session_state['memory'].add_to_whitelist(list(all_final_terms))
                st.session_state['memory'].save_memory()
                
                st.success(f"Patient {curr_pat} exported successfully to: {OUTPUT_DIR / root_folder_name}")
        
        with c_wipe:
            if st.button("⚠️ WIPE & EXIT (Zero Trace)"):
                cleanup_session_traces()
                st.session_state.clear()
                st.stop()
