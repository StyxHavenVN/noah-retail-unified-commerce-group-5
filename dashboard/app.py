import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import os
import time

# =============================================
# CẤU HÌNH
# =============================================
KONG_URL = os.environ.get("KONG_URL", "http://kong-gateway:8000")
API_KEY  = os.environ.get("KONG_API_KEY", "noah-secret-key")

HEADERS = {
    "apikey": API_KEY,
    "Content-Type": "application/json",
}

# =============================================
# PAGE CONFIG
# =============================================
st.set_page_config(
    page_title="NOAH Retail — Unified Commerce Dashboard",
    page_icon="🛒",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# =============================================
# CUSTOM CSS — Premium Dark Theme
# =============================================
st.markdown("""
<style>
    /* --- Global --- */
    .stApp {
        background: linear-gradient(135deg, #0f0c29 0%, #1a1a2e 50%, #16213e 100%);
    }
    .block-container { padding-top: 1.5rem; }

    /* --- Metric cards --- */
    .metric-card {
        background: rgba(255,255,255,0.05);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255,255,255,0.10);
        border-radius: 16px;
        padding: 1.5rem;
        text-align: center;
        transition: transform 0.2s;
    }
    .metric-card:hover { transform: translateY(-4px); }
    .metric-value {
        font-size: 2.2rem;
        font-weight: 800;
        background: linear-gradient(90deg, #00d2ff, #3a7bd5);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .metric-label {
        color: rgba(255,255,255,0.6);
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 1px;
        margin-top: 0.3rem;
    }

    /* --- Section headers --- */
    .section-header {
        color: #e0e0e0;
        font-size: 1.1rem;
        font-weight: 700;
        margin-bottom: 0.8rem;
        padding-bottom: 0.4rem;
        border-bottom: 2px solid rgba(58,123,213,0.4);
    }

    /* --- Status badges --- */
    .badge-ok {
        background: #00c853; color: #fff;
        padding: 3px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600;
    }
    .badge-pending {
        background: #ff9100; color: #fff;
        padding: 3px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600;
    }
    .badge-fail {
        background: #ff1744; color: #fff;
        padding: 3px 10px; border-radius: 12px;
        font-size: 0.75rem; font-weight: 600;
    }

    /* --- Hide Streamlit defaults --- */
    #MainMenu, footer, header { visibility: hidden; }

    /* --- Table tweaks --- */
    .stDataFrame { border-radius: 12px; overflow: hidden; }
</style>
""", unsafe_allow_html=True)


# =============================================
# HELPER — API CALLS
# =============================================
@st.cache_data(ttl=30)
def fetch_report(page=1, page_size=20):
    """Lấy dữ liệu từ Report API qua Kong Gateway."""
    try:
        resp = requests.get(
            f"{KONG_URL}/api/report",
            headers=HEADERS,
            params={"page": page, "page_size": page_size},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        else:
            st.error(f"Report API trả về HTTP {resp.status_code}")
            return None
    except requests.exceptions.ConnectionError:
        return None
    except Exception as e:
        st.error(f"Lỗi kết nối Report API: {e}")
        return None


@st.cache_data(ttl=30)
def fetch_summary():
    """Lấy tổng quan từ Report API /api/report/summary."""
    try:
        resp = requests.get(
            f"{KONG_URL}/api/report/summary",
            headers=HEADERS,
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json().get("summary", {})
        return None
    except Exception:
        return None


@st.cache_data(ttl=30)
def fetch_orders(page=1, limit=10):
    """Lấy danh sách đơn hàng từ Order API qua Kong."""
    try:
        resp = requests.get(
            f"{KONG_URL}/api/orders",
            headers=HEADERS,
            params={"page": page, "limit": limit},
            timeout=10,
        )
        if resp.status_code == 200:
            return resp.json()
        return None
    except Exception:
        return None


def check_service_health(service_path):
    """Kiểm tra health của service qua Kong."""
    try:
        resp = requests.get(
            f"{KONG_URL}{service_path}",
            headers=HEADERS,
            timeout=5,
        )
        return resp.status_code == 200
    except Exception:
        return False


# =============================================
# HEADER
# =============================================
st.markdown("""
<div style="text-align:center; padding: 0.5rem 0 1.5rem;">
    <h1 style="color:#fff; font-size:2.2rem; font-weight:800; margin:0;">
        🛒 NOAH Retail — Unified Commerce
    </h1>
    <p style="color:rgba(255,255,255,0.5); font-size:0.9rem; margin-top:0.3rem;">
        CMU-CS 445 System Integration Practices &nbsp;|&nbsp; Nhóm 5
    </p>
</div>
""", unsafe_allow_html=True)


# =============================================
# PHẦN 1: METRIC CARDS
# =============================================
summary = fetch_summary()
report  = fetch_report(page=1, page_size=20)

col1, col2, col3, col4 = st.columns(4)

total_orders   = summary.get("total_orders", 0)   if summary else "—"
total_revenue  = summary.get("total_revenue", 0)   if summary else "—"
pending_orders = summary.get("pending_orders", 0)  if summary else "—"
total_customers = summary.get("total_customers", 0) if summary else "—"

with col1:
    val = f"{total_orders:,}" if isinstance(total_orders, (int, float)) else total_orders
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{val}</div>
        <div class="metric-label">📦 Tổng đơn hàng</div>
    </div>""", unsafe_allow_html=True)

with col2:
    if isinstance(total_revenue, (int, float)):
        val = f"{total_revenue:,.0f}₫"
    else:
        val = total_revenue
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{val}</div>
        <div class="metric-label">💰 Tổng doanh thu</div>
    </div>""", unsafe_allow_html=True)

with col3:
    val = f"{pending_orders}" if isinstance(pending_orders, (int, float)) else pending_orders
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{val}</div>
        <div class="metric-label">⏳ Đơn chờ xử lý</div>
    </div>""", unsafe_allow_html=True)

with col4:
    val = f"{total_customers}" if isinstance(total_customers, (int, float)) else total_customers
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-value">{val}</div>
        <div class="metric-label">👥 Khách hàng</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# =============================================
# PHẦN 2: BIỂU ĐỒ DOANH THU + HEALTH CHECK
# =============================================
left_col, right_col = st.columns([2, 1])

with left_col:
    st.markdown('<div class="section-header">📊 Doanh Thu Theo Khách Hàng (Data Stitching)</div>', unsafe_allow_html=True)

    if report and report.get("success"):
        df = pd.DataFrame(report["data"])
        if not df.empty and "user_id" in df.columns and "total_revenue" in df.columns:
            revenue_by_user = df.groupby("user_id")["total_revenue"].sum().reset_index()
            revenue_by_user["user_label"] = revenue_by_user["user_id"].apply(lambda x: f"User {x}")
            revenue_by_user = revenue_by_user.sort_values("total_revenue", ascending=True).tail(10)

            fig = px.bar(
                revenue_by_user,
                x="total_revenue",
                y="user_label",
                orientation="h",
                color="total_revenue",
                color_continuous_scale=["#3a7bd5", "#00d2ff"],
                labels={"total_revenue": "Doanh thu (VNĐ)", "user_label": ""},
            )
            fig.update_layout(
                plot_bgcolor="rgba(0,0,0,0)",
                paper_bgcolor="rgba(0,0,0,0)",
                font_color="#ccc",
                showlegend=False,
                coloraxis_showscale=False,
                margin=dict(l=0, r=20, t=10, b=10),
                height=350,
                xaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
                yaxis=dict(gridcolor="rgba(255,255,255,0.05)"),
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Chưa có dữ liệu doanh thu.")
    else:
        st.warning("⚠️ Không thể kết nối Report API. Hãy kiểm tra hệ thống Docker.")

with right_col:
    st.markdown('<div class="section-header">🔗 Trạng Thái Hệ Thống</div>', unsafe_allow_html=True)

    services = {
        "Order API":  "/api/orders?limit=1",
        "Report API": "/api/report?page_size=1",
    }
    for name, path in services.items():
        ok = check_service_health(path)
        badge = '<span class="badge-ok">● ONLINE</span>' if ok else '<span class="badge-fail">● OFFLINE</span>'
        st.markdown(f"""
        <div style="display:flex; justify-content:space-between; align-items:center;
                    padding:0.6rem 1rem; margin-bottom:0.5rem;
                    background:rgba(255,255,255,0.04); border-radius:10px;">
            <span style="color:#ddd; font-weight:600;">{name}</span>
            {badge}
        </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div style="display:flex; justify-content:space-between; align-items:center;
                padding:0.6rem 1rem; margin-bottom:0.5rem;
                background:rgba(255,255,255,0.04); border-radius:10px;">
        <span style="color:#ddd; font-weight:600;">Kong Gateway</span>
        <span class="badge-ok">● PORT 8000</span>
    </div>""", unsafe_allow_html=True)


# =============================================
# PHẦN 3: BẢNG ĐỐI SOÁT ĐƠN HÀNG
# =============================================
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">🔍 Bảng Đối Soát Đơn Hàng — Data Stitching (MySQL ↔ PostgreSQL)</div>', unsafe_allow_html=True)

# Pagination controls
pcol1, pcol2, pcol3 = st.columns([1, 3, 1])
with pcol1:
    page_size = st.selectbox("Số dòng / trang", [10, 20, 50, 100], index=1, key="page_size")
with pcol3:
    current_page = st.number_input("Trang", min_value=1, value=1, step=1, key="current_page")

# Fetch with pagination
report_paged = fetch_report(page=current_page, page_size=page_size)

if report_paged and report_paged.get("success") and report_paged.get("data"):
    df_table = pd.DataFrame(report_paged["data"])

    # Select & rename columns for display
    display_cols = {
        "order_id":       "Mã ĐH",
        "product_name":   "Sản Phẩm",
        "quantity":       "SL",
        "unit_price":     "Đơn Giá",
        "total_revenue":  "Tổng Tiền",
        "web_status":     "Web (MySQL)",
        "finance_status": "Tài Chính (PG)",
    }
    available = [c for c in display_cols if c in df_table.columns]
    df_show = df_table[available].rename(columns=display_cols)

    # Format currency columns
    for col in ["Đơn Giá", "Tổng Tiền"]:
        if col in df_show.columns:
            df_show[col] = df_show[col].apply(
                lambda x: f"{x:,.0f}₫" if pd.notna(x) else "—"
            )

    st.dataframe(
        df_show,
        use_container_width=True,
        hide_index=True,
        height=min(len(df_show) * 38 + 40, 600),
    )

    # Pagination info
    pagination = report_paged.get("pagination", {})
    total_count = pagination.get("total_count", 0)
    total_pages = pagination.get("total_pages", 1)
    st.caption(f"Trang {current_page}/{total_pages} — Tổng: {total_count:,} bản ghi")

elif report_paged and not report_paged.get("data"):
    st.info("📭 Không có dữ liệu trên trang này.")
else:
    st.warning("⚠️ Không thể tải dữ liệu đối soát. Hãy chạy `docker-compose up -d` trước.")


# =============================================
# PHẦN 4: TẠO ĐƠN HÀNG NHANH
# =============================================
st.markdown("<br>", unsafe_allow_html=True)
st.markdown('<div class="section-header">🛒 Tạo Đơn Hàng Mới (qua Kong Gateway)</div>', unsafe_allow_html=True)

ocol1, ocol2, ocol3, ocol4 = st.columns([1, 1, 1, 1])
with ocol1:
    new_user_id = st.number_input("User ID", min_value=1, value=1, step=1)
with ocol2:
    new_product_id = st.number_input("Product ID", min_value=1, value=101, step=1)
with ocol3:
    new_quantity = st.number_input("Số lượng", min_value=1, value=1, step=1)
with ocol4:
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🚀 Gửi Đơn Hàng", use_container_width=True):
        try:
            resp = requests.post(
                f"{KONG_URL}/api/orders",
                headers=HEADERS,
                json={
                    "user_id": new_user_id,
                    "product_id": new_product_id,
                    "quantity": new_quantity,
                },
                timeout=10,
            )
            if resp.status_code in (200, 201, 202):
                data = resp.json()
                st.success(f"✅ Đơn hàng #{data.get('order_id', '?')} đã tạo thành công! Status: {data.get('status', 'PENDING')}")
                st.cache_data.clear()
            else:
                st.error(f"❌ Lỗi: HTTP {resp.status_code} — {resp.text}")
        except Exception as e:
            st.error(f"❌ Không thể kết nối Order API: {e}")


# =============================================
# FOOTER
# =============================================
st.markdown("""
<div style="text-align:center; padding:2rem 0 1rem; color:rgba(255,255,255,0.25); font-size:0.75rem;">
    NOAH Retail — Unified Commerce System &nbsp;|&nbsp; Nhóm 5 — CMU-CS 445 NIS (2026)
</div>
""", unsafe_allow_html=True)