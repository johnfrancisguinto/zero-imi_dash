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

SKU_MASTER = json.loads(
    os.getenv(
        "SKU_MASTER",
        "{}"
    )
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
<style>

/* Product selector cards */

div[data-testid="stButton"] > button {

    background:#111 !important;

    border:3px solid #949494 !important;

    border-radius:12px !important;

    min-height:95px !important;

    font-size:22px !important;

    font-weight:bold !important;

    color:#C1E9E2 !important;

    white-space:pre-line !important;

}

div[data-testid="stButton"] > button:hover {

    border:3px solid #00FF00 !important;

    color:#00FF00 !important;

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

def get_sku_name(sku_number):

    sku_info = SKU_MASTER.get(
        str(sku_number).strip(),
        {}
    )

    return sku_info.get(
        "name",
        "UNKNOWN SKU"
    )

def get_part(vin):
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
SPREADSHEET = client.open_by_key(
    SPREADSHEET_ID
)

# ================= UTIL =================
# @st.cache_data(ttl=300)
def load_sheet(sheet_name):
    sh = SPREADSHEET.worksheet(
    sheet_name
)
    df = pd.DataFrame(sh.get_all_records())

    if df.empty:
        return df

    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]
    df = df.map(lambda x: str(x).strip())
    df["datetime"] = pd.to_datetime(
        df["datetime"],
        errors="coerce"
    )

    # oldest to newest
    df = df.sort_values("datetime")

    if "sku_number" in df.columns:

        df["sku_number"] = (
            df["sku_number"]
            .replace("", pd.NA)
            .replace(" ", pd.NA)
        )

        df["sku_number"] = (
            df.groupby("serial_number")["sku_number"]
            .ffill()
        )

    if "bcb_part_number" in df.columns:

        df["bcb_part_number"] = (
            df["bcb_part_number"]
            .replace("", pd.NA)
            .replace(" ", pd.NA)
        )

        df["bcb_part_number"] = (
            df.groupby("serial_number")["bcb_part_number"]
            .ffill()
        )

    # latest first for dashboard
    df = df.sort_values(
        "datetime",
        ascending=False
    )
    df["sku"] = df["serial_number"].astype(str).apply(get_part)

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

def render_dashboard(df, title, view="overall"):
    # st.subheader(title)

    if df.empty:
        st.warning("No data")
        return 0

    latest, stalled = process_df(df)

    daily_count, weekly_count = get_production_counts(df)

    station_order = get_station_order(df)
    today = datetime.now().date()

    daily_df = df[
        df["datetime"].dt.date == today
    ].copy()

    days_since_sunday = (
        datetime.now().weekday() + 1
    ) % 7

    last_sunday = (
        datetime.now().date() -
        pd.Timedelta(days=days_since_sunday)
    )

    weekly_df = df[
        df["datetime"].dt.date >= last_sunday
    ].copy()

    def render_units_and_pf(view_df):

        latest_view, _ = process_df(view_df)
        

        if title == "BIKE Line":

            latest_view = latest_view[
                latest_view["station"] != "Shipped"
            ]

            st.subheader("🏷️ SKU on Line")
            sku_df = latest.copy()

            sku_df["sku_number"] = (
                sku_df["sku_number"]
                .fillna("")
                .astype(str)
                .str.strip()
            )

            sku_df.loc[
                sku_df["sku_number"] == "",
                "sku_number"
            ] = "UNKNOWN SKU"

            sku_counts = (
                sku_df
                .groupby(["sku_number", "sku"])
                .size()
                .reset_index(name="count")
                .sort_values("count", ascending=False)
            )

            sku_cols = st.columns(2)

            for i, row in enumerate(sku_counts.itertuples()):

                with sku_cols[i % 2]:

                    st.metric(
                        label=f"{row.sku_number} | {row.sku}",
                        value=row.count
                    )

        left_col, right_col = st.columns([1, 1])

        # ================= UNITS =================

        with left_col:

            st.markdown("### 🛵 Units")

            for pc in station_order:

                station_df = latest_view[
                    latest_view["station"] == pc
                ]

                with st.expander(
                    f"{pc} ({len(station_df)})"
                ):

                    if station_df.empty:

                        st.write("No units")

                    else:

                        badges = []

                        for _, row in station_df.iterrows():

                            vin = str(row["serial_number"])

                            sku_num = str(
                                row.get("sku_number", "")
                            ).strip()

                            bcb_num = str(
                                row.get("bcb_part_number", "")
                            ).strip()

                            if pc in ["MBB Config", "PREL"]:

                                display_text = (
                                    f"{vin} - {sku_num}"
                                    if sku_num
                                    else vin
                                )

                            elif pc == "FQC":

                                display_text = (
                                    f"{vin} - {bcb_num}"
                                    if bcb_num
                                    else vin
                                )

                            else:

                                display_text = vin

                            result = str(
                                row["results"]
                            ).upper()

                            bg = (
                                "#00AA00"
                                if result == "PASS"
                                else "#CC0000"
                            )

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
                                    {display_text}
                                </span>
                                """
                            )

                        st.markdown(
                            "".join(badges),
                            unsafe_allow_html=True
                        )

        # ================= PASS FAIL =================

        with right_col:

            st.markdown(
                "### 📊 Pass / Fail"
            )

            pf_station = (
                view_df
                .groupby(
                    ["station", "results"]
                )
                .size()
                .unstack(fill_value=0)
            )

            cols = st.columns(len(station_order))

            for i, station in enumerate(station_order):

                with cols[i]:

                    if station in pf_station.index:
                        row = pf_station.loc[station]

                        pass_count = row.get("PASS", 0)
                        fail_count = row.get("FAIL", 0)

                    else:

                        pass_count = 0
                        fail_count = 0

                    total = pass_count + fail_count

                    pass_rate = (
                        pass_count / total * 100
                        if total > 0
                        else 0
                    )

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

        
    if view == "daily":

        view_df = daily_df

        st.markdown(f"""
        <div class='card'>
            <div style='font-size:14px;'>📅 DAILY OUTPUT</div>
            <div style='font-size:26px;font-weight:bold;color:#00AEEF;'>
                {daily_count}
            </div>
        </div>
        """, unsafe_allow_html=True)

    elif view == "weekly":

        view_df = weekly_df

        st.markdown(f"""
        <div class='card'>
            <div style='font-size:14px;'>📈 WEEKLY OUTPUT</div>
            <div style='font-size:26px;font-weight:bold;color:#FF3139;'>
                {weekly_count}
            </div>
        </div>
        """, unsafe_allow_html=True)

    else:

        view_df = df

        total_wip = len(latest)

        if title == "BIKE Line":

            total_wip = len(
                latest[
                    latest["station"] != "Shipped"
                ]
            )

        st.markdown(f"""
        <div class='card'>
            <div style='font-size:14px;'>📦 TOTAL OVERALL</div>
            <div style='font-size:26px;font-weight:bold;color:#00FF00;'>
                {total_wip}
            </div>
        </div>
        """, unsafe_allow_html=True)

    st.divider()

    render_units_and_pf(view_df)

    # # Alerts
    # st.subheader("🚨 ALERTS")

    # col1, col2 = st.columns(2)

    # with col1:
    #     st.markdown("### Stalled")
    #     if stalled.empty:
    #         st.success("OK")
    #     else:
    #         st.dataframe(
    #             stalled[
    #                 ["serial_number","station","hours"]
    #             ],
    #             hide_index=True,
    #             use_container_width=True,
    #             height=200
    #         )

    # with col2:
    #     stuck = latest[latest["steps"] <= 1]
    #     st.markdown("### No Movement")
    #     if stuck.empty:
    #         st.success("OK")
    #     else:
    #         st.dataframe(
    #             stuck[
    #                 ["serial_number","station","steps"]
    #             ],
    #             hide_index=True,
    #             use_container_width=True,
    #             height=200
    #         )

    return len(latest)

# ================= GLOBAL SUMMARY =================

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

# ================= PRODUCT SELECTOR =================

if "selected_product" not in st.session_state:
    st.session_state.selected_product = "BIKE Line"

selected = st.session_state.selected_product

col1, col2, col3, col4 = st.columns(4)

# ================= ALL PRODUCTS =================

with col1:

    st.markdown(f"""
    <div style="
        background:#111;
        padding:6px;
        border-radius:12px;
        text-align:center;
        border:3px solid #949494;
    ">
        <div style="font-size:18px;color:#C1E9E2;">
            ALL PRODUCTS
        </div>
        <div style="
            font-size:32px;
            color:#949494;
            font-weight:bold;
        ">
            {total_all}
        </div>
    </div>
    """, unsafe_allow_html=True)


# ================= BIKE =================

with col2:

    # bike_border = (
    #     "#00FF00"
    #     if selected == "BIKE Line"
    #     else "#949494"
    # )

    # st.markdown(f"""
    # <div style="
    #     background:#111;
    #     padding:6px;
    #     border-radius:12px;
    #     text-align:center;
    #     border:3px solid {bike_border};
    #     margin-bottom:5px;
    # ">
    #     <div style="font-size:18px;color:#C1E9E2;">
    #         🛵 BIKE Line
    #     </div>
    #     <div style="
    #         font-size:32px;
    #         color:{bike_border};
    #         font-weight:bold;
    #     ">
    #         {product_totals['BIKE Line']}
    #     </div>
    # </div>
    # """, unsafe_allow_html=True)

    if st.button(
        f"🛵 BIKE Line\n{product_totals['BIKE Line']}",
        key="bike_line",
        use_container_width=True
    ):
        st.session_state.selected_product = "BIKE Line"
        st.rerun()


# ================= BCB =================

with col3:

    # bcb_border = (
    #     "#00FF00"
    #     if selected == "BCB Line"
    #     else "#949494"
    # )

    # st.markdown(f"""
    # <div style="
    #     background:#111;
    #     padding:6px;
    #     border-radius:12px;
    #     text-align:center;
    #     border:3px solid {bcb_border};
    #     margin-bottom:5px;
    # ">
    #     <div style="font-size:18px;color:#C1E9E2;">
    #         🔋 BCB Line
    #     </div>
    #     <div style="
    #         font-size:32px;
    #         color:{bcb_border};
    #         font-weight:bold;
    #     ">
    #         {product_totals['BCB Line']}
    #     </div>
    # </div>
    # """, unsafe_allow_html=True)

    if st.button(
        f"🔋 BCB Line\n{product_totals['BCB Line']}",
        key="bcb_line",
        use_container_width=True
    ):
        st.session_state.selected_product = "BCB Line"
        st.rerun()


# ================= CII =================

with col4:

    # cii_border = (
    #     "#00FF00"
    #     if selected == "CII Line"
    #     else "#949494"
    # )

    # st.markdown(f"""
    # <div style="
    #     background:#111;
    #     padding:6px;
    #     border-radius:12px;
    #     text-align:center;
    #     border:3px solid {cii_border};
    #     margin-bottom:5px;
    # ">
    #     <div style="font-size:18px;color:#C1E9E2;">
    #         ⚙️ CII Line
    #     </div>
    #     <div style="
    #         font-size:32px;
    #         color:{cii_border};
    #         font-weight:bold;
    #     ">
    #         {product_totals['CII Line']}
    #     </div>
    # </div>
    # """, unsafe_allow_html=True)

    if st.button(
        f"⚙️ CII Line\n{product_totals['CII Line']}",
        key="cii_line",
        use_container_width=True
    ):
        st.session_state.selected_product = "CII Line"
        st.rerun()


selected_product = st.session_state.selected_product

sheet_name = PRODUCT_SHEETS[selected_product]

df = load_sheet(sheet_name)

st.divider()

# ================= BIKE LINE =================

if selected_product == "BIKE Line":
    bike_sheet = SPREADSHEET.worksheet(
        "Bike_line"
    )

    ship_sheet = SPREADSHEET.worksheet(
        "Shipments"
    )

    daily_tab, weekly_tab, overall_tab, pdi_tab, logistics_tab = st.tabs([
    "📅 Daily",
    "📈 Weekly",
    "📊 Overall",
    "📝 PDI Entry",
    "🚚 Bike Logistics"
    ])


    with daily_tab:
        render_dashboard(
            df,
            selected_product,
            "daily"
        )

    with weekly_tab:
        render_dashboard(
            df,
            selected_product,
            "weekly"
        )

    with overall_tab:
        render_dashboard(
            df,
            selected_product,
            "overall"
        )

    with pdi_tab:

        st.subheader("📝 PDI Entry")

        latest, _ = process_df(df)
        
        available_pdi = latest[
            (latest["station"] == "FQC")
            &
            (latest["results"] == "PASS")
        ]

        if available_pdi.empty:

            st.info(
                "No units available for PDI."
            )

        else:

            pdi_table = pd.DataFrame({
                "Select": False,

                "VIN":
                    available_pdi[
                        "serial_number"
                    ].tolist(),

                "SKU Number":
                    available_pdi[
                        "sku_number"
                    ].fillna("").tolist(),

                "BCB PN":
                    available_pdi[
                        "bcb_part_number"
                    ].fillna("").tolist()
            })

            pdi_table["SKU Name"] = (
                pdi_table["SKU Number"]
                .apply(get_sku_name)
            )

            pdi_table = pdi_table[
                [
                    "Select",
                    "SKU Number",
                    "SKU Name",
                    "VIN",
                    "BCB PN"
                ]
            ]

            edited = st.data_editor(
                pdi_table,
                hide_index=True,
                use_container_width=True,
                disabled=["VIN"]
            )

            selected_units = edited[
                edited["Select"]
            ]["VIN"].tolist()

            col1, col2 = st.columns(2)

            with col1:
                st.metric(
                    "Available",
                    len(available_pdi)
                )

            with col2:
                st.metric(
                    "Selected",
                    len(selected_units)
                )

            if st.button(
                f"✅ Submit {len(selected_units)} PDI Unit(s)",
                use_container_width=True,
                key="submit_pdi"
            ):

                if not selected_units:

                    st.warning(
                        "Select at least one unit."
                    )

                else:

                    now = datetime.now().strftime(
                        "%Y-%m-%d %H:%M:%S"
                    )

                    for vin in selected_units:

                        bike_sheet.append_row([
                            now,
                            "PDI",
                            vin,
                            "PASS"
                        ])

                    st.success(
                        f"{len(selected_units)} unit(s) updated."
                    )
                    st.cache_data.clear()
                    st.rerun()

    with logistics_tab:

        st.subheader("🚚 Bike Logistics")

        bike_df = df

        latest, _ = process_df(
            bike_df
        )
        available_shipment = latest[
            (latest["station"] == "PDI")
            &
            (latest["results"] == "PASS")
        ]

        shipment_id = st.text_input(
            "Shipment ID"
        )

        ship_table = pd.DataFrame({
            "Select": False,

            "VIN":
                available_shipment[
                    "serial_number"
                ].tolist(),

            "SKU Number":
                available_shipment[
                    "sku_number"
                ].fillna("").tolist(),

            "BCB PN":
                available_shipment[
                    "bcb_part_number"
                ].fillna("").tolist()
        })

        ship_table["SKU Name"] = (
            ship_table["SKU Number"]
            .apply(get_sku_name)
        )

        ship_table = ship_table[
            [
                "Select",
                "SKU Number",
                "SKU Name",
                "VIN",
                "BCB PN"
            ]
        ]

        edited = st.data_editor(
            ship_table,
            hide_index=True,
            use_container_width=True,
            disabled=["VIN"]
        )

        selected_units = edited[
            edited["Select"]
        ]["VIN"].tolist()

        col1, col2, col3 = st.columns(3)

        with col1:
            st.metric(
                "Available For Shipment",
                len(available_shipment)
            )

        with col2:
            st.metric(
                "Selected",
                len(selected_units)
            )

        with col3:
            st.metric(
                "Shipped Units",
                len(
                    latest[
                        latest["station"] == "Shipped"
                    ]
                )
            )

        if st.button(
            f"🚚 Ship {len(selected_units)} Unit(s)",
            use_container_width=True,
            key="ship_units"
        ):

            if not shipment_id:

                st.error(
                    "Enter Shipment ID"
                )

            elif not selected_units:

                st.error(
                    "Select at least one unit."
                )

            else:

                now = datetime.now().strftime(
                    "%Y-%m-%d %H:%M:%S"
                )

                for vin in selected_units:

                    bike_sheet.append_row([
                        now,
                        "Shipped",
                        vin,
                        "PASS"
                    ])

                    ship_sheet.append_row([
                        now,
                        shipment_id,
                        vin
                    ])

                st.success(
                    f"{len(selected_units)} unit(s) shipped."
                )
                st.cache_data.clear()
                st.rerun()

    st.divider()

    st.markdown("### 🧭 WIP Trace")

    serial = st.selectbox(
        "VIN",
        sorted(df["serial_number"].dropna().unique()),
        key="bike_wip_trace"
    )

    trace = (
        df[
            df["serial_number"] == serial
        ]
        .sort_values(
            "datetime",
            ascending=False
        )
    )
    row_count = len(trace)

    table_height = min(
        max((row_count + 1) * 35, 100),
        220
    )
    def color_result(val):

        color = (
            "#00ff00"
            if str(val).upper() == "PASS"
            else "#ff3333"
        )

        return f"color:{color}; font-weight:bold"
    
    st.dataframe(
        trace[
            [
                "datetime",
                "station",
                "serial_number",
                "sku_number",
                "bcb_part_number",
                "results",
                "failure_remarks"
            ]
        ].style.map(
            color_result,
            subset=["results"]
        ),
        use_container_width=True,
        hide_index=True,
        height=table_height
    )

else:

    render_dashboard(df, selected_product)

# AUTO REFRESH
st_autorefresh(interval=REFRESH_INTERVAL, key="refresh")
st.caption("Auto-refresh every 5 minutes")
