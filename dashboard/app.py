"""
NOAH Retail – Module 6: Dashboard
"""

import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px

# ── Cấu hình trang ───────────────────────────────────────────
st.set_page_config(
    page_title="NOAH Retail – Dashboard",
    page_icon="🏪",
    layout="wide",
)

# ── Config ────────────────────────────────────────────────────
REPORT_API_URL = os.getenv("REPORT_API_URL", "http://localhost:8000")
USE_MOCK       = os.getenv("USE_MOCK", "false").lower() == "true"

# ── Mock data ─────────────────────────────────────────────────
MOCK_DATA = {
    "success": True,
    "total_records": 6,
    "data": [
        {"order_id": 1, "product_name": "iPhone 15 Pro",      "status": "COMPLETED", "quantity": 2, "unit_price": 25990000, "total_revenue": 51980000},
        {"order_id": 2, "product_name": "Samsung Galaxy S24", "status": "COMPLETED", "quantity": 1, "unit_price": 21990000, "total_revenue": 21990000},
        {"order_id": 3, "product_name": "MacBook Air M3",     "status": "COMPLETED", "quantity": 1, "unit_price": 32990000, "total_revenue": 32990000},
        {"order_id": 4, "product_name": "Sony WH-1000XM5",   "status": "COMPLETED", "quantity": 3, "unit_price":  8490000, "total_revenue": 25470000},
        {"order_id": 5, "product_name": "iPad Pro M2",        "status": "COMPLETED", "quantity": 2, "unit_price": 24990000, "total_revenue": 49980000},
        {"order_id": 6, "product_name": "Dell XPS 15",        "status": "COMPLETED", "quantity": 1, "unit_price": 28990000, "total_revenue": 28990000},
    ]
}

# ── Fetch data ────────────────────────────────────────────────
@st.cache_data(ttl=15)
def fetch_report():
    if USE_MOCK:
        return MOCK_DATA, None
    try:
        headers = {"apikey": "noah-secret-key"}  # ← đúng key trong kong.yml
        resp = requests.get(f"{REPORT_API_URL}/api/report", headers=headers, timeout=10)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.ConnectionError:
        return None, "Không kết nối được API. Kiểm tra Docker đang chạy chưa."
    except requests.exceptions.Timeout:
        return None, "API timeout (>10s)."
    except Exception as e:
        return None, str(e)

# ─────────────────────────────────────────────────────────────
#  UI
# ─────────────────────────────────────────────────────────────
st.title("🏪 NOAH Retail – Unified Commerce Dashboard")
st.caption("Đồ án môn học: CMU-CS 445 | Nhóm 5")

with st.sidebar:
    st.markdown("### ⚙️ Cài đặt")
    if st.button("🔄 Refresh dữ liệu"):
        st.cache_data.clear()
        st.rerun()
    st.markdown("---")
    st.markdown(f"**API URL:** `{REPORT_API_URL}`")
    st.markdown("🟡 Mock mode" if USE_MOCK else "🟢 Live mode")

st.markdown("---")

result, error = fetch_report()

if error:
    st.error(f"❌ Lỗi kết nối: {error}")
    st.info("💡 Tip: Chạy `docker compose up` để khởi động backend.")
    st.stop()

if not result.get("success"):
    st.error("API trả về lỗi. Kiểm tra log của report_api container.")
    st.stop()

df = pd.DataFrame(result["data"])

if df.empty:
    st.warning("⚠️ Chưa có đơn hàng nào trong hệ thống.")
    st.stop()

# ── KPI Cards ─────────────────────────────────────────────────
st.subheader("📊 Tổng quan")
c1, c2, c3, c4 = st.columns(4)

total_orders  = result["total_records"]
total_revenue = df["total_revenue"].sum()
avg_order_val = df["total_revenue"].mean()
top_product   = df.groupby("product_name")["total_revenue"].sum().idxmax()

c1.metric("📋 Tổng đơn hàng",     total_orders)
c2.metric("💰 Tổng doanh thu",    f"{total_revenue:,.0f} VND")
c3.metric("📦 Giá trị TB/đơn",    f"{avg_order_val:,.0f} VND")
c4.metric("🏆 Sản phẩm bán chạy", top_product)

st.markdown("---")

# ── Charts ────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("💰 Doanh thu theo sản phẩm")
    rev_by_product = (
        df.groupby("product_name")["total_revenue"]
        .sum().reset_index()
        .sort_values("total_revenue", ascending=True)
    )
    fig1 = px.bar(
        rev_by_product, x="total_revenue", y="product_name",
        orientation="h",
        labels={"total_revenue": "Doanh thu (VND)", "product_name": "Sản phẩm"},
        color="total_revenue", color_continuous_scale="Blues",
    )
    fig1.update_layout(showlegend=False, height=350, coloraxis_showscale=False)
    st.plotly_chart(fig1, use_container_width=True)

with col2:
    st.subheader("🛒 Số lượng bán theo sản phẩm")
    qty_by_product = (
        df.groupby("product_name")["quantity"]
        .sum().reset_index()
        .sort_values("quantity", ascending=False)
    )
    fig2 = px.pie(
        qty_by_product, names="product_name", values="quantity",
        hole=0.4, color_discrete_sequence=px.colors.sequential.Blues_r,
    )
    fig2.update_layout(height=350)
    st.plotly_chart(fig2, use_container_width=True)

st.markdown("---")

# ── Chi tiết đơn hàng ─────────────────────────────────────────
st.subheader("📋 Chi tiết đơn hàng (Data Stitching: MySQL ✚ PostgreSQL)")

display_df = df[["order_id", "product_name", "status", "quantity", "unit_price", "total_revenue"]].copy()
display_df["unit_price"]    = display_df["unit_price"].apply(lambda x: f"{x:,.0f} VND")
display_df["total_revenue"] = display_df["total_revenue"].apply(lambda x: f"{x:,.0f} VND")
display_df = display_df.rename(columns={
    "order_id":      "Mã đơn",
    "product_name":  "Sản phẩm",
    "status":        "Trạng thái",
    "quantity":      "Số lượng",
    "unit_price":    "Đơn giá",
    "total_revenue": "Doanh thu",
})
st.dataframe(display_df, use_container_width=True, height=300)

st.markdown("---")
st.subheader("📈 Thống kê nhanh")
cc1, cc2 = st.columns(2)

with cc1:
    st.markdown("**Top 3 đơn hàng giá trị cao nhất**")
    top3 = df.nlargest(3, "total_revenue")[["order_id", "product_name", "total_revenue"]].copy()
    top3["total_revenue"] = top3["total_revenue"].apply(lambda x: f"{x:,.0f} VND")
    st.dataframe(top3, use_container_width=True, hide_index=True)

with cc2:
    st.markdown("**Tổng doanh thu theo sản phẩm**")
    rev_summary = df.groupby("product_name")["total_revenue"].sum().reset_index()
    rev_summary["total_revenue"] = rev_summary["total_revenue"].apply(lambda x: f"{x:,.0f} VND")
    st.dataframe(rev_summary, use_container_width=True, hide_index=True)