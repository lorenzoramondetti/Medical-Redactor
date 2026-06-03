
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from config import SETTINGS, STAGING_DIR
from utils import get_readable_size
import os
import shutil
import stat
from pathlib import Path

def sidebar_ui(memory, is_review_phase=False, patients_available=None, all_keys=None):
    # Inject CSS globally to style buttons dynamically based on span markers
    st.markdown(
        """
        <style>
        /* Clinical blue button styles (safe continuation/actions) */
        div:has(> div > span#clinical-blue-btn) + div button,
        div:has(span#clinical-blue-btn) + div button {
            background-color: #1E88E5 !important;
            color: white !important;
            border-color: #1E88E5 !important;
            font-weight: 600 !important;
        }
        div:has(> div > span#clinical-blue-btn) + div button:hover,
        div:has(span#clinical-blue-btn) + div button:hover {
            background-color: #1565C0 !important;
            border-color: #1565C0 !important;
        }

        /* Clinical green button styles (primary launching actions) */
        div:has(> div > span#clinical-green-btn) + div button,
        div:has(span#clinical-green-btn) + div button {
            background-color: #10B981 !important;
            color: white !important;
            border-color: #10B981 !important;
            font-weight: 600 !important;
        }
        div:has(> div > span#clinical-green-btn) + div button:hover,
        div:has(span#clinical-green-btn) + div button:hover {
            background-color: #059669 !important;
            border-color: #059669 !important;
        }

        /* Clinical destructive red button styles (destructive actions) */
        div:has(> div > span#clinical-red-btn) + div button,
        div:has(span#clinical-red-btn) + div button {
            background-color: #EF4444 !important;
            color: white !important;
            border-color: #EF4444 !important;
            font-weight: 600 !important;
        }
        div:has(> div > span#clinical-red-btn) + div button:hover,
        div:has(span#clinical-red-btn) + div button:hover {
            background-color: #DC2626 !important;
            border-color: #DC2626 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )
    with st.sidebar:
        st.title("🏥 Medical Redactor")
        st.caption("⚠️ Work in Progress (Research Prototype)")
        st.markdown("---")
        
        # Wire the state back to main.py
        current_staging = SETTINGS.get("custom_staging_path", "")
        custom_staging = st.session_state.get('new_custom_staging', current_staging)
        
        if is_review_phase and patients_available and all_keys:
            current_pat = st.session_state.get('current_patient')
            idx_pat = patients_available.index(current_pat) if current_pat in patients_available else 0
            st.session_state['current_patient'] = st.selectbox("Select Patient", patients_available, index=idx_pat)
            
            patient_files = [k for k in all_keys if k.startswith(st.session_state['current_patient'] + "/")]
            if 'current_file' not in st.session_state or st.session_state['current_file'] not in patient_files:
                st.session_state['current_file'] = patient_files[0] if patient_files else None
                
            if patient_files:
                display_names = [f.replace(st.session_state['current_patient'] + "/", "") for f in patient_files]
                curr_file = st.session_state.get('current_file')
                idx_file = patient_files.index(curr_file) if curr_file in patient_files else 0
                chosen_display = st.selectbox("Select Document", display_names, index=idx_file)
                st.session_state['current_file'] = st.session_state['current_patient'] + "/" + chosen_display
                
            selected_file = st.session_state.get('current_file')
            if selected_file and 'file_objs' in st.session_state and selected_file in st.session_state['file_objs']:
                processor = st.session_state['file_objs'][selected_file]
                num_pages = processor.get_page_count()
                
                if 'page_idx' not in st.session_state:
                    st.session_state['page_idx'] = 0
                else:
                    st.session_state['page_idx'] = min(st.session_state['page_idx'], num_pages - 1)
                
                st.markdown("---")
                st.markdown("**📄 Navigation**")
                
                c1, c2 = st.columns(2)
                with c1:
                    if st.button("⬅️ Prev", key="btn_prev_page", disabled=(num_pages <= 1 or st.session_state['page_idx'] <= 0), use_container_width=True):
                        st.session_state['page_idx'] = max(0, st.session_state['page_idx'] - 1)
                        import time; time.sleep(0.15)
                        st.rerun()
                with c2:
                    if st.button("Next ➡️", key="btn_next_page", disabled=(num_pages <= 1 or st.session_state['page_idx'] >= num_pages - 1), use_container_width=True):
                        st.session_state['page_idx'] = min(num_pages - 1, st.session_state['page_idx'] + 1)
                        import time; time.sleep(0.15)
                        st.rerun()
                        
                if num_pages > 1:
                    new_page = st.slider("Page", 1, num_pages, st.session_state['page_idx'] + 1) - 1
                    if new_page != st.session_state['page_idx']:
                        st.session_state['page_idx'] = new_page
                        import time; time.sleep(0.15)
                        st.rerun()
                else:
                    st.markdown("<p style='text-align: center; margin-top: 5px; color: gray;'>Page 1 of 1</p>", unsafe_allow_html=True)
                
            st.divider()
            ephemeral = st.checkbox(
                "Incognito Session", 
                value=SETTINGS.get("ephemeral_session", False),
                help="If checked, learned terms are NOT saved to disk. Memory is wiped on exit."
            )
            
            # --- Date Replacement System ---
            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
            date_replacement_active = st.checkbox(
                "Date Replacement",
                value=SETTINGS.get("date_replacement_active", False),
                help="Replaces dates in the PDF with 'Day X' calculated from the baseline date.",
                key="date_repl_check_1"
            )
            
            baseline_date_str = SETTINGS.get("baseline_date")
            import datetime
            try:
                default_date = datetime.datetime.strptime(baseline_date_str, "%Y-%m-%d").date() if baseline_date_str else datetime.date.today()
            except Exception:
                default_date = datetime.date.today()
                
            baseline_date = None
            baseline_day_index = SETTINGS.get("baseline_day_index", 1)
            
            date_format = SETTINGS.get("date_format", "%d/%m/%Y")
            date_max_range_days = SETTINGS.get("date_max_range_days", 365)
            
            if date_replacement_active:
                baseline_date = st.date_input("Baseline Date (Admission)", value=default_date, key="date_input_1")
                baseline_day_index = st.radio(
                    "The admission day is:",
                    options=[0, 1],
                    format_func=lambda x: f"Day {x}",
                    index=0 if baseline_day_index == 0 else 1,
                    horizontal=True,
                    key="day_idx_1"
                )
                
                format_options = {"%d/%m/%Y": "DD/MM/YYYY", "%m/%d/%Y": "MM/DD/YYYY", "%Y-%m-%d": "YYYY-MM-DD"}
                rev_format_options = {v: k for k, v in format_options.items()}
                
                selected_fmt_label = st.selectbox(
                    "Preferred Date Format",
                    options=list(format_options.values()),
                    index=list(format_options.keys()).index(date_format) if date_format in format_options else 0,
                    key="date_fmt_1"
                )
                date_format = rev_format_options[selected_fmt_label]
                
                date_max_range_days = st.number_input(
                    "Maximum Day Range",
                    min_value=1,
                    max_value=36500,
                    value=int(date_max_range_days),
                    help="Dates further than these days from the baseline date (e.g. date of birth) will be redacted but not replaced with 'Day X'.",
                    key="date_range_1"
                )
            
            manual_mode = SETTINGS.get("manual_mode", False)
            new_active_model = "gliner"
            ai_threshold = float(SETTINGS.get("ai_threshold", 0.45))
        else:
            # 1. Settings - under Title
            st.header("⚙️ Settings")
            
            st.subheader("Privacy")
            ephemeral = st.checkbox(
                "Incognito Session", 
                value=SETTINGS.get("ephemeral_session", False),
                help="If checked, learned terms are NOT saved to disk. Memory is wiped on exit."
            )
            
            # --- Date Replacement System ---
            st.markdown("<div style='margin-top: 5px;'></div>", unsafe_allow_html=True)
            date_replacement_active = st.checkbox(
                "Date Replacement",
                value=SETTINGS.get("date_replacement_active", False),
                help="Replaces dates in the PDF with 'Day X' calculated from the baseline date.",
                key="date_repl_check_2"
            )
            
            baseline_date_str = SETTINGS.get("baseline_date")
            import datetime
            try:
                default_date = datetime.datetime.strptime(baseline_date_str, "%Y-%m-%d").date() if baseline_date_str else datetime.date.today()
            except Exception:
                default_date = datetime.date.today()
                
            baseline_date = None
            baseline_day_index = SETTINGS.get("baseline_day_index", 1)
            
            date_format = SETTINGS.get("date_format", "%d/%m/%Y")
            date_max_range_days = SETTINGS.get("date_max_range_days", 365)
            
            if date_replacement_active:
                baseline_date = st.date_input("Baseline Date (Admission)", value=default_date, key="date_input_2")
                baseline_day_index = st.radio(
                    "The admission day is:",
                    options=[0, 1],
                    format_func=lambda x: f"Day {x}",
                    index=0 if baseline_day_index == 0 else 1,
                    horizontal=True,
                    key="day_idx_2"
                )
                
                format_options = {"%d/%m/%Y": "DD/MM/YYYY", "%m/%d/%Y": "MM/DD/YYYY", "%Y-%m-%d": "YYYY-MM-DD"}
                rev_format_options = {v: k for k, v in format_options.items()}
                
                selected_fmt_label = st.selectbox(
                    "Preferred Date Format",
                    options=list(format_options.values()),
                    index=list(format_options.keys()).index(date_format) if date_format in format_options else 0,
                    key="date_fmt_2"
                )
                date_format = rev_format_options[selected_fmt_label]
                
                date_max_range_days = st.number_input(
                    "Maximum Day Range",
                    min_value=1,
                    max_value=36500,
                    value=int(date_max_range_days),
                    help="Dates further than these days from the baseline date (e.g. date of birth) will be redacted but not replaced with 'Day X'.",
                    key="date_range_2"
                )
            
            manual_mode = st.checkbox(
                "Manual Mode (No AI)", 
                value=SETTINGS.get("manual_mode", False),
                help="Disable AI to save RAM. You will need to manually highlight terms."
            )
            
            # 3. Artificial Intelligence - under Settings
            st.markdown("---")
            st.subheader("🤖 Artificial Intelligence")
            
            new_active_model = "gliner"
            
            # Dynamic Confidence Threshold Slider
            if not manual_mode:
                # Sync session states
                if 'ai_sensitivity_slider' not in st.session_state:
                    st.session_state['ai_sensitivity_slider'] = float(SETTINGS.get("ai_threshold", 0.45))
                if 'ai_sensitivity_number' not in st.session_state:
                    st.session_state['ai_sensitivity_number'] = float(SETTINGS.get("ai_threshold", 0.45))
                    
                # Define change handlers to keep them in sync natively
                def on_slider_change():
                    st.session_state['ai_sensitivity_number'] = round(st.session_state['ai_sensitivity_slider'], 2)
                    
                def on_number_change():
                    st.session_state['ai_sensitivity_slider'] = round(st.session_state['ai_sensitivity_number'], 2)
                    
                st.markdown(
                    "**AI Sensitivity (Confidence Threshold)**",
                    help="A lower threshold increases AI sensitivity (capturing more terms, but potentially increasing false positives). A higher threshold makes the AI more selective."
                )
                col_slider, col_number = st.columns([3, 2])
                
                with col_slider:
                    st.slider(
                        "AI Sensitivity Slider",
                        min_value=0.10,
                        max_value=0.90,
                        step=0.01,
                        label_visibility="collapsed",
                        key="ai_sensitivity_slider",
                        on_change=on_slider_change
                    )
                    
                with col_number:
                    st.number_input(
                        "AI Sensitivity Number",
                        min_value=0.10,
                        max_value=0.90,
                        step=0.01,
                        format="%.2f",
                        label_visibility="collapsed",
                        key="ai_sensitivity_number",
                        on_change=on_number_change
                    )
                    
                ai_threshold = st.session_state['ai_sensitivity_slider']
                
                st.markdown(
                    """
                    <div style="background-color: rgba(30, 136, 229, 0.08); 
                                border-left: 4px solid #1E88E5; 
                                border-radius: 8px; 
                                padding: 16px; 
                                margin: 12px 0px;">
                        <h4 style="margin: 0px 0px 10px 0px; color: #90CAF9; font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 6px;">
                            <span>⚡</span> Model: gliner_multi_pii-v1
                        </h4>
                        <ul style="margin: 0px; padding-left: 18px; font-size: 12.5px; color: #F8FAFC; line-height: 1.6; list-style-type: disc;">
                            <li style="margin-bottom: 8px;"><strong style="color: #64B5F6; font-weight: 600;">Architecture:</strong> ONNX-Optimized Span-Based Named Entity Recognition (NER).</li>
                            <li style="margin-bottom: 8px;"><strong style="color: #64B5F6; font-weight: 600;">Capabilities:</strong> Automatically detects patient and doctor names, dates, medical roles, address details, hospital locations, and personal identifiers (IDs, phone, email).</li>
                            <li style="margin-bottom: 8px;"><strong style="color: #64B5F6; font-weight: 600;">GDPR Security:</strong> Operates 100% locally on this device with absolute zero network footprint, fully compliant with strict hospital data privacy regulations.</li>
                            <li style="margin-bottom: 0px;"><strong style="color: #64B5F6; font-weight: 600;">Tuning:</strong> Adjust the slider above to control sensitivity. Lower values maximize PII detection, while higher values reduce false highlights.</li>
                        </ul>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
            else:
                ai_threshold = float(SETTINGS.get("ai_threshold", 0.45))

        # Scan for staged patients (to return grouped_patients)
        grouped_patients = {}
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

        return grouped_patients, ephemeral, manual_mode, custom_staging, new_active_model, ai_threshold, date_replacement_active, baseline_date, baseline_day_index, date_format, date_max_range_days

def render_acquisition_wizard(memory):
    """
    Renders the full-screen Patient Acquisition Wizard.
    Returns: bool (True if wizard is fully completed and AI should begin)
    """
    # Inject CSS for clinical button colors to avoid red anti-pattern
    st.markdown(
        """
        <style>
        /* Clinical blue button styles (safe continuation/actions) */
        div:has(> div > span#clinical-blue-btn) + div button,
        div:has(span#clinical-blue-btn) + div button {
            background-color: #1E88E5 !important;
            color: white !important;
            border-color: #1E88E5 !important;
            font-weight: 600 !important;
        }
        div:has(> div > span#clinical-blue-btn) + div button:hover,
        div:has(span#clinical-blue-btn) + div button:hover {
            background-color: #1565C0 !important;
            border-color: #1565C0 !important;
        }

        /* Clinical green button styles (primary launching actions) */
        div:has(> div > span#clinical-green-btn) + div button,
        div:has(span#clinical-green-btn) + div button {
            background-color: #10B981 !important;
            color: white !important;
            border-color: #10B981 !important;
            font-weight: 600 !important;
        }
        div:has(> div > span#clinical-green-btn) + div button:hover,
        div:has(span#clinical-green-btn) + div button:hover {
            background-color: #059669 !important;
            border-color: #059669 !important;
        }

        /* Clinical destructive red button styles (destructive actions) */
        div:has(> div > span#clinical-red-btn) + div button,
        div:has(span#clinical-red-btn) + div button {
            background-color: #EF4444 !important;
            color: white !important;
            border-color: #EF4444 !important;
            font-weight: 600 !important;
        }
        div:has(> div > span#clinical-red-btn) + div button:hover,
        div:has(span#clinical-red-btn) + div button:hover {
            background-color: #DC2626 !important;
            border-color: #DC2626 !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    col_title, col_logos = st.columns([3.5, 2.5])
    with col_title:
        st.title("🏥 Welcome")
        st.write("Secure offline anonymization of medical documents using local Artificial Intelligence.")
        
    with col_logos:
        import base64
        assets_dir = Path(__file__).parent.parent / "assets"
        logo_unito_path = assets_dir / "logoUnito.png"
        logo_ecdc_path = assets_dir / "ECDC_logo.svg.png"
        
        unito_b64 = ""
        ecdc_b64 = ""
        if logo_unito_path.exists():
            try:
                with open(logo_unito_path, "rb") as f:
                    unito_b64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception:
                pass
        if logo_ecdc_path.exists():
            try:
                with open(logo_ecdc_path, "rb") as f:
                    ecdc_b64 = base64.b64encode(f.read()).decode('utf-8')
            except Exception:
                pass
                
        if unito_b64 or ecdc_b64:
            logos_html = "<div style='display: flex; align-items: center; justify-content: flex-end; gap: 12px; margin-top: 12px;'>"
            logos_html += "<span style='font-size: 13px; color: #94A3B8; font-weight: 500; white-space: nowrap;'>Software developed for a project of</span>"
            if unito_b64:
                logos_html += f"<img src='data:image/png;base64,{unito_b64}' style='height: 52px; width: auto; object-fit: contain; background: white; padding: 3px; border-radius: 6px;' />"
            if ecdc_b64:
                logos_html += f"<img src='data:image/png;base64,{ecdc_b64}' style='height: 52px; width: auto; object-fit: contain; background: white; padding: 3px; border-radius: 6px;' />"
            logos_html += "</div>"
            st.markdown(logos_html, unsafe_allow_html=True)
    
    with st.expander("📖 How it works & System Guide", expanded=False):
        st.markdown(
            """
            1. **📁 Upload Documents:** Categorize patient files into specific types (clinical records, labs, consultations, exams).
            2. **🤖 AI Scan:** The local engine auto-detects PII (names, dates, locations, IDs) with zero trace or network calls.
            3. **✍️ Manual Review:** Verify and adjust findings. Corrections on any page auto-propagate to subsequent pages instantly.
            4. **🔒 Secure Redaction:** Final approved PDFs are black-masked and structured in randomly-generated secure patient folders.
            """
        )
    
    st.warning(
        "⚠️ **Research Prototype:** Local GDPR-compliant offline anonymization. "
        "A human operator must supervise and verify all redacted documents before clinical use."
    )
    
    # Operator Identity for GDPR Accountability
    st.markdown("### ✍️ Operator Signature")
    st.caption("Please provide your name to sign off on this anonymization session (required for GDPR Audit).")
    col_fn, col_ln = st.columns(2)
    with col_fn:
        operator_fname = st.text_input("First Name", key="operator_first_name")
    with col_ln:
        operator_lname = st.text_input("Last Name", key="operator_last_name")
        
    operator_ready = bool(operator_fname.strip() and operator_lname.strip())
    
    if not operator_ready:
        st.info("ℹ️ Please enter your First and Last Name to unlock the session start buttons.")
    
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

    # Wizard State Init
    if 'wizard_total' not in st.session_state:
        st.session_state['wizard_total'] = 0
    if 'wizard_current_step' not in st.session_state:
        st.session_state['wizard_current_step'] = 1
        
    # Phase 1: Setup
    if st.session_state['wizard_total'] == 0:
        st.divider()
        
        # Resume interrupted session section if staging has previous patients
        if existing_staged:
            st.markdown("### 🔄 Interrupted Session Detected")
            st.info(f"💾 **{len(existing_staged)} Patient(s) from a previous session detected in Staging.** You can resume the analysis or clear the queue.")
            
            confirm_key = "confirm_delete_staging"
            if st.session_state.get(confirm_key, False):
                st.warning("⚠️ **Are you sure you want to delete the previous session's patients?** This action cannot be undone.")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    st.markdown('<span id="clinical-red-btn"></span>', unsafe_allow_html=True)
                    if st.button("🗑️ Yes, Delete", use_container_width=True, type="primary"):
                        def remove_readonly(func, path, _):
                            os.chmod(path, stat.S_IWRITE)
                            func(path)
                        for d in existing_staged:
                            shutil.rmtree(STAGING_DIR / d, onerror=remove_readonly)
                        st.session_state[confirm_key] = False
                        st.success("Previous session deleted successfully.")
                        st.rerun()
                with col_no:
                    if st.button("❌ Cancel", use_container_width=True):
                        st.session_state[confirm_key] = False
                        st.rerun()
            else:
                col_resume, col_del = st.columns([3, 1])
                with col_resume:
                    st.markdown('<span id="clinical-blue-btn"></span>', unsafe_allow_html=True)
                    if st.button("🔄 Resume Interrupted Session", use_container_width=True, type="primary"):
                        if not operator_ready:
                            st.error("⚠️ Please fill in your First and Last Name in the Operator Signature section above to proceed.")
                        else:
                            st.session_state['auto_start_analysis'] = True
                            st.rerun()
                with col_del:
                    st.markdown('<span id="clinical-red-btn"></span>', unsafe_allow_html=True)
                    if st.button("🗑️ Delete Session", use_container_width=True):
                        st.session_state[confirm_key] = True
                        st.rerun()
            st.divider()
            
        # Initialize session state for patient count if not present
        if 'patients_count_selection' not in st.session_state:
            st.session_state['patients_count_selection'] = 1
            
        # Synchronize input state
        if 'patients_count_input' not in st.session_state:
            st.session_state['patients_count_input'] = st.session_state['patients_count_selection']
            
        # Callback functions for buttons to safely modify input state before widget instantiation
        def increment_count():
            if st.session_state['patients_count_selection'] < 500:
                st.session_state['patients_count_selection'] += 1
                st.session_state['patients_count_input'] = st.session_state['patients_count_selection']

        def decrement_count():
            if st.session_state['patients_count_selection'] > 1:
                st.session_state['patients_count_selection'] -= 1
                st.session_state['patients_count_input'] = st.session_state['patients_count_selection']
            
        col_left, col_spacer, col_right = st.columns([4.0, 1.0, 3.0])
        
        with col_left:
            # 1. Security (One-Way Valve)
            st.markdown("### 🔒 Step 1: Security Setup")
            
            st.caption("To prevent PHI from touching the USB drive before redaction, define a temporary folder on the hospital PC.")
            
            current_staging = SETTINGS.get("custom_staging_path", "")
            if current_staging:
                st.success(f"**Active Staging:**\n`{current_staging}`")
            else:
                st.info(f"**Active Staging:**\nHost Temp (Default)")
                
            # Directory Picker Workaround (Native Windows dialog with web-explorer fallback)
            if st.button("📁 Select Local Hospital Folder (C:\\...)", use_container_width=True, key="main_select_folder"):
                try:
                    import subprocess
                    import sys
                    
                    # PowerShell command to open a modern Explorer-style folder dialog using the OpenFileDialog hack (looks like the screenshot)
                    ps_script = (
                        "[System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms') | Out-Null; "
                        "$d = New-Object System.Windows.Forms.OpenFileDialog; "
                        "$d.ValidateNames = $false; "
                        "$d.CheckFileExists = $false; "
                        "$d.CheckPathExists = $true; "
                        "$d.FileName = 'Select this folder'; "
                        "$d.Title = 'Select Secure Hospital Staging Folder'; "
                        "if ($d.ShowDialog() -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output ([System.IO.Path]::GetDirectoryName($d.FileName)) }"
                    )
                    cmd = ["powershell", "-NoProfile", "-Command", ps_script]
                    
                    # Hide powershell console window popup on Windows
                    startupinfo = None
                    if os.name == 'nt':
                        startupinfo = subprocess.STARTUPINFO()
                        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                        startupinfo.wShowWindow = subprocess.SW_HIDE
                        
                    result = subprocess.run(
                        cmd,
                        capture_output=True,
                        text=True,
                        startupinfo=startupinfo,
                        check=True
                    )
                    selected_path = result.stdout.strip()
                    
                    if selected_path:
                        normalized_path = os.path.normpath(selected_path)
                        st.session_state['new_custom_staging'] = normalized_path
                        st.session_state['show_folder_picker'] = False
                        st.rerun()
                except Exception as e:
                    # In case of any exception (e.g., if not running on Windows or PowerShell error), fallback to web explorer
                    st.session_state['show_folder_picker'] = True
                    st.rerun()
                
            if st.session_state.get('show_folder_picker', False):
                st.markdown("#### 🗂️ Folder Explorer")
                
                # Init current view path
                if 'picker_curr_path' not in st.session_state:
                    import platform
                    st.session_state['picker_curr_path'] = "C:\\" if platform.system() == "Windows" else "/"
                    
                curr = st.session_state['picker_curr_path']
                path_obj = Path(curr)
                col_up, col_sel, col_cancel = st.columns([1, 2, 1])
                with col_up:
                    if st.button("⬆️ Up", use_container_width=True, key="picker_up_btn"):
                        st.session_state['picker_curr_path'] = str(path_obj.parent)
                        st.rerun()
                with col_sel:
                    if st.button(f"✅ Select '{path_obj.name or curr}'", type="primary", use_container_width=True, key="picker_sel_btn"):
                        st.session_state['new_custom_staging'] = curr
                        st.session_state['show_folder_picker'] = False
                        st.rerun()
                with col_cancel:
                    if st.button("❌ Cancel", use_container_width=True, key="picker_cancel_btn"):
                        st.session_state['show_folder_picker'] = False
                        st.rerun()
                
                # List directories
                try:
                    folders = [f.name for f in os.scandir(curr) if f.is_dir() and not f.name.startswith('.')]
                    folders.sort()
                    
                    st.caption(f"Current: `{curr}`")
                    
                    with st.container(height=300):
                        for folder in folders:
                            if st.button(f"📁 {folder}", key=f"btn_main_fld_{folder}", use_container_width=True):
                                st.session_state['picker_curr_path'] = str(path_obj / folder)
                                st.rerun()
                except PermissionError:
                    st.error("Access Denied to this folder.")
                    
            if st.button("Reset to Host Temp Default", use_container_width=True, key="main_reset_folder"):
                st.session_state['new_custom_staging'] = ""
                st.rerun()
                
        with col_right:
            # 2. Setup Batch
            st.markdown("### 🔢 Step 2: Setup Batch")
            st.write("Select the number of patients you want to anonymize in this session:")
            
            # Direct Big Number Input styled as a premium card (scoped only to main view content, excluding sidebar)
            st.markdown(
                """
                <style>
                /* Target the wrapper div of the number input */
                div[data-testid="stMain"] div[data-testid="stNumberInput"] > div[data-testid="stNumberInputContainer"],
                div[data-testid="stMain"] div[data-testid="stNumberInput"] > div {
                    background-color: #1E232E !important;
                    border: 2px solid #4F5E70 !important;
                    border-radius: 12px !important;
                    box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.15) !important;
                    padding: 0px !important;
                    height: 50px !important;
                    display: flex !important;
                    align-items: center !important;
                    justify-content: center !important;
                }

                /* Style the input field inside to be centered and colored */
                div[data-testid="stMain"] div[data-testid="stNumberInput"] input {
                    color: #FF4B4B !important;
                    font-size: 28px !important;
                    font-weight: 700 !important;
                    text-align: center !important;
                    background: transparent !important;
                    border: none !important;
                    height: 100% !important;
                    width: 100% !important;
                    padding: 0px !important;
                    outline: none !important;
                    box-shadow: none !important;
                    display: block !important;
                }

                /* Hide standard Streamlit spinner buttons completely */
                div[data-testid="stMain"] div[data-testid="stNumberInput"] button {
                    display: none !important;
                    width: 0px !important;
                    height: 0px !important;
                    visibility: hidden !important;
                    opacity: 0 !important;
                }

                /* Hide default HTML5 browser spinners */
                div[data-testid="stMain"] div[data-testid="stNumberInput"] input::-webkit-outer-spin-button,
                div[data-testid="stMain"] div[data-testid="stNumberInput"] input::-webkit-inner-spin-button {
                    -webkit-appearance: none !important;
                    margin: 0 !important;
                }
                div[data-testid="stMain"] div[data-testid="stNumberInput"] input[type=number] {
                    -moz-appearance: textfield !important;
                }

                /* Make sure the focus state of the input does not show default Streamlit styling */
                div[data-testid="stMain"] div[data-testid="stNumberInput"] > div:focus-within {
                    border-color: #FF4B4B !important;
                    box-shadow: 0px 0px 8px rgba(255, 75, 75, 0.5) !important;
                }
                
                /* Remove extra spacing or padding that Streamlit might add below the input */
                div[data-testid="stMain"] div[data-testid="stNumberInput"] {
                    margin-bottom: 12px !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
            
            total_input = st.number_input(
                "Patients Count Selection",
                min_value=1,
                max_value=500,
                key="patients_count_input",
                label_visibility="collapsed"
            )
            
            # Keep both states in sync
            st.session_state['patients_count_selection'] = total_input
            
            # Control buttons side-by-side (➖ on left, ➕ on right)
            col_minus, col_plus = st.columns(2)
            with col_minus:
                st.button("➖", key="dec_btn", use_container_width=True, on_click=decrement_count)
            with col_plus:
                st.button("➕", key="inc_btn", use_container_width=True, on_click=increment_count)
                        
            # Bottom of stacked card: Start Ingestion full-width button
            st.markdown('<span id="clinical-green-btn"></span>', unsafe_allow_html=True)
            if st.button("Start Ingestion", type="primary", use_container_width=True):
                if not operator_ready:
                    st.error("⚠️ Please fill in your First and Last Name in the Operator Signature section above to proceed.")
                else:
                    st.session_state['wizard_total'] = st.session_state['patients_count_selection']
                    st.rerun()
                 
        # Pre-emptive Memory Management compressed into a dedicated expander dropdown menu
        st.divider()
        with st.expander("🧠 Pre-emptive Memory Management", expanded=False):
            st.write("Configure learned terms, custom whitelist, and blacklist presets directly below:")
            memory_manager_ui(memory)
        
        render_diagnostic_panel(memory)
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
        st.markdown("### 📘 Clinical Records")
        st.caption("Descriptive documents containing prose and names.")
        clinica_files = st.file_uploader("Upload Clinical Records", type="pdf", accept_multiple_files=True, key=f"up_c_{current}")
        
    with c2:
        st.markdown("### 📊 Structured Data")
        st.caption("Tabular lab results, blood work, etc.")
        laboratori_files = st.file_uploader("Upload Lab Results", type="pdf", accept_multiple_files=True, key=f"up_l_{current}")

    st.markdown("---")
    
    c3, c4 = st.columns(2)
    with c3:
        st.markdown("### 🩺 Instrumental Exams")
        st.caption("ECGs, radiological reports, spirometry, etc.")
        esami_files = st.file_uploader("Upload Instrumental Exams", type="pdf", accept_multiple_files=True, key=f"up_e_{current}")
        
    with c4:
        st.markdown("### 👨‍⚕️ Specialist Consultations")
        st.caption("Specialist visit reports (cardiology, neurology, etc.)")
        consulenze_files = st.file_uploader("Upload Specialist Consultations", type="pdf", accept_multiple_files=True, key=f"up_s_{current}")
        
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
             if not clinica_files and not laboratori_files and not esami_files and not consulenze_files:
                 st.error("You must upload at least one file to proceed.")
             else:
                 # Construct physical staging envelope
                 target_pat_dir = STAGING_DIR / assigned_uuid
                 dir_clinica = target_pat_dir / "CARTELLA_CLINICA"
                 dir_lab = target_pat_dir / "DATI_STRUTTURATI"
                 dir_esami = target_pat_dir / "ESAMI_STRUMENTALI"
                 dir_consulenze = target_pat_dir / "CONSULENZE_SPECIALISTICHE"
                 
                 dir_clinica.mkdir(parents=True, exist_ok=True)
                 dir_lab.mkdir(parents=True, exist_ok=True)
                 dir_esami.mkdir(parents=True, exist_ok=True)
                 dir_consulenze.mkdir(parents=True, exist_ok=True)
                 
                 for cf in clinica_files:
                     with open(dir_clinica / cf.name, "wb") as f: f.write(cf.getbuffer())
                 for lf in laboratori_files:
                     with open(dir_lab / lf.name, "wb") as f: f.write(lf.getbuffer())
                 for ef in esami_files:
                     with open(dir_esami / ef.name, "wb") as f: f.write(ef.getbuffer())
                 for sf in consulenze_files:
                     with open(dir_consulenze / sf.name, "wb") as f: f.write(sf.getbuffer())
                     
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
                     
    render_diagnostic_panel(memory)
    return False

def render_page_editor(col_canvas, col_tools, file_name, page_index, pdf_processor, current_terms, manual_rects_for_page):
    """
    Renders the editor for a single page:
    - Left: Canvas for manual redaction
    - Right: Text list editing
    Returns: (updated_terms_list, new_manual_rects_for_page_or_None)
    """
    
    # --- Text Column ---
    with col_tools:
        st.subheader("Text Redaction")
        st.caption("Edit terms found by AI/Memory")
        
        # 1. Search input
        search_query = st.text_input(
            "🔍 Search...",
            value="",
            placeholder="🔍 Search a term...",
            label_visibility="collapsed",
            key=f"search_{file_name}_{page_index}"
        )
        
        # 2. Letter/Symbol filter segmented control
        options = ["ALL"] + [chr(i) for i in range(ord('A'), ord('Z')+1)] + ["#"]
        selected_letter = st.segmented_control(
            "Filter by letter",
            options=options,
            default="ALL",
            label_visibility="collapsed",
            key=f"letter_{file_name}_{page_index}"
        )
        selected_letter = selected_letter or "ALL"
        
        # Extract and sort all terms case-insensitively
        all_terms = sorted(list({t.strip() for t in current_terms if t.strip()}), key=str.lower)
        
        # Apply Search and Alphabet filters to get the visible subset
        visible_terms = []
        for t in all_terms:
            # Search query filter (case-insensitive)
            if search_query and search_query.strip().lower() not in t.lower():
                continue
                
            # Letter/symbol filter
            if selected_letter != "ALL":
                if not t:
                    continue
                first_char = t[0].upper()
                if selected_letter == "#":
                    if first_char.isalpha():
                        continue
                else:
                    if first_char != selected_letter:
                        continue
            visible_terms.append(t)
            
        # Track the last programmatic state rendered in the text area (terms & filters)
        last_rendered_key = f"last_rendered_{file_name}_{page_index}"
        current_state = (search_query, selected_letter, tuple(sorted(current_terms)))
        
        # Stable key for st.text_area
        text_area_key = f"txt_{file_name}_{page_index}"
        
        # If programmatic state changed OR if the text area widget key has been unmounted and cleared by Streamlit, re-initialize it
        if (text_area_key not in st.session_state) or (last_rendered_key not in st.session_state) or (st.session_state[last_rendered_key] != current_state):
            st.session_state[text_area_key] = "\n".join(visible_terms)
            st.session_state[last_rendered_key] = current_state
            
        text_input = st.text_area(
            f"Terms to redact from Page {page_index+1}",
            height=450,
            key=text_area_key
        )
        
        # Process updates using localized diffing to preserve hidden terms
        edited_visible_terms = [t.strip() for t in text_input.split("\n") if t.strip()]
        
        old_visible_set = set(visible_terms)
        new_visible_set = set(edited_visible_terms)
        
        added_filtered = new_visible_set - old_visible_set
        removed_filtered = old_visible_set - new_visible_set
        
        full_terms_set = set(all_terms)
        full_terms_set.update(added_filtered)
        full_terms_set.difference_update(removed_filtered)
        
        # Final fully updated terms list (used for canvas rendering and returned)
        updated_terms = sorted(list({t for t in full_terms_set if t.strip()}), key=str.lower)
        
        if added_filtered or removed_filtered:
            rev_key_temp = f"canvas_rev_{file_name}_{page_index}"
            st.session_state[rev_key_temp] = st.session_state.get(rev_key_temp, 0) + 1
            
        # Graphical Redaction legend and controls enclosed in a styled container
        with st.container(border=True):
            st.markdown(
                """
                <h4 style="margin-top: 0; color: #fff;">✏️ Graphical Redaction</h4>
                <p style="color: #ccc; font-size: 0.95em; line-height: 1.5; margin-bottom: 15px;">
                Use your <b>left mouse button</b> to click and draw red rectangles directly onto the document canvas on the left. 
                This is ideal for permanently erasing non-textual graphical elements like <b>logos, signatures, stamps, or barcodes</b>.<br><br>
                <i>Note: drawn rectangles cannot be resized or moved once applied. Use Undo if you need to retry!</i>
                </p>
                """, 
                unsafe_allow_html=True
            )
            
            apply_to_all = st.checkbox(
                "🔄 Apply drawn rectangles to ALL pages of this document", 
                value=True, 
                help="Perfect for repeating headers, hospital logos, or page-margin markings."
            )
            
            btn_col1, btn_col2 = st.columns(2)
            with btn_col1:
                action_undo = st.button("↩️ Undo Last Action", use_container_width=True)
            with btn_col2:
                action_clear_all = st.button("🗑️ Delete All", use_container_width=True)
    
    # --- Canvas Column ---
    with col_canvas:
        st.subheader("🔎 Manual Redaction")
        
        # Mode switch and Zoom controls
        if 'canvas_width' not in st.session_state:
            st.session_state['canvas_width'] = 1100
        canvas_width = st.session_state['canvas_width']
        
        # Inject CSS to make the zoom buttons look like a cohesive button group
        st.markdown(
            """
            <style>
            /* Container for the zoom controls */
            div[data-testid="stHorizontalBlock"]:has(button[help="Zoom Out"]) {
                background-color: #1E293B;
                border-radius: 8px;
                padding: 4px;
                border: 1px solid #334155;
                box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
                align-items: center;
                gap: 2px !important;
            }
            /* Style the individual buttons inside the group to be seamless */
            div[data-testid="stHorizontalBlock"]:has(button[help="Zoom Out"]) button {
                border: none !important;
                background-color: transparent !important;
                color: #94A3B8 !important;
                font-weight: 600 !important;
                padding: 4px 0px !important;
            }
            div[data-testid="stHorizontalBlock"]:has(button[help="Zoom Out"]) button:hover {
                background-color: #334155 !important;
                color: #F8FAFC !important;
                border-radius: 6px !important;
            }
            </style>
            """, unsafe_allow_html=True
        )

        col_mode, col_spacer, col_zoom = st.columns([1.5, 1.5, 1.2])
        with col_mode:
            canvas_mode = st.segmented_control(
                "Select mode", 
                options=["✏️ Draw", "🧹 Delete"], 
                default="✏️ Draw",
                key=f"canvas_mode_{file_name}_{page_index}",
                label_visibility="collapsed"
            )
        with col_zoom:
            zoom_pct = int(canvas_width / 1100 * 100)
            z_col1, z_col2, z_col3 = st.columns([1, 1.2, 1], gap="small")
            with z_col1:
                if st.button("➖", key=f"zoom_out_{file_name}_{page_index}", help="Zoom Out", use_container_width=True):
                    st.session_state['canvas_width'] = max(500, canvas_width - 100)
                    st.rerun()
            with z_col2:
                if st.button(f"{zoom_pct}%", key=f"zoom_reset_{file_name}_{page_index}", help="Reset Zoom", use_container_width=True):
                    st.session_state['canvas_width'] = 1100
                    st.rerun()
            with z_col3:
                if st.button("➕", key=f"zoom_in_{file_name}_{page_index}", help="Zoom In", use_container_width=True):
                    st.session_state['canvas_width'] = min(2200, canvas_width + 100)
                    st.rerun()
                    
        drawing_mode = "rect" if canvas_mode == "✏️ Draw" else "transform"
        
        if drawing_mode == "rect":
            st.info("✏️ **Draw Mode Active:** Click and drag your left mouse button on the document canvas to highlight and redact any non-textual elements like signatures, logos, or barcodes.")
        elif drawing_mode == "transform":
            st.info("🧹 **Delete Mode Active:** Double-click on any red rectangle to delete it, or click to select it and press **DELETE / Backspace** on your keyboard.")
                
        # Render background image
        # Cache the generated PIL image object. If we pass a brand new PIL image pointer to st_canvas 
        # on every rerun, it interprets it as a "new background" and fires an infinite loop of redraws.
        terms_hash = hash(tuple(updated_terms))
        bg_cache_key = f"bg_{file_name}_{page_index}_{terms_hash}_{canvas_width}"
        
        # Free up memory from old page/term caches by keeping only the active one
        if st.session_state.get('active_bg_key') != bg_cache_key:
            old_key = st.session_state.get('active_bg_key')
            if old_key and old_key in st.session_state:
                del st.session_state[old_key]
                
            # Ora render_page_for_canvas ritorna anche ai_rects (coordinate PDF dei termini)
            st.session_state[bg_cache_key] = pdf_processor.render_page_for_canvas(page_index, updated_terms, max_width=canvas_width)
            st.session_state['active_bg_key'] = bg_cache_key
            
        bg_img, scale_x, scale_y, ai_rects = st.session_state[bg_cache_key]
        
        if bg_img:
            # Inject CSS to make Canvas Toolbar Icons (SVG) visible on Dark Mode, center the canvas
            st.markdown(
                """
                <style>
                /* Invert colors of SVG icons inside the streamlit canvas wrapper */
                div[data-testid="stCanvas"] svg {
                    filter: invert(1) brightness(2);
                }
                /* Center the canvas wrapper inside the parent container */
                div[data-testid="stCanvas"] {
                    margin: 0 auto !important;
                }
                /* Center the custom component sandbox iframe horizontally */
                div[data-testid="stColumn"] div[data-testid="stComponentSandbox"] {
                    display: flex !important;
                    justify-content: center !important;
                }
                div[data-testid="stColumn"] div[data-testid="stComponentSandbox"] iframe {
                    margin: 0 auto !important;
                }
                /* Style the Graphical Redaction bordered container in premium Dark Grey */
                div[data-testid="stColumn"] div[data-testid="stVerticalBlockBorderWrapper"] {
                    background-color: #262730 !important;
                    border: 1px solid #444444 !important;
                    border-radius: 8px !important;
                    padding: 15px !important;
                }
                </style>
                """,
                unsafe_allow_html=True
            )
            
            json_cache_key = f"canvas_json_{file_name}_{page_index}"
            rev_key = f"canvas_rev_{file_name}_{page_index}"
            rev = st.session_state.get(rev_key, 0)
            widget_key = f"canvas_{file_name}_{page_index}_{rev}_{canvas_width}"
            
            # To prevent the st_canvas floating-point infinite React loop, we MUST ensure 
            # the `initial_drawing` prop remains completely static for the lifetime of the widget_key.
            snapshot_key = f"canvas_snapshot_{widget_key}"
            if snapshot_key not in st.session_state:
                # Creiamo gli oggetti JSON (FabricJS) partendo dai riquadri trovati dall'IA
                objects = []
                for idx, r_data in enumerate(ai_rects):
                    r = r_data["rect"]
                    term = r_data["term"]
                    # Converti da PDF Coords a Canvas Coords
                    left = r.x0 / scale_x
                    top = r.y0 / scale_y
                    width = (r.x1 - r.x0) / scale_x
                    height = (r.y1 - r.y0) / scale_y
                    objects.append({
                        "type": "rect",
                        "left": left,
                        "top": top,
                        "width": width,
                        "height": height,
                        "fill": "rgba(255, 0, 0, 0.3)",
                        "stroke": "#FFFFFF",
                        "strokeWidth": 2,
                        "originX": "left",
                        "originY": "top",
                        "version": "4.4.0",
                        "is_ai": True,  # Custom flag
                        "strokeDashArray": [1, 0], # Hidden tag for robust identification
                        "id": f"ai_{idx}",
                        "term": term
                    })
                
                # Aggiungiamo anche i manual rects già esistenti
                for i, mr in enumerate(manual_rects_for_page):
                    left = mr[0] / scale_x
                    top = mr[1] / scale_y
                    width = (mr[2] - mr[0]) / scale_x
                    height = (mr[3] - mr[1]) / scale_y
                    objects.append({
                        "type": "rect",
                        "left": left,
                        "top": top,
                        "width": width,
                        "height": height,
                        "fill": "rgba(255, 0, 0, 0.5)",
                        "stroke": "#FFFFFF",
                        "strokeWidth": 2,
                        "strokeDashArray": [2, 0], # Hidden tag for manual identification
                        "originX": "left",
                        "originY": "top",
                        "version": "4.4.0",
                        "is_manual": True
                    })
                
                st.session_state[snapshot_key] = {"version": "4.4.0", "objects": objects}
                
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
                drawing_mode=drawing_mode,
                key=widget_key,
                display_toolbar=True
            )
            
            # If canvas_result.json_data is None, it means the canvas hasn't initialized its state back to Python yet.
            if canvas_result.json_data is not None:
                # Update the raw JSON cache instantly as long as it isn't an empty reset phase
                st.session_state[json_cache_key] = canvas_result.json_data
                new_user_rects = []
                remaining_ai_ids = set()
                
                for obj in canvas_result.json_data["objects"]:
                    if obj["type"] == "rect":
                        # Match AI rects by coordinate matching. Fabric.js may strip custom attributes
                        # or normalize colors, so spatial location is the only 100% reliable anchor.
                        x = obj["left"]
                        y = obj["top"]
                        w = obj["width"] * obj.get("scaleX", 1.0)
                        h = obj["height"] * obj.get("scaleY", 1.0)
                        
                        x0 = x * scale_x
                        y0 = y * scale_y
                        x1 = (x + w) * scale_x
                        y1 = (y + h) * scale_y
                        
                        fill = obj.get("fill", "")
                        clean_fill = fill.replace(" ", "")
                        dash_array = obj.get("strokeDashArray", None)
                        
                        is_ai_match = False
                        
                        # Use hidden strokeDashArray tag OR fill color to robustly identify AI vs Manual rects
                        # AI rects have fill rgba(255,0,0,0.3) and strokeDashArray [1, 0]
                        # Manual rects have fill rgba(255,0,0,0.5) or 0.4 and strokeDashArray [2, 0] or None
                        is_ai_by_tag = dash_array == [1, 0]
                        is_ai_by_color = clean_fill == "rgba(255,0,0,0.3)"
                        
                        if is_ai_by_tag or is_ai_by_color:
                            # Find the closest matching AI rect
                            best_idx = -1
                            min_dist = float('inf')
                            for idx, r_data in enumerate(ai_rects):
                                ai_r = r_data["rect"]
                                dist = abs(ai_r[0] - x0) + abs(ai_r[1] - y0)
                                if dist < min_dist and dist < 25.0:  # Relaxed tolerance
                                    min_dist = dist
                                    best_idx = idx
                                    
                            if best_idx != -1:
                                remaining_ai_ids.add(f"ai_{best_idx}")
                                is_ai_match = True
                        else:
                            # If it's not the AI fill color/tag, it's definitely a manual rect
                            is_ai_match = False
                                
                        if not is_ai_match and not is_ai_by_tag and not is_ai_by_color:
                            new_user_rects.append([x0, y0, x1, y1])
                            
                # Deduplicate manual rects to prevent infinite summing/overlap accumulation
                seen_manual = set()
                deduped_rects = []
                for r in new_user_rects:
                    rect_key = (round(r[0], 1), round(r[1], 1), round(r[2], 1), round(r[3], 1))
                    if rect_key not in seen_manual:
                        seen_manual.add(rect_key)
                        deduped_rects.append(r)
                new_user_rects = deduped_rects

                # Heuristic to prevent transient empty canvas state from deleting all terms on load
                is_transient = len(canvas_result.json_data["objects"]) == 0 and len(initial_drawing["objects"]) > 0
                
                if is_transient:
                    # Return None for new_user_rects to prevent transient empty canvas from clearing manual drawings
                    return updated_terms, None, apply_to_all, action_undo, action_clear_all, []
                
                # Detect deleted AI terms from canvas (only in active transform/delete mode to prevent loading race-conditions)
                deleted_terms = []
                if drawing_mode == "transform":
                    for idx, r_data in enumerate(ai_rects):
                        if f"ai_{idx}" not in remaining_ai_ids:
                            deleted_terms.append(r_data["term"])
                
                return updated_terms, new_user_rects, apply_to_all, action_undo, action_clear_all, deleted_terms
            else:
                return updated_terms, None, apply_to_all, action_undo, action_clear_all, []
            
        else:
            st.error("Error rendering page.")
            return updated_terms, None, False, False, False, []
@st.fragment
def memory_manager_ui(memory, in_sidebar=False):
    # Inject CSS for high-density, compact lists with subtle separators and monospace monospace styling
    st.markdown(
        """
        <style>
        /* Compact terms list styles to override Streamlit row padding and margin */
        div.compact-terms-list div[data-testid="column"] {
            padding: 0px !important;
            margin: 0px !important;
            align-self: center !important;
        }
        /* Style inner row columns only, preventing outer grid columns from getting borders */
        div.compact-terms-list div[data-testid="column"] div[data-testid="stHorizontalBlock"] {
            gap: 4px !important;
            padding: 2px 0px !important;
            margin: 0px !important;
            border-bottom: 1px solid rgba(255, 255, 255, 0.05) !important;
        }
        div.compact-terms-list p {
            margin: 0px !important;
            padding: 0px !important;
            font-size: 13px !important;
            font-family: monospace !important;
            color: #E2E8F0 !important;
            line-height: 24px !important;
        }
        div.compact-terms-list button {
            padding: 0px 6px !important;
            margin: 0px !important;
            height: 24px !important;
            min-height: 24px !important;
            line-height: 24px !important;
            font-size: 12px !important;
            background-color: transparent !important;
            border: none !important;
            color: #EF4444 !important;
        }
        div.compact-terms-list button:hover {
            color: #DC2626 !important;
            background-color: rgba(239, 68, 68, 0.1) !important;
        }
        /* Tight gap for the vertical block containing list rows */
        div.compact-terms-list div[data-testid="stVerticalBlock"] > div {
            gap: 0px !important;
        }
        /* Inline Add Button inside text input */
        div[data-testid="stVerticalBlock"]:has(div.inline-add-container) {
            position: relative !important;
        }
        
        /* Hide the helper anchor markdown element completely so it takes 0px space */
        div.element-container:has(div.inline-add-container) {
            display: none !important;
        }

        /* Pad the input field so text doesn't clash with the inline '+' button */
        div.element-container:has(input#add_white) div[data-testid="stTextInput"] input,
        div.element-container:has(input#add_black) div[data-testid="stTextInput"] input {
            padding-right: 42px !important;
            border-radius: 8px !important;
        }

        /* Position the button wrapper absolute within the input field area */
        div.element-container:has(input#add_white) + div.element-container,
        div.element-container:has(input#add_black) + div.element-container {
            position: absolute !important;
            right: 4px !important;
            top: 4px !important;
            z-index: 99 !important;
            margin: 0px !important;
            padding: 0px !important;
            height: 30px !important;
            width: 30px !important;
        }

        /* Sleek, borderless pink plus button styling */
        div.element-container:has(input#add_white) + div.element-container button,
        div.element-container:has(input#add_black) + div.element-container button {
            background: transparent !important;
            border: none !important;
            color: #E24A8D !important; /* Premium pink accent matching user sketch */
            font-size: 22px !important;
            font-weight: 500 !important;
            line-height: 30px !important;
            padding: 0px !important;
            margin: 0px !important;
            height: 30px !important;
            min-height: 30px !important;
            width: 30px !important;
            box-shadow: none !important;
            cursor: pointer !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            transition: color 0.2s ease, transform 0.15s ease !important;
        }

        div.element-container:has(input#add_white) + div.element-container button:hover,
        div.element-container:has(input#add_black) + div.element-container button:hover {
            color: #F472B6 !important;
            background: rgba(226, 74, 141, 0.1) !important;
            border-radius: 6px !important;
            transform: scale(1.1) !important;
        }

        div.element-container:has(input#add_white) + div.element-container button:active,
        div.element-container:has(input#add_black) + div.element-container button:active {
            transform: scale(0.9) !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    last_deleted = st.session_state.get('last_deleted', None)

    if memory.ephemeral:
        st.warning("🕵️ Incognito Mode: Changes here will be lost on exit.")
        
    # --- PRESET DATA ---
    PRESETS = {
        "Italian Provinces (Redact)": {
            "type": "whitelist",
            "file": "sigle_province_italiane.json"
        },
        "Address Keywords (Redact)": {
            "type": "whitelist",
            "terms": ["Via", "Piazza", "Viale", "Corso", "V.le", "P.zza", "Strada", "C.so"]
        },
        "Clinical Labels (Keep)": {
            "type": "blacklist",
            "terms": ["Paziente:", "Nato il:", "Nata il:", "Data:", "CF:", "Referto:", "Codice Fiscale:", "Dati Strutturati", "PRONTO SOCCORSO"]
        },
        "Medical Roles (Keep)": {
            "type": "blacklist",
            "terms": ["Medico di Guardia", "Infermiera", "Specializzando", "Anestesista", "Caposala", "Personale Infermieristico", "Medico Curante"]
        },
        "Hospital Departments (Keep)": {
            "type": "blacklist",
            "terms": ["Cardiologia", "Radiologia", "Pronto Soccorso", "Chirurgia", "Medicina Generale", "Terapia Intensiva", "UOC"]
        },
        "Common Exams (Keep)": {
            "type": "blacklist",
            "terms": ["E.C.G.", "RX", "TC", "RMN", "Ecografia", "Analisi del Sangue", "Esami Ematochimici", "EGA", "M.C."]
        },
        "Anatomy Words (Keep)": {
            "type": "blacklist",
            "terms": ["Addome", "Torace", "SNC", "Arti", "Bacino", "Cuore", "Polmoni", "SNC", "Colonna"]
        },
        "Measurement Units (Keep)": {
            "type": "blacklist",
            "terms": ["mg/dL", "mmol/L", "mEq/L", "pg", "fL", "g/dL", "U/L"]
        }
    }

    # Helper to add/remove presets
    def toggle_preset(preset_name):
        config = PRESETS[preset_name]
        terms = []
        if "file" in config:
            import json
            from config import PROVINCE_FILE
            try:
                with open(PROVINCE_FILE, "r", encoding="utf-8") as f:
                    terms = json.load(f)
            except: pass
        else:
            terms = config["terms"]
            
        if config["type"] == "whitelist":
            # Check if all terms are already in whitelist
            all_in = all(t in memory.whitelist for t in terms)
            if all_in:
                memory.whitelist.difference_update(terms)
            else:
                memory.add_to_whitelist(terms)
        else:
            # Check if all terms are already in blacklist
            all_in = all(t in memory.blacklist for t in terms)
            if all_in:
                memory.blacklist.difference_update(terms)
                memory.blacklist_lower = {t.lower() for t in memory.blacklist}
            else:
                memory.add_to_blacklist(terms)
        
        memory.save_memory()

    # --- UI LAYOUT ---
    t1, t2, t3, t4 = st.tabs(["🚫 Terms to Redact", "🔒 Terms to Keep (Do Not Redact)", "🛠️ Presets", "🎯 Advanced Rules"])
    
    with t4:
        st.subheader("Advanced Recognition Rules")
        st.caption("Enable or disable dynamic recognition rules for IDs, Signatures, Dates, and common structures.")
        
        from regex_rules_manager import RegexRulesManager, DEFAULT_REGEX_RULES
        regex_manager = RegexRulesManager()
        
        c1, c2 = st.columns([3, 1])
        if c2.button("🔄 Reset to Default", key="btn_reset_rules", use_container_width=True):
            regex_manager.reset_to_defaults()
            st.rerun()
            
        for rule_name, rule_data in regex_manager.rules.items():
            active = rule_data.get("active", True)
            desc = rule_data.get("description", "")
            is_default = rule_name in DEFAULT_REGEX_RULES
            
            # Use columns to align checkbox, description, and delete button (if custom)
            if not is_default:
                rc1, rc2, rc3 = st.columns([2.5, 4.5, 1])
                with rc1:
                    new_active = st.checkbox(rule_name, value=active, key=f"regex_{rule_name}")
                with rc2:
                    st.caption(desc)
                with rc3:
                    if st.button("🗑️", key=f"del_rule_{rule_name}", use_container_width=True):
                        del regex_manager.rules[rule_name]
                        regex_manager.save_rules()
                        st.rerun()
            else:
                rc1, rc2 = st.columns([2.5, 5.5])
                with rc1:
                    new_active = st.checkbox(rule_name, value=active, key=f"regex_{rule_name}")
                with rc2:
                    st.caption(desc)
                
            if new_active != active:
                regex_manager.rules[rule_name]["active"] = new_active
                regex_manager.save_rules()
                st.rerun()
                
        st.divider()
        st.subheader("➕ Add Custom Recognition Rule")
        st.caption("Define custom Regular Expressions (Regex) to match specific identifiers, codes, or formats unique to your clinical workflows.")
        
        col_new_name, col_new_pattern = st.columns([2, 3])
        with col_new_name:
            rule_name_input = st.text_input("Rule Name", placeholder="e.g. Italian Postal Code", key="new_rule_name")
        with col_new_pattern:
            rule_pattern_input = st.text_input("Regex Pattern", placeholder="e.g. \\b\\d{5}\\b", key="new_rule_pattern")
            
        rule_desc_input = st.text_input("Description / Help Text", placeholder="Describe what this rule matches (e.g. Matches 5-digit CAP/Zip codes)", key="new_rule_desc")
        
        # Add button styled with clinical green color
        st.markdown('<span id="clinical-green-btn"></span>', unsafe_allow_html=True)
        btn_add_rule = st.button("➕ Add Recognition Rule", key="btn_add_custom_rule", use_container_width=True)
        
        if btn_add_rule:
            name = rule_name_input.strip()
            pattern = rule_pattern_input.strip()
            desc = rule_desc_input.strip()
            
            if not name:
                st.error("⚠️ Please enter a Rule Name.")
            elif not pattern:
                st.error("⚠️ Please enter a Regex Pattern.")
            elif name in regex_manager.rules:
                st.error(f"⚠️ A rule named '{name}' already exists.")
            else:
                # Validate regex pattern
                try:
                    import re
                    re.compile(pattern)
                    # Pattern is valid! Save it.
                    regex_manager.rules[name] = {
                        "active": True,
                        "pattern": pattern,
                        "group": 0,
                        "description": desc if desc else f"Custom pattern: {pattern}"
                    }
                    regex_manager.save_rules()
                    st.session_state["new_rule_name"] = ""
                    st.session_state["new_rule_pattern"] = ""
                    st.session_state["new_rule_desc"] = ""
                    st.success(f"✅ Rule '{name}' added successfully!")
                    st.rerun()
                except re.error as e:
                    st.error(f"⚠️ Invalid Regex Pattern: {e}")

    with t3:
        st.subheader("Quick-Toggle Presets")
        st.caption("Apply batches of common terms to your memory.")
        
        cols = st.columns(2)
        for i, preset_name in enumerate(PRESETS.keys()):
            col = cols[i % 2]
            config = PRESETS[preset_name]
            
            # Check current status
            terms = []
            if "file" in config:
                # For provinces, just check one sample for UI speed
                is_active = "(MI)" in memory.whitelist
            else:
                is_active = all(t in (memory.whitelist if config["type"] == "whitelist" else memory.blacklist) for t in config["terms"])
            
            btn_label = f"✅ {preset_name}" if is_active else f"➕ {preset_name}"
            if col.button(btn_label, key=f"pre_{preset_name}", use_container_width=True):
                toggle_preset(preset_name)
                st.rerun()

    with t1:
        c_met1, c_met2 = st.columns([2, 1])
        with c_met1:
            st.markdown(f"### {len(memory.whitelist)} terms marked to Redact")
        with c_met2:
            confirm_key_w = "confirm_clear_white"
            if st.session_state.get(confirm_key_w, False):
                st.write(f"🗑️ Delete all {len(memory.whitelist)} terms?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("🗑️ Yes", key="clear_white_confirm_yes", type="primary", use_container_width=True):
                        st.session_state['last_deleted'] = {'term': list(memory.whitelist), 'type': 'whitelist_all'}
                        memory.whitelist = set()
                        memory.save_memory()
                        st.session_state[confirm_key_w] = False
                        st.rerun()
                with col_no:
                    if st.button("❌ No", key="clear_white_confirm_no", use_container_width=True):
                        st.session_state[confirm_key_w] = False
                        st.rerun()
            else:
                if st.button("🗑️ Clear All", key="clear_white", use_container_width=True):
                    if len(memory.whitelist) > 0:
                        st.session_state[confirm_key_w] = True
                        st.rerun()
                
        # Undo Banner for Single or All Whitelist Deletions
        if last_deleted and last_deleted.get('type') in ['whitelist', 'whitelist_all']:
            undo_cols = st.columns([4, 1])
            with undo_cols[0]:
                if last_deleted['type'] == 'whitelist_all':
                    st.info("🗑️ Cleared all terms from Redact list.")
                else:
                    st.info(f"🗑️ Term '{last_deleted['term']}' removed from Redact list.")
            with undo_cols[1]:
                if st.button("↩️ Undo", key="undo_w", use_container_width=True):
                    if last_deleted['type'] == 'whitelist_all':
                        memory.whitelist.update(last_deleted['term'])
                    else:
                        memory.whitelist.add(last_deleted['term'])
                    memory.save_memory()
                    st.session_state['last_deleted'] = None
                    st.rerun()
                
        search_w = st.text_input("Search Terms to Redact", placeholder="Search Terms", key="search_whitelist").lower()
        
        filtered_w = sorted([t for t in memory.whitelist if search_w in t.lower()])
        
        st.markdown('<div class="compact-terms-list">', unsafe_allow_html=True)
        with st.container(height=300):
            if not filtered_w:
                st.write("No terms found.")
            else:
                if in_sidebar:
                    for term in filtered_w:
                        col_t, col_b = st.columns([5.5, 1])
                        col_t.write(term)
                        if col_b.button("🗑️", key=f"del_w_{term}", use_container_width=True):
                            st.session_state['last_deleted'] = {'term': term, 'type': 'whitelist'}
                            memory.whitelist.remove(term)
                            memory.save_memory()
                            st.rerun()
                else:
                    col1, col2, col3 = st.columns(3)
                    col1_terms = filtered_w[0::3]
                    col2_terms = filtered_w[1::3]
                    col3_terms = filtered_w[2::3]
                    
                    for col, terms in zip([col1, col2, col3], [col1_terms, col2_terms, col3_terms]):
                        with col:
                            for term in terms:
                                col_t, col_b = st.columns([4, 1.2])
                                col_t.write(term)
                                if col_b.button("🗑️", key=f"del_w_{term}"):
                                    st.session_state['last_deleted'] = {'term': term, 'type': 'whitelist'}
                                    memory.whitelist.remove(term)
                                    memory.save_memory()
                                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        st.markdown("**Add New Term to Redact**")
        with st.container():
            st.markdown('<div class="inline-add-container"></div>', unsafe_allow_html=True)
            new_w = st.text_input("Add New Term to Redact", key="add_white", label_visibility="collapsed", placeholder="Type a term...")
            add_clicked = st.button("+", key="btn_add_white")
            
        if add_clicked or (new_w and new_w.strip() != ""):
            term_to_add = new_w.strip()
            if term_to_add:
                memory.add_to_whitelist([term_to_add])
                memory.save_memory()
                st.session_state['add_white'] = ""
                st.rerun()

    with t2:
        c_met1_b, c_met2_b = st.columns([2, 1])
        with c_met1_b:
            st.markdown(f"### {len(memory.blacklist)} terms marked to Keep")
        with c_met2_b:
            confirm_key_b = "confirm_clear_black"
            if st.session_state.get(confirm_key_b, False):
                st.write(f"🗑️ Delete all {len(memory.blacklist)} terms?")
                col_yes, col_no = st.columns(2)
                with col_yes:
                    if st.button("🗑️ Yes", key="clear_black_confirm_yes", type="primary", use_container_width=True):
                        st.session_state['last_deleted'] = {'term': list(memory.blacklist), 'type': 'blacklist_all'}
                        memory.blacklist = set()
                        memory.blacklist_lower = set()
                        memory.save_memory()
                        st.session_state[confirm_key_b] = False
                        st.rerun()
                with col_no:
                    if st.button("❌ No", key="clear_black_confirm_no", use_container_width=True):
                        st.session_state[confirm_key_b] = False
                        st.rerun()
            else:
                if st.button("🗑️ Clear All", key="clear_black", use_container_width=True):
                    if len(memory.blacklist) > 0:
                        st.session_state[confirm_key_b] = True
                        st.rerun()
                
        # Undo Banner for Single or All Blacklist Deletions
        if last_deleted and last_deleted.get('type') in ['blacklist', 'blacklist_all']:
            undo_cols = st.columns([4, 1])
            with undo_cols[0]:
                if last_deleted['type'] == 'blacklist_all':
                    st.info("🗑️ Cleared all terms from Keep list.")
                else:
                    st.info(f"🗑️ Term '{last_deleted['term']}' removed from Keep list.")
            with undo_cols[1]:
                if st.button("↩️ Undo", key="undo_b", use_container_width=True):
                    if last_deleted['type'] == 'blacklist_all':
                        memory.blacklist.update(last_deleted['term'])
                        memory.blacklist_lower.update(t.lower() for t in last_deleted['term'])
                    else:
                        memory.blacklist.add(last_deleted['term'])
                        memory.blacklist_lower.add(last_deleted['term'].lower())
                    memory.save_memory()
                    st.session_state['last_deleted'] = None
                    st.rerun()
                
        search_b = st.text_input("Search Terms to Keep", placeholder="Search Terms", key="search_blacklist").lower()
        
        filtered_b = sorted([t for t in memory.blacklist if search_b in t.lower()])
        
        st.markdown('<div class="compact-terms-list">', unsafe_allow_html=True)
        with st.container(height=300):
            if not filtered_b:
                st.write("No terms found.")
            else:
                if in_sidebar:
                    for term in filtered_b:
                        col_t, col_b = st.columns([5.5, 1])
                        col_t.write(term)
                        if col_b.button("🗑️", key=f"del_b_{term}", use_container_width=True):
                            st.session_state['last_deleted'] = {'term': term, 'type': 'blacklist'}
                            memory.blacklist.remove(term)
                            memory.blacklist_lower.remove(term.lower())
                            memory.save_memory()
                            st.rerun()
                else:
                    col1, col2, col3 = st.columns(3)
                    col1_terms = filtered_b[0::3]
                    col2_terms = filtered_b[1::3]
                    col3_terms = filtered_b[2::3]
                    
                    for col, terms in zip([col1, col2, col3], [col1_terms, col2_terms, col3_terms]):
                        with col:
                            for term in terms:
                                col_t, col_b = st.columns([4, 1.2])
                                col_t.write(term)
                                if col_b.button("🗑️", key=f"del_b_{term}"):
                                    st.session_state['last_deleted'] = {'term': term, 'type': 'blacklist'}
                                    memory.blacklist.remove(term)
                                    memory.blacklist_lower.remove(term.lower())
                                    memory.save_memory()
                                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
        
        st.divider()
        st.markdown("**Add New Term to Keep**")
        with st.container():
            st.markdown('<div class="inline-add-container"></div>', unsafe_allow_html=True)
            new_b = st.text_input("Add New Term to Keep", key="add_black", label_visibility="collapsed", placeholder="Type a term...")
            add_clicked_b = st.button("+", key="btn_add_black")
            
        if add_clicked_b or (new_b and new_b.strip() != ""):
            term_to_add = new_b.strip()
            if term_to_add:
                memory.add_to_blacklist([term_to_add])
                memory.save_memory()
                st.session_state['add_black'] = ""
                st.rerun()


def render_diagnostic_panel(memory):
    """
    Renders a diagnostic dashboard with system status
    and real-time logs from log_capture_handler (RAM-only).
    """
    import time
    with st.expander("🛠️ System Diagnostics & Real-Time Logs (Zero-Trace)"):
        st.subheader("📊 System Status")
        st.caption("Run instant diagnostic tests on write permissions, disk space, and hardware availability.")
        
        # Test Runner Button
        if st.button("🔍 Run Diagnostic Tests", key="btn_run_diagnostics", use_container_width=True):
            from utils import run_diagnostic_tests
            with st.spinner("Running tests..."):
                st.session_state['diagnostic_results'] = run_diagnostic_tests()
                st.session_state['diagnostic_time'] = time.strftime("%H:%M:%S")
                st.success("Tests completed successfully!")
        
        # Display Diagnostic Results if available
        if 'diagnostic_results' in st.session_state:
            results = st.session_state['diagnostic_results']
            st.markdown(f"*Last checked at: `{st.session_state['diagnostic_time']}`*")
            
            # Grid of results
            cols = st.columns(len(results))
            for i, (test_name, test_info) in enumerate(results.items()):
                with cols[i % len(cols)]:
                    status = test_info["status"]
                    message = test_info["message"]
                    
                    # Decide color & emoji based on status
                    if status == "SUCCESS":
                        st.markdown(f"🟢 **{test_name.upper()}**\n\n{message}")
                    elif status == "WARNING":
                        st.markdown(f"🟡 **{test_name.upper()}**\n\n{message}")
                    elif status == "ERROR":
                        st.markdown(f"🔴 **{test_name.upper()}**\n\n{message}")
                    else:
                        st.markdown(f"⚪ **{test_name.upper()}**\n\n{message}")
        else:
            st.info("Click the button above to run diagnostics on modules and write permissions.")
            
        st.markdown("---")
        
        # Real-time Log Viewer
        st.subheader("📋 Application Logs (RAM)")
        st.caption("Showing the latest logs generated by the application in RAM memory (no files written to disk).")
        
        from utils import log_capture_handler
        logs = log_capture_handler.get_logs()
        
        col_log_actions, col_log_spacing = st.columns([1, 3])
        with col_log_actions:
            if st.button("🔄 Refresh Logs", key="btn_refresh_logs", use_container_width=True):
                st.rerun()
                
        if logs:
            st.code(logs, language="log")
        else:
            st.info("No logs recorded in memory yet.")
