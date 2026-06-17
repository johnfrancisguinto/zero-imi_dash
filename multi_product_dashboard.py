import gspread
import pandas as pd
import streamlit as st
from google.oauth2.service_account import Credentials
from datetime import datetime
from streamlit_autorefresh import st_autorefresh

import os
import json

# ================= CONFIG =================
SPREADSHEET_ID = "1Zx9yhlJb4gr8yKec7owh3xhwG36azWXhx4eK5WIYPR4"
REFRESH_INTERVAL = 300000

# Define product sheets
PRODUCT_SHEETS = {
    "BIKE Line": "Bike_line",
    "BCB Line": "BCB_line",
    "CII Line": "CII_line",
}

# station order per product (edit if needed)
STATIONS_PER_PRODUCT = {
    "BIKE Line": ["MBB Config", "PREL", "FQC"],  # 3 stations
    "BCB Line": ["BAT0", "BAT2/3", "FQC"], # 4 stations
    "CII Line": ["BAT0", "BAT2/3", "Post-Shower", "FQC"], # 5 stations
}

st.markdown("""
<style>

/* EXISTING STYLES */
.card {
    background-color:#111;
    color:white;
    padding:20px;
    border-radius:12px;
    text-align:center;
}
.station-box {
    display:inline-block;
    padding:10px 20px;
    margin:5px;
    border-radius:10px;
    background:#222;
}

/* spacing between tabs */
.stTabs [role="tablist"] {
    gap: 20px;
}

/* tab buttons */
.stTabs [role="tab"] {
    font-size: 26px;          /* 🔥 make bigger */
    font-weight: bold;
    padding: 12px 20px;
    border-radius: 12px;
    background-color: #222;
    color: white;
    margin-top: 40px;
    margin-bottom: 15px;
}

/* active tab */
.stTabs [role="tab"][aria-selected="true"] {
    background-color: #969696;
    color: black;
}

/* hover effect */
.stTabs [role="tab"]:hover {
    background-color: #636363;
    color: black;
}

</style>
""", unsafe_allow_html=True)

# AUTO REFRESH
st_autorefresh(interval=REFRESH_INTERVAL, key="refresh")

# UI
st.set_page_config(layout="wide")# UI STYLE (FACTORY LOOK)
# st.title("🏭 IMI PRODUCTION DASHBOARD")
st.markdown("""
<h1 style='
    text-align: center;
    font-size: 50px;
    color: #D12300;
    margin-bottom: 10px;
'>
🏭  LIVE: IMI PRODUCTION DASHBOARD
</h1>
""", unsafe_allow_html=True)

# Google Sheets
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

creds_dict = json.loads(os.environ["GOOGLE_CREDENTIALS"])


creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")

creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
client = gspread.authorize(creds)

# ================= UTIL =================
def load_sheet(sheet_name):
    sh = client.open_by_key(SPREADSHEET_ID).worksheet(sheet_name)
    df = pd.DataFrame(sh.get_all_records())

    if df.empty:
        return df

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.map(lambda x: str(x).strip())
    df["datetime"] = pd.to_datetime(df["datetime"], errors="coerce")
    df = df.sort_values("datetime", ascending=False)

    return df


def process_df(df):
    latest = df.groupby("serial_number").first().reset_index()
    history = df.sort_values("datetime").groupby("serial_number")["station"].apply(list)

    latest["steps"] = latest["serial_number"].map(lambda x: len(set(history.get(x, []))))

    now = datetime.now()
    latest["hours"] = (now - latest["datetime"]).dt.total_seconds() / 3600

    stalled = latest[latest["hours"] > 24]

    return latest, stalled


def render_dashboard(df, title):
    st.subheader(title)

    if df.empty:
        st.warning("No data")
        return 0

    latest, stalled = process_df(df)

    # total = len(latest)
    # st.metric("TOTAL ACTIVE SERIALS", total)

    # station counts
    # counts = latest["station"].value_counts().to_dict()
    station_order = STATIONS_PER_PRODUCT[title]

    # counts_full = {pc: counts.get(pc, 0) for pc in station_order}

    # cols = st.columns(len(station_order))
    # for i, pc in enumerate(station_order):
    #     with cols[i]:
    #         st.metric(pc, counts_full[pc])

    # Flow grouped
    st.subheader("🔄Unit per STATION")
    for pc in station_order:
        serials = latest[latest["station"] == pc]["serial_number"].tolist()
        with st.expander(f"{pc} ({len(serials)})"):
            st.write(", ".join(serials[:20]) if serials else "No units")

    # ================= TRACE =================
    st.subheader("🧭 SERIAL TRACE")
    serial = st.selectbox("Select/Type VIN", df["serial_number"].unique())
    trace = df[df["serial_number"]==serial].sort_values("datetime")
    
    def color_result(val):
        color = "#00ff00" if val=="PASS" else "#ff3333"
        return f"color:{color}; font-weight:bold"
    
    st.dataframe(
        trace[["datetime", "station", "serial_number", "results"]]
        .style.map(color_result, subset=["results"]),hide_index=True)

    # ================= PASS FAIL PER PC =================
    st.subheader("📊 PASS / FAIL PER STATION")

    pf_station = df.groupby(["station", "results"]).size().unstack(fill_value=0)

    cols = st.columns(len(station_order))

    for i, station in enumerate(station_order):
        with cols[i]:
            # Get row safely (even if station has no data)
            if station in pf_station.index:
                row = pf_station.loc[station]
                pass_count = row.get("PASS", 0)
                fail_count = row.get("FAIL", 0)
            else:
                pass_count = 0
                fail_count = 0

            total = pass_count + fail_count
            pass_rate = (pass_count / total * 100) if total > 0 else 0

            # Optional color logic
            if pass_rate >= 95:
                rate_color = "#00ff00"
            elif pass_rate >= 85:
                rate_color = "#ffaa00"
            else:
                rate_color = "#ff3333"

            st.markdown(f"""
            <div class='card'>
                <div style='font-size:18px;'>{station}</div>
                <div style='color:#00ff00;'>PASS: {pass_count}  <span style='color:#ff3333;'>FAIL: {fail_count}</span></div>
                <div style='margin-top:10px;font-size:20px;'>
                    PASS RATE: <span style='color:{rate_color};'>{pass_rate:.1f}%</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Alerts
    st.subheader("🚨 ALERTS")

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("### Stalled")
        if stalled.empty:
            st.success("OK")
        else:
            st.dataframe(stalled[["serial_number","station","hours"]],hide_index=True)

    with col2:
        stuck = latest[latest["steps"] <= 1]
        st.markdown("### No Movement")
        if stuck.empty:
            st.success("OK")
        else:
            st.dataframe(stuck[["serial_number","station","steps"]],hide_index=True)

    return total

# ================= GLOBAL SUMMARY =================
st.subheader("📊 SUMMARY")

product_totals = {}

for name, sheet_name in PRODUCT_SHEETS.items():
    df_temp = load_sheet(sheet_name)
    if df_temp.empty:
        product_totals[name] = 0
    else:
        latest, _ = process_df(df_temp)
        product_totals[name] = len(latest)

total_all = sum(product_totals.values())

cols = st.columns(len(PRODUCT_SHEETS) + 1)
# cols[0].metric("ALL PRODUCTS", total_all)
cols[0].markdown(f"""
<div style="
    background:#111;
    padding:15px;
    border-radius:12px;
    text-align:center;
    border:3px solid #949494;
">
    <div style="font-size:20px;color:#C1E9E2;">ALL PRODUCTS</div>
    <div style="font-size:50px;color:#949494;font-weight:bold;">
        {total_all}
    </div>
</div>
""", unsafe_allow_html=True)

for i, (name, val) in enumerate(product_totals.items()):
    # cols[i+1].metric(name, val)
    cols[i+1].markdown(f"""
    <div style="
        background:#111;
        padding:15px;
        border-radius:12px;
        text-align:center;
        border:3px solid #949494;
    ">
        <div style="font-size:20px;color:#C1E9E2;">{name}</div>
        <div style="font-size:50px;color:#949494;font-weight:bold;">
            {val}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ================= TABS =================
tabs = st.tabs(list(PRODUCT_SHEETS.keys()))

for tab, (name, sheet_name) in zip(tabs, PRODUCT_SHEETS.items()):
    with tab:
        df = load_sheet(sheet_name)
        render_dashboard(df, name)

st.caption("Auto-refresh every 5 minutes")
