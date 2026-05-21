import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import urllib.request
import urllib.parse
import json
import time

# RUSH Brand Colors
RUSH_ORANGE = "#FF6B00"
RUSH_TEAL = "#00AFAA"
RUSH_YELLOW = "#FDD756"
RUSH_RED = "#CE0E2D"
RUSH_GREY = "#667085"
RUSH_DARK = "#2B2F38"
RUSH_WHITE = "#FFFFFF"
RUSH_LIGHT_BG = "#F9FAFB"

st.set_page_config(page_title="RUSH Project Tracker", layout="wide", initial_sidebar_state="expanded")

st.markdown(f'''<style>
.stApp {{ background-color: {RUSH_WHITE}; }}
.stMetricValue {{ color: {RUSH_ORANGE}; font-weight: bold; }}
div[data-testid="stMetricLabel"] {{ color: {RUSH_GREY}; }}
h1, h2, h3 {{ color: {RUSH_DARK}; }}
.label-section {{
    font-weight: 700; font-size: 14px; color: {RUSH_WHITE};
    background-color: {RUSH_ORANGE}; padding: 6px 12px;
    border-radius: 6px; margin: 16px 0 8px 0; display: block;
}}
.field-label {{
    font-weight: 600; color: {RUSH_DARK}; font-size: 13px;
    margin-bottom: 2px; display: block;
}}
.req {{ color: {RUSH_RED}; }}
</style>''', unsafe_allow_html=True)

st.title("🚀 RUSH Project Tracker")

# ==================== SHEET CONFIG ====================
SHEET_ID = "1psrfYR3Qp2y-thiiz7eyY7EIrooe0zVaUXIghlvK2ws"

HEADER = [
    "ID","Doc Type","Project Name","Control Number","Merchant","Endorsed By",
    "Project Price","Links","Date Endorsed Commercial","Doc Expiry Date",
    "Date Endorsed BA","Assigned BA","Date Ack BA","Doc State","Tribe",
    "Project Status","Date Endorsed Tech","Go Live Date","Remarks","Created By","Created At"
]

SETTINGS_HEADER = ["Key","Values"]

# ==================== SESSION STATE ====================
for key, default in [
    ("user_email", None),
    ("projects", None),
    ("settings", None),
    ("last_refresh", 0),
]:
    if key not in st.session_state:
        st.session_state[key] = default

# ==================== GOOGLE SHEETS READ ====================
@st.cache_data(ttl=30)
def fetch_sheet(tab_name):
    try:
        url = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/gviz/tq?tqx=out:csv&sheet={urllib.parse.quote(tab_name)}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode("utf-8")
        import csv, io
        reader = csv.DictReader(io.StringIO(raw))
        return [row for row in reader]
    except Exception as e:
        return []

def load_projects():
    rows = fetch_sheet("Projects")
    # Filter out empty rows
    return [r for r in rows if r.get("Project Name","").strip()]

def load_settings():
    rows = fetch_sheet("Settings")
    settings = {
        "doc_types": ["System Design","Feature Spec","Integration Doc","Release Notes"],
        "ba_list": ["BA001 - John Smith","BA002 - Maria Garcia","BA003 - Sarah Chen","BA004 - Ahmed Hassan"],
        "doc_states": ["Draft","In Review","Approved","Published","Archived"],
        "tribes": ["Core Tribe","Growth Tribe","Infrastructure Tribe","Platform Tribe"],
        "statuses": ["Backlog","In Progress","In Review","Testing","Ready to Launch","Live","On Hold","Completed"]
    }
    for row in rows:
        k = row.get("Key","").strip()
        v = row.get("Values","").strip()
        if k and v:
            settings[k] = [x.strip() for x in v.split("|") if x.strip()]
    return settings

# Load on first visit
if st.session_state.projects is None:
    st.session_state.projects = load_projects()
if st.session_state.settings is None:
    st.session_state.settings = load_settings()

settings   = st.session_state.settings
doc_types  = settings.get("doc_types", [])
ba_list    = settings.get("ba_list", [])
doc_states = settings.get("doc_states", [])
tribes     = settings.get("tribes", [])
statuses   = settings.get("statuses", [])

# ==================== AUTH ====================
if not st.session_state.user_email:
    _, col, _ = st.columns([1, 2, 1])
    with col:
        st.markdown("## 🔐 Sign In to RUSH Project Tracker")
        st.markdown("**Email**")
        email = st.text_input("", placeholder="you@rush.ph", key="si_email", label_visibility="collapsed")
        st.markdown("**Password**")
        password = st.text_input("", type="password", placeholder="••••••••", key="si_pass", label_visibility="collapsed")
        st.markdown("&nbsp;", unsafe_allow_html=True)
        if st.button("Sign In →", use_container_width=True):
            if email and len(password) >= 6:
                st.session_state.user_email = email
                st.rerun()
            else:
                st.error("❌ Enter a valid email and password (min 6 chars)")
    st.stop()

# ==================== SIDEBAR ====================
st.sidebar.markdown(f"👤 **{st.session_state.user_email}**")

col1, col2 = st.sidebar.columns(2)
with col1:
    if st.button("🔄 Refresh", use_container_width=True):
        fetch_sheet.clear()
        st.session_state.projects = load_projects()
        st.session_state.settings = load_settings()
        st.rerun()
with col2:
    if st.button("🔓 Sign Out", use_container_width=True):
        st.session_state.user_email = None
        st.rerun()

st.sidebar.markdown("---")
st.sidebar.title("⚙️ Settings")
st.sidebar.caption("Changes here update locally. Edit the Settings tab in Google Sheets for permanent changes.")

def manage_list(label, key, items):
    with st.sidebar.expander(label):
        for i, item in enumerate(items):
            c1, c2 = st.columns([0.82, 0.18])
            with c1: st.write(f"• {item}")
            with c2:
                if st.button("✕", key=f"del_{key}_{i}"):
                    items.pop(i); st.rerun()
        c1, c2 = st.columns([0.75, 0.25])
        with c1:
            nv = st.text_input("", key=f"new_{key}", label_visibility="collapsed", placeholder="Add new...")
        with c2:
            if st.button("Add", key=f"add_{key}"):
                if nv and nv not in items:
                    items.append(nv); st.rerun()

manage_list("📋 Document Types", "doc", doc_types)
manage_list("👤 Assigned BAs",    "ba",  ba_list)
manage_list("📄 Document States", "state", doc_states)
manage_list("🏢 Tribes",          "tribe", tribes)
manage_list("📊 Project Statuses","status", statuses)

# ==================== EXPIRY HELPER ====================
def tag_expiry(projects):
    today = datetime.now().date()
    for p in projects:
        try:
            exp = datetime.strptime(p.get("Doc Expiry Date",""), "%Y-%m-%d").date()
            if exp < today:
                p["expiry_status"] = "Expired"
            elif (exp - today).days <= 7:
                p["expiry_status"] = "Expiring Soon"
            else:
                p["expiry_status"] = "Active"
        except:
            p["expiry_status"] = "Active"
    return projects

# ==================== TABS ====================
tab1, tab2, tab3 = st.tabs(["📝 Create Project", "📊 Dashboard", "📋 All Projects"])

# ==================== TAB 1: CREATE ====================
with tab1:
    st.subheader("Create New Project")

    with st.form("project_form", clear_on_submit=True):

        st.markdown('<span class="label-section">📋 Basic Information</span>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<span class="field-label">📋 Document Type <span class="req">*</span></span>', unsafe_allow_html=True)
            f_doc_type = st.selectbox("", doc_types, label_visibility="collapsed", key="f_doc_type")
        with c2:
            st.markdown('<span class="field-label">📌 Project Name <span class="req">*</span></span>', unsafe_allow_html=True)
            f_proj_name = st.text_input("", placeholder="Enter project name", label_visibility="collapsed", key="f_proj_name")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<span class="field-label">🔢 Control Number</span>', unsafe_allow_html=True)
            f_ctrl = st.text_input("", placeholder="Auto-generated if blank", label_visibility="collapsed", key="f_ctrl")
        with c2:
            st.markdown('<span class="field-label">🏪 Merchant</span>', unsafe_allow_html=True)
            f_merchant = st.text_input("", placeholder="Enter merchant name", label_visibility="collapsed", key="f_merchant")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<span class="field-label">✅ Endorsed By</span>', unsafe_allow_html=True)
            f_endorsed = st.text_input("", placeholder="Endorser name", label_visibility="collapsed", key="f_endorsed")
        with c2:
            st.markdown('<span class="field-label">💰 Project Price (PHP)</span>', unsafe_allow_html=True)
            f_price = st.number_input("", value=0.0, min_value=0.0, label_visibility="collapsed", key="f_price")

        st.divider()
        st.markdown('<span class="label-section">🔗 Links (optional — up to 5)</span>', unsafe_allow_html=True)
        links = []
        lc = st.columns(5)
        for i in range(5):
            with lc[i]:
                lv = st.text_input(f"URL {i+1}", key=f"lnk_{i}", label_visibility="collapsed", placeholder=f"URL {i+1}")
                if lv: links.append(lv)

        st.divider()
        st.markdown('<span class="label-section">📅 Endorsement Dates</span>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<span class="field-label">Date Endorsed to Commercials</span>', unsafe_allow_html=True)
            f_date_com = st.date_input("", label_visibility="collapsed", key="f_date_com")
        with c2:
            st.markdown('<span class="field-label">⏰ Document Expiry Date</span>', unsafe_allow_html=True)
            f_expiry = st.date_input("", label_visibility="collapsed", key="f_expiry")
        with c3:
            st.markdown('<span class="field-label">Date Endorsed to Tech</span>', unsafe_allow_html=True)
            f_date_tech = st.date_input("", label_visibility="collapsed", key="f_date_tech")

        st.divider()
        st.markdown('<span class="label-section">👤 BA & Go-Live Dates</span>', unsafe_allow_html=True)
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown('<span class="field-label">Date Endorsed to BA</span>', unsafe_allow_html=True)
            f_date_ba = st.date_input("", label_visibility="collapsed", key="f_date_ba")
        with c2:
            st.markdown('<span class="field-label">✔️ Date Acknowledged by BA</span>', unsafe_allow_html=True)
            f_date_ack = st.date_input("", label_visibility="collapsed", key="f_date_ack")
        with c3:
            st.markdown('<span class="field-label">🚀 Go Live Date</span>', unsafe_allow_html=True)
            f_golive = st.date_input("", label_visibility="collapsed", key="f_golive")

        st.divider()
        st.markdown('<span class="label-section">🎯 Assignment & Workflow</span>', unsafe_allow_html=True)
        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<span class="field-label">👤 Assigned BA</span>', unsafe_allow_html=True)
            f_ba = st.selectbox("", ba_list, label_visibility="collapsed", key="f_ba")
        with c2:
            st.markdown('<span class="field-label">🏢 Tribe</span>', unsafe_allow_html=True)
            f_tribe = st.selectbox("", tribes, label_visibility="collapsed", key="f_tribe")

        c1, c2 = st.columns(2)
        with c1:
            st.markdown('<span class="field-label">📄 Document State</span>', unsafe_allow_html=True)
            f_doc_state = st.selectbox("", doc_states, label_visibility="collapsed", key="f_doc_state")
        with c2:
            st.markdown('<span class="field-label">📊 Project Status</span>', unsafe_allow_html=True)
            f_status = st.selectbox("", statuses, label_visibility="collapsed", key="f_status")

        st.divider()
        st.markdown('<span class="label-section">📝 Remarks</span>', unsafe_allow_html=True)
        f_remarks = st.text_area("", placeholder="Enter any remarks or notes", label_visibility="collapsed", height=80, key="f_remarks")

        st.markdown("---")
        submitted = st.form_submit_button("✅ Create Project", use_container_width=True)

        if submitted:
            if not f_proj_name:
                st.error("❌ Project Name is required")
            else:
                ctrl = f_ctrl or f"AUTO-{len(st.session_state.projects)+1:04d}"
                if f_ctrl and any(p.get("Control Number") == f_ctrl for p in st.session_state.projects):
                    st.error(f"❌ Control Number '{f_ctrl}' already exists")
                else:
                    new_p = {
                        "ID": datetime.now().isoformat(),
                        "Doc Type": f_doc_type,
                        "Project Name": f_proj_name,
                        "Control Number": ctrl,
                        "Merchant": f_merchant,
                        "Endorsed By": f_endorsed,
                        "Project Price": f_price,
                        "Links": " | ".join(links),
                        "Date Endorsed Commercial": str(f_date_com),
                        "Doc Expiry Date": str(f_expiry),
                        "Date Endorsed BA": str(f_date_ba),
                        "Assigned BA": f_ba,
                        "Date Ack BA": str(f_date_ack),
                        "Doc State": f_doc_state,
                        "Tribe": f_tribe,
                        "Project Status": f_status,
                        "Date Endorsed Tech": str(f_date_tech),
                        "Go Live Date": str(f_golive),
                        "Remarks": f_remarks,
                        "Created By": st.session_state.user_email,
                        "Created At": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    }
                    st.session_state.projects.append(new_p)
                    st.success("✅ Project created successfully!")
                    st.info("💡 To save permanently & share with your team: manually add this row to your Google Sheet, or connect a write-enabled backend.")
                    st.balloons()

# ==================== TAB 2: DASHBOARD ====================
with tab2:
    st.subheader("📊 Project Dashboard")
    projects = tag_expiry(list(st.session_state.projects))

    if projects:
        total       = len(projects)
        in_progress = sum(1 for p in projects if p.get("Project Status") == "In Progress")
        live        = sum(1 for p in projects if p.get("Project Status") == "Live")
        on_hold     = sum(1 for p in projects if p.get("Project Status") == "On Hold")
        expired     = sum(1 for p in projects if p.get("expiry_status") == "Expired")
        exp_soon    = sum(1 for p in projects if p.get("expiry_status") == "Expiring Soon")

        c1,c2,c3,c4,c5,c6 = st.columns(6)
        c1.metric("📊 Total", total)
        c2.metric("⏳ In Progress", in_progress)
        c3.metric("🚀 Live", live)
        c4.metric("⏸️ On Hold", on_hold)
        c5.metric("❌ Expired", expired)
        c6.metric("⚠️ Expiring Soon", exp_soon)

        st.markdown("---")
        c1, c2 = st.columns(2)
        with c1:
            sd = pd.Series([p.get("Project Status") for p in projects]).value_counts()
            fig = px.pie(values=sd.values, names=sd.index, title="Project Status Distribution",
                         color_discrete_sequence=[RUSH_ORANGE, RUSH_TEAL, RUSH_YELLOW, RUSH_RED, RUSH_GREY])
            fig.update_layout(paper_bgcolor=RUSH_WHITE, plot_bgcolor=RUSH_WHITE, font=dict(color=RUSH_DARK))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            td = pd.Series([p.get("Tribe") for p in projects]).value_counts()
            fig = px.bar(x=td.values, y=td.index, orientation='h', title="Projects by Tribe",
                         color_discrete_sequence=[RUSH_TEAL])
            fig.update_layout(paper_bgcolor=RUSH_WHITE, plot_bgcolor=RUSH_WHITE, font=dict(color=RUSH_DARK), yaxis_title="")
            st.plotly_chart(fig, use_container_width=True)

        c1, c2 = st.columns(2)
        with c1:
            dd = pd.Series([p.get("Doc Type") for p in projects]).value_counts()
            fig = px.bar(x=dd.index, y=dd.values, title="Projects by Document Type",
                         color_discrete_sequence=[RUSH_ORANGE])
            fig.update_layout(paper_bgcolor=RUSH_WHITE, plot_bgcolor=RUSH_WHITE, font=dict(color=RUSH_DARK))
            st.plotly_chart(fig, use_container_width=True)
        with c2:
            try:
                pdf = pd.DataFrame([{"tribe": p.get("Tribe"), "price": float(str(p.get("Project Price","0")).replace(",","") or 0)} for p in projects])
                ptribe = pdf.groupby("tribe")["price"].sum().sort_values()
                fig = px.bar(x=ptribe.values, y=ptribe.index, orientation='h', title="Total Price by Tribe",
                             color_discrete_sequence=[RUSH_TEAL])
                fig.update_layout(paper_bgcolor=RUSH_WHITE, plot_bgcolor=RUSH_WHITE, font=dict(color=RUSH_DARK), xaxis_title="₱", yaxis_title="")
                st.plotly_chart(fig, use_container_width=True)
            except:
                st.info("Price chart unavailable")

        st.markdown("---")
        st.subheader("🏪 Merchants per Project")
        mlist = []
        for p in projects:
            if p.get("Merchant","").strip():
                try:
                    price = float(str(p.get("Project Price","0")).replace(",","") or 0)
                except:
                    price = 0
                mlist.append({
                    "Project": p.get("Project Name"),
                    "Merchant": p.get("Merchant"),
                    "Tribe": p.get("Tribe"),
                    "Status": p.get("Project Status"),
                    "Price": f"₱{price:,.2f}",
                    "Go Live": p.get("Go Live Date"),
                    "Expiry": p.get("Doc Expiry Date"),
                    "Expiry Status": p.get("expiry_status")
                })
        if mlist:
            st.dataframe(pd.DataFrame(mlist), use_container_width=True, hide_index=True)
        else:
            st.info("No merchants assigned yet")
    else:
        st.info("📭 No projects yet. Create one in the 'Create Project' tab!")

# ==================== TAB 3: ALL PROJECTS ====================
with tab3:
    st.subheader("📋 All Projects")
    projects = tag_expiry(list(st.session_state.projects))

    if projects:
        st.write("**Filter Projects:**")
        c1, c2, c3 = st.columns(3)
        with c1:
            f_status = st.multiselect("Status", statuses, default=[])
        with c2:
            f_tribe = st.multiselect("Tribe", tribes, default=[])
        with c3:
            f_expiry = st.multiselect("Expiry Status", ["Active","Expiring Soon","Expired"], default=[])

        filtered = [p for p in projects
                    if (not f_status or p.get("Project Status") in f_status)
                    and (not f_tribe  or p.get("Tribe") in f_tribe)
                    and (not f_expiry or p.get("expiry_status") in f_expiry)]

        st.markdown(f"Showing **{len(filtered)}** of **{len(projects)}** projects")
        st.markdown("---")

        for idx, p in enumerate(filtered):
            emoji = "🟢" if p.get("expiry_status")=="Active" else ("🟡" if p.get("expiry_status")=="Expiring Soon" else "🔴")
            try:
                price_display = f"₱{float(str(p.get('Project Price','0')).replace(',','') or 0):,.2f}"
            except:
                price_display = "₱0.00"

            c1, c2 = st.columns([0.88, 0.12])
            with c1:
                st.markdown(f"### 📌 {p.get('Project Name')}")
                a,b,c,d = st.columns(4)
                a.write(f"**Control #:** {p.get('Control Number','—')}")
                b.write(f"**Merchant:** {p.get('Merchant') or '—'}")
                c.write(f"**Status:** {p.get('Project Status','—')}")
                d.write(f"**Tribe:** {p.get('Tribe','—')}")
                a,b,c,d = st.columns(4)
                a.write(f"**Doc Type:** {p.get('Doc Type','—')}")
                b.write(f"**BA:** {p.get('Assigned BA','—')}")
                c.write(f"**Price:** {price_display}")
                d.write(f"**Doc State:** {p.get('Doc State','—')}")
                a,b,c,d = st.columns(4)
                a.write(f"**Go Live:** {p.get('Go Live Date','—')}")
                b.write(f"**Expiry:** {p.get('Doc Expiry Date','—')}")
                c.write(f"**Endorsed By:** {p.get('Endorsed By') or '—'}")
                d.write(f"{emoji} **{p.get('expiry_status','—')}**")
                if p.get("Links","").strip():
                    st.markdown(f"**Links:** {p.get('Links')}")
                if p.get("Remarks","").strip():
                    st.write(f"**Remarks:** {p.get('Remarks')}")
            with c2:
                if st.button("🗑️ Delete", key=f"del_{idx}", use_container_width=True):
                    st.session_state.projects.pop(idx)
                    st.rerun()
            st.markdown("---")
    else:
        st.info("📭 No projects yet.")
