import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Material Tracker Intelligence", layout="wide")
st.title("📦 Material Tracker Intelligence")

conn = sqlite3.connect(":memory:")

st.header("📤 Load Tracker Data")
uploaded_file = st.file_uploader("Upload your Material Tracker Excel file", type=["xlsx"])

if uploaded_file is not None:
    df = pd.read_excel(uploaded_file, sheet_name="Material Tracker", header=2)
    df.columns = [
        "serial_no", "building", "package", "description", "uom",
        "boq_qty", "actual_qty", "approved_make", "po_number", "po_date",
        "vendor_name", "vendor_contact", "tds_approval_date_bl", "tds_approved_actual_date",
        "mfg_clearance_bl_date", "mfg_clearance_actual_date", "approval_status",
        "place_of_origin", "lead_time_days", "expected_dispatch_date",
        "expected_delivery_date", "bl_delivery_date", "need_date_at_site",
        "float_days", "delivered_qty", "remarks", "need_date_cup_recovery"
    ]
    df = df.dropna(subset=["serial_no"])
    df.to_sql("material_tracker", conn, if_exists="replace", index=False)
    st.success(f"Loaded {len(df)} rows")
else:
    st.info("👆 Upload a Material Tracker Excel file to get started")
    st.stop()

st.header("Package Overview")
df_packages = pd.read_sql("""
    SELECT package, COUNT(*) AS item_count
    FROM material_tracker
    GROUP BY package
    ORDER BY item_count DESC
""", conn)
st.dataframe(df_packages, use_container_width=True)

st.header("⚠️ At-Risk Items (Negative Float)")
df_risk = pd.read_sql("""
    SELECT package, COUNT(*) AS negative_float_count
    FROM material_tracker
    WHERE float_days < 0
    GROUP BY package
    HAVING COUNT(*) > 5
    ORDER BY negative_float_count DESC
""", conn)
st.dataframe(df_risk, use_container_width=True)

st.header("🔍 Explore by Package")
all_packages = pd.read_sql("SELECT DISTINCT package FROM material_tracker", conn)
selected = st.selectbox("Choose a package", all_packages["package"])

df_selected = pd.read_sql(
    "SELECT * FROM material_tracker WHERE package = ?",
    conn, params=(selected,)
)
st.dataframe(df_selected, use_container_width=True)
st.metric("Items in this package", len(df_selected))
st.metric("Items behind schedule", len(df_selected[df_selected["float_days"] < 0]))

st.header("📊 Item Count by Package")
st.bar_chart(df_packages.set_index("package"))

st.header("🏢 Filter by Building")
all_buildings = pd.read_sql("SELECT DISTINCT building FROM material_tracker", conn)
selected_building = st.selectbox("Choose a building", all_buildings["building"].dropna())

df_building = pd.read_sql(
    "SELECT * FROM material_tracker WHERE building = ?",
    conn, params=(selected_building,)
)
st.dataframe(df_building, use_container_width=True)

st.header("🔎 Quick Answers (no AI needed)")
question = st.text_input("Try: 'negative float', 'package count', 'HVAC', 'not approved'")

if question:
    q = question.lower()
    if "negative float" in q or "behind schedule" in q or "at risk" in q:
        result = pd.read_sql("""
            SELECT package, COUNT(*) AS count FROM material_tracker
            WHERE float_days < 0 GROUP BY package ORDER BY count DESC
        """, conn)
        st.dataframe(result, use_container_width=True)
    elif "package count" in q or "how many packages" in q:
        result = pd.read_sql("SELECT COUNT(DISTINCT package) AS total_packages FROM material_tracker", conn)
        st.dataframe(result, use_container_width=True)
    elif "not approved" in q or "pending" in q:
        result = pd.read_sql("""
            SELECT package, COUNT(*) AS pending_count FROM material_tracker
            WHERE approval_status IS NULL OR approval_status != 'Approved'
            GROUP BY package ORDER BY pending_count DESC
        """, conn)
        st.dataframe(result, use_container_width=True)
    else:
        result = pd.read_sql(
            "SELECT * FROM material_tracker WHERE package LIKE ?",
            conn, params=(f"%{question}%",)
        )
        if len(result) > 0:
            st.dataframe(result, use_container_width=True)
        else:
            st.write("No pre-built answer for that yet.")
