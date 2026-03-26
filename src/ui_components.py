
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from config import SETTINGS, STAGING_DIR
from utils import get_readable_size
import os
import shutil
import stat
from pathlib import Path

def sidebar_ui(memory):
    with st.sidebar:
        st.title("🏥 Medical Redactor")
        st.caption("Professional Edition")
        
        st.header("📂 Input Manager")
        
        # Cleaned up Sidebar: Only Direct Upload & Settings
        st.header("📂 Direct Folder Import")
        st.caption("Optional fallback method")
        
        uploaded_files = st.file_uploader(
            "Upload Pre-Made Patient Folders", 
            type="pdf", 
            accept_multiple_files=True,
            help="Drag and drop patient folders (e.g. PAZIENTE_1) containing subfolders like CARTELLA_CLINICA and DATI_STRUTTURATI."
        )
        
        grouped_patients = {}
        if uploaded_files:
            for f in uploaded_files:
                parts = f.name.replace("\\", "/").split("/")
                if len(parts) >= 3:
                    patient_id = parts[0]
                    category = parts[1]
                elif len(parts) == 2:
                    patient_id = parts[0]
                    category = "GENERIC"
                else:
                    patient_id = "PAZIENTE_UNASSIGNED"
                    category = "GENERIC"
                    
                if patient_id not in grouped_patients:
                    grouped_patients[patient_id] = {}
                if category not in grouped_patients[patient_id]:
                    grouped_patients[patient_id][category] = []
                    
                grouped_patients[patient_id][category].append(f)

        # Merge Staged Patients (From Wizard)
        import io
        staged_patients = []
        try:
            staged_patients = [
                d for d in os.listdir(STAGING_DIR) 
                if os.path.isdir(STAGING_DIR / d) 
                and not d.startswith('.') 
                and not d.startswith('$')
                and d != "System Volume Information"
            ]
        except PermissionError:
            pass

        if staged_patients:
             for pat_id in staged_patients:
                  if pat_id not in grouped_patients: grouped_patients[pat_id] = {}
                  
                  pat_path = STAGING_DIR / pat_id
                  for root, _, files in os.walk(pat_path):
                      for file in files:
                          if file.lower().endswith('.pdf'):
                              full_path = Path(root) / file
                              rel_path = full_path.relative_to(STAGING_DIR) 
                              category = rel_path.parts[1] if len(rel_path.parts) > 1 else "GENERIC"
                              
                              if category not in grouped_patients[pat_id]: grouped_patients[pat_id][category] = []
                              
                              class StagedFileWrapper:
                                  def __init__(self, path, rel_name):
                                      self.path = path
                                      self.name = str(rel_name).replace("\\", "/") 
                                  def read(self):
                                      with open(self.path, "rb") as f: return f.read()
                                      
                              grouped_patients[pat_id][category].append(StagedFileWrapper(full_path, rel_path))
                              
        st.markdown("---")
        st.header("⚙️ Settings")
        
        # Privacy Controls
        st.subheader("Privacy")
        ephemeral = st.checkbox(
            "Incognito Session", 
            value=SETTINGS.get("ephemeral_session", False),
            help="If checked, learned terms are NOT saved to disk. Memory is wiped on exit."
        )
        # Update run-time setting (and potentially memory mode if restart)
        # Note: Changing this mid-session might require restart logic, handled in main.
        
        # Manual Mode Toggle
        manual_mode = st.checkbox(
            "Manual Mode (No AI)", 
            value=SETTINGS.get("manual_mode", False),
            help="Disable AI to save RAM. You will need to manually highlight terms."
        )
        
        # Secure USB Staging Path
        st.markdown("---")
        st.subheader("Security (One-Way Valve)")
        
        # Display current path
        current_staging = SETTINGS.get("custom_staging_path", "")
        if current_staging:
            st.success(f"**Active Staging:**\n`{current_staging}`")
        else:
            st.info("**Active Staging:**\nUSB Drive (Default)")
            
        st.caption("To prevent PHI from touching the USB drive before redaction, define a temporary folder on the hospital PC.")
        
        # Native Directory Picker workaround (Visual Explorer)
        if st.button("📁 Select Local Hospital Folder (C:\...)", use_container_width=True):
            st.session_state['show_folder_picker'] = True
            st.rerun()
            
        if st.session_state.get('show_folder_picker', False):
            st.markdown("### 🗂️ Folder Explorer")
            
            # Init current view path
            if 'picker_curr_path' not in st.session_state:
                # Start at C: on Windows, or / on Unix
                import platform
                st.session_state['picker_curr_path'] = "C:\\" if platform.system() == "Windows" else "/"
                
            curr = st.session_state['picker_curr_path']
            
            # Up button
            path_obj = Path(curr)
            col_up, col_sel, col_cancel = st.columns([1, 2, 1])
            with col_up:
                if st.button("⬆️ Up", use_container_width=True):
                    st.session_state['picker_curr_path'] = str(path_obj.parent)
                    st.rerun()
            with col_sel:
                if st.button(f"✅ Select '{path_obj.name or curr}'", type="primary", use_container_width=True):
                    st.session_state['new_custom_staging'] = curr
                    st.session_state['show_folder_picker'] = False
                    st.rerun()
            with col_cancel:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state['show_folder_picker'] = False
                    st.rerun()
            
            # List directories
            try:
                folders = [f.name for f in os.scandir(curr) if f.is_dir() and not f.name.startswith('.')]
                folders.sort()
                
                # Show as selectable buttons
                st.caption(f"Current: `{curr}`")
                
                # Paginate if too many (keep UI clean)
                with st.container(height=300):
                    for folder in folders:
                        if st.button(f"📁 {folder}", key=f"btn_fld_{folder}", use_container_width=True):
                            st.session_state['picker_curr_path'] = str(path_obj / folder)
                            st.rerun()
            except PermissionError:
                st.error("Access Denied to this folder.")
                
        if st.button("Reset to USB Default", use_container_width=True):
            st.session_state['new_custom_staging'] = ""
            st.rerun()

        # Wire the state back to main.py
        custom_staging = st.session_state.get('new_custom_staging', current_staging)
        st.markdown("---")
        
        # Action Buttons
        start_btn = st.button("🚀 Start Analysis", type="primary", use_container_width=True, disabled=not uploaded_files and not staged_patients)
        
        return grouped_patients, start_btn, ephemeral, manual_mode, custom_staging

def render_acquisition_wizard():
    """
    Renders the full-screen Patient Acquisition Wizard.
    Returns: bool (True if wizard is fully completed and AI should begin)
    """
    st.title("🏥 Patient Acquisition Wizard")
    st.markdown("Automated ingestion and structuring of hospital records.")
    
    # Check if Staging Queue already has files and user wants to bypass wizard
    existing_staged = []
    try:
        existing_staged = [
            d for d in os.listdir(STAGING_DIR) 
            if os.path.isdir(STAGING_DIR / d) 
            and not d.startswith('.') 
            and not d.startswith('$')
            and d != "System Volume Information"
        ]
    except PermissionError:
        st.error(f"Access Denied to Staging Directory: `{STAGING_DIR}`. Please reset your Security settings.")

    if existing_staged:
        st.info(f"**{len(existing_staged)} Patients** are already in the Staging Queue.")
        col1, col2 = st.columns(2)
        with col1:
             if st.button("🚀 Skip & Start AI Analysis", use_container_width=True, type="primary"):
                 st.session_state['auto_start_analysis'] = True
                 st.rerun()
        with col2:
             if st.button("🗑️ Clear Staging Queue", use_container_width=True):
                 def remove_readonly(func, path, _):
                     os.chmod(path, stat.S_IWRITE)
                     func(path)
                     
                 for d in existing_staged:
                     shutil.rmtree(STAGING_DIR / d, onerror=remove_readonly)
                 st.rerun()
        st.divider()

    # Wizard State Init
    if 'wizard_total' not in st.session_state:
        st.session_state['wizard_total'] = 0
    if 'wizard_current_step' not in st.session_state:
        st.session_state['wizard_current_step'] = 1
        
    # Phase 1: Setup
    if st.session_state['wizard_total'] == 0:
        st.subheader("Step 1: Setup Batch")
        st.write("How many patients do you want to import in this session?")
        
        col_inp, col_btn = st.columns([1, 1])
        with col_inp:
            total_input = st.number_input("Number of Patients", min_value=1, max_value=500, value=1)
        with col_btn:
             st.write("") # Spacing
             st.write("")
             if st.button("Start Ingestion", type="primary"):
                 st.session_state['wizard_total'] = total_input
                 st.rerun()
        return False
        
    # Phase 2: Sequential Ingestion
    total = st.session_state['wizard_total']
    current = st.session_state['wizard_current_step']
    
    # Progress UI
    progress_val = (current - 1) / total
    st.progress(progress_val)
    st.subheader(f"Ingesting Patient {current} of {total}")
    
    # Generate UUID for the current step immediately
    uuid_key = f"wizard_uuid_{current}"
    import uuid
    if uuid_key not in st.session_state:
        st.session_state[uuid_key] = uuid.uuid4().hex[:8].upper()
    
    assigned_uuid = st.session_state[uuid_key]
    
    st.info(f"🔒 **Anonymous ID Assigned:** `{assigned_uuid}`")
    
    st.markdown("---")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### 📘 Cartella Clinica")
        st.caption("Descriptive documents containing prose and names.")
        clinica_files = st.file_uploader("Upload Clinical Records", type="pdf", accept_multiple_files=True, key=f"up_c_{current}")
        
    with c2:
        st.markdown("### 📊 Dati Strutturati")
        st.caption("Tabular lab results, blood work, etc.")
        laboratori_files = st.file_uploader("Upload Lab Results", type="pdf", accept_multiple_files=True, key=f"up_l_{current}")
        
    st.markdown("---")
    
    btn_c1, btn_c2, btn_c3 = st.columns([1, 2, 1])
    
    with btn_c1:
         if current > 1:
             if st.button("⬅️ Back"):
                 st.session_state['wizard_current_step'] -= 1
                 st.rerun()
                 
    with btn_c3:
        btn_label = "Capture & Next ➡️" if current < total else "Capture & Finish Batch ✅"
        
        if st.button(btn_label, type="primary"):
             if not clinica_files and not laboratori_files:
                 st.error("You must upload at least one file to proceed.")
             else:
                 # Construct physical staging envelope
                 target_pat_dir = STAGING_DIR / assigned_uuid
                 dir_clinica = target_pat_dir / "CARTELLA_CLINICA"
                 dir_lab = target_pat_dir / "DATI_STRUTTURATI"
                 
                 dir_clinica.mkdir(parents=True, exist_ok=True)
                 dir_lab.mkdir(parents=True, exist_ok=True)
                 
                 for cf in clinica_files:
                     with open(dir_clinica / cf.name, "wb") as f: f.write(cf.getbuffer())
                 for lf in laboratori_files:
                     with open(dir_lab / lf.name, "wb") as f: f.write(lf.getbuffer())
                     
                 # Advance state
                 if current < total:
                     st.session_state['wizard_current_step'] += 1
                     st.rerun()
                 else:
                     st.success("Batch Ingestion Complete!")
                     st.session_state['wizard_total'] = 0 # Reset wizard
                     st.session_state['wizard_current_step'] = 1
                     st.session_state['auto_start_analysis'] = True
                     st.rerun() # Signal main.py to start AI Phase
                     
    return False

def render_page_editor(file_name, page_index, pdf_processor, current_terms, manual_rects_for_page):
    """
    Renders the editor for a single page:
    - Left: Text list editing
    - Right: Canvas for manual redaction
    Returns: (updated_terms_list, new_manual_rects_for_page_or_None)
    """
    
    col_text, col_canvas = st.columns([1, 4])
    
    # --- Text Column ---
    with col_text:
        st.subheader("Text Redaction")
        st.caption("Edit terms found by AI/Memory")
        
        # Sort for display
        sorted_terms = sorted(list(current_terms))
        text_input = st.text_area(
            f"Terms on Page {page_index+1}",
            value="\n".join(sorted_terms),
            height=600,
            key=f"txt_{file_name}_{page_index}"
        )
        
        # Process updates
        updated_terms = [t.strip() for t in text_input.split("\n") if t.strip()]
        
        # Canvas Legend
        st.markdown(
            """
            <div style="background-color: #262730; padding: 15px; border-radius: 8px; margin-top: 20px; border: 1px solid #444;">
                <h4 style="margin-top: 0; color: #fff;">🛠️ Oggetti Disegnati</h4>
                <p style="color: #ccc; font-size: 0.9em; line-height: 1.4;">
                Per annullare l'ultimo rettangolo disegnato a mano o per eliminarli tutti,
                utilizza gli appositi pulsanti grigi situati qui sotto.<br><br>
                <i>Ricorda: i rettangoli applicati non si possono spostare dopo averli disegnati, usa l'Annulla se sbagli mira!</i>
                </p>
            </div>
            """, 
            unsafe_allow_html=True
        )
        
        st.markdown("<br>", unsafe_allow_html=True)
        btn_col1, btn_col2 = st.columns(2)
        with btn_col1:
            action_undo = st.button("↩️ Undo Ultimo Rettangolo", use_container_width=True)
        with btn_col2:
            action_clear_all = st.button("🗑️ Elimina Tutti", use_container_width=True)
    
    # --- Canvas Column ---
    with col_canvas:
        st.subheader("Manual Redaction")
        st.caption("Draw rectangles over logos, barcodes, or missed text.")
        
        # Render background image
        # Cache the generated PIL image object. If we pass a brand new PIL image pointer to st_canvas 
        # on every rerun, it interprets it as a "new background" and fires an infinite loop of redraws.
        terms_hash = hash(tuple(updated_terms))
        bg_cache_key = f"bg_{file_name}_{page_index}_{terms_hash}"
        
        # Free up memory from old page/term caches by keeping only the active one
        if st.session_state.get('active_bg_key') != bg_cache_key:
            old_key = st.session_state.get('active_bg_key')
            if old_key and old_key in st.session_state:
                del st.session_state[old_key]
                
            st.session_state[bg_cache_key] = pdf_processor.render_page_for_canvas(page_index, updated_terms)
            st.session_state['active_bg_key'] = bg_cache_key
            
        bg_img, scale_x, scale_y = st.session_state[bg_cache_key]
        
        if bg_img:
            # Inject CSS to make Canvas Toolbar Icons (SVG) visible on Dark Mode
            st.markdown(
                """
                <style>
                /* Invert colors of SVG icons inside the streamlit canvas wrapper */
                div[data-testid="stCanvas"] svg {
                    filter: invert(1) brightness(2);
                }
                </style>
                """,
                unsafe_allow_html=True
            )
        
            # We add a checkbox to determine if the rectangles drawn should be applied globally
            apply_to_all = st.checkbox("Apply drawn rectangles to ALL pages (e.g., for headers/footers)", value=True)
            
            json_cache_key = f"canvas_json_{file_name}_{page_index}"
            rev_key = f"canvas_rev_{file_name}_{page_index}"
            rev = st.session_state.get(rev_key, 0)
            widget_key = f"canvas_{file_name}_{page_index}_{rev}"
            
            # To prevent the st_canvas floating-point infinite React loop, we MUST ensure 
            # the `initial_drawing` prop remains completely static for the lifetime of the widget_key.
            snapshot_key = f"canvas_snapshot_{widget_key}"
            if snapshot_key not in st.session_state:
                st.session_state[snapshot_key] = st.session_state.get(json_cache_key, {"version": "4.4.0", "objects": []})
                
            initial_drawing = st.session_state[snapshot_key]
            
            canvas_result = st_canvas(
                fill_color="rgba(255, 0, 0, 0.4)", # Semi-transparent red for drawing
                stroke_width=2,
                stroke_color="#FFFFFF",            # White borders make icons visible in Dark Mode
                background_image=bg_img,
                initial_drawing=initial_drawing,
                update_streamlit=True,
                height=bg_img.height,
                width=bg_img.width,
                drawing_mode="rect",
                key=widget_key,
                display_toolbar=False
            )
            
            # If canvas_result.json_data is None, it means the canvas hasn't initialized its state back to Python yet.
            if canvas_result.json_data is not None:
                # Update the raw JSON cache instantly as long as it isn't an empty reset phase
                st.session_state[json_cache_key] = canvas_result.json_data
                
                new_rects = []
                for obj in canvas_result.json_data["objects"]:
                    if obj["type"] == "rect":
                        # Pixel Coords
                        x = obj["left"]
                        y = obj["top"]
                        w = obj["width"]
                        h = obj["height"]
                        
                        # Convert to PDF Coords
                        x0 = x * scale_x
                        y0 = y * scale_y
                        x1 = (x + w) * scale_x
                        y1 = (y + h) * scale_y
                        
                        new_rects.append([x0, y0, x1, y1])
                return updated_terms, new_rects, apply_to_all, action_undo, action_clear_all
            else:
                return updated_terms, None, apply_to_all, action_undo, action_clear_all
            
        else:
            st.error("Error rendering page.")
            return updated_terms, None, False, False, False

def memory_manager_ui(memory):
    st.header("🧠 Memory Management")
    if memory.ephemeral:
        st.warning("🕵️ Incognito Mode: Changes here will be lost on exit.")
        
    t1, t2 = st.tabs(["Allowed Terms (Whitelist)", "Ignored Terms (Blacklist)"])
    
    with t1:
        st.caption("Terms to ALWAYS redact (e.g., Doctor Names)")
        val = st.text_area("Whitelist", value="\n".join(sorted(memory.whitelist)), height=200)
        if st.button("Save Whitelist"):
            new_set = set([t.strip() for t in val.split("\n") if t.strip()])
            memory.whitelist = new_set
            memory.save_memory()
            st.success("Whitelist updated.")
            
    with t2:
        st.caption("Terms to NEVER redact (False Positives)")
        val = st.text_area("Blacklist", value="\n".join(sorted(memory.blacklist)), height=200)
        if st.button("Save Blacklist"):
            new_set = set([t.strip() for t in val.split("\n") if t.strip()])
            memory.blacklist = new_set
            memory.save_memory()
            st.success("Blacklist updated.")
