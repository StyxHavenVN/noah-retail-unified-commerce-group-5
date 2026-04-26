/* =============================================
   NOAH RETAIL STOREFRONT — Application Logic
   ============================================= */

// Kong Gateway URL — trong Docker, storefront gọi qua host machine port
const API_BASE = window.location.hostname === 'localhost'
    ? 'http://localhost:8000'
    : 'http://kong-gateway:8000';
const API_KEY = 'noah-secret-key';
const HEADERS = { 'apikey': API_KEY, 'Content-Type': 'application/json' };

// Product emoji mapping cho UI
const PRODUCT_EMOJIS = [
    '📱','💻','🎧','⌚','📷','🖥️','🎮','🔌','💡','🔋',
    '🖨️','📀','🎤','🎵','📡','🔧','🧲','💿','🗄️','🔑'
];

// State
let allProducts = [];
let displayedProducts = [];
let cart = [];
let currentPage = 1;
const PAGE_SIZE = 12;

// =============================================
// INIT
// =============================================
document.addEventListener('DOMContentLoaded', () => {
    loadProducts();
    createToastContainer();
});

function createToastContainer() {
    const c = document.createElement('div');
    c.className = 'toast-container';
    c.id = 'toast-container';
    document.body.appendChild(c);
}

// =============================================
// PRODUCTS API
// =============================================
async function loadProducts() {
    const grid = document.getElementById('products-grid');
    const skeleton = document.getElementById('loading-skeleton');
    
    try {
        const resp = await fetch(`${API_BASE}/api/products?limit=200`, {
            headers: HEADERS
        });

        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        allProducts = data.products || [];

        // Ẩn skeleton
        if (skeleton) skeleton.style.display = 'none';

        // Render sản phẩm
        currentPage = 1;
        displayedProducts = allProducts.slice(0, PAGE_SIZE);
        renderProducts(displayedProducts, false);
        updateLoadMore();

    } catch (err) {
        console.error('Lỗi tải sản phẩm:', err);
        if (skeleton) skeleton.innerHTML = `
            <div style="grid-column:1/-1; text-align:center; padding:3rem; color:var(--text-secondary);">
                <p style="font-size:2rem; margin-bottom:1rem;">⚠️</p>
                <p>Không thể kết nối API. Hãy chạy <code>docker-compose up -d</code></p>
                <button onclick="loadProducts()" style="margin-top:1rem; padding:0.5rem 1.5rem; 
                    background:var(--accent); border:none; border-radius:8px; color:#fff; cursor:pointer;
                    font-family:var(--font);">
                    Thử lại
                </button>
            </div>`;
    }
}

function renderProducts(products, append = false) {
    const grid = document.getElementById('products-grid');
    if (!append) grid.innerHTML = '';

    products.forEach((p, i) => {
        const emoji = PRODUCT_EMOJIS[p.id % PRODUCT_EMOJIS.length];
        const card = document.createElement('div');
        card.className = 'product-card';
        card.style.animationDelay = `${i * 0.05}s`;
        card.dataset.productId = p.id;

        card.innerHTML = `
            <div class="product-img">${emoji}</div>
            <div class="product-body">
                <div class="product-name">${escapeHtml(p.name)}</div>
                <div class="product-id">Mã SP: #${p.id}</div>
                <div class="product-price">${formatPrice(p.price)}</div>
                <button class="add-cart-btn" id="add-btn-${p.id}"
                    onclick="addToCart(${p.id}, '${escapeHtml(p.name)}', ${p.price})">
                    🛒 Thêm vào giỏ
                </button>
            </div>`;
        grid.appendChild(card);
    });
}

function loadMoreProducts() {
    currentPage++;
    const start = (currentPage - 1) * PAGE_SIZE;
    const end = start + PAGE_SIZE;
    const newProducts = getFilteredProducts().slice(start, end);
    displayedProducts = displayedProducts.concat(newProducts);
    renderProducts(newProducts, true);
    updateLoadMore();
}

function updateLoadMore() {
    const wrap = document.getElementById('load-more-wrap');
    const total = getFilteredProducts().length;
    wrap.style.display = displayedProducts.length < total ? 'block' : 'none';
}

// =============================================
// SEARCH & SORT
// =============================================
function getFilteredProducts() {
    const query = document.getElementById('search-input').value.toLowerCase();
    let filtered = allProducts.filter(p =>
        p.name.toLowerCase().includes(query) || String(p.id).includes(query)
    );

    const sort = document.getElementById('sort-select').value;
    if (sort === 'price-asc') filtered.sort((a, b) => a.price - b.price);
    else if (sort === 'price-desc') filtered.sort((a, b) => b.price - a.price);
    else if (sort === 'name') filtered.sort((a, b) => a.name.localeCompare(b.name));

    return filtered;
}

function filterProducts() {
    currentPage = 1;
    displayedProducts = getFilteredProducts().slice(0, PAGE_SIZE);
    renderProducts(displayedProducts, false);
    updateLoadMore();
}

function sortProducts() { filterProducts(); }

// =============================================
// CART
// =============================================
function addToCart(id, name, price) {
    const existing = cart.find(item => item.id === id);
    if (existing) {
        existing.quantity++;
    } else {
        cart.push({ id, name, price, quantity: 1 });
    }

    // Button animation
    const btn = document.getElementById(`add-btn-${id}`);
    if (btn) {
        btn.classList.add('added');
        btn.textContent = '✅ Đã thêm!';
        setTimeout(() => {
            btn.classList.remove('added');
            btn.textContent = '🛒 Thêm vào giỏ';
        }, 800);
    }

    updateCartUI();
    showToast(`Đã thêm "${name}" vào giỏ hàng`);
}

function removeFromCart(id) {
    cart = cart.filter(item => item.id !== id);
    updateCartUI();
}

function changeQty(id, delta) {
    const item = cart.find(i => i.id === id);
    if (!item) return;
    item.quantity += delta;
    if (item.quantity <= 0) return removeFromCart(id);
    updateCartUI();
}

function getCartTotal() {
    return cart.reduce((sum, item) => sum + item.price * item.quantity, 0);
}

function getCartCount() {
    return cart.reduce((sum, item) => sum + item.quantity, 0);
}

function updateCartUI() {
    // Badge
    document.getElementById('cart-badge').textContent = getCartCount();

    // Cart items
    const itemsEl = document.getElementById('cart-items');
    const emptyEl = document.getElementById('cart-empty');
    const footerEl = document.getElementById('cart-footer');

    if (cart.length === 0) {
        emptyEl.style.display = 'block';
        footerEl.style.display = 'none';
        itemsEl.innerHTML = '<p class="cart-empty">Giỏ hàng trống</p>';
        return;
    }

    footerEl.style.display = 'block';
    const emoji_map = id => PRODUCT_EMOJIS[id % PRODUCT_EMOJIS.length];

    itemsEl.innerHTML = cart.map(item => `
        <div class="cart-item">
            <div class="cart-item-icon">${emoji_map(item.id)}</div>
            <div class="cart-item-info">
                <div class="cart-item-name">${escapeHtml(item.name)}</div>
                <div class="cart-item-price">${formatPrice(item.price)}</div>
            </div>
            <div class="cart-item-qty">
                <button class="qty-btn" onclick="changeQty(${item.id}, -1)">−</button>
                <span class="qty-val">${item.quantity}</span>
                <button class="qty-btn" onclick="changeQty(${item.id}, 1)">+</button>
            </div>
            <button class="cart-item-remove" onclick="removeFromCart(${item.id})">🗑️</button>
        </div>
    `).join('');

    document.getElementById('cart-total-amount').textContent = formatPrice(getCartTotal());
}

function toggleCart() {
    document.getElementById('cart-sidebar').classList.toggle('open');
    document.getElementById('cart-overlay').classList.toggle('open');
}

// =============================================
// CHECKOUT
// =============================================
function showCheckout() {
    toggleCart(); // Close cart sidebar

    // Build order summary
    const summaryEl = document.getElementById('order-summary');
    summaryEl.innerHTML = `
        <div style="font-weight:700; margin-bottom:0.5rem;">📦 Đơn hàng của bạn:</div>
        ${cart.map(item => `
            <div style="display:flex; justify-content:space-between; padding:0.2rem 0;">
                <span>${escapeHtml(item.name)} × ${item.quantity}</span>
                <span style="color:var(--cyan);">${formatPrice(item.price * item.quantity)}</span>
            </div>
        `).join('')}
        <div style="border-top:1px solid var(--border); margin-top:0.5rem; padding-top:0.5rem;
            display:flex; justify-content:space-between; font-weight:700; font-size:1.1rem;">
            <span>Tổng cộng:</span>
            <span style="color:var(--green);">${formatPrice(getCartTotal())}</span>
        </div>`;

    document.getElementById('checkout-overlay').classList.add('open');
    document.getElementById('checkout-modal').classList.add('open');
}

function hideCheckout() {
    document.getElementById('checkout-overlay').classList.remove('open');
    document.getElementById('checkout-modal').classList.remove('open');
}

async function placeOrder(event) {
    event.preventDefault();
    const submitBtn = document.getElementById('submit-btn');
    const btnText = submitBtn.querySelector('.btn-text');
    const btnLoader = submitBtn.querySelector('.btn-loader');

    // Loading state
    submitBtn.disabled = true;
    btnText.style.display = 'none';
    btnLoader.style.display = 'inline';

    // Tạo user_id từ phone hash
    const phone = document.getElementById('customer-phone').value;
    const userId = Math.abs(hashCode(phone)) % 1000 + 1;

    let allSuccess = true;
    let orderIds = [];

    // Gửi từng item trong giỏ hàng thành 1 đơn riêng
    for (const item of cart) {
        try {
            const resp = await fetch(`${API_BASE}/api/orders`, {
                method: 'POST',
                headers: HEADERS,
                body: JSON.stringify({
                    user_id: userId,
                    product_id: item.id,
                    quantity: item.quantity
                })
            });

            if (resp.ok) {
                const data = await resp.json();
                orderIds.push(data.order_id || '?');
            } else {
                allSuccess = false;
            }
        } catch (err) {
            console.error('Order error:', err);
            allSuccess = false;
        }
    }

    // Reset form
    submitBtn.disabled = false;
    btnText.style.display = 'inline';
    btnLoader.style.display = 'none';
    hideCheckout();

    if (allSuccess) {
        // Show success
        document.getElementById('success-detail').textContent =
            `Mã đơn hàng: #${orderIds.join(', #')} — Tổng: ${formatPrice(getCartTotal())}`;
        document.getElementById('success-overlay').classList.add('open');
        document.getElementById('success-modal').classList.add('open');

        // Clear cart
        cart = [];
        updateCartUI();
        document.getElementById('checkout-form').reset();
    } else {
        showToast('⚠️ Có lỗi khi đặt hàng. Vui lòng thử lại!');
    }
}

function hideSuccess() {
    document.getElementById('success-overlay').classList.remove('open');
    document.getElementById('success-modal').classList.remove('open');
}

// =============================================
// UTILS
// =============================================
function formatPrice(val) {
    return new Intl.NumberFormat('vi-VN').format(val) + '₫';
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function hashCode(str) {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
        hash = ((hash << 5) - hash) + str.charCodeAt(i);
        hash |= 0;
    }
    return hash;
}

function showToast(message) {
    const container = document.getElementById('toast-container');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transform = 'translateX(100%)';
        toast.style.transition = 'all 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, 2500);
}
