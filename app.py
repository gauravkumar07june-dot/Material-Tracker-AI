import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Material Tracker Intelligence", page_icon="📦", layout="wide")

st.markdown("""
<style>
.kpi-card {
    background: linear-gradient(135deg, #1B2A4A 0%, #2E5EAA 100%);
    padding: 20px; border-radius: 12px; color: white; text-align: center;
}
.kpi-value { font-size: 32px; font-weight: 700; margin: 0; }
.kpi-label { font-size: 13px; opacity: 0.85; margin: 0; }
.risk-card {
    background: linear-gradient(135deg, #7A1F1F 0%, #B03A2E 100%);
    padding: 20px; border-radius: 12px; color: white; text-align: center;
}
.good-card {
    background: linear-gradient(135deg, #1F5C2E 0%, #2E8B4E 100%);
    padding: 20px; border-radius: 12px; color: white; text-align: center;
}
</style>
""", unsafe_allow_html=True)

st.title("📦 Material Tracker Intelligence")
st.caption("Live dashboard — upload your latest tracker to refresh")

conn = sqlite3.connect(":memory:")

uploaded_file = st.file_uploader("📤 Upload Material Tracker Excel file", type=["xlsx"])

if uploaded_file is None:
    st.info("👆 Upload a file to get started")
    st.stop()

df = pd.read_excel(uploaded_file, sheet_name="Material Tracker", header=0)
df = df.loc[:, df.columns.notna()]

df.columns = [
    "serial_no", "building", "package", "power_turn_on_support", "description", "uom",
    "boq_qty", "actual_qty", "delivered_qty", "delivery_completed_pct", "total_partial",
    "approved_make", "po_number", "po_date", "vendor_name", "vendor_contact",
    "tds_approval_date_bl", "tds_approved_actual_date", "mfg_clearance_bl_date",
    "mfg_clearance_actual_date", "approval_status", "sea_air", "place_of_origin",
    "lead_time_days", "expected_dispatch_date", "expected_delivery_date",
    "revised_expected_delivery_date", "bl_delivery_date", "need_date_at_site",
    "float_days", "remarks", "on_site", "mep_store_warehouse", "vendor_container_facility"
]
df = df.dropna(subset=["serial_no"])
df.to_sql("material_tracker", conn, if_exists="replace", index=False)

total_items = len(df)
total_packages = df["package"].nunique()
at_risk = len(df[df["float_days"] < 0])
approved_pct = round((df["approval_status"] == "Approved").sum() / total_items * 100, 1)

c1, c2, c3, c4 = st.columns(4)
with c1:
    st.markdown(f'<div class="kpi-card"><p class="kpi-value">{total_items}</p><p class="kpi-label">Total Items</p></div>', unsafe_allow_html=True)
with c2:
    st.markdown(f'<div class="kpi-card"><p class="kpi-value">{total_packages}</p><p class="kpi-label">Packages</p></div>', unsafe_allow_html=True)
with c3:
    st.markdown(f'<div class="risk-card"><p class="kpi-value">{at_risk}</p><p class="kpi-label">At-Risk Items</p></div>', unsafe_allow_html=True)
with c4:
    st.markdown(f'<div class="kpi-card"><p class="kpi-value">{approved_pct}%</p><p class="kpi-label">Approved</p></div>', unsafe_allow_html=True)

po_issued = df["po_number"].notna().sum()
avg_delivery_pct = round(df["delivery_completed_pct"].mean() * 100, 1) if df["delivery_completed_pct"].max() <= 1 else round(df["delivery_completed_pct"].mean(), 1)
on_site_count = int(df["on_site"].sum()) if df["on_site"].dtype == bool else len(df[df["on_site"] == True])
avg_lead_time = round(df["lead_time_days"].mean(), 1)

st.write("")
d1, d2, d3, d4 = st.columns(4)
with d1:
    st.markdown(f'<div class="good-card"><p class="kpi-value">{po_issued}</p><p class="kpi-label">POs Issued</p></div>', unsafe_allow_html=True)
with d2:
    st.markdown(f'<div class="good-card"><p class="kpi-value">{avg_delivery_pct}%</p><p class="kpi-label">Avg Delivery Completed</p></div>', unsafe_allow_html=True)
with d3:
    st.markdown(f'<div class="good-card"><p class="kpi-value">{on_site_count}</p><p class="kpi-label">Items On Site</p></div>', unsafe_allow_html=True)
with d4:
    st.markdown(f'<div class="good-card"><p class="kpi-value">{avg_lead_time}</p><p class="kpi-label">Avg Lead Time (days)</p></div>', unsafe_allow_html=True)

st.write("")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["📊 Overview", "⚠️ At-Risk", "🔍 By Package", "🏢 By Building", "🔎 Ask"])

with tab1:
    df_packages = pd.read_sql("""
        SELECT package, COUNT(*) AS item_count
        FROM material_tracker GROUP BY package ORDER BY item_count DESC
    """, conn)
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Items by Package")
        st.bar_chart(df_packages.set_index("package"))
    with right:
        st.subheader("Ranking")
        st.dataframe(df_packages, use_container_width=True, hide_index=True)

with tab2:
    df_risk = pd.read_sql("""
        SELECT package, COUNT(*) AS negative_float_count
        FROM material_tracker WHERE float_days < 0
        GROUP BY package ORDER BY negative_float_count DESC
    """, conn)
    st.subheader("Packages With At-Risk Items")
    st.bar_chart(df_risk.set_index("package"))
    st.dataframe(df_risk, use_container_width=True, hide_index=True)

with tab3:
    all_packages = pd.read_sql("SELECT DISTINCT package FROM material_tracker", conn)
    selected = st.selectbox("Choose a package", all_packages["package"])
    df_selected = pd.read_sql("SELECT * FROM material_tracker WHERE package = ?", conn, params=(selected,))
    m1, m2 = st.columns(2)
    m1.metric("Items in package", len(df_selected))
    m2.metric("Behind schedule", len(df_selected[df_selected["float_days"] < 0]))
    st.dataframe(df_selected, use_container_width=True)

with tab4:
    all_buildings = pd.read_sql("SELECT DISTINCT building FROM material_tracker", conn)
    selected_building = st.selectbox("Choose a building", all_buildings["building"].dropna())
    df_building = pd.read_sql("SELECT * FROM material_tracker WHERE building = ?", conn, params=(selected_building,))
    st.dataframe(df_building, use_container_width=True)

with tab5:
    st.caption("Try: 'negative float', 'delivery completed', 'PO issued', 'pending approval', "
               "'vendor Rittal', 'building CUP', 'average lead time', 'on site', 'sea vs air'")
    question = st.text_input("Ask a question about your tracker")

    if question:
        q = question.lower()
        result = None

        if "negative float" in q or "behind schedule" in q or "at risk" in q:
            result = pd.read_sql("""
                SELECT package, COUNT(*) AS count FROM material_tracker
                WHERE float_days < 0 GROUP BY package ORDER BY count DESC
            """, conn)

        elif "delivery" in q and ("complet" in q or "%" in q or "percent" in q):
            result = pd.read_sql("""
                SELECT package, ROUND(AVG(delivery_completed_pct) * 100, 1) AS avg_delivery_pct,
                       SUM(delivered_qty) AS total_delivered, SUM(boq_qty) AS total_boq_qty
                FROM material_tracker GROUP BY package ORDER BY avg_delivery_pct ASC
            """, conn)

        elif "po issued" in q or "how many po" in q or "purchase order" in q:
            result = pd.read_sql("""
                SELECT package, COUNT(po_number) AS po_issued_count,
                       COUNT(*) - COUNT(po_number) AS po_pending_count
                FROM material_tracker GROUP BY package ORDER BY po_pending_count DESC
            """, conn)

        elif "package count" in q or "how many packages" in q:
            result = pd.read_sql("SELECT COUNT(DISTINCT package) AS total_packages FROM material_tracker", conn)

        elif "not approved" in q or "pending approval" in q or ("pending" in q and "po" not in q):
            result = pd.read_sql("""
                SELECT package, COUNT(*) AS pending_count FROM material_tracker
                WHERE approval_status IS NULL OR approval_status != 'Approved'
                GROUP BY package ORDER BY pending_count DESC
            """, conn)

        elif "vendor" in q:
            words = q.replace("vendor", "").strip()
            result = pd.read_sql(
                "SELECT * FROM material_tracker WHERE vendor_name LIKE ?",
                conn, params=(f"%{words}%",)
            )

        elif "building" in q:
            words = q.replace("building", "").strip()
            result = pd.read_sql(
                "SELECT * FROM material_tracker WHERE building LIKE ?",
                conn, params=(f"%{words}%",)
            )

        elif "average lead time" in q or "avg lead time" in q:
            result = pd.read_sql("""
                SELECT package, ROUND(AVG(lead_time_days), 1) AS avg_lead_time
                FROM material_tracker GROUP BY package ORDER BY avg_lead_time DESC
            """, conn)

        elif "on site" in q:
            result = pd.read_sql("""
                SELECT package, COUNT(*) AS on_site_count
                FROM material_tracker WHERE on_site = 1
                GROUP BY package ORDER BY on_site_count DESC
            """, conn)

        elif "sea" in q or "air" in q:
            result = pd.read_sql("""
                SELECT sea_air, COUNT(*) AS count
                FROM material_tracker GROUP BY sea_air
            """, conn)

        elif "total qty" in q or "boq qty" in q or "quantity" in q:
            result = pd.read_sql("""
                SELECT package, SUM(boq_qty) AS total_boq_qty, SUM(actual_qty) AS total_actual_qty
                FROM material_tracker GROUP BY package ORDER BY total_boq_qty DESC
            """, conn)

        elif "approved" in q:
            result = pd.read_sql("""
                SELECT approval_status, COUNT(*) AS count
                FROM material_tracker GROUP BY approval_status
            """, conn)

        else:
            result = pd.read_sql("""
                SELECT * FROM material_tracker
                WHERE package LIKE ? OR vendor_name LIKE ? OR description LIKE ?
            """, conn, params=(f"%{question}%", f"%{question}%", f"%{question}%"))

        if result is not None:
            if len(result) > 0:
                st.dataframe(result, use_container_width=True, hide_index=True)
            else:
                st.write("No matching data found for that question.")
