import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import json

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

# ── Google Sheets ────────────────────────────────────────────────
SHEET_ID   = st.secrets["GOOGLE_SHEETS_ID"]
SA_CREDS   = st.secrets["service_account"]
SCOPE      = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]

PROJECT_COLS = [
    "ID","Doc Type","Project Name","Control Number","Merchant","Endorsed By",
    "Project Price","Links","Date Endorsed Commercial","Doc Expiry Date",
    "Date Endorsed BA","Assigned BA","Date Ack BA","Doc State","Tribe",
    "Project Status","Date Endorsed Tech","Go Live Date","Approval Status","Remarks","Created At"
]
SETTINGS_COLS = ["doc_types","ba_list","doc_states","tribes","statuses"]

@st.cache_resource
def get_gc():
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(SA_CREDS), scopes=SCOPE)
    return gspread.authorize(creds)

def get_sheet(tab):
    gc = get_gc()
    sh = gc.open_by_key(SHEET_ID)
    try:
        return sh.worksheet(tab)
    except:
        ws = sh.add_worksheet(tab, rows=1000, cols=30)
        if tab == "Projects":
            ws.append_row(PROJECT_COLS)
        elif tab == "Settings":
            ws.append_row(["key","value"])
        return ws

@st.cache_data(ttl=15)
def load_projects():
    try:
        ws = get_sheet("Projects")
        records = ws.get_all_records()
        return records
    except:
        return []

def save_project(p):
    ws = get_sheet("Projects")
    ws.append_row([p.get(c,"") for c in PROJECT_COLS])
    load_projects.clear()

def delete_project_row(project_id):
    ws = get_sheet("Projects")
    cell = ws.find(project_id)
    if cell:
        ws.delete_rows(cell.row)
    load_projects.clear()

@st.cache_data(ttl=30)
def load_settings():
    try:
        ws = get_sheet("Settings")
        records = ws.get_all_records()
        result = {}
        for r in records:
            result[r["key"]] = json.loads(r["value"]) if r.get("value") else []
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

# ── Session State Init ───────────────────────────────────────────
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "projects" not in st.session_state:
    st.session_state.projects = []
if "settings_loaded" not in st.session_state:
    st.session_state.settings_loaded = False
if "show_create_form" not in st.session_state:
    st.session_state.show_create_form = False

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

# ── Auth ──────────────────────────────────────────────────────────
if not st.session_state.user_email:
    st.sidebar.title("Login")
    mode = st.sidebar.radio("", ["Sign In","Sign Up"], label_visibility="collapsed")
    _, col, _ = st.columns([1,2,1])
    with col:
        st.markdown("## Welcome to RUSH Project Tracker")
        st.markdown(f"**Email**")
        email = st.text_input("", placeholder="you@rush.ph", key="auth_email", label_visibility="collapsed")
        st.markdown("**Password**")
        pwd = st.text_input("", type="password", key="auth_pwd", label_visibility="collapsed")
        if mode == "Sign Up":
            st.markdown("**Confirm Password**")
            cpwd = st.text_input("", type="password", key="auth_cpwd", label_visibility="collapsed")
        if st.button("Continue", use_container_width=True):
            if not email or not pwd:
                st.error("Fill all fields")
            elif len(pwd) < 6:
                st.error("Password min 6 characters")
            elif mode == "Sign Up" and pwd != cpwd:
                st.error("Passwords do not match")
            else:
                st.session_state.user_email = email
                st.session_state.projects   = load_projects()
                st.rerun()
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────
st.sidebar.markdown(f"**{st.session_state.user_email}**")
if st.sidebar.button("Sign Out", use_container_width=True):
    st.session_state.user_email = None
    st.rerun()
if st.sidebar.button("Refresh Data", use_container_width=True):
    load_projects.clear()
    st.session_state.projects = load_projects()
    st.rerun()
st.sidebar.markdown("---")
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
manage_list("Project Statuses","statuses")

doc_types  = s["doc_types"]
ba_list    = s["ba_list"]
doc_states = s["doc_states"]
tribes     = s["tribes"]
statuses   = s["statuses"]

# ── Tabs ──────────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["Dashboard", "All Projects"])

def lsec(t): st.markdown(f'<p class="lsec">{t}</p>', unsafe_allow_html=True)
def flbl(t): st.markdown(f'<span class="flbl">{t}</span>', unsafe_allow_html=True)

# ── Expiry Helper ─────────────────────────────────────────────────
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

# ── Tab 1: Dashboard ──────────────────────────────────────────────
with tab1:
    st.subheader("Project Dashboard")
    projects = tag_expiry(load_projects())

    if projects:
        total       = len(projects)
        in_progress = sum(1 for p in projects if p.get("Project Status")=="In Progress")
        live        = sum(1 for p in projects if p.get("Project Status")=="Live")
        on_hold     = sum(1 for p in projects if p.get("Project Status")=="On Hold")
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
        st.subheader("Project Pipeline & Movement Progress")
        
        # Display sequential funnel flow matching pipeline progression
        status_order = ["Backlog", "In Progress", "In Review", "Testing", "Ready to Launch", "Live", "Completed"]
        status_counts = {stage: sum(1 for p in projects if p.get("Project Status") == stage) for stage in status_order}
        
        fig_funnel = go.Figure(go.Funnel(
            y=list(status_counts.keys()),
            x=list(status_counts.values()),
            marker={"color": [RUSH_GREY, RUSH_ORANGE, RUSH_YELLOW, RUSH_TEAL, RUSH_TEAL, RUSH_ORANGE, RUSH_GREY]},
            textinfo="value+percent initial"
        ))
        fig_funnel.update_layout(title_text="Project Volume Movement Through Pipeline States", paper_bgcolor=RUSH_WHITE, plot_bgcolor=RUSH_WHITE, font=dict(color=RUSH_DARK), margin=dict(l=40, r=40, t=40, b=40))
        st.plotly_chart(fig_funnel, use_container_width=True)
        
        st.markdown("---")
        st.subheader("Individual Project Milestone Tracking")
        selected_p_name = st.selectbox("Select a project to inspect dynamic movement timeline:", [p.get("Project Name") for p in projects])
        
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
                    status_box = f"🟢 **Completed**<br>`{ms_date}`" if is_complete else "⚪ *Pending*"
                    st.markdown(f"""
                    <div style="border: 1px solid {RUSH_GREY}; padding: 12px; border-radius: 6px; background-color: {RUSH_WHITE}; text-align: center;">
                        <span style="font-size: 13px; font-weight: 600; color: {RUSH_DARK};">{ms_name}</span><br>
                        <span style="font-size: 14px; margin-top: 6px; display: inline-block;">{status_box}</span>
                    </div>
                    """, unsafe_allow_html=True)

        st.markdown("---")
        c1,c2 = st.columns(2)
        with c1:
            sd = pd.Series([p.get("Project Status") for p in projects]).value_counts()
            fig = px.pie(values=sd.values, names=sd.index, title="Project Status Distribution",
                         color_discrete_sequence=[RUSH_ORANGE,RUSH_TEAL,RUSH_YELLOW,RUSH_RED,RUSH_GREY])
            fig.update_layout(paper_bgcolor=RUSH_WHITE, plot_bgcolor=RUSH_WHITE, font=dict(color=RUSH_DARK))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            td = pd.Series([p.get("Tribe") for p in projects]).value_counts()
            fig = px.bar(x=td.values, y=td.index, orientation='h', title="Projects by Tribe",
                         color_discrete_sequence=[RUSH_TEAL])
            fig.update_layout(paper_bgcolor=RUSH_WHITE, plot_bgcolor=RUSH_WHITE, font=dict(color=RUSH_DARK), yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

    else:
        st.info("No projects yet. Create one in the All Projects tab!")

# ── Tab 2: All Projects ───────────────────────────────────────────
with tab2:
    st.subheader("All Projects")
    projects = tag_expiry(load_projects())
    
    # Toggle formulation area inline
    if not st.session_state.show_create_form:
        if st.button("Create New Project", type="primary"):
            st.session_state.show_create_form = True
            st.rerun()
    else:
        if st.button("Close Creation Form"):
            st.session_state.show_create_form = False
            st.rerun()
            
        st.markdown("### Create New Project Form")
        lsec("Basic Information")
        c1,c2 = st.columns(2)
        with c1:
            flbl("Document Type *")
            doc_type = st.selectbox("", doc_types, label_visibility="collapsed", key="f_doctype")
            
        with st.form("create_form", clear_on_submit=True):
            with c2:
                pass 
            
            c1,c2 = st.columns(2)
            with c1:
                flbl("Project Name *")
                project_name = st.text_input("", placeholder="Enter project name", label_visibility="collapsed", key="f_name")
            with c2:
                flbl("Control Number")
                ctrl_no = st.text_input("", placeholder="Leave blank to auto-generate", label_visibility="collapsed", key="f_ctrl")
            
            c1,c2 = st.columns(2)
            with c1:
                flbl("Merchant")
                merchant = st.text_input("", placeholder="Enter merchant name", label_visibility="collapsed", key="f_merchant")
            with c2:
                flbl("Endorsed By")
                endorsed_by = st.text_input("", placeholder="Endorser name", label_visibility="collapsed", key="f_endorsed")
            
            c1,c2 = st.columns(2)
            with c1:
                flbl("Project Price (PHP)")
                price = st.number_input("", value=0.0, min_value=0.0, label_visibility="collapsed", key="f_price")
            with c2:
                if doc_type == "CRF":
                    flbl("Approval Status")
                    approval_status = st.selectbox("", ["Approved", "Rejected"], label_visibility="collapsed", key="f_approval")
                else:
                    approval_status = "N/A"

            # Reordered Section: Assignment & Workflow moved above Links
            st.divider()
            lsec("Assignment & Workflow")
            c1,c2 = st.columns(2)
            with c1:
                flbl("Assigned BA")
                assigned_ba = st.selectbox("", ba_list, label_visibility="collapsed", key="f_ba")
            with c2:
                flbl("Tribe")
                tribe = st.selectbox("", tribes, label_visibility="collapsed", key="f_tribe")
            c1,c2 = st.columns(2)
            with c1:
                flbl("Document State")
                doc_state = st.selectbox("", doc_states, label_visibility="collapsed", key="f_docstate")
            with c2:
                flbl("Project Status")
                proj_status = st.selectbox("", statuses, label_visibility="collapsed", key="f_status")

            st.divider()
            lsec("Links")
            lc = st.columns(4)
            with lc[0]:
                flbl("CRF")
                crf_url = st.text_input("", key="f_link_crf", label_visibility="collapsed", placeholder="URL")
            with lc[1]:
                flbl("BRF")
                brf_url = st.text_input("", key="f_link_brf", label_visibility="collapsed", placeholder="URL")
            with lc[2]:
                flbl("FEF")
                fef_url = st.text_input("", key="f_link_fef", label_visibility="collapsed", placeholder="URL")
            with lc[3]:
                flbl("Figma")
                figma_url = st.text_input("", key="f_link_figma", label_visibility="collapsed", placeholder="URL")

            st.divider()
            lsec("Endorsement Dates")
            c1,c2,c3 = st.columns(3)
            with c1:
                flbl("Date Endorsed to Commercials")
                d_commercial = st.date_input("", value=None, label_visibility="collapsed", key="f_dcom")
            with c2:
                flbl("Document Expiry Date")
                d_expiry = st.date_input("", value=None, label_visibility="collapsed", key="f_dexp")
            with c3:
                flbl("Date Endorsed to Tech")
                d_tech = st.date_input("", value=None, label_visibility="collapsed", key="f_dtech")

            st.divider()
            lsec("BA & Go-Live Dates")
            c1,c2,c3 = st.columns(3)
            with c1:
                flbl("Date Endorsed to BA")
                d_ba = st.date_input("", value=None, label_visibility="collapsed", key="f_dba")
            with c2:
                flbl("Date Acknowledged by BA")
                d_ack = st.date_input("", value=None, label_visibility="collapsed", key="f_dack")
            with c3:
                flbl("Go Live Date")
                d_golive = st.date_input("", value=None, label_visibility="collapsed", key="f_golive")

            st.divider()
            lsec("Remarks")
            remarks = st.text_area("", placeholder="Enter any remarks or notes", label_visibility="collapsed", height=80, key="f_remarks")

            st.markdown("---")
            if st.form_submit_button("Submit Project Details", use_container_width=True):
                if not project_name:
                    st.error("Project Name is required")
                else:
                    # Specialized Custom Control Number Generation
                    year_str = datetime.now().strftime("%Y")
                    type_seq = sum(1 for p in st.session_state.projects if p.get("Doc Type") == doc_type) + 1
                    
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
                            clean_doc = doc_type.upper().replace(" ", "")
                            final_ctrl = f"{clean_doc}-{year_str}-{type_seq:04d}"

                    if ctrl_no and any(p.get("Control Number") == ctrl_no for p in st.session_state.projects):
                        st.error(f"Control Number '{ctrl_no}' already exists")
                    else:
                        links_compiled = []
                        if crf_url: links_compiled.append(f"CRF: {crf_url}")
                        if brf_url: links_compiled.append(f"BRF: {brf_url}")
                        if fef_url: links_compiled.append(f"FEF: {fef_url}")
                        if figma_url: links_compiled.append(f"Figma: {figma_url}")

                        new_p = {
                            "ID": datetime.now().isoformat(),
                            "Doc Type": doc_type, "Project Name": project_name,
                            "Control Number": final_ctrl, "Merchant": merchant,
                            "Endorsed By": endorsed_by, "Project Price": price,
                            "Links": " | ".join(links_compiled),
                            "Date Endorsed Commercial": str(d_commercial) if d_commercial else "",
                            "Doc Expiry Date": str(d_expiry) if d_expiry else "",
                            "Date Endorsed BA": str(d_ba) if d_ba else "",
                            "Assigned BA": assigned_ba, 
                            "Date Ack BA": str(d_ack) if d_ack else "",
                            "Doc State": doc_state, "Tribe": tribe,
                            "Project Status": proj_status,
                            "Date Endorsed Tech": str(d_tech) if d_tech else "",
                            "Go Live Date": str(d_golive) if d_golive else "",
                            "Approval Status": approval_status,
                            "Remarks": remarks,
                            "Created At": datetime.now().isoformat()
                        }
                        save_project(new_p)
                        st.session_state.projects.append(new_p)
                        st.session_state.show_create_form = False
                        st.success("Project created and saved to Google Sheets!")
                        st.rerun()

    st.markdown("---")
    
    # Filter interface updates
    if projects:
        unique_merchants = sorted(list(set(p.get("Merchant") for p in projects if p.get("Merchant"))))
        
        c1,c2,c3,c4 = st.columns(4)
        with c1: f_status = st.multiselect("Status", statuses, default=[])
        with c2: f_tribe  = st.multiselect("Tribe", tribes, default=[])
        with c3: f_expiry = st.multiselect("Expiry Status", ["Active","Expiring Soon","Expired"], default=[])
        with c4: f_merchant = st.multiselect("Merchant", unique_merchants, default=[])

        filtered = [p for p in projects
                    if (not f_status or p.get("Project Status") in f_status)
                    and (not f_tribe  or p.get("Tribe") in f_tribe)
                    and (not f_expiry or p.get("expiry_status") in f_expiry)
                    and (not f_merchant or p.get("Merchant") in f_merchant)]

        st.markdown("---")
        for idx, p in enumerate(filtered):
            c1,c2 = st.columns([0.87,0.13])
            with c1:
                st.markdown(f"### {p.get('Project Name')}")
                a,b,c,d = st.columns(4)
                a.write(f"**Control #:** {p.get('Control Number')}")
                b.write(f"**Merchant:** {p.get('Merchant') or 'N/A'}")
                c.write(f"**Status:** {p.get('Project Status')}")
                d.write(f"**Tribe:** {p.get('Tribe')}")
                a,b,c,d = st.columns(4)
                a.write(f"**Doc Type:** {p.get('Doc Type')}")
                b.write(f"**BA:** {p.get('Assigned BA')}")
                c.write(f"**Price:** PHP {float(p.get('Project Price',0) or 0):,.2f}")
                d.write(f"**Doc State:** {p.get('Doc State')}")
                a,b,c,d = st.columns(4)
                a.write(f"**Go Live:** {p.get('Go Live Date') or 'N/A'}")
                b.write(f"**Expiry:** {p.get('Doc Expiry Date') or 'N/A'}")
                c.write(f"**Endorsed By:** {p.get('Endorsed By') or 'N/A'}")
                if p.get("Doc Type") == "CRF":
                    d.write(f"**Approval:** {p.get('Approval Status', 'N/A')}")
                else:
                    d.write(f"**Expiry Status:** {p.get('expiry_status')}")
                
                if p.get("Links"): st.markdown(f"**Links:** {p.get('Links')}")
                if p.get("Remarks"): st.write(f"**Remarks:** {p.get('Remarks')}")
            with c2:
                if st.button("Delete", key=f"del_{idx}", use_container_width=True):
                    delete_project_row(p.get("ID",""))
                    st.session_state.projects = load_projects()
                    st.rerun()
            st.markdown("---")
    else:
        st.info("No projects found matching current filter configuration.")
