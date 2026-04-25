"""
NOAH Retail – Module 3: Dashboard (Streamlit)
=============================================
Giao diện hiển thị dữ liệu đối soát giữa MySQL và PostgreSQL.
Gọi qua Kong Gateway với API key authentication.
"""

import os
import requests
import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime

# ── Page config ───────────────────────────────────────────────
st.set_page_config(
    page_title="NOAH Retail – Unified Commerce Dashboard",
    page_icon="🏪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Config ────────────────────────────────────────────────────
# Match docker-compose service name and env keys by default.
KONG_URL = os.getenv("KONG_URL", "http://kong-gateway:8000")
API_KEY  = os.getenv("KONG_API_KEY", "noah-secret-key")
HEADERS  = {"apikey": API_KEY, "Content-Type": "application/json"}


# ── Helpers ───────────────────────────────────────────────────

@st.cache_data(ttl=10)   # Cache 10 giây, tự refresh
def fetch_report():
    try:
        resp = requests.get(f"{KONG_URL}/api/report", headers=HEADERS, timeout=15)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)


@st.cache_data(ttl=10)
def fetch_inventory():
    try:
        resp = requests.get(f"{KONG_URL}/inventory/api/inventory", headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)


def post_order(user_id, product_id, quantity):
    try:
        payload = {"user_id": user_id, "product_id": product_id, "quantity": quantity}
        resp = requests.post(f"{KONG_URL}/api/orders", json=payload, headers=HEADERS, timeout=10)
        resp.raise_for_status()
        return resp.json(), None
    except requests.exceptions.RequestException as e:
        return None, str(e)


# ── Sidebar ───────────────────────────────────────────────────
with st.sidebar:
    st.image("https://via.placeholder.com/200x60?text=NOAH+Retail", width=200)
    st.markdown("---")
    st.markdown("### 🔧 Cài đặt")
    auto_refresh = st.toggle("Auto-refresh (10s)", value=False)
    if auto_refresh:
        import time
        st.rerun()

    st.markdown("---")
    st.markdown("### 📦 Tạo đơn hàng Test")
    with st.form("order_form"):
        uid  = st.number_input("User ID",    min_value=1, value=1)
        pid  = st.number_input("Product ID", min_value=101, value=101)
        qty  = st.number_input("Số lượng",   min_value=1, value=1)
        submitted = st.form_submit_button("📨 Gửi đơn hàng")

    if submitted:
        result, err = post_order(uid, pid, qty)
        if result:
            st.success(f"✅ Order #{result['order_id']} đã nhận!")
        else:
            st.error(f"❌ Lỗi: {err}")

    st.markdown("---")
    st.caption(f"Last refresh: {datetime.now().strftime('%H:%M:%S')}")
    if st.button("🔄 Refresh ngay"):
        st.cache_data.clear()
        st.rerun()


# ── Main content ──────────────────────────────────────────────
st.title("🏪 NOAH Retail – Unified Commerce Dashboard")
st.caption("Góc nhìn toàn cảnh (Single View) – Data Stitching từ MySQL + PostgreSQL qua Kong Gateway")

report, err = fetch_report()

if err:
    st.error(f"❌ Không lấy được dữ liệu từ Report Service: {err}")
    st.info("💡 Kiểm tra Kong Gateway đang chạy tại port 8000")
    st.stop()

summary = report.get("summary", {})

# ── Row 1: KPI Cards ──────────────────────────────────────────
c1, c2, c3, c4 = st.columns(4)

with c1:
    st.metric(
        label="📋 Tổng đơn hàng",
        value=summary.get("total_orders", 0),
    )
with c2:
    st.metric(
        label="✅ Đã đồng bộ",
        value=summary.get("synced_orders", 0),
        delta=f"{summary.get('sync_rate', 0)}% sync rate",
    )
with c3:
    st.metric(
        label="⏳ Đang chờ",
        value=summary.get("pending_orders", 0),
    )
with c4:
    revenue = summary.get("total_revenue", 0)
    st.metric(
        label="💰 Tổng doanh thu",
        value=f"{revenue:,.0f} VND",
    )

st.markdown("---")

# ── Row 2: Charts ─────────────────────────────────────────────
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Doanh thu theo khách hàng")
    rev_data = report.get("revenue_by_user", [])
    if rev_data:
        rev_df = pd.DataFrame(rev_data)
        fig = px.bar(
            rev_df,
            x="user_id",
            y="total_revenue",
            labels={"user_id": "User ID", "total_revenue": "Doanh thu (VND)"},
            color="total_revenue",
            color_continuous_scale="Blues",
        )
        fig.update_layout(showlegend=False, height=350)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Chưa có dữ liệu doanh thu")

with col_right:
    st.subheader("🔄 Trạng thái đồng bộ")
    synced  = summary.get("synced_orders", 0)
    pending = summary.get("pending_orders", 0)
    if synced + pending > 0:
        fig2 = go.Figure(data=[go.Pie(
            labels=["SYNCED ✅", "PENDING ⏳"],
            values=[synced, pending],
            hole=0.45,
            marker_colors=["#2ecc71", "#f39c12"],
        )])
        fig2.update_layout(height=350, showlegend=True)
        st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("Chưa có đơn hàng nào")

st.markdown("---")

# ── Row 3: Orders Table ───────────────────────────────────────
st.subheader("📋 Bảng đối soát đơn hàng")
st.caption("🔵 Màu xanh = đã khớp giữa MySQL và PostgreSQL | 🔴 Màu đỏ = chưa đồng bộ Finance")

orders = report.get("orders", [])
if orders:
    df = pd.DataFrame(orders)

    # Highlight rows chưa sync
    def highlight_status(row):
        if row.get("status") == "SYNCED":
            return ["background-color: #d5f5e3"] * len(row)
        elif row.get("status") == "PENDING":
            return ["background-color: #fdebd0"] * len(row)
        return [""] * len(row)

    display_cols = [c for c in
        ["order_id","user_id","product_name","quantity","total_price","status","payment_status","created_at"]
        if c in df.columns]

    st.dataframe(
        df[display_cols].style.apply(highlight_status, axis=1),
        use_container_width=True,
        height=350,
    )
else:
    st.info("Chưa có đơn hàng. Hãy tạo đơn thử qua sidebar!")

# ── Row 4: Inventory ──────────────────────────────────────────
st.markdown("---")
st.subheader("📦 Tồn kho hiện tại (đồng bộ từ Legacy Adapter)")

inventory = report.get("inventory", [])
if inventory:
    inv_df = pd.DataFrame(inventory)
    fig3 = px.bar(
        inv_df,
        x="name",
        y="quantity",
        color="quantity",
        color_continuous_scale=["red", "yellow", "green"],
        labels={"name": "Sản phẩm", "quantity": "Số lượng tồn kho"},
    )
    fig3.update_layout(height=300, xaxis_tickangle=-30)
    st.plotly_chart(fig3, use_container_width=True)

# ── Row 5: Unsynced alert ─────────────────────────────────────
unsynced = report.get("unsynced_orders", [])
if unsynced:
    st.markdown("---")
    st.warning(f"⚠️ **{len(unsynced)} đơn hàng chưa đồng bộ sang Finance (PostgreSQL)**")
    st.dataframe(pd.DataFrame(unsynced), use_container_width=True)
