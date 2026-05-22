import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

# ── Design System Color Variables ────────────────────────────────
RUSH_ORANGE = "#FF6B00"
RUSH_TEAL   = "#00AFAA"
RUSH_YELLOW = "#FDD756"
RUSH_RED    = "#CE0E2D"
RUSH_GREY   = "#667085"
RUSH_DARK   = "#2B2F38"
RUSH_WHITE  = "#FFFFFF"

st.set_page_config(page_title="RUSH Project Tracker", layout="wide", initial_sidebar_state="expanded")
st.markdown(f"""<style>
.stApp {{background-color:{RUSH_WHITE};}}
.stMetricValue {{color:{RUSH_ORANGE};font-weight:bold;}}
h1,h2,h3 {{color:{RUSH_DARK};}}
.lsec {{font-weight:700;font-size:15px;color:{RUSH_ORANGE};margin-top:16px;margin-bottom:6px;border-left:4px solid {RUSH_ORANGE};padding-left:8px;}}
.flbl {{font-weight:600;color:{RUSH_DARK};font-size:13px;margin-bottom:4px;display:block;}}
</style>""", unsafe_allow_html=True)

st.title("RUSH Project Tracker")

# ── Google Sheets Hardened Dynamic Header-Sync Engine ───────────
SHEET_ID   = st.secrets["GOOGLE_SHEETS_ID"]
SA_CREDS   = st.secrets["service_account"]
SCOPE      = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

PROJECT_COLS = [
    "ID", "Doc Type", "Project Name", "Control Number", "PO Status", "Merchant", "Endorsed By",
    "Project Price", "Links", "Date Endorsed Commercial", "Doc Expiry Date",
    "Date Endorsed BA", "Assigned BA", "Date Ack BA", "Doc State", "Tribe", "Sprint",
    "Pipeline Status", "Date Endorsed Tech", "Go Live Date", "Project Status", 
    "Reason for Rejection", "Rejector", "Remarks", "Created At"
]

@st.cache_resource
def get_gc():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(SA_CREDS), scopes=SCOPE)
    return gspread.authorize(creds)

def get_sheet(tab):
    gc = get_gc()
    sh = gc.open_by_key(SHEET_ID)
    try:
        return sh.worksheet(tab)
    except gspread.exceptions.WorksheetNotFound:
        ws = sh.add_worksheet(tab, rows=1000, cols=35)
        if tab == "Projects":
            ws.append_row(PROJECT_COLS)
        elif tab == "Settings":
            ws.append_row(["key","value"])
        return ws

@st.cache_data(ttl=5)
def load_projects():
    try:
        ws = get_sheet("Projects")
        raw_rows = ws.get_all_values()
        if not raw_rows or len(raw_rows) < 1:
            return []
            
        headers = raw_rows[0]
        
        # Self-Healing Schema: Automatically add missing columns to user's sheet if old sheet exists
        missing_cols = [c for c in PROJECT_COLS if c not in headers]
        if missing_cols:
            for col in missing_cols:
                ws.update_cell(1, len(headers) + 1, col)
                headers.append(col)
            raw_rows = ws.get_all_values()
            headers = raw_rows[0]
            
        records = []
        for row in raw_rows[1:]:
            record = {}
            for col_name in PROJECT_COLS:
                if col_name in headers:
                    idx = headers.index(col_name)
                    record[col_name] = row[idx] if idx < len(row) else ""
                else:
                    record[col_name] = ""
            records.append(record)
        return records
    except Exception as e:
        st.error(f"Failed to fetch data from sheet: {e}")
        return []

def save_project(p):
    try:
        ws = get_sheet("Projects")
        raw_rows = ws.get_all_values()
        headers = raw_rows[0] if raw_rows else PROJECT_COLS
        
        row_to_append = []
        for col in headers:
            row_to_append.append(str(p.get(col, "")))
            
        ws.append_row(row_to_append)
        load_projects.clear()
        return True
    except Exception as e:
        st.error(f"Google Sheets Save Error: {e}")
        return False

def update_project_row(project_id, updated_p):
    try:
        ws = get_sheet("Projects")
        cell = ws.find(project_id)
        if cell:
            raw_rows = ws.get_all_values()
            headers = raw_rows[0]
            
            row_values = []
            for col in headers:
                if col in updated_p:
                    row_values.append(str(updated_p[col]))
                else:
                    row_values.append("")
                    
            end_col_letter = gspread.utils.rowcol_to_a1(cell.row, len(headers)).split(str(cell.row))[0]
            ws.update(f"A{cell.row}:{end_col_letter}{cell.row}", [row_values])
        load_projects.clear()
        return True
    except Exception as e:
        st.error(f"Error updating row in Google Sheets: {e}")
        return False

def delete_project_row(project_id):
    try:
        ws = get_sheet("Projects")
        cell = ws.find(project_id)
        if cell:
            ws.delete_rows(cell.row)
        load_projects.clear()
    except Exception as e:
        st.error(f"Error removing row from Google Sheets: {e}")

@st.cache_data(ttl=30)
def load_settings():
    try:
        ws = get_sheet("Settings")
        raw_rows = ws.get_all_values()
        if not raw_rows or len(raw_rows) < 2:
            return {}
            
        result = {}
        for row in raw_rows[1:]:
            if len(row) >= 2:
                key_val = row[0]
                json_val = row[1]
                if key_val:
                    try:
                        result[key_val] = json.loads(json_val) if json_val else []
                    except:
                        result[key_val] = []
        return result
    except:
        return {}

def save_settings(settings_dict):
    ws = get_sheet("Settings")
    ws.clear()
    ws.append_row(["key","value"])
    for k, v in settings_dict.items():
        ws.append_row([k, json.dumps(v)])
    load_settings.clear()

# ── Session State Configuration Management ───────────────────────
if "projects" not in st.session_state:
    st.session_state.projects = load_projects()
if "form_id" not in st.session_state:
    st.session_state.form_id = 0

DEFAULT_SETTINGS = {
    "doc_types": ["CRF","BRF","FEF","System Design","Feature Spec","Integration Doc","Release Notes"],
    "ba_list":   ["BA001 - John Smith","BA002 - Maria Garcia","BA003 - Sarah Chen","BA004 - Ahmed Hassan"],
    "doc_states":["Draft","In Review","Approved","Published","Archived"],
    "tribes":    ["Core Tribe","Growth Tribe","Infrastructure Tribe","Platform Tribe"],
    "statuses":  ["Backlog","In Progress","In Review","Testing","Ready to Launch","Live","On Hold","Completed"]
}

if "settings" not in st.session_state:
    remote = load_settings()
    st.session_state.settings = {k: remote.get(k, v) for k, v in DEFAULT_SETTINGS.items()}

# ── Sidebar Dynamic Settings Workspace ─────────────────────────────
st.sidebar.title("Settings")
s = st.session_state.settings

def manage_list(label, key):
    items = s[key]
    with st.sidebar.expander(label):
        st.write(f"**{label}:**")
        for i, item in enumerate(items):
            c1,c2 = st.columns([0.8,0.2])
            c1.write(f"• {item}")
            if c2.button("X", key=f"d_{key}_{i}"):
                items.pop(i)
                save_settings(s)
                st.rerun()
        c1,c2 = st.columns([0.75,0.25])
        nv = c1.text_input("", key=f"n_{key}", label_visibility="collapsed", placeholder="Add new...")
        if c2.button("Add", key=f"a_{key}"):
            if nv and nv not in items:
                items.append(nv)
                save_settings(s)
                st.rerun()

manage_list("Document Types","doc_types")
manage_list("Assigned BAs","ba_list")
manage_list("Document States","doc_states")
manage_list("Tribes","tribes")
manage_list("Pipeline Statuses","statuses")

doc_types  = s["doc_types"]
ba_list    = s["ba_list"]
doc_states = s["doc_states"]
tribes     = s["tribes"]
statuses   = s["statuses"]

# ── Tabs Navigation Architecture ──────────────────────────────────
tab1, tab2, tab3 = st.tabs(["Create Project", "All Projects", "Dashboard"])

def lsec(t): st.markdown(f'<p class="lsec">{t}</p>', unsafe_allow_html=True)
def flbl(t): st.markdown(f'<span class="flbl">{t}</span>', unsafe_allow_html=True)

def tag_expiry(projects):
    today = datetime.now().date()
    for p in projects:
        try:
            exp_val = p.get("Doc Expiry Date","")
            if exp_val and exp_val != "None" and exp_val != "":
                exp = datetime.strptime(str(exp_val), "%Y-%m-%d").date()
                p["expiry_status"] = "Expired" if exp < today else ("Expiring Soon" if (exp-today).days<=7 else "Active")
            else:
                p["expiry_status"] = "Active"
        except:
            p["expiry_status"] = "Active"
    return projects

def safe_index(options, value):
    try:
        return options.index(value)
    except ValueError:
        return 0

# ── Tab 1: Create Project Entry Form (Enter-Key Safe & Resettable) ──
with tab1:
    st.subheader("Add New Record Entry")
    
    # State versions allow full form clearance outside standard HTML containers
    fid = st.session_state.form_id
    
    placeholder_doc_types = [""] + doc_types
    placeholder_ba_list   = [""] + ba_list
    placeholder_tribes    = [""] + tribes
    placeholder_doc_states = [""] + doc_states
    placeholder_statuses  = [""] + statuses
    placeholder_po_status = ["", "Done", "Not Yet Done"]

    doc_type = st.selectbox("Document Type *", placeholder_doc_types, index=0, key=f"f_doctype_{fid}")
    
    crf_subtype = ""
    if doc_type == "CRF":
        crf_subtype = st.selectbox("CRF Type Option", ["", "BRF", "FEF"], index=0, key=f"f_crf_subtype_{fid}")
    
    c1, c2 = st.columns(2)
    with c1:
        project_name = st.text_input("Project Name *", placeholder="Enter project name", key=f"f_name_{fid}")
    with c2:
        merchant = st.text_input("Merchant", placeholder="Enter merchant name", key=f"f_merchant_{fid}")

    c1, c2 = st.columns(2)
    with c1:
        ctrl_no = st.text_input("Control Number", placeholder="Leave blank to auto-generate tracking sequence", key=f"f_ctrl_{fid}")
    with c2:
        po_status = st.selectbox("PO Status", placeholder_po_status, index=0, key=f"f_postatus_{fid}")
        
    c1, c2 = st.columns(2)
    with c1:
        endorsed_by = st.text_input("Endorsed By", placeholder="Endorser name", key=f"f_endorsed_{fid}")
    with c2:
        price = st.number_input("Project Price (PHP)", value=0.0, min_value=0.0, key=f"f_price_{fid}")

    project_status = "N/A"
    reason_for_rejection = ""
    rejector = ""
    
    if doc_type in ["CRF", "BRF", "FEF"]:
        project_status = st.selectbox("Project Status", ["", "Approved", "Rejected"], index=0, key=f"f_project_status_{fid}")
        
        if project_status == "Rejected":
            c1, c2 = st.columns(2)
            with c1:
                reason_for_rejection = st.text_input("Reason for Rejection *", placeholder="State why this project was rejected", key=f"f_reason_rejection_{fid}")
            with c2:
                rejector = st.text_input("Rejector *", placeholder="Name of individual who rejected the project", key=f"f_rejector_{fid}")

    if doc_type == "CRF":
        lsec("Commercial Timeline")
        g1_left, g1_right = st.columns(2)
        with g1_left: d_commercial = st.date_input("Date Endorsed to Commercials", value=None, key=f"f_dcom_{fid}")
        with g1_right: d_expiry = st.date_input("Document Expiry Date", value=None, key=f"f_dexp_{fid}")
    else:
        d_commercial, d_expiry = "", ""

    lsec("BA Assignment & Workflow")
    g2_left, g2_right = st.columns(2)
    with g2_left: d_ba = st.date_input("Date Endorsed to BA", value=None, key=f"f_dba_{fid}")
    with g2_right: d_ack = st.date_input("Date Acknowledged by BA", value=None, key=f"f_dack_{fid}")

    c1, c2 = st.columns(2)
    with c1:
        assigned_ba = st.selectbox("Assigned BA", placeholder_ba_list, index=0, key=f"f_ba_{fid}")
    with c2:
        doc_state = st.selectbox("Document State", placeholder_doc_states, index=0, key=f"f_docstate_{fid}")

    lsec("Tribe & Sprint Parameters")
    c1, c2 = st.columns(2)
    with c1:
        tribe = st.selectbox("Tribe", placeholder_tribes, index=0, key=f"f_tribe_{fid}")
    with c2:
        sprint = st.text_input("Sprint (Optional)", placeholder="e.g., Sprint 42", key=f"f_sprint_{fid}")

    lsec("Tech Timeline & Status")
    g3_left, g3_right = st.columns(2)
    with g3_left: d_tech = st.date_input("Date Endorsed to Tech", value=None, key=f"f_dtech_{fid}")
    with g3_right: d_golive = st.date_input("Go Live Date", value=None, key=f"f_golive_{fid}")
        
    pipeline_status = st.selectbox("Pipeline Status", placeholder_statuses, index=0, key=f"f_status_{fid}")

    lsec("Links")
    lc = st.columns(4)
    with lc[0]: crf_url = st.text_input("CRF Link", key=f"f_link_crf_{fid}", placeholder="URL")
    with lc[1]: brf_url = st.text_input("BRF Link", key=f"f_link_brf_{fid}", placeholder="URL")
    with lc[2]: fef_url = st.text_input("FEF Link", key=f"f_link_fef_{fid}", placeholder="URL")
    with lc[3]: figma_url = st.text_input("Figma Link", key=f"f_link_figma_{fid}", placeholder="URL")

    lsec("Remarks")
    remarks = st.text_area("Remarks / Notes", placeholder="Enter any extra remarks...", height=70, key=f"f_remarks_{fid}")

    st.markdown("---")
    if st.button("Save Project Data", use_container_width=True, type="primary"):
        if not project_name or doc_type == "":
            st.error("Document Type and Project Name are mandatory fields.")
        elif project_status == "Rejected" and (not reason_for_rejection or not rejector):
            st.error("Reason for Rejection and Rejector are required fields when status is marked 'Rejected'.")
        else:
            year_str = datetime.now().strftime("%Y")
            type_seq = sum(1 for p in load_projects() if str(p.get("Doc Type", "")).startswith(doc_type)) + 1
            
            if ctrl_no:
                final_ctrl = ctrl_no
            else:
                if doc_type == "CRF":
                    final_ctrl = f"CRF-{year_str}-{type_seq:04d}"
                elif doc_type == "BRF":
                    tribe_clean = tribe.replace(" Tribe", "").upper() if tribe else "UNKNOWN"
                    final_ctrl = f"BRF-{tribe_clean}-{year_str}-{type_seq:04d}"
                elif doc_type == "FEF":
                    final_ctrl = f"FEF-{year_str}-{type_seq:04d}"
                else:
                    clean_doc = doc_type.upper().replace(" ", "") if doc_type else "DOC"
                    final_ctrl = f"{clean_doc}-{year_str}-{type_seq:04d}"

            links_compiled = []
            if crf_url: links_compiled.append(f"CRF: {crf_url}")
            if brf_url: links_compiled.append(f"BRF: {brf_url}")
            if fef_url: links_compiled.append(f"FEF: {fef_url}")
            if figma_url: links_compiled.append(f"Figma: {figma_url}")

            final_saved_doc_type = f"CRF - {crf_subtype}" if (doc_type == "CRF" and crf_subtype) else doc_type

            new_p = {
                "ID": datetime.now().isoformat(),
                "Doc Type": final_saved_doc_type, "Project Name": project_name,
                "Control Number": final_ctrl, "PO Status": po_status, "Merchant": merchant,
                "Endorsed By": endorsed_by, "Project Price": price,
                "Links": " | ".join(links_compiled),
                "Date Endorsed Commercial": str(d_commercial) if d_commercial else "",
                "Doc Expiry Date": str(d_expiry) if d_expiry else "",
                "Date Endorsed BA": str(d_ba) if d_ba else "",
                "Assigned BA": assigned_ba, 
                "Date Ack BA": str(d_ack) if d_ack else "",
                "Doc State": doc_state, "Tribe": tribe, "Sprint": sprint,
                "Pipeline Status": pipeline_status,
                "Date Endorsed Tech": str(d_tech) if d_tech else "",
                "Go Live Date": str(d_golive) if d_golive else "",
                "Project Status": project_status,
                "Reason for Rejection": reason_for_rejection,
                "Rejector": rejector,
                "Remarks": remarks,
                "Created At": datetime.now().isoformat()
            }
            if save_project(new_p):
                st.session_state.form_id += 1 # Increments layout version state to instantly clear the inputs
                st.success("Project added successfully!")
                st.rerun()

# ── Tab 2: All Projects Matrix Table View ────────────────────────
with tab2:
    st.subheader("All Projects Registry")
    projects = tag_expiry(load_projects())
    
    if projects:
        unique_merchants = sorted(list(set(p.get("Merchant") for p in projects if p.get("Merchant"))))
        
        f_search = st.text_input("Search Project Name", placeholder="Type project name to instantly filter standard registry list...", value="")
        
        f_status, f_tribe, f_expiry, f_merchant = [], [], [], []
        c1, c2, c3, c4 = st.columns(4)
        with c1: f_status = st.multiselect("Filter Pipeline Status", statuses, default=[])
        with c2: f_tribe  = st.multiselect("Filter Tribe", tribes, default=[])
        with c3: f_expiry = st.multiselect("Filter Expiry", ["Active","Expiring Soon","Expired"], default=[])
        with c4: f_merchant = st.multiselect("Filter Merchant", unique_merchants, default=[])

        filtered = [p for p in projects
                    if (not f_search or f_search.lower() in str(p.get("Project Name")).lower())
                    and (not f_status or p.get("Pipeline Status") in f_status)
                    and (not f_tribe  or p.get("Tribe") in f_tribe)
                    and (not f_expiry or p.get("expiry_status") in f_expiry)
                    and (not f_merchant or p.get("Merchant") in f_merchant)]

        st.markdown("---")
        
        th1, th2, th3, th4, th5, th6, th7, th8 = st.columns([1.5, 2.0, 1.3, 1.2, 1.2, 1.0, 1.8, 1.2])
        th1.markdown("**Control #**")
        th2.markdown("**Project Name**")
        th3.markdown("**Merchant**")
        th4.markdown("**Pipeline Status**")
        th5.markdown("**Tribe**")
        th6.markdown("**Doc Type**")
        th7.markdown("**Details**")
        th8.markdown("**Action**")
        st.markdown("<hr style='margin:4px 0px 12px 0px; border-top: 2px solid #2B2F38;' />", unsafe_allow_html=True)
        
        for idx, p in enumerate(filtered):
            r1, r2, r3, r4, r5, r6, r7, r8 = st.columns([1.5, 2.0, 1.3, 1.2, 1.2, 1.0, 1.8, 1.2])
            
            r1.write(p.get("Control Number"))
            r2.write(f"**{p.get('Project Name')}**")
            r3.write(p.get("Merchant") or "N/A")
            r4.write(p.get("Pipeline Status") or "N/A")
            r5.write(p.get("Tribe") or "N/A")
            r6.write(p.get("Doc Type") or "N/A")
            
            detail_items = [f"PHP {float(p.get('Project Price',0) or 0):,.2f}"]
            if p.get("Sprint"): detail_items.append(f"Sprint: {p.get('Sprint')}")
            if p.get("PO Status"): detail_items.append(f"PO: {p.get('PO Status')}")
            if p.get("Project Status") and p.get("Project Status") != "N/A":
                detail_items.append(f"Status: {p.get('Project Status')}")
                
            r7.write(" | ".join(detail_items))
            
            with r8:
                with st.popover("Edit", use_container_width=True):
                    st.markdown(f"### Edit Row: {p.get('Control Number')}")
                    
                    e_doc_types = [""] + doc_types
                    e_ba_list = [""] + ba_list
                    e_tribes = [""] + tribes
                    e_doc_states = [""] + doc_states
                    e_statuses = [""] + statuses
                    e_po_status = ["", "Done", "Not Yet Done"]
                    
                    raw_stored_type = p.get("Doc Type", "")
                    base_parsed_type = "CRF" if raw_stored_type.startswith("CRF") else raw_stored_type
                    extracted_sub = raw_stored_type.split(" - ")[1] if " - " in raw_stored_type else ""

                    edit_doc_type = st.selectbox("Document Type *", e_doc_types, index=safe_index(e_doc_types, base_parsed_type), key=f"e_dt_{idx}")
                    
                    edit_crf_subtype = ""
                    if edit_doc_type == "CRF":
                        edit_crf_subtype = st.selectbox("CRF Type Option", ["", "BRF", "FEF"], index=safe_index(["", "BRF", "FEF"], extracted_sub), key=f"e_crf_sub_{idx}")

                    edit_name = st.text_input("Project Name *", value=p.get("Project Name"), key=f"e_nm_{idx}")
                    edit_ctrl = st.text_input("Control Number", value=p.get("Control Number"), key=f"e_ctrl_{idx}")
                    edit_po = st.selectbox("PO Status", e_po_status, index=safe_index(e_po_status, p.get("PO Status")), key=f"e_po_{idx}")
                    
                    edit_merchant = st.text_input("Merchant", value=p.get("Merchant"), key=f"e_mer_{idx}")
                    edit_endorsed = st.text_input("Endorsed By", value=p.get("Endorsed By"), key=f"e_end_{idx}")
                    edit_price = st.number_input("Price (PHP)", value=float(p.get("Project Price", 0) or 0), min_value=0.0, key=f"e_pr_{idx}")
                    
                    edit_approval = "N/A"
                    edit_reason = ""
                    edit_rej_person = ""
                    
                    if edit_doc_type in ["CRF", "BRF", "FEF"]:
                        e_app_options = ["", "Approved", "Rejected"]
                        edit_approval = st.selectbox("Project Status", e_app_options, index=safe_index(e_app_options, p.get("Project Status")), key=f"e_app_{idx}")
                        
                        if edit_approval == "Rejected":
                            edit_reason = st.text_input("Reason for Rejection *", value=p.get("Reason for Rejection", ""), key=f"e_reas_{idx}")
                            edit_rej_person = st.text_input("Rejector *", value=p.get("Rejector", ""), key=f"e_rejctr_{idx}")

                    def parse_date_safely(d_str):
                        try:
                            return datetime.strptime(d_str, "%Y-%m-%d").date() if d_str and d_str != "None" else None
                        except:
                            return None

                    if edit_doc_type == "CRF":
                        lsec("Commercial Timeline")
                        ed_com = st.date_input("Date Endorsed to Commercials", value=parse_date_safely(p.get("Date Endorsed Commercial")), key=f"ed_com_{idx}")
                        ed_exp = st.date_input("Document Expiry Date", value=parse_date_safely(p.get("Doc Expiry Date")), key=f"ed_exp_{idx}")
                    else:
                        ed_com, ed_exp = "", ""

                    lsec("BA Assignment & Workflow")
                    ed_ba = st.date_input("Date Endorsed to BA", value=parse_date_safely(p.get("Date Endorsed BA")), key=f"ed_ba_{idx}")
                    ed_ack = st.date_input("Date Acknowledged by BA", value=parse_date_safely(p.get("Date Ack BA")), key=f"ed_ack_{idx}")
                    
                    edit_ba = st.selectbox("Assigned BA", e_ba_list, index=safe_index(e_ba_list, p.get("Assigned BA")), key=f"e_ba_{idx}")
                    edit_doc_state = st.selectbox("Document State", e_doc_states, index=safe_index(e_doc_states, p.get("Doc State")), key=f"e_ds_{idx}")
                    
                    lsec("Tribe & Sprint Parameters")
                    edit_tribe = st.selectbox("Tribe", e_tribes, index=safe_index(e_tribes, p.get("Tribe")), key=f"e_tr_{idx}")
                    edit_sprint = st.text_input("Sprint", value=p.get("Sprint",""), key=f"e_sp_{idx}")
                    
                    lsec("Tech Timeline & Status")
                    ed_tech = st.date_input("Date Endorsed to Tech", value=parse_date_safely(p.get("Date Endorsed Tech")), key=f"ed_tech_{idx}")
                    ed_go = st.date_input("Go Live Date", value=parse_date_safely(p.get("Go Live Date")), key=f"ed_go_{idx}")
                    edit_status = st.selectbox("Pipeline Status", e_statuses, index=safe_index(e_statuses, p.get("Pipeline Status")), key=f"e_st_{idx}")
                    
                    edit_remarks = st.text_area("Remarks", value=p.get("Remarks"), key=f"e_rem_{idx}")
                    
                    if st.button("Update Record", key=f"save_edit_{idx}", use_container_width=True, type="primary"):
                        if not edit_name or edit_doc_type == "":
                            st.error("Mandatory fields missing.")
                        elif edit_approval == "Rejected" and (not edit_reason or not edit_rej_person):
                            st.error("Reason for Rejection and Rejector are mandatory for Rejected status.")
                        else:
                            final_edit_doc_type = f"CRF - {edit_crf_subtype}" if (edit_doc_type == "CRF" and edit_crf_subtype) else edit_doc_type
                            
                            updated_p = {
                                "ID": p.get("ID"),
                                "Doc Type": final_edit_doc_type,
                                "Project Name": edit_name,
                                "Control Number": edit_ctrl,
                                "PO Status": edit_po,
                                "Merchant": edit_merchant,
                                "Endorsed By": edit_endorsed,
                                "Project Price": edit_price,
                                "Links": p.get("Links"), 
                                "Date Endorsed Commercial": str(ed_com) if ed_com else "",
                                "Doc Expiry Date": str(ed_exp) if ed_exp else "",
                                "Date Endorsed BA": str(ed_ba) if ed_ba else "",
                                "Assigned BA": edit_ba,
                                "Date Ack BA": str(ed_ack) if ed_ack else "",
                                "Doc State": edit_doc_state,
                                "Tribe": edit_tribe,
                                "Sprint": edit_sprint,
                                "Pipeline Status": edit_status,
                                "Date Endorsed Tech": str(ed_tech) if ed_tech else "",
                                "Go Live Date": str(ed_go) if ed_go else "",
                                "Project Status": edit_approval,
                                "Reason for Rejection": edit_reason,
                                "Rejector": edit_rej_person,
                                "Remarks": edit_remarks,
                                "Created At": p.get("Created At")
                            }
                            if update_project_row(p.get("ID"), updated_p):
                                st.success("Record parameters modified successfully!")
                                st.rerun()
                
                if st.button("Delete", key=f"del_{idx}", use_container_width=True, type="secondary"):
                    delete_project_row(p.get("ID",""))
                    st.rerun()
                    
            st.markdown("<hr style='margin:6px 0px; border-top: 1px solid #E5E5E5;' />", unsafe_allow_html=True)
    else:
        st.info("No projects match your registry search query or active filter configurations.")

# ── Tab 3: Dashboard Analytics ────────────────────────────────────
with tab3:
    st.subheader("Project Dashboard Metrics")
    projects = tag_expiry(load_projects())

    if projects:
        total       = len(projects)
        in_progress = sum(1 for p in projects if p.get("Pipeline Status")=="In Progress")
        live        = sum(1 for p in projects if p.get("Pipeline Status")=="Live")
        on_hold     = sum(1 for p in projects if p.get("Pipeline Status")=="On Hold")
        expired     = sum(1 for p in projects if p.get("expiry_status")=="Expired")
        exp_soon    = sum(1 for p in projects if p.get("expiry_status")=="Expiring Soon")

        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("Total", total)
        c2.metric("In Progress", in_progress)
        c3.metric("Live", live)
        c4.metric("On Hold", on_hold)
        c5.metric("Expired", expired)
        c6.metric("Expiring Soon", exp_soon)

        st.markdown("---")
        st.subheader("Project Pipeline Volumetric Flow")
        status_order = ["Backlog", "In Progress", "In Review", "Testing", "Ready to Launch", "Live", "Completed"]
        status_counts = {stage: sum(1 for p in projects if p.get("Pipeline Status") == stage) for stage in status_order}
        
        fig_funnel = go.Figure(go.Funnel(
            y=list(status_counts.keys()),
            x=list(status_counts.values()),
            marker={"color": [RUSH_GREY, RUSH_ORANGE, RUSH_YELLOW, RUSH_TEAL, RUSH_TEAL, RUSH_ORANGE, RUSH_GREY]},
            textinfo="value+percent initial"
        ))
        fig_funnel.update_layout(paper_bgcolor=RUSH_WHITE, plot_bgcolor=RUSH_WHITE, font=dict(color=RUSH_DARK), margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig_funnel, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Individual Project Milestone Tracking")
        selected_p_name = st.selectbox("Select a project to view timelines:", [p.get("Project Name") for p in projects])
        
        if selected_p_name:
            p_data = next(p for p in projects if p.get("Project Name") == selected_p_name)
            milestones = {
                "Commercial Endorsement": p_data.get("Date Endorsed Commercial"),
                "Tech Endorsement": p_data.get("Date Endorsed Tech"),
                "BA Endorsement": p_data.get("Date Endorsed BA"),
                "BA Acknowledgement": p_data.get("Date Ack BA"),
                "Go Live Date": p_data.get("Go Live Date")
            }
            
            ms_cols = st.columns(len(milestones))
            for idx, (ms_name, ms_date) in enumerate(milestones.items()):
                with ms_cols[idx]:
                    is_complete = ms_date and ms_date != "None" and ms_date != ""
                    status_box = f"Completed<br>`{ms_date}`" if is_complete else "Pending"
                    st.markdown(f"""
                    <div style="border: 1px solid {RUSH_GREY}; padding: 12px; border-radius: 6px; background-color: {RUSH_WHITE}; text-align: center;">
                        <span style="font-size: 13px; font-weight: 600; color: {RUSH_DARK};">{ms_name}</span><br>
                        <span style="font-size: 14px; margin-top: 6px; display: inline-block;">{status_box}</span>
                    </div>
                    """, unsafe_allow_html=True)
    else:
        st.info("No records are currently stored inside the spreadsheet system.")
