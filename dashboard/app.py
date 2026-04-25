import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import numpy as np
import math
import requests
import os


# ──────────────────────────────────────────────────────────────
# PAGE CONFIG
# ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="NOAH · Reconciliation Dashboard",
    page_icon="🔬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ──────────────────────────────────────────────────────────────
# PREMIUM CSS INJECTION
# ──────────────────────────────────────────────────────────────
st.markdown("""
<style>
/* ── Google Font ── */
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');
* { font-family: 'Inter', sans-serif !important; }

/* ── Root palette ── */
:root {
    --bg-primary: #0f1117;
    --bg-card: #1a1d29;
    --accent: #6c63ff;
    --accent-glow: rgba(108,99,255,.25);
    --green: #00c896;
    --red: #ff4d6a;
    --yellow: #ffb84d;
    --text-primary: #e8eaed;
    --text-muted: #8b8fa3;
    --border: rgba(255,255,255,.06);
}

/* ── Hide Streamlit boilerplate ── */
#MainMenu, footer, header {visibility:hidden;}
.stDeployButton {display:none;}

/* ── Sidebar ── */
section[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #12141f 0%, #1a1d29 100%);
    border-right: 1px solid var(--border);
}
section[data-testid="stSidebar"] .stMarkdown h1,
section[data-testid="stSidebar"] .stMarkdown h2,
section[data-testid="stSidebar"] .stMarkdown h3 { color: var(--accent); }

/* ── KPI Cards ── */
.kpi-grid { display:grid; grid-template-columns:repeat(4,1fr); gap:16px; margin-bottom:24px; }
.kpi-card {
    background: linear-gradient(135deg, #1e2235 0%, #1a1d29 100%);
    border: 1px solid var(--border);
    border-radius: 16px;
    padding: 24px;
    position: relative;
    overflow: hidden;
    transition: transform .2s, box-shadow .2s;
}
.kpi-card:hover { transform:translateY(-3px); box-shadow:0 8px 30px rgba(0,0,0,.3); }
.kpi-card::before {
    content:''; position:absolute; top:0; left:0; right:0; height:3px;
    background: linear-gradient(90deg, var(--accent), var(--green));
}
.kpi-card.warn::before { background: linear-gradient(90deg, var(--yellow), var(--red)); }
.kpi-icon { font-size:28px; margin-bottom:8px; }
.kpi-value { font-size:32px; font-weight:800; color:#fff; line-height:1.1; }
.kpi-label { font-size:13px; color:var(--text-muted); margin-top:6px; font-weight:500; }
.kpi-badge {
    display:inline-block; padding:3px 10px; border-radius:20px;
    font-size:11px; font-weight:700; margin-top:8px;
}
.badge-ok  { background:rgba(0,200,150,.15); color:var(--green); }
.badge-err { background:rgba(255,77,106,.15); color:var(--red); }

/* ── Section headers ── */
.section-hdr {
    font-size:20px; font-weight:700; color:#fff;
    margin:32px 0 16px; padding-bottom:8px;
    border-bottom:2px solid var(--accent);
    display:flex; align-items:center; gap:10px;
}

/* ── Reconciliation proof card ── */
.proof-box {
    background: linear-gradient(135deg,#161926,#1e2235);
    border:1px solid var(--border); border-radius:14px;
    padding:20px 24px; margin:8px 0 20px;
}
.proof-title { font-size:15px; font-weight:700; color:var(--accent); margin-bottom:10px; }
.proof-row { display:flex; justify-content:space-between; padding:6px 0; border-bottom:1px solid var(--border); font-size:13px; color:var(--text-primary);}
.proof-row:last-child {border:none; font-weight:700; font-size:15px; color:var(--green);}

/* ── Pagination bar ── */
.page-bar {
    display:flex; align-items:center; justify-content:center;
    gap:8px; padding:12px 0; margin:8px 0;
}
.page-info {
    background:var(--bg-card); border:1px solid var(--border);
    border-radius:10px; padding:8px 20px; color:var(--text-primary);
    font-size:13px; font-weight:600;
}

/* ── Status badges in table ── */
.st-match  { color:var(--green); font-weight:700; }
.st-differ { color:var(--red);   font-weight:700; }

/* ── Responsive ── */
@media(max-width:768px){ .kpi-grid{grid-template-columns:repeat(2,1fr);} }
</style>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# DATA LOADING (API → fallback mock)
# ──────────────────────────────────────────────────────────────
REPORT_API_URL = os.getenv("REPORT_API_URL", "http://localhost:8000/report")
USE_MOCK = os.getenv("USE_MOCK", "true").lower() == "true"
API_KEY = os.getenv("API_KEY", "noah-secret-key")

@st.cache_data(ttl=120)
def fetch_report_api():
    """Fetch stitched data from Report API (through Kong)."""
    try:
        headers = {"apikey": API_KEY}
        resp = requests.get(f"{REPORT_API_URL}/api/report", headers=headers, timeout=8)
        if resp.status_code == 200:
            body = resp.json()
            if body.get("success") and body.get("data"):
                return pd.DataFrame(body["data"]), "live"
    except Exception:
        pass
    return None, "error"

@st.cache_data
def generate_mock_data():
    """Generate realistic mock data that mirrors the real DB schema."""
    np.random.seed(42)
    n_orders = 800

    product_ids = list(range(100, 300))
    product_names = {pid: f"Product_{pid}" for pid in product_ids}
    product_prices = {pid: np.random.randint(15, 500) * 1000 for pid in product_ids}

    order_ids = list(range(1, n_orders + 1))
    o_product_id = np.random.choice(product_ids, n_orders)
    o_quantity = np.random.randint(1, 6, n_orders)
    o_status = np.random.choice(["Success", "PENDING", "FAILED"], n_orders, p=[0.72, 0.18, 0.10])
    o_dates = pd.date_range("2026-01-04", periods=n_orders, freq="50min")

    df_orders = pd.DataFrame({
        "order_id": order_ids,
        "product_id": o_product_id,
        "product_name": [product_names[pid] for pid in o_product_id],
        "quantity_order": o_quantity,
        "unit_price_order": [product_prices[pid] for pid in o_product_id],
        "status": o_status,
        "created_at": o_dates,
    })
    df_orders["total_price_order"] = df_orders["quantity_order"] * df_orders["unit_price_order"]

    # Transactions in PostgreSQL — only for Success orders
    df_success = df_orders[df_orders["status"] == "Success"].copy()
    df_tx = df_success[["order_id"]].copy()
    df_tx["quantity_tx"] = df_success["quantity_order"].values.copy()
    df_tx["unit_price_tx"] = df_success["unit_price_order"].values.copy()

    # Inject ~12% mismatches to prove reconciliation
    n_err = int(len(df_tx) * 0.12)
    err_idx = np.random.choice(df_tx.index, n_err, replace=False)
    df_tx.loc[err_idx[:n_err//2], "quantity_tx"] += np.random.randint(1, 4, n_err//2)
    df_tx.loc[err_idx[n_err//2:], "unit_price_tx"] += np.random.randint(-50, 80, n_err - n_err//2) * 1000

    df_tx["total_revenue_tx"] = df_tx["quantity_tx"] * df_tx["unit_price_tx"]

    # Merge = Data Stitching
    merged = pd.merge(df_success, df_tx, on="order_id", how="inner")
    merged["total_revenue_order"] = merged["total_price_order"]
    merged["total_revenue_tx"] = merged["total_revenue_tx"]
    merged["delta_qty"] = merged["quantity_tx"] - merged["quantity_order"]
    merged["delta_price"] = merged["unit_price_tx"] - merged["unit_price_order"]
    merged["delta_revenue"] = merged["total_revenue_tx"] - merged["total_revenue_order"]
    merged["match_status"] = np.where(
        (merged["delta_qty"] == 0) & (merged["delta_price"] == 0),
        "✅ Khớp", "❌ Lệch"
    )
    return merged, df_orders

def load_data():
    if not USE_MOCK:
        api_df, status = fetch_report_api()
        if api_df is not None and not api_df.empty:
            return api_df, status, None
    merged, df_orders = generate_mock_data()
    return merged, "mock", df_orders

df, data_source, df_all_orders = load_data()

# ──────────────────────────────────────────────────────────────
# SIDEBAR
# ──────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🔬 NOAH Dashboard")
    st.markdown("---")
    st.markdown("**Nguồn dữ liệu:**")
    if data_source == "live":
        st.success("🟢 Report API (Live)")
    else:
        st.info("🔵 Mock Data (Demo)")

    st.markdown("---")
    st.markdown("### 🎛️ Bộ lọc")
    filter_status = st.selectbox("Trạng thái đối soát", ["Tất cả", "✅ Khớp", "❌ Lệch"])
    page_size = st.select_slider("Số dòng / trang", options=[10, 20, 50, 100], value=20)

    st.markdown("---")
    st.markdown("### 📋 Kiến trúc hệ thống")
    st.markdown("""
    ```
    MySQL ──┐
            ├─► Report API ─► Dashboard
    Postgres┘   (Stitching)
    ```
    """)
    st.markdown("---")
    st.caption("Noah Unified Commerce · Group 5")

# ──────────────────────────────────────────────────────────────
# HEADER
# ──────────────────────────────────────────────────────────────
st.markdown("""
<div style="text-align:center;padding:10px 0 6px;">
    <h1 style="font-size:36px;font-weight:800;
    background:linear-gradient(135deg,#6c63ff,#00c896);
    -webkit-background-clip:text;-webkit-text-fill-color:transparent;
    margin:0;">📊 Dashboard Đối Soát Dữ Liệu</h1>
    <p style="color:#8b8fa3;font-size:14px;margin-top:4px;">
    Reconciliation &amp; Data Stitching · MySQL ↔ PostgreSQL</p>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# KPI CARDS
# ──────────────────────────────────────────────────────────────
total = len(df)
khop = len(df[df["match_status"] == "✅ Khớp"])
lech = total - khop
pct = (khop / total * 100) if total else 0
total_rev = df["total_revenue_order"].sum() if "total_revenue_order" in df.columns else 0

def fmt_vnd(v):
    if v >= 1_000_000_000:
        return f"{v/1_000_000_000:.1f} tỷ"
    if v >= 1_000_000:
        return f"{v/1_000_000:.1f} tr"
    return f"{v:,.0f}"

st.markdown(f"""
<div class="kpi-grid">
    <div class="kpi-card">
        <div class="kpi-icon">📦</div>
        <div class="kpi-value">{total:,}</div>
        <div class="kpi-label">Tổng bản ghi đối soát</div>
    </div>
    <div class="kpi-card">
        <div class="kpi-icon">✅</div>
        <div class="kpi-value">{khop:,}</div>
        <div class="kpi-label">Khớp lệnh hoàn toàn</div>
        <span class="kpi-badge badge-ok">{pct:.1f}%</span>
    </div>
    <div class="kpi-card warn">
        <div class="kpi-icon">⚠️</div>
        <div class="kpi-value">{lech:,}</div>
        <div class="kpi-label">Lệch dữ liệu</div>
        <span class="kpi-badge badge-err">{100-pct:.1f}%</span>
    </div>
    <div class="kpi-card">
        <div class="kpi-icon">💰</div>
        <div class="kpi-value">{fmt_vnd(total_rev)}</div>
        <div class="kpi-label">Tổng doanh thu (Orders)</div>
    </div>
</div>
""", unsafe_allow_html=True)

# ──────────────────────────────────────────────────────────────
# CHARTS
# ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">📈 Biểu đồ phân tích</div>', unsafe_allow_html=True)

c1, c2 = st.columns(2)

with c1:
    fig_donut = go.Figure(go.Pie(
        labels=["Khớp lệnh", "Lệch dữ liệu"], values=[khop, lech],
        hole=.55, marker=dict(colors=["#00c896", "#ff4d6a"]),
        textinfo="label+percent", textfont=dict(size=13),
    ))
    fig_donut.update_layout(
        title=dict(text="Tỷ lệ Khớp / Lệch", font=dict(size=16, color="#fff")),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e8eaed"), showlegend=False,
        margin=dict(t=50, b=20, l=20, r=20), height=340,
        annotations=[dict(text=f"<b>{pct:.0f}%</b>", x=.5, y=.5,
                          font_size=28, font_color="#00c896", showarrow=False)]
    )
    st.plotly_chart(fig_donut, width='stretch')

with c2:
    df_lech = df[df["match_status"] == "❌ Lệch"].copy()
    df_lech["abs_delta"] = df_lech["delta_revenue"].abs()
    top10 = df_lech.nlargest(10, "abs_delta")
    fig_bar = go.Figure(go.Bar(
        x=top10["order_id"].astype(str), y=top10["delta_revenue"],
        marker=dict(color=top10["delta_revenue"],
                    colorscale=[[0,"#ff4d6a"],[0.5,"#ffb84d"],[1,"#6c63ff"]]),
        text=[fmt_vnd(abs(v)) for v in top10["delta_revenue"]],
        textposition="outside", textfont=dict(size=11),
    ))
    fig_bar.update_layout(
        title=dict(text="Top 10 đơn lệch doanh thu lớn nhất", font=dict(size=16, color="#fff")),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#e8eaed"), height=340,
        margin=dict(t=50, b=40, l=60, r=20),
        xaxis=dict(title="Order ID", gridcolor="rgba(255,255,255,.05)"),
        yaxis=dict(title="Chênh lệch (VNĐ)", gridcolor="rgba(255,255,255,.05)"),
    )
    st.plotly_chart(fig_bar, width='stretch')

# Row 2 charts
c3, c4 = st.columns(2)
with c3:
    if "product_name" in df.columns:
        rev_by_prod = df.groupby("product_name")["total_revenue_order"].sum().nlargest(8).reset_index()
        fig_h = go.Figure(go.Bar(
            y=rev_by_prod["product_name"], x=rev_by_prod["total_revenue_order"],
            orientation="h",
            marker=dict(color=rev_by_prod["total_revenue_order"],
                        colorscale=[[0,"#6c63ff"],[1,"#00c896"]]),
            text=[fmt_vnd(v) for v in rev_by_prod["total_revenue_order"]],
            textposition="inside",
        ))
        fig_h.update_layout(
            title=dict(text="Top 8 sản phẩm theo doanh thu", font=dict(size=16, color="#fff")),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e8eaed"), height=340,
            margin=dict(t=50, b=20, l=100, r=20),
            xaxis=dict(gridcolor="rgba(255,255,255,.05)"),
            yaxis=dict(autorange="reversed"),
        )
        st.plotly_chart(fig_h, width='stretch')

with c4:
    if "created_at" in df.columns:
        df_time = df.copy()
        df_time["date"] = pd.to_datetime(df_time["created_at"]).dt.date
        daily = df_time.groupby("date").agg(
            orders=("order_id", "count"),
            revenue=("total_revenue_order", "sum")
        ).reset_index()
        fig_line = go.Figure()
        fig_line.add_trace(go.Scatter(
            x=daily["date"], y=daily["revenue"], mode="lines+markers",
            name="Doanh thu", line=dict(color="#6c63ff", width=2),
            marker=dict(size=5), fill="tozeroy",
            fillcolor="rgba(108,99,255,.1)"
        ))
        fig_line.update_layout(
            title=dict(text="Doanh thu theo ngày", font=dict(size=16, color="#fff")),
            paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#e8eaed"), height=340,
            margin=dict(t=50, b=40, l=60, r=20),
            xaxis=dict(gridcolor="rgba(255,255,255,.05)"),
            yaxis=dict(gridcolor="rgba(255,255,255,.05)"),
        )
        st.plotly_chart(fig_line, width='stretch')

# ──────────────────────────────────────────────────────────────
# DATA RECONCILIATION PROOF
# ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">🔍 Chứng minh khớp lệnh dữ liệu</div>', unsafe_allow_html=True)

p1, p2 = st.columns(2)

with p1:
    sum_rev_order = df["total_revenue_order"].sum()
    sum_rev_tx = df["total_revenue_tx"].sum()
    delta_total = sum_rev_tx - sum_rev_order
    st.markdown(f"""
    <div class="proof-box">
        <div class="proof-title">💡 So sánh tổng doanh thu hai hệ thống</div>
        <div class="proof-row"><span>Tổng doanh thu MySQL (Orders)</span><span>{sum_rev_order:,.0f} VNĐ</span></div>
        <div class="proof-row"><span>Tổng doanh thu PostgreSQL (Transactions)</span><span>{sum_rev_tx:,.0f} VNĐ</span></div>
        <div class="proof-row"><span>Chênh lệch tổng</span><span>{delta_total:+,.0f} VNĐ</span></div>
        <div class="proof-row"><span>🎯 Tỷ lệ khớp lệnh toàn hệ thống</span><span>{pct:.1f}%</span></div>
    </div>
    """, unsafe_allow_html=True)

with p2:
    qty_match = len(df[df["delta_qty"] == 0])
    price_match = len(df[df["delta_price"] == 0])
    full_match = khop
    st.markdown(f"""
    <div class="proof-box">
        <div class="proof-title">📊 Chi tiết từng tiêu chí đối soát</div>
        <div class="proof-row"><span>Khớp SỐ LƯỢNG (qty_order = qty_tx)</span><span>{qty_match} / {total}</span></div>
        <div class="proof-row"><span>Khớp ĐƠN GIÁ (price_order = price_tx)</span><span>{price_match} / {total}</span></div>
        <div class="proof-row"><span>Khớp TOÀN BỘ (cả qty + price)</span><span>{full_match} / {total}</span></div>
        <div class="proof-row"><span>🎯 Kết luận: Dữ liệu khớp lệnh</span><span>{pct:.1f}% chính xác</span></div>
    </div>
    """, unsafe_allow_html=True)

# Sample proof: show 3 matching rows
st.markdown("**Ví dụ minh chứng: 3 bản ghi KHỚP hoàn toàn**")
df_proof = df[df["match_status"] == "✅ Khớp"].head(3)
cols_proof = ["order_id", "product_name", "quantity_order", "quantity_tx",
              "unit_price_order", "unit_price_tx", "total_revenue_order",
              "total_revenue_tx", "delta_qty", "delta_price", "match_status"]
cols_show = [c for c in cols_proof if c in df_proof.columns]
st.dataframe(df_proof[cols_show], width='stretch', hide_index=True)

# ──────────────────────────────────────────────────────────────
# PAGINATED DATA TABLE
# ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-hdr">📋 Bảng dữ liệu đối soát chi tiết (Phân trang)</div>', unsafe_allow_html=True)

# Filter
if filter_status != "Tất cả":
    df_filtered = df[df["match_status"] == filter_status].reset_index(drop=True)
else:
    df_filtered = df.reset_index(drop=True)

total_rows = len(df_filtered)
total_pages = max(1, math.ceil(total_rows / page_size))

if "page" not in st.session_state:
    st.session_state.page = 1
st.session_state.page = min(st.session_state.page, total_pages)

# Pagination controls
nav1, nav2, nav3, nav4, nav5 = st.columns([1, 1, 3, 1, 1])
with nav1:
    if st.button("⏮ Đầu", disabled=(st.session_state.page <= 1), use_container_width=True, key="btn_first"):
        st.session_state.page = 1
        st.rerun()
with nav2:
    if st.button("◀ Trước", disabled=(st.session_state.page <= 1), use_container_width=True, key="btn_prev"):
        st.session_state.page -= 1
        st.rerun()
with nav3:
    st.markdown(
        f'<div class="page-bar"><div class="page-info">'
        f'Trang <b>{st.session_state.page}</b> / <b>{total_pages}</b> &nbsp;·&nbsp; '
        f'{total_rows:,} bản ghi</div></div>',
        unsafe_allow_html=True
    )
with nav4:
    if st.button("Sau ▶", disabled=(st.session_state.page >= total_pages), use_container_width=True, key="btn_next"):
        st.session_state.page += 1
        st.rerun()
with nav5:
    if st.button("Cuối ⏭", disabled=(st.session_state.page >= total_pages), use_container_width=True, key="btn_last"):
        st.session_state.page = total_pages
        st.rerun()

# Slice data
s = (st.session_state.page - 1) * page_size
e = s + page_size
df_page = df_filtered.iloc[s:e]

# Style the dataframe
display_cols = ["order_id", "product_name", "quantity_order", "quantity_tx",
                "unit_price_order", "unit_price_tx", "total_revenue_order",
                "total_revenue_tx", "delta_revenue", "match_status"]
display_cols = [c for c in display_cols if c in df_page.columns]

def highlight_rows(row):
    if row.get("match_status") == "❌ Lệch":
        return ["background-color: rgba(255,77,106,.08); color: #ff8a9e;"] * len(row)
    return ["background-color: rgba(0,200,150,.04);"] * len(row)

styled = df_page[display_cols].style.apply(highlight_rows, axis=1)

st.dataframe(styled, width='stretch', height=520, hide_index=True)

# Quick page jump
with st.expander("🔢 Nhảy đến trang"):
    jump = st.number_input("Nhập số trang:", min_value=1, max_value=total_pages, value=st.session_state.page)
    if st.button("Đi đến"):
        st.session_state.page = jump
        st.rerun()

# ──────────────────────────────────────────────────────────────
# FOOTER
# ──────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown("""
<div style="text-align:center; padding:10px 0 20px;">
    <p style="color:#8b8fa3; font-size:12px;">
    🏗️ <b>Noah Unified Commerce</b> · Group 5 · Module 6: Dashboard<br>
    Data Stitching: MySQL (Orders) ↔ PostgreSQL (Transactions) via Report API
    </p>
</div>
""", unsafe_allow_html=True)