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

# ── Google Sheets Schema Configuration ───────────────────────────
SHEET_ID   = st.secrets["GOOGLE_SHEETS_ID"]
SA_CREDS   = st.secrets["service_account"]
SCOPE      = ["https://spreadsheets.google.com/feeds","https://www.googleapis.com/auth/drive"]

# Updated to naturally include PO Status and Sprint rows
PROJECT_COLS = [
    "ID", "Doc Type", "Project Name", "Control Number", "PO Status", "Merchant", "Endorsed By",
    "Project Price", "Links", "Date Endorsed Commercial", "Doc Expiry Date",
    "Date Endorsed BA", "Assigned BA", "Date Ack BA", "Doc State", "Tribe", "Sprint",
    "Project Status", "Date Endorsed Tech", "Go Live Date", "Approval Status", "Remarks", "Created At"
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
    except:
        ws = sh.add_worksheet(tab, rows=1000, cols=33)
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

def update_project_row(project_id, updated_p):
    ws = get_sheet("Projects")
    cell = ws.find(project_id)
    if cell:
        row_values = [str(updated_p.get(c, "")) for c in PROJECT_COLS]
        ws.update(range_name=f"A{cell.row}:W{cell.row}", values=[row_values])
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
if "projects" not in st.session_state:
    st.session_state.projects = load_projects()

DEFAULT_SETTINGS = {
    "doc_types": ["CRF","BRF","FEF","System Design","Feature Spec","Integration Doc","Release Notes"],
    "ba_list":   ["BA001 - John Smith","BA002 - Maria Garcia","BA003 - Sarah Chen","BA004 - Ahmed Hassan"],
    "doc_states":["Draft","In Review","Approved","Published","Archived"],
    "tribes":    ["Core Tribe","Growth Tribe","Infrastructure Tribe","Platform Tribe"],
    "statuses":
