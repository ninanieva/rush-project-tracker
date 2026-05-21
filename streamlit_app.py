import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import gspread
from oauth2client.service_account import ServiceAccountCredentials

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

st.title("🚀 RUSH Project Tracker")

# ── Google Sheets ────────────────────────────────────────────────
SHEET_ID   = st.secrets["GOOGLE_SHEETS_ID"]
SA_CREDS   = st.secrets["service_account"]
SCOPE      = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]
PROJECT_COLS = [
    "ID","Doc Type","Project Name","Control Number","Merchant","Endorsed By",
    "Project Price","Links","Date Endorsed Commercial","Doc Expiry Date",
    "Date Endorsed BA","Assigned BA","Date Ack BA","Doc State","Tribe",
    "Project Status","Date Endorsed Tech","Go Live Date","Remarks","Created At"
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
    import json
    ws = get_sheet("Settings")
    ws.clear()
    ws.append_row(["key","value"])
    for k, v in settings_dict.items():
        ws.append_row([k, json.dumps(v)])
    load_settings.clear()

import json

# ── Session State Init ───────────────────────────────────────────
if "user_email" not in st.session_state:
    st.session_state.user_email = None
if "projects" not in st.session_state:
    st.session_state.projects = []
if "settings_loaded" not in st.session_state:
    st.session_state.settings_loaded = False

DEFAULT_SETTINGS = {
    "doc_types": ["System Design","Feature Spec","Integration Doc","Release Notes"],
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
    st.sidebar.title("🔐 Login")
    mode = st.sidebar.radio("", ["Sign In","Sign Up"], label_visibility="collapsed")
    _, col, _ = st.columns([1,2,1])
    with col:
        st.markdown("## 🔐 Welcome to RUSH Project Tracker")
        st.markdown(f"**Email**")
        email = st.text_input("", placeholder="you@rush.ph", key="auth_email", label_visibility="collapsed")
        st.markdown("**Password**")
        pwd = st.text_input("", type="password", key="auth_pwd", label_visibility="collapsed")
        if mode == "Sign Up":
            st.markdown("**Confirm Password**")
            cpwd = st.text_input("", type="password", key="auth_cpwd", label_visibility="collapsed")
        if st.button("Continue", use_container_width=True):
            if not email or not pwd:
                st.error("❌ Fill all fields")
            elif len(pwd) < 6:
                st.error("❌ Password min 6 characters")
            elif mode == "Sign Up" and pwd != cpwd:
                st.error("❌ Passwords do not match")
            else:
                st.session_state.user_email = email
                st.session_state.projects   = load_projects()
                st.rerun()
    st.stop()

# ── Sidebar ───────────────────────────────────────────────────────
st.sidebar.markdown(f"👤 **{st.session_state.user_email}**")
if st.sidebar.button("🔓 Sign Out", use_container_width=True):
    st.session_state.user_email = None
    st.rerun()
if st.sidebar.button("🔄 Refresh Data", use_container_width=True):
    load_projects.clear()
    st.session_state.projects = load_projects()
    st.rerun()
st.sidebar.markdown("---")
st.sidebar.title("⚙️ Settings")

s = st.session_state.settings

def manage_list(label, key):
    items = s[key]
    with st.sidebar.expander(label):
        st.write(f"**{label}:**")
        for i, item in enumerate(items):
            c1,c2 = st.columns([0.8,0.2])
            c1.write(f"• {item}")
            if c2.button("❌", key=f"d_{key}_{i}"):
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

manage_list("📋 Document Types","doc_types")
manage_list("👤 Assigned BAs","ba_list")
manage_list("📄 Document States","doc_states")
manage_list("🏢 Tribes","tribes")
manage_list("📊 Project Statuses","statuses")

doc_types  = s["doc_types"]
ba_list    = s["ba_list"]
doc_states = s["doc_states"]
tribes     = s["tribes"]
statuses   = s["statuses"]

# ── Tabs ──────────────────────────────────────────────────────────
tab1,tab2,tab3 = st.tabs(["📝 Create Project","📊 Dashboard","📋 All Projects"])

def lsec(t): st.markdown(f'<p class="lsec">{t}</p>', unsafe_allow_html=True)
def flbl(t): st.markdown(f'<span class="flbl">{t}</span>', unsafe_allow_html=True)

# ── Tab 1: Create ─────────────────────────────────────────────────
with tab1:
    st.subheader("Create New Project")
    with st.form("create_form", clear_on_submit=True):
        lsec("📋 Basic Information")
        c1,c2 = st.columns(2)
        with c1:
            flbl("📋 Document Type *")
            doc_type = st.selectbox("", doc_types, label_visibility="collapsed", key="f_doctype")
        with c2:
            flbl("📌 Project Name *")
            project_name = st.text_input("", placeholder="Enter project name", label_visibility="collapsed", key="f_name")
        c1,c2 = st.columns(2)
        with c1:
            flbl("🔢 Control Number")
            ctrl_no = st.text_input("", placeholder="Auto-generated if blank", label_visibility="collapsed", key="f_ctrl")
        with c2:
            flbl("🏪 Merchant")
            merchant = st.text_input("", placeholder="Enter merchant name", label_visibility="collapsed", key="f_merchant")
        c1,c2 = st.columns(2)
        with c1:
            flbl("✅ Endorsed By")
            endorsed_by = st.text_input("", placeholder="Endorser name", label_visibility="collapsed", key="f_endorsed")
        with c2:
            flbl("💰 Project Price (PHP)")
            price = st.number_input("", value=0.0, min_value=0.0, label_visibility="collapsed", key="f_price")

        st.divider()
        lsec("🔗 Links")
        flbl("Add up to 5 links (optional)")
        links = []
        lc = st.columns(5)
        for i in range(5):
            with lc[i]:
                v = st.text_input(f"URL {i+1}", key=f"f_link{i}", label_visibility="collapsed", placeholder=f"URL {i+1}")
                if v: links.append(v)

        st.divider()
        lsec("📅 Endorsement Dates")
        c1,c2,c3 = st.columns(3)
        with c1:
            flbl("Date Endorsed to Commercials")
            d_commercial = st.date_input("", label_visibility="collapsed", key="f_dcom")
        with c2:
            flbl("⏰ Document Expiry Date")
            d_expiry = st.date_input("", label_visibility="collapsed", key="f_dexp")
        with c3:
            flbl("Date Endorsed to Tech")
            d_tech = st.date_input("", label_visibility="collapsed", key="f_dtech")

        st.divider()
        lsec("👤 BA & Go-Live Dates")
        c1,c2,c3 = st.columns(3)
        with c1:
            flbl("Date Endorsed to BA")
            d_ba = st.date_input("", label_visibility="collapsed", key="f_dba")
        with c2:
            flbl("✔️ Date Acknowledged by BA")
            d_ack = st.date_input("", label_visibility="collapsed", key="f_dack")
        with c3:
            flbl("🚀 Go Live Date")
            d_golive = st.date_input("", label_visibility="collapsed", key="f_golive")

        st.divider()
        lsec("🎯 Assignment & Workflow")
        c1,c2 = st.columns(2)
        with c1:
            flbl("👤 Assigned BA")
            assigned_ba = st.selectbox("", ba_list, label_visibility="collapsed", key="f_ba")
        with c2:
            flbl("🏢 Tribe")
            tribe = st.selectbox("", tribes, label_visibility="collapsed", key="f_tribe")
        c1,c2 = st.columns(2)
        with c1:
            flbl("📄 Document State")
            doc_state = st.selectbox("", doc_states, label_visibility="collapsed", key="f_docstate")
        with c2:
            flbl("📊 Project Status")
            proj_status = st.selectbox("", statuses, label_visibility="collapsed", key="f_status")

        st.divider()
        lsec("📝 Remarks")
        remarks = st.text_area("", placeholder="Enter any remarks or notes", label_visibility="collapsed", height=80, key="f_remarks")

        st.markdown("---")
        if st.form_submit_button("✅ Create Project", use_container_width=True):
            if not project_name:
                st.error("❌ Project Name is required")
            else:
                ctrl = ctrl_no or f"AUTO-{len(st.session_state.projects)+1:04d}"
                if ctrl_no and any(p.get("Control Number")==ctrl_no for p in st.session_state.projects):
                    st.error(f"❌ Control Number '{ctrl_no}' already exists")
                else:
                    new_p = {
                        "ID": datetime.now().isoformat(),
                        "Doc Type": doc_type, "Project Name": project_name,
                        "Control Number": ctrl, "Merchant": merchant,
                        "Endorsed By": endorsed_by, "Project Price": price,
                        "Links": " | ".join(links),
                        "Date Endorsed Commercial": str(d_commercial),
                        "Doc Expiry Date": str(d_expiry),
                        "Date Endorsed BA": str(d_ba),
                        "Assigned BA": assigned_ba, "Date Ack BA": str(d_ack),
                        "Doc State": doc_state, "Tribe": tribe,
                        "Project Status": proj_status,
                        "Date Endorsed Tech": str(d_tech),
                        "Go Live Date": str(d_golive),
                        "Remarks": remarks,
                        "Created At": datetime.now().isoformat()
                    }
                    save_project(new_p)
                    st.session_state.projects.append(new_p)
                    st.success("✅ Project created and saved to Google Sheets!")
                    st.balloons()

# ── Expiry Helper ─────────────────────────────────────────────────
def tag_expiry(projects):
    today = datetime.now().date()
    for p in projects:
        try:
            exp = datetime.strptime(str(p.get("Doc Expiry Date","")), "%Y-%m-%d").date()
            p["expiry_status"] = "Expired" if exp < today else ("Expiring Soon" if (exp-today).days<=7 else "Active")
        except:
            p["expiry_status"] = "Active"
    return projects

# ── Tab 2: Dashboard ──────────────────────────────────────────────
with tab2:
    st.subheader("📊 Project Dashboard")
    projects = tag_expiry(load_projects())

    if projects:
        total       = len(projects)
        in_progress = sum(1 for p in projects if p.get("Project Status")=="In Progress")
        live        = sum(1 for p in projects if p.get("Project Status")=="Live")
        on_hold     = sum(1 for p in projects if p.get("Project Status")=="On Hold")
        expired     = sum(1 for p in projects if p.get("expiry_status")=="Expired")
        exp_soon    = sum(1 for p in projects if p.get("expiry_status")=="Expiring Soon")

        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("📊 Total", total)
        c2.metric("⏳ In Progress", in_progress)
        c3.metric("🚀 Live", live)
        c4.metric("⏸️ On Hold", on_hold)
        c5.metric("❌ Expired", expired)
        c6.metric("⚠️ Expiring Soon", exp_soon)

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
        c1,c2 = st.columns(2)
        with c1:
            dd = pd.Series([p.get("Doc Type") for p in projects]).value_counts()
            fig = px.bar(x=dd.index, y=dd.values, title="Projects by Document Type",
                         color_discrete_sequence=[RUSH_ORANGE])
            fig.update_layout(paper_bgcolor=RUSH_WHITE, plot_bgcolor=RUSH_WHITE, font=dict(color=RUSH_DARK))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            pdf = pd.DataFrame([{"tribe": p.get("Tribe"), "price": float(p.get("Project Price",0) or 0)} for p in projects])
            pt = pdf.groupby("tribe")["price"].sum().sort_values()
            fig = px.bar(x=pt.values, y=pt.index, orientation='h', title="Total Price by Tribe",
                         color_discrete_sequence=[RUSH_TEAL])
            fig.update_layout(paper_bgcolor=RUSH_WHITE, plot_bgcolor=RUSH_WHITE, font=dict(color=RUSH_DARK), xaxis_title="₱", yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

        st.markdown("---")
        st.subheader("🏪 Merchants per Project")
        ml = [{"Project": p.get("Project Name"), "Merchant": p.get("Merchant"),
               "Tribe": p.get("Tribe"), "Status": p.get("Project Status"),
               "Price": f"₱{float(p.get('Project Price',0) or 0):,.2f}",
               "Go Live": p.get("Go Live Date"), "Expiry": p.get("Doc Expiry Date")}
              for p in projects if p.get("Merchant")]
        if ml:
            st.dataframe(pd.DataFrame(ml), use_container_width=True, hide_index=True)
        else:
            st.info("No merchants assigned yet")
    else:
        st.info("📭 No projects yet. Create one in the 'Create Project' tab!")

# ── Tab 3: All Projects ───────────────────────────────────────────
with tab3:
    st.subheader("📋 All Projects")
    projects = tag_expiry(load_projects())

    if projects:
        c1,c2,c3 = st.columns(3)
        with c1: f_status = st.multiselect("Status", statuses, default=[])
        with c2: f_tribe  = st.multiselect("Tribe", tribes, default=[])
        with c3: f_expiry = st.multiselect("Expiry Status", ["Active","Expiring Soon","Expired"], default=[])

        filtered = [p for p in projects
                    if (not f_status or p.get("Project Status") in f_status)
                    and (not f_tribe  or p.get("Tribe") in f_tribe)
                    and (not f_expiry or p.get("expiry_status") in f_expiry)]

        st.markdown("---")
        for idx, p in enumerate(filtered):
            em = "🟢" if p.get("expiry_status")=="Active" else ("🟡" if p.get("expiry_status")=="Expiring Soon" else "🔴")
            c1,c2 = st.columns([0.87,0.13])
            with c1:
                st.markdown(f"### 📌 {p.get('Project Name')}")
                a,b,c,d = st.columns(4)
                a.write(f"**Control #:** {p.get('Control Number')}")
                b.write(f"**Merchant:** {p.get('Merchant') or 'N/A'}")
                c.write(f"**Status:** {p.get('Project Status')}")
                d.write(f"**Tribe:** {p.get('Tribe')}")
                a,b,c,d = st.columns(4)
                a.write(f"**Doc Type:** {p.get('Doc Type')}")
                b.write(f"**BA:** {p.get('Assigned BA')}")
                c.write(f"**Price:** ₱{float(p.get('Project Price',0) or 0):,.2f}")
                d.write(f"**Doc State:** {p.get('Doc State')}")
                a,b,c,d = st.columns(4)
                a.write(f"**Go Live:** {p.get('Go Live Date')}")
                b.write(f"**Expiry:** {p.get('Doc Expiry Date')}")
                c.write(f"**Endorsed By:** {p.get('Endorsed By') or 'N/A'}")
                d.write(f"{em} **{p.get('expiry_status')}**")
                if p.get("Links"): st.markdown(f"**Links:** {p.get('Links')}")
                if p.get("Remarks"): st.write(f"**Remarks:** {p.get('Remarks')}")
            with c2:
                if st.button("🗑️ Delete", key=f"del_{idx}", use_container_width=True):
                    delete_project_row(p.get("ID",""))
                    st.session_state.projects = load_projects()
                    st.rerun()
            st.markdown("---")
    else:
        st.info("📭 No projects yet.")
