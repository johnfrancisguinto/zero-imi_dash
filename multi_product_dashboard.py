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

st.set_page_config(
    page_title="Zero Dashboard",
    page_icon="Zero_logo.ico",
    layout="wide"
)

st.markdown("""
<style>

/* ===== PAGE ===== */
.block-container{
    padding-top:1.5rem;
    padding-bottom:0rem;
    max-width:100%;
}

/* ===== BACKGROUND ===== */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(
        180deg,
        #DBDBDB 0%,
        #BFBFBF 100%
    );
}

/* ===== HEADERS ===== */
h1{
    color:#FF3139;
    text-shadow: 0 0 12px rgba(212,255,0,0.5);
    margin:0;
}

h2,h3{
    margin-top:0rem !important;
    margin-bottom:0.4rem !important;
}

/* ===== SUMMARY / KPI CARDS ===== */
.card{
    background:#111;
    color:white;
    padding:10px;
    border-radius:12px;
    text-align:center;
    box-shadow:0 2px 4px rgba(0,0,0,0.2);
}

/* ===== TABS ===== */
.stTabs [role="tablist"]{
    gap:10px;
}

.stTabs [role="tab"]{
    font-size:15px;
    font-weight:bold;
    padding:7px 12px;
    border-radius:10px;
    background-color:#222;
    color:white;
    margin-top:5px;
    margin-bottom:5px;
}

.stTabs [role="tab"][aria-selected="true"]{
    background-color:#969696;
    color:black;
}

.stTabs [role="tab"]:hover{
    background-color:#636363;
    color:black;
}

/* ===== DATAFRAMES ===== */
[data-testid="stDataFrame"]{
    font-size:12px;
}

/* ===== SELECTBOX ===== */
div[data-baseweb="select"]{
    font-size:12px;
}

/* ===== EXPANDERS ===== */
.streamlit-expanderHeader{
    padding-top:0px;
    padding-bottom:0px;
}

</style>
""", unsafe_allow_html=True)

st.markdown("""
<div style="
display:flex;
align-items:center;
justify-content:center;
gap:15px;
padding-top:10px;
padding-bottom:10px;
overflow:visible;
">

<img src="https://raw.githubusercontent.com/johnfrancisguinto/zero-imi_dash/main/Zero-Motorcycles-logo.png"
width="120">

<h1 style="
color:#FF3139;
font-size:36px;
margin:0;
">
LIVE: IMI PRODUCTION DASHBOARD
</h1>
            
</div>
""", unsafe_allow_html=True)

st.markdown("""
<style>

header {
    visibility:hidden;
}

footer {
    visibility:hidden;
}

#MainMenu {
    visibility:hidden;
}

[data-testid="stToolbar"] {
    display:none;
}

.block-container {
    padding-top:0rem;
    padding-bottom:0rem;
    padding-left:1rem;
    padding-right:1rem;
}

</style>
""", unsafe_allow_html=True)

TYPE_MAP = {
    "D": "ADVENTURE",
    "Z": "STREET"
}

VARIANT_MAP = {
    "FD": "SRF",
    "FE": "SRS",
    "FG": "SR",
    "FS": "S",
    "ZA": "DSRX",
    "ZB": "DSR",
    "ZS": "DS",
    "XD": "FX",
    "XF": "FXE"
}

MY_MAP = {
    "R": "24MY",
    "S": "25MY",
    "T": "26MY",
    "V": "27MY"
}


def get_sku(vin):
    try:
        product_type = TYPE_MAP.get(vin[3], "UNKNOWN")
        variant = VARIANT_MAP.get(vin[4:6], "UNKNOWN")
        model_year = MY_MAP.get(vin[9], "UNKNOWN")

        return f"{variant} {model_year}"

    except Exception:
        return "UNKNOWN"
        
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
    df["sku"] = df["serial_number"].astype(str).apply(get_sku)

    return df


def process_df(df):
    latest = df.groupby("serial_number").first().reset_index()
    history = df.sort_values("datetime").groupby("serial_number")["station"].apply(list)

    latest["steps"] = latest["serial_number"].map(lambda x: len(set(history.get(x, []))))

    now = datetime.now()
    latest["hours"] = (now - latest["datetime"]).dt.total_seconds() / 3600

    stalled = latest[latest["hours"] > 24]

    return latest, stalled
def get_station_order(df):

    if df.empty:
        return []

    stations = (
        df["station"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    return stations

def get_production_counts(df):
    if df.empty:
        return 0, 0

    now = datetime.now()

    # Only completed units
    completed = df[
        (df["station"] == "FQC") &
        (df["results"] == "PASS")
    ].copy()

    # Daily Count
    today = now.date()

    daily_count = (
        completed[
            completed["datetime"].dt.date == today
        ]["serial_number"]
        .nunique()
    )

    # Weekly Count (Sunday reset)
    days_since_sunday = (now.weekday() + 1) % 7
    last_sunday = now.date() - pd.Timedelta(days=days_since_sunday)

    weekly_count = (
        completed[
            completed["datetime"].dt.date >= last_sunday
        ]["serial_number"]
        .nunique()
    )

    return daily_count, weekly_count

def render_dashboard(df, title):
    # st.subheader(title)

    if df.empty:
        st.warning("No data")
        return 0

    latest, stalled = process_df(df)
        
    daily_count, weekly_count = get_production_counts(df)

    station_order = get_station_order(df)

    # counts_full = {pc: counts.get(pc, 0) for pc in station_order}

    # cols = st.columns(len(station_order))
    # for i, pc in enumerate(station_order):
    #     with cols[i]:
    #         st.metric(pc, counts_full[pc])

    left_col, right_col = st.columns([1, 2])

    with left_col:

        if title == "BIKE Line":

            latest = latest[
                latest["station"] != "Shipped"
    ]
            st.subheader("🏷️ SKU on Line")
        
            sku_counts = (
                latest.groupby("sku")
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
            )
        
            sku_cols = st.columns(2)
            
            for i, row in enumerate(sku_counts.itertuples()):
                with sku_cols[i % 2]:
                    st.metric(
                        label=row.sku,
                        value=row.count
                    )
                
        st.markdown("### 🛵 Units")

        for pc in station_order:
        
            station_df = latest[
                latest["station"] == pc
            ]
        
            with st.expander(
                f"{pc} ({len(station_df)})",
                expanded=False
            ):
        
                if station_df.empty:
                    st.write("No units")
        
                else:
        
                    badges = []
        
                    for _, row in station_df.iterrows():
        
                        vin = row["serial_number"]
        
                        result = str(
                            row["results"]
                        ).upper()
        
                        bg = "#00AA00" if result == "PASS" else "#CC0000"
        
                        badges.append(
                            f"""
                            <span style="
                                background:{bg};
                                color:white;
                                padding:3px 8px;
                                border-radius:8px;
                                margin:2px;
                                display:inline-block;
                                font-size:12px;
                                font-weight:bold;
                            ">
                                {vin}
                            </span>
                            """
                        )
        
                    st.markdown(
                        "".join(badges),
                        unsafe_allow_html=True
                    )

    with right_col:
        
        kpi1, kpi2 = st.columns(2)
    
        with kpi1:
            st.markdown(f"""
            <div class='card'>
                <div style='font-size:14px;'>📅 DAILY OUTPUT</div>
                <div style='font-size:26px;font-weight:bold;color:#00AEEF;'>
                    {daily_count}
                </div>
            </div>
            """, unsafe_allow_html=True)
    
        with kpi2:
            st.markdown(f"""
            <div class='card'>
                <div style='font-size:14px;'>📈 WEEKLY OUTPUT</div>
                <div style='font-size:26px;font-weight:bold;color:#FF3139;'>
                    {weekly_count}
                </div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("### 🧭 WIP Trace")

        serial = st.selectbox(
            "VIN",
            df["serial_number"].unique()
        )

        trace = (
            df[df["serial_number"] == serial]
            .sort_values("datetime")
        )
        
        def color_result(val):
            color = "#00ff00" if val=="PASS" else "#ff3333"
            return f"color:{color}; font-weight:bold"
        
        st.dataframe(
            trace[
                [
                    "datetime",
                    "station",
                    "serial_number",
                    "results"
                ]
            ].style.map(
                color_result,
                subset=["results"]
            ),
            use_container_width=True,
            hide_index=True,
            height=280
        )

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
                <div style='font-size:15px;'>{station}</div>
                <div style='color:#00ff00;'>PASS: {pass_count}  <span style='color:#ff3333;'>FAIL: {fail_count}</span></div>
                <div style='margin-top:10px;font-size:16px;'>
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
            st.dataframe(
                stalled[
                    ["serial_number","station","hours"]
                ],
                hide_index=True,
                use_container_width=True,
                height=200
            )

    with col2:
        stuck = latest[latest["steps"] <= 1]
        st.markdown("### No Movement")
        if stuck.empty:
            st.success("OK")
        else:
            st.dataframe(
                stuck[
                    ["serial_number","station","steps"]
                ],
                hide_index=True,
                use_container_width=True,
                height=200
            )

    return total

# ================= GLOBAL SUMMARY =================
# st.subheader("📈 SUMMARY")

product_totals = {}

for name, sheet_name in PRODUCT_SHEETS.items():

    df_temp = load_sheet(sheet_name)

    if df_temp.empty:

        product_totals[name] = 0

    else:

        latest, _ = process_df(df_temp)

        if name == "BIKE Line":

            latest = latest[
                latest["station"] != "Shipped"
            ]

        product_totals[name] = len(latest)

total_all = sum(product_totals.values())

cols = st.columns(len(PRODUCT_SHEETS) + 1)
# cols[0].metric("ALL PRODUCTS", total_all)
cols[0].markdown(f"""
<div style="
    background:#111;
    padding:6px;
    border-radius:12px;
    text-align:center;
    border:3px solid #949494;
">
    <div style="font-size:18px;color:#C1E9E2;">ALL PRODUCTS</div>
    <div style="font-size:32px;color:#949494;font-weight:bold;">
        {total_all}
    </div>
</div>
""", unsafe_allow_html=True)

for i, (name, val) in enumerate(product_totals.items()):
    # cols[i+1].metric(name, val)
    cols[i+1].markdown(f"""
    <div style="
        background:#111;
        padding:6px;
        border-radius:12px;
        text-align:center;
        border:3px solid #949494;
    ">
        <div style="font-size:18px;color:#C1E9E2;">{name}</div>
        <div style="font-size:32px;color:#949494;font-weight:bold;">
            {val}
        </div>
    </div>
    """, unsafe_allow_html=True)

# ================= TABS =================
tab_names = list(PRODUCT_SHEETS.keys()) + [
    "🚚 Bike Logistics"
]

tabs = st.tabs(tab_names)

for tab, (name, sheet_name) in zip(
    tabs[:len(PRODUCT_SHEETS)],
    PRODUCT_SHEETS.items()
):
    
    with tab:
        df = load_sheet(sheet_name)
        render_dashboard(df, name)

    with tabs[-1]:

        st.subheader("🚚 Bike Logistics")

        bike_df = load_sheet("Bike_line")

        latest, _ = process_df(bike_df)

        available = latest[
            latest["station"] == "PDI"
        ]

        col1, col2 = st.columns(2)

        with col1:

            st.metric(
                "Available For Shipment",
                len(available)
            )

        with col2:

            shipped_count = len(
                latest[
                    latest["station"] == "Shipped"
                ]
            )

            st.metric(
                "Shipped Units",
                shipped_count
            )

        st.divider()

        selected_units = st.multiselect(
            "Units to Ship",
            available["serial_number"].tolist()
        )

        shipment_id = st.text_input(
            "Shipment ID"
        )

        if st.button(
            "🚚 Mark Selected as Shipped"
        ):

            if not shipment_id:

                st.error(
                    "Enter Shipment ID"
                )

            elif not selected_units:

                st.error(
                    "Select units"
                )

            else:

                bike_sheet = (
                    client.open_by_key(
                        SPREADSHEET_ID
                    )
                    .worksheet("Bike_line")
                )

                ship_sheet = (
                    client.open_by_key(
                        SPREADSHEET_ID
                    )
                    .worksheet("Shipments")
                )

                now = (
                    datetime.now()
                    .strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )
                )

                for serial in selected_units:

                    bike_sheet.append_row([
                        now,
                        serial,
                        "Shipped",
                        "PASS"
                    ])

                    ship_sheet.append_row([
                        now,
                        shipment_id,
                        serial
                    ])

                st.success(
                    f"{len(selected_units)} unit(s) shipped"
                )

                st.rerun()


# AUTO REFRESH
st_autorefresh(interval=REFRESH_INTERVAL, key="refresh")
st.caption("Auto-refresh every 5 minutes")
