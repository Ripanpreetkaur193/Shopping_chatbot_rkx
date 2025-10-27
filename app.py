# app.py
import io, base64, re
from dataclasses import dataclass
from typing import Dict

import streamlit as st
import pandas as pd
from PIL import Image
from difflib import get_close_matches

# Optional imports for live FX rates (used by Currency Converter)
try:
    import requests
except Exception:
    requests = None

# ------------------------------------------------
# PAGE CONFIG
# ------------------------------------------------
st.set_page_config(page_title="Shopping Chatbot Assistant", page_icon="🛍️", layout="wide")

# ------------------------------------------------
# SMALL UTILS (used by new features)
# ------------------------------------------------
CURRENCY_SYMBOLS = {"USD": "$", "CAD": "CA$", "EUR": "€", "INR": "₹"}

def b64_download(data: bytes, filename: str, label: str):
    b64 = base64.b64encode(data).decode()
    href = f'<a download="{filename}" href="data:application/octet-stream;base64,{b64}">{label}</a>'
    st.markdown(href, unsafe_allow_html=True)

# ====== NEW FEATURE HELPERS (1) Currency Converter ======
@st.cache_data(ttl=1800)
def fetch_rates(base="USD") -> Dict[str, float]:
    """Fetch live currency rates; fallback to static demo rates if offline."""
    static = {"USD": {"USD": 1, "CAD": 1.36, "EUR": 0.92, "INR": 65.0}}
    if requests is None:
        return static.get(base, static["USD"])
    try:
        r = requests.get(f"https://api.exchangerate.host/latest?base={base}", timeout=5)
        if r.ok:
            return r.json().get("rates", static["USD"])
    except Exception:
        pass
    return static.get(base, static["USD"])

def format_money(amount: float, currency: str) -> str:
    sym = CURRENCY_SYMBOLS.get(currency, "")
    return f"{sym}{amount:,.2f} {currency}" if sym else f"{amount:,.2f} {currency}"

def currency_converter_panel():
    st.subheader("💱 Currency Converter")
    st.caption("Convert USD to CAD, EUR, or INR (live rates via exchangerate.host; falls back to demo rates).")

    usd_amount = st.number_input("Enter amount in USD ($):", min_value=0.0, value=100.0, step=1.0)
    target_currency = st.selectbox("Convert to:", ["CAD", "EUR", "INR"], index=0)

    rates = fetch_rates("USD")
    converted = usd_amount * float(rates.get(target_currency, 1.0))

    st.markdown("---")
    st.subheader("Converted Amount 💰")
    st.metric(label=f"{usd_amount:.2f} USD → {target_currency}", value=format_money(converted, target_currency))
    st.caption("Demo fallback rates: 1 USD = 1.36 CAD, 0.92 EUR, 65 INR")

# ====== NEW FEATURE HELPERS (2) Virtual Try-On ======
@dataclass
class OverlayConfig:
    scale: float = 1.0
    x: int = 0
    y: int = 0
    opacity: float = 0.9

def alpha_composite(base_rgba: Image.Image, overlay_rgba: Image.Image, cfg: OverlayConfig) -> Image.Image:
    ow = int(overlay_rgba.width * cfg.scale)
    oh = int(overlay_rgba.height * cfg.scale)
    overlay_resized = overlay_rgba.resize((max(1, ow), max(1, oh)))
    canvas = base_rgba.copy()
    canvas.paste(overlay_resized, (cfg.x, cfg.y), overlay_resized.split()[3])  # use alpha channel as mask
    if cfg.opacity < 1.0:
        canvas = Image.blend(base_rgba, canvas, cfg.opacity)
    return canvas

def virtual_tryon_panel():
    st.subheader("🪄 Virtual Try-On (Prototype)")
    st.caption("Overlay a transparent clothing/accessory PNG on your photo.")
    base_img = st.file_uploader("Upload base image (your photo/model) — JPG/PNG", type=["jpg","jpeg","png"])
    overlay_img = st.file_uploader("Upload overlay PNG (transparent background)", type=["png"])

    if not base_img or not overlay_img:
        st.info("Tip: Use transparent PNGs (e.g., jeans, sunglasses, earrings).")
        return

    base = Image.open(base_img).convert("RGBA")
    overlay = Image.open(overlay_img).convert("RGBA")

    st.image(base, caption="Base Image", use_container_width=True)
    st.image(overlay, caption="Overlay Image (PNG)", use_container_width=True)

    st.divider()
    cfg = OverlayConfig()
    cfg.scale = st.slider("Scale", 0.1, 3.0, 1.0, 0.05)
    cfg.opacity = st.slider("Opacity", 0.1, 1.0, 0.9, 0.05)
    cfg.x = st.slider("X Position", 0, base.width, base.width // 3)
    cfg.y = st.slider("Y Position", 0, base.height, base.height // 3)

    if st.button("Render Try-On"):
        out = alpha_composite(base, overlay, cfg)
        st.image(out, caption="Result", use_container_width=True)
        buf = io.BytesIO()
        out.convert("RGB").save(buf, format="JPEG", quality=95)
        b64_download(buf.getvalue(), "tryon_result.jpg", "⬇️ Download image")

# ------------------------------------------------
# SIDEBAR FEATURES (first 15 unchanged + 2 new at end)
# ------------------------------------------------
st.sidebar.title("🛍️ Shopping Features")
st.sidebar.write("Select a Feature:")
features = [
    "Search Products", "🧹 Clear Chat History", "Compare Products", "Personalized Recommendations",
    "Track Orders", "Availability by Location", "Cart Reminder", "Discounts & Promo Codes",
    "Back-in-Stock Alerts", "Size & Fit Help", "Product Reviews", "Bundle Suggestions",
    "Reorder Quickly", "Checkout Inside Chat", "Multi-language Support",
    # new:
    "💱 Currency Converter", "🪄 Virtual Try-On (Prototype)"
]
selected_feature = st.sidebar.radio("", features, index=0)

# ------------------------------------------------
# MAIN PAGE TITLE
# ------------------------------------------------
st.title("🛍️ Shopping Chatbot Assistant")
st.caption("Chat naturally — ask about products, colors, or budgets 💬")

# ------------------------------------------------
# LOAD DATASET (with fallback)
# ------------------------------------------------
csv_loaded = True
try:
    df = pd.read_csv("shopping_trends_updated.csv")
except FileNotFoundError:
    csv_loaded = False
    # Small fallback dataset so the app still runs
    df = pd.DataFrame({
        "Item Purchased": ["Blue Jeans", "Black Sneakers", "White T-Shirt", "Red Dress", "Green Hoodie", "Yellow Scarf"],
        "Category": ["Bottoms", "Shoes", "Tops", "Dresses", "Outerwear", "Accessories"],
        "Color": ["Blue", "Black", "White", "Red", "Green", "Yellow"],
        "Price USD": [49.99, 69.99, 19.99, 89.99, 59.99, 14.99],
        "Location": ["Vancouver", "Toronto", "Kamloops", "Calgary", "Vancouver", "Kamloops"],
        "Brand": ["DenimCo", "RunFast", "CottonClub", "Elegance", "WarmWear", "Silky"]
    })

df.columns = df.columns.str.lower().str.strip()

# Detect columns dynamically
item_col = next((c for c in df.columns if "item" in c), None)
price_col = next((c for c in df.columns if any(x in c for x in ["price", "amount", "cost", "usd"])), None)
color_col = next((c for c in df.columns if "color" in c), None)
category_col = next((c for c in df.columns if "category" in c), None)
size_col = next((c for c in df.columns if "size" in c), None)
brand_col = next((c for c in df.columns if "brand" in c or "company" in c), None)
stock_col = next((c for c in df.columns if "stock" in c or "availability" in c), None)

# Ensure price is numeric
if price_col:
    df[price_col] = pd.to_numeric(df[price_col], errors="coerce")

# ------------------------------------------------
# MEMORY
# ------------------------------------------------
if "conversation" not in st.session_state:
    st.session_state["conversation"] = []
if "context" not in st.session_state:
    st.session_state["context"] = {"item": None, "color": None, "budget": None, "price_type": None, "step": "greet"}
if "compare_history" not in st.session_state:
    st.session_state["compare_history"] = []
if "preferences" not in st.session_state:
    st.session_state["preferences"] = {"color": None, "category": None}
# New states for added features
if "cart" not in st.session_state:
    st.session_state["cart"] = []                   # list of {"name", "qty", "price"}
if "reminders" not in st.session_state:
    st.session_state["reminders"] = []
if "coupons" not in st.session_state:
    st.session_state["coupons"] = {"WELCOME10": {"type": "percent", "value": 10},
                                   "SAVE15": {"type": "percent", "value": 15},
                                   "FLAT5": {"type": "flat", "value": 5}}
if "applied_coupon" not in st.session_state:
    st.session_state["applied_coupon"] = None
if "alerts" not in st.session_state:
    st.session_state["alerts"] = {}                # item -> {"color":..., "size":...}
if "past_orders" not in st.session_state:
    st.session_state["past_orders"] = [
        {"item": "Blue Jeans", "qty": 1, "price": 49.99},
        {"item": "Black Sneakers", "qty": 1, "price": 69.99},
        {"item": "White T-Shirt", "qty": 2, "price": 19.99},
    ]
if "reviews" not in st.session_state:
    st.session_state["reviews"] = {}

# ------------------------------------------------
# HELPER FUNCTIONS (search/chat)
# ------------------------------------------------
def find_product(search_text: str):
    """Find product by item and optional color contained in the text."""
    txt = (search_text or "").lower()
    color_match, item_match = None, None

    # color guess
    if color_col:
        for c in df[color_col].dropna().unique():
            if not isinstance(c, str):
                continue
            if c.lower() in txt:
                color_match = c
                break

    # item guess
    if item_col:
        unique_items = [i for i in df[item_col].dropna().unique() if isinstance(i, str)]
        # try exact substring first
        for i in unique_items:
            if i.lower() in txt:
                item_match = i
                break
        # fallback to fuzzy closest
        if not item_match and unique_items:
            hit = get_close_matches(txt, [i.lower() for i in unique_items], n=1)
            item_match = next((i for i in unique_items if i.lower() == (hit[0] if hit else "")), None)

    if item_match:
        filtered = df[df[item_col].str.contains(re.escape(item_match), case=False, na=False)] if item_col else df.copy()
        if color_match and color_col:
            filtered = filtered[filtered[color_col].str.contains(re.escape(color_match), case=False, na=False)]
        if not filtered.empty:
            return filtered.iloc[0]
    return None

def extract_filters(text: str):
    text = (text or "").lower()

    # budget and direction
    budget, price_type = None, None
    m_less = re.search(r"(?:under|less|below)\s*\$?\s*(\d+)", text)
    m_more = re.search(r"(?:more than|above|over|greater(?: than)?)\s*\$?\s*(\d+)", text)
    if m_less:
        budget, price_type = int(m_less.group(1)), "less"
    elif m_more:
        budget, price_type = int(m_more.group(1)), "more"

    # color list
    colors = ["black", "blue", "white", "red", "green", "yellow", "pink", "purple", "grey", "gray", "brown", "maroon"]
    found_color = next((c for c in colors if c in text), None)
    if found_color == "gray":
        found_color = "grey"

    # item via fuzzy match
    items = df[item_col].dropna().unique().tolist() if item_col else []
    lower_items = [x.lower() for x in items if isinstance(x, str)]
    found_item = None
    for i in lower_items:
        if i in text:
            found_item = i
            break
    if not found_item and lower_items:
        hit = get_close_matches(text, lower_items, n=1)
        found_item = hit[0] if hit else None

    return found_item, found_color, budget, price_type

def search_products(item=None, color=None, budget=None, price_type=None):
    results = df.copy()

    if item and item_col:
        results = results[results[item_col].str.contains(re.escape(item), case=False, na=False)]
    if color and color_col:
        results = results[results[color_col].str.contains(re.escape(color), case=False, na=False)]
    if (budget is not None) and price_col:
        if price_type == "less":
            results = results[results[price_col] <= float(budget)]
        elif price_type == "more":
            results = results[results[price_col] >= float(budget)]

    results = results.dropna(subset=[price_col]) if price_col else results
    if results.empty:
        return None
    if price_col and price_col in results.columns:
        results = results.sort_values(by=price_col, ascending=True)
    return results.head(3)

def respond_like_bot(results, item, color, budget, price_type):
    if price_type == "less" and budget:
        intro = f"Here are some {color or ''} {item or 'items'} under ${budget} 🛍️"
    elif price_type == "more" and budget:
        intro = f"Here are some {color or ''} {item or 'items'} over ${budget} 💎"
    else:
        intro = f"Here are some {color or ''} {item or 'items'} I think you’ll love 💫"
    reply = intro + "\n\n"
    for _, row in results.iterrows():
        name = row[item_col] if item_col else "Item"
        color_val = row[color_col] if color_col else "-"
        price_val = f"${row[price_col]:.2f}" if price_col and pd.notnull(row[price_col]) else "N/A"
        category_val = row[category_col] if category_col else "-"
        reply += f"✨ **{name}** — {price_val}\n"
        reply += f"   Category: {category_val} | Color: {color_val}\n\n"
    reply += "Would you like me to show *similar* or *cheaper* options next?"
    return reply

def cart_total():
    total = sum(i["qty"] * i["price"] for i in st.session_state["cart"])
    coup = st.session_state.get("applied_coupon")
    if coup:
        rule = st.session_state["coupons"][coup]
        if rule["type"] == "percent":
            total = total * (1 - rule["value"] / 100.0)
        else:
            total = max(0.0, total - rule["value"])
    return round(total, 2)

# ------------------------------------------------
# CLEAR CHAT HISTORY
# ------------------------------------------------
if selected_feature == "🧹 Clear Chat History":
    st.subheader("🧾 Your Recent Chat History")
    if st.session_state["conversation"]:
        for sender, msg in st.session_state["conversation"]:
            with st.chat_message("user" if sender == "You" else "assistant"):
                st.markdown(msg)
    else:
        st.info("No previous chat history 💬")
    if st.button("🧹 Clear Now"):
        st.session_state.clear()
        st.success("✅ Chat history cleared successfully!")
    st.stop()

# ------------------------------------------------
# COMPARE PRODUCTS
# ------------------------------------------------
if selected_feature == "Compare Products":
    st.subheader("🔍 Compare Two Products")
    st.write("Type two product names to compare (e.g., **blue jeans vs black jeans**)")

    for hist in st.session_state["compare_history"]:
        with st.chat_message("assistant"):
            st.markdown(f"### 🆚 Comparing **{hist['p1']} ({hist['c1']})** vs **{hist['p2']} ({hist['c2']})**")
            st.table(pd.DataFrame(hist["table"]))
            st.success("Here's your comparison! 💕 Which one would you like to explore further?")
            st.divider()

    user_compare = st.chat_input("Type your comparison (e.g., black jeans vs blue jeans)...")
    if user_compare:
        match = re.split(r"\s+vs\s+|\s+and\s+", user_compare.lower())
        if len(match) >= 2:
            p1, p2 = find_product(match[0].strip()), find_product(match[1].strip())
            if p1 is not None and p2 is not None:
                comp_data = {
                    "Attribute": ["Price", "Color", "Category"],
                    f"{p1[item_col]} ({p1[color_col]})": [
                        f"${p1[price_col]:.2f}" if price_col else "-", p1[color_col] if color_col else "-", p1[category_col] if category_col else "-"
                    ],
                    f"{p2[item_col]} ({p2[color_col]})": [
                        f"${p2[price_col]:.2f}" if price_col else "-", p2[color_col] if color_col else "-", p2[category_col] if category_col else "-"
                    ],
                }
                st.session_state["compare_history"].append({
                    "p1": p1[item_col], "c1": p1[color_col] if color_col else "-",
                    "p2": p2[item_col], "c2": p2[color_col] if color_col else "-",
                    "table": comp_data
                })
                st.rerun()
            else:
                st.warning("⚠️ Couldn't find both items — please check spelling or color terms.")
        else:
            st.info("💡 Use `product1 vs product2` format.")
    st.stop()

# ------------------------------------------------
# PERSONALIZED RECOMMENDATIONS
# ------------------------------------------------
if selected_feature == "Personalized Recommendations":
    st.subheader("💖 Personalized Recommendations")
    st.write("Tell me what you like — colors, categories, or styles — and I’ll find perfect matches for you!")

    user_pref = st.chat_input("Tell me your favorite color, category, or style...")

    if user_pref:
        colors = ["black", "blue", "white", "red", "green", "yellow", "pink", "purple", "grey", "brown", "maroon"]
        found_color = next((c for c in colors if c in user_pref.lower()), None)
        found_category = None
        if category_col:
            for cat in df[category_col].dropna().unique():
                if isinstance(cat, str) and cat.lower() in user_pref.lower():
                    found_category = cat
                    break

        if found_color:
            st.session_state["preferences"]["color"] = found_color
        if found_category:
            st.session_state["preferences"]["category"] = found_category

        filtered = df.copy()
        if st.session_state["preferences"]["color"] and color_col:
            filtered = filtered[filtered[color_col].str.contains(st.session_state["preferences"]["color"], case=False, na=False)]
        if st.session_state["preferences"]["category"] and category_col:
            filtered = filtered[filtered[category_col].str.contains(st.session_state["preferences"]["category"], case=False, na=False)]

        if not filtered.empty:
            filtered = filtered.sort_values(by=price_col).head(5) if price_col else filtered.head(5)
            with st.chat_message("assistant"):
                st.markdown("### 💫 Based on your style, here are some personalized picks for you:")
                for _, row in filtered.iterrows():
                    price_val = f"${row[price_col]:.2f}" if price_col else "N/A"
                    color_val = row[color_col] if color_col else "-"
                    cat_val = row[category_col] if category_col else "-"
                    st.markdown(f"🛍️ **{row[item_col]}** — {price_val}  \n🎨 Color: {color_val} | 🏷️ Category: {cat_val}")
                st.success("Would you like more suggestions or a different color?")
        else:
            st.warning("I couldn’t find matching products 😅 — try another color or category!")
    else:
        with st.chat_message("assistant"):
            st.markdown("Hi there 💕! Tell me what kind of products you love — I’ll personalize your shopping list!")
    st.stop()

# ------------------------------------------------
# TRACK ORDERS
# ------------------------------------------------
if selected_feature == "Track Orders":
    st.subheader("📦 Track Your Orders")
    st.write("You can ask me things like:")
    st.markdown("""
    - `Track order #2045`
    - `Where is my red handbag order?`
    - `Show my recent orders`
    """)

    if "orders" not in st.session_state:
        st.session_state["orders"] = [
            {"id": "2045", "item": "Red Handbag", "status": "Out for Delivery", "eta": "Today by 6 PM"},
            {"id": "2356", "item": "Blue Jeans", "status": "Delivered", "eta": "Delivered on Oct 22"},
            {"id": "2789", "item": "Black Sneakers", "status": "Processing", "eta": "Expected in 2 days"},
        ]

    user_query = st.chat_input("Enter your order number or product name...")

    if user_query:
        user_query = user_query.lower().strip()
        found_order = None
        for order in st.session_state["orders"]:
            if order["id"] in user_query or order["item"].lower() in user_query:
                found_order = order
                break

        if found_order:
            with st.chat_message("assistant"):
                st.markdown(f"### 🧾 Order Details")
                st.markdown(f"**Order ID:** {found_order['id']}")
                st.markdown(f"**Item:** {found_order['item']}")
                st.markdown(f"**Status:** {found_order['status']}")
                st.markdown(f"**Estimated Delivery:** {found_order['eta']}")
                if found_order["status"].lower() == "delivered":
                    st.success("✅ Your order has been delivered!")
                elif found_order["status"].lower() == "out for delivery":
                    st.info("🚚 Your order is on the way!")
                else:
                    st.warning("🕒 Your order is being processed.")
        else:
            with st.chat_message("assistant"):
                st.warning("⚠️ Sorry, I couldn’t find an order with that ID or name. Please check again.")
    else:
        with st.chat_message("assistant"):
            st.markdown("Hi there! 👋 Enter an **order ID** (e.g., `#2045`) or product name (e.g., `blue jeans`) to track it.")
    st.stop()

# ------------------------------------------------
# AVAILABILITY BY LOCATION
# ------------------------------------------------
if selected_feature == "Availability by Location":
    st.subheader("📍 Check Product Availability by Location")
    st.write("Enter your city or location to see which items are available there!")

    location_col = next((c for c in df.columns if "location" in c or "city" in c or "store" in c), None)

    simulated_availability = {
        "vancouver": ["Blue Jeans", "White Sneakers", "Red Dress"],
        "toronto": ["Black Sneakers", "Blue Jacket", "Pink Handbag"],
        "kamloops": ["Yellow Scarf", "Green Hoodie", "White Jeans"],
        "calgary": ["Grey T-Shirt", "Black Jeans", "Purple Dress"]
    }

    user_location = st.chat_input("Type your city name (e.g., Vancouver, Toronto, Kamloops)...")

    if user_location:
        user_location = user_location.lower().strip()

        if location_col:
            available_items = df[df[location_col].str.contains(user_location, case=False, na=False)]
            if not available_items.empty:
                with st.chat_message("assistant"):
                    st.markdown(f"### 🏬 Products available in **{user_location.title()}**")
                    for _, row in available_items.iterrows():
                        name = row[item_col] if item_col else "Item"
                        color_val = row[color_col] if color_col else "-"
                        price_val = f"${row[price_col]:.2f}" if price_col else "N/A"
                        st.markdown(f"🛍️ **{name}** — {price_val}  \n🎨 Color: {color_val}")
                    st.success(f"{len(available_items)} products found in {user_location.title()} ✅")
            else:
                st.warning(f"⚠️ No items found in {user_location.title()} — try another city.")
        else:
            found = simulated_availability.get(user_location, [])
            if found:
                with st.chat_message("assistant"):
                    st.markdown(f"### 🏬 Products available in **{user_location.title()}**:")
                    for item in found:
                        st.markdown(f"- 🛒 **{item}**")
                    st.success(f"{len(found)} products found in {user_location.title()} ✅")
            else:
                st.warning(f"Sorry, I couldn't find products in {user_location.title()} 😅")
    else:
        with st.chat_message("assistant"):
            st.markdown("👋 Hi there! Type a **city name** to check which items are available near you.")
    st.stop()

# ------------------------------------------------
# CART REMINDER
# ------------------------------------------------
if selected_feature == "Cart Reminder":
    st.subheader("🛒 Cart Reminder")
    st.write("Add products to your cart, view items, and set a checkout reminder!")

    user_action = st.chat_input("Type: 'Add black sneakers x2', 'Show cart', 'Remind me later', or 'Clear cart'...")

    def parse_add(text):
        # "add blue jeans x2" or "add blue jeans"
        m = re.search(r"add\s+(.*?)\s*(?:x(\d+))?$", text, re.IGNORECASE)
        if not m:
            return None, 1
        name = m.group(1)
        name = re.sub(r"\s*to cart$", "", name, flags=re.IGNORECASE).strip().title()
        qty = int(m.group(2)) if m.group(2) else 1
        return name, qty

    if user_action:
        txt = user_action.lower().strip()
        if txt.startswith("add"):
            name, qty = parse_add(user_action)
            if name:
                # find a price from dataset if possible
                price_guess = None
                if item_col and price_col:
                    cand = df[df[item_col].str.contains(re.escape(name.split()[0]), case=False, na=False)]
                    if not cand.empty:
                        try:
                            price_guess = float(cand.iloc[0][price_col])
                        except Exception:
                            price_guess = None
                price_guess = price_guess if price_guess is not None else 20.0
                st.session_state["cart"].append({"name": name, "qty": qty, "price": price_guess})
                with st.chat_message("assistant"):
                    st.success(f"✅ Added **{qty} × {name}** to your cart.")
            else:
                st.warning("Couldn’t parse that. Try `Add blue jeans x2`.")
        elif "show" in txt and "cart" in txt:
            if st.session_state["cart"]:
                with st.chat_message("assistant"):
                    st.markdown("### 🛍️ Your Cart")
                    for i, it in enumerate(st.session_state["cart"], start=1):
                        st.markdown(f"{i}. **{it['name']}** — {it['qty']} × ${it['price']:.2f}")
                    st.info(f"Cart total: **${cart_total():.2f}**")
            else:
                st.warning("Your cart is empty.")
        elif "remind" in txt:
            st.session_state["reminders"].append("Checkout your cart later today 🕒")
            with st.chat_message("assistant"):
                st.info("🔔 Reminder set! I’ll nudge you later to complete checkout.")
        elif "clear" in txt and "cart" in txt:
            st.session_state["cart"].clear()
            st.session_state["applied_coupon"] = None
            with st.chat_message("assistant"):
                st.success("🧹 Cart cleared.")
        else:
            with st.chat_message("assistant"):
                st.markdown("💬 Try: `Add blue jeans x2`, `Show cart`, `Remind me later`, or `Clear cart`.")
    else:
        with st.chat_message("assistant"):
            st.markdown("👋 Start with: `Add black sneakers x1` or `Show cart`.")
    st.stop()

# ------------------------------------------------
# DISCOUNTS & PROMO CODES
# ------------------------------------------------
if selected_feature == "Discounts & Promo Codes":
    st.subheader("🏷️ Discounts & Promo Codes")
    st.write("Apply a coupon to your current cart total.")

    if not st.session_state["cart"]:
        st.info("🛒 Your cart is empty. Add something first in **Cart Reminder** or while chatting.")
    else:
        st.markdown(f"**Current cart total:** ${cart_total():.2f} (before coupon)")
        code = st.text_input("Enter coupon code (e.g., WELCOME10, SAVE15, FLAT5)")
        if st.button("Apply Code"):
            c = (code or "").strip().upper()
            if c in st.session_state["coupons"]:
                st.session_state["applied_coupon"] = c
                st.success(f"🎉 Applied **{c}**! New total: **${cart_total():.2f}**")
            else:
                st.warning("Invalid code. Try WELCOME10 / SAVE15 / FLAT5.")
        if st.session_state["applied_coupon"]:
            st.info(f"Active coupon: **{st.session_state['applied_coupon']}**")
    st.stop()

# ------------------------------------------------
# BACK-IN-STOCK ALERTS
# ------------------------------------------------
if selected_feature == "Back-in-Stock Alerts":
    st.subheader("🔔 Back-in-Stock Alerts")
    st.write("Tell me the item (and optional color/size) you want to be notified about.")

    q = st.chat_input("Example: 'Notify me when Blue Jeans size M is back'")

    if q:
        # naive parse
        size = None
        m = re.search(r"size\s+([a-z0-9]+)", q.lower())
        if m:
            size = m.group(1).upper()
        # find item name heuristic
        words = q.replace("notify me when", "").replace("is back", "").strip().title()
        item_name = words
        st.session_state["alerts"][item_name] = {"size": size}
        with st.chat_message("assistant"):
            st.success(f"✅ Alert created for **{item_name}**{' (size '+size+')' if size else ''}. I’ll notify you when it’s restocked.")
    else:
        with st.chat_message("assistant"):
            st.markdown("Type something like: **Notify me when Black Sneakers size 8 is back**.")
    st.stop()

# ------------------------------------------------
# SIZE & FIT HELP  (IMPROVED)
# ------------------------------------------------
if selected_feature == "Size & Fit Help":
    st.subheader("📐 Size & Fit Help")
    st.write("Get quick size guidance. Example: 'What size for 30-inch waist in jeans?'")

    size_table = {
        "jeans": {"XS": 26, "S": 28, "M": 30, "L": 32, "XL": 34},
        "tshirt": {"XS": 34, "S": 36, "M": 38, "L": 40, "XL": 42},
        "shoes": {"US": [6,7,8,9,10,11]}
    }

    def cm_to_in(x: float) -> float:
        return round(x / 2.54, 1)

    ask = st.chat_input("Ask a fit question...")
    if ask:
        low = ask.lower().strip()
        reply = "I couldn’t parse that — try asking about jeans, tshirt, or shoe sizes."

        # patterns
        # jeans: accept "30-inch waist", "waist 30", "76 cm waist"
        waist_in = re.search(r"(?:waist\s*)?(\d+(?:\.\d+)?)\s*(?:in|inch|inches)\b", low)
        waist_cm = re.search(r"(?:waist\s*)?(\d+(?:\.\d+)?)\s*(?:cm|centimeter|centimeters)\b", low)
        waist_plain = re.search(r"waist\s*(\d+(?:\.\d+)?)\b", low)

        if "jean" in low:
            if waist_in:
                w = float(waist_in.group(1))
            elif waist_cm:
                w = cm_to_in(float(waist_cm.group(1)))
            elif waist_plain:
                w = float(waist_plain.group(1))
            else:
                w = None

            if w is not None:
                mapping = size_table["jeans"]
                closest = min(mapping.items(), key=lambda kv: abs(kv[1] - w))[0]
                reply = f"For a **{w:.1f}-inch waist**, try **{closest}** in jeans."
            else:
                reply = "Tell me your waist (e.g., *30 inch* or *76 cm*) and I’ll suggest a jeans size."

        elif "t-shirt" in low or "tshirt" in low or "tee" in low or "shirt" in low:
            chest_in = re.search(r"(?:chest\s*)?(\d+(?:\.\d+)?)\s*(?:in|inch|inches)\b", low)
            chest_cm = re.search(r"(?:chest\s*)?(\d+(?:\.\d+)?)\s*(?:cm|centimeter|centimeters)\b", low)
            chest_plain = re.search(r"chest\s*(\d+(?:\.\d+)?)\b", low)

            if chest_in:
                c = float(chest_in.group(1))
            elif chest_cm:
                c = cm_to_in(float(chest_cm.group(1)))
            elif chest_plain:
                c = float(chest_plain.group(1))
            else:
                c = None

            if c is not None:
                mapping = size_table["tshirt"]
                closest = min(mapping.items(), key=lambda kv: abs(kv[1] - c))[0]
                reply = f"For a **{c:.1f}-inch chest**, try **{closest}** in T-shirts."
            else:
                reply = "Share your chest size (in inches or cm) and I’ll map it to T-shirt sizes."

        elif "shoe" in low or "shoes" in low or "sneaker" in low or "sneakers" in low:
            eu = re.search(r"\beu\s*(\d{2})\b", low)
            if eu:
                eu_size = int(eu.group(1))
                # simple conversion band
                us_guess = round((eu_size - 33) * 0.5 + 4, 1)
                reply = f"EU {eu_size} is roughly **US {us_guess}**. Common US sizes we carry: **6–11**."
            else:
                reply = "Common US sizes: **6–11**. If you know your **EU** size, tell me and I’ll convert."

        with st.chat_message("assistant"):
            st.info(reply)
    else:
        with st.chat_message("assistant"):
            st.markdown("💡 Example: *What size jeans for 30-inch (or 76 cm) waist?*")
    st.stop()

# ------------------------------------------------
# PRODUCT REVIEWS
# ------------------------------------------------
if selected_feature == "Product Reviews":
    st.subheader("⭐ Product Reviews")
    st.write("Add or view quick text reviews for items.")

    action = st.radio("Choose:", ["View Reviews", "Add Review"], horizontal=True)
    item_name = st.text_input("Item name (exact or partial)")
    if action == "Add Review":
        rating = st.slider("Rating", 1, 5, 5)
        text = st.text_area("Your review")
        if st.button("Submit Review"):
            if not item_name.strip():
                st.warning("Please enter an item name.")
            else:
                key = item_name.strip().title()
                st.session_state["reviews"].setdefault(key, []).append({"rating": rating, "text": text})
                st.success("Thanks! Your review was added.")
    else:
        if st.button("Show Reviews"):
            key = item_name.strip().title()
            items = st.session_state["reviews"].get(key, [])
            if not items:
                st.info("No reviews yet.")
            else:
                for i, r in enumerate(items, start=1):
                    st.markdown(f"**{i}. {key}** — {r['rating']}⭐  \n{r['text']}")
    st.stop()

# ------------------------------------------------
# BUNDLE SUGGESTIONS
# ------------------------------------------------
if selected_feature == "Bundle Suggestions":
    st.subheader("🎁 Bundle Suggestions")
    st.write("Type a product and I’ll suggest a matching bundle (top + bottom + accessory).")

    q = st.chat_input("Example: 'Suggest bundle for Blue Jeans'")
    if q:
        base = (q.split("for")[-1] if "for" in q.lower() else q).strip().title()
        bundle = [
            {"name": f"Classic Tee to match {base}", "price": 19.99},
            {"name": f"Casual Jacket with {base}", "price": 39.99},
            {"name": f"Minimalist Belt for {base}", "price": 14.99},
        ]
        with st.chat_message("assistant"):
            st.markdown("### Suggested Bundle")
            total = 0
            for b in bundle:
                total += b["price"]
                st.markdown(f"- **{b['name']}** — ${b['price']:.2f}")
            st.info(f"Bundle total: **${total:.2f}** (save 10% vs buying separately)")
    else:
        with st.chat_message("assistant"):
            st.markdown("Try: *Suggest bundle for Black Sneakers*")
    st.stop()

# ------------------------------------------------
# REORDER QUICKLY
# ------------------------------------------------
if selected_feature == "Reorder Quickly":
    st.subheader("🔁 Reorder Quickly")
    st.write("Pick an item from your past orders and add it to cart instantly.")

    if not st.session_state["past_orders"]:
        st.info("No past orders found.")
    else:
        options = [f"{o['item']} — ${o['price']:.2f} (x{o['qty']})" for o in st.session_state["past_orders"]]
        choice = st.selectbox("Previous purchases:", options)
        qty = st.number_input("Quantity", 1, 10, 1)
        if st.button("Add to Cart"):
            idx = options.index(choice)
            order = st.session_state["past_orders"][idx]
            st.session_state["cart"].append({"name": order["item"], "qty": int(qty), "price": order["price"]})
            st.success(f"Added **{qty} × {order['item']}** to cart.")
    st.stop()

# ------------------------------------------------
# CHECKOUT INSIDE CHAT
# ------------------------------------------------
if selected_feature == "Checkout Inside Chat":
    st.subheader("💳 Checkout Inside Chat")
    if not st.session_state["cart"]:
        st.info("Your cart is empty.")
    else:
        st.markdown("### Order Summary")
        for it in st.session_state["cart"]:
            st.markdown(f"- **{it['name']}** — {it['qty']} × ${it['price']:.2f}")
        st.markdown(f"**Subtotal:** ${sum(i['qty']*i['price'] for i in st.session_state['cart']):.2f}")
        if st.session_state["applied_coupon"]:
            st.markdown(f"**Coupon:** {st.session_state['applied_coupon']}")
        st.success(f"**Total to pay:** ${cart_total():.2f}")

        name = st.text_input("Name")
        address = st.text_area("Shipping Address")
        pay_method = st.selectbox("Payment Method", ["Visa", "Mastercard", "Amex", "PayPal"])
        if st.button("Confirm & Pay"):
            if not name or not address:
                st.warning("Please fill name and address.")
            else:
                new_id = str(3000 + len(st.session_state.get("orders", [])) + 1)
                st.session_state.setdefault("orders", []).append({
                    "id": new_id, "item": f"{len(st.session_state['cart'])} items",
                    "status": "Processing", "eta": "3–5 business days"
                })
                st.session_state["cart"].clear()
                st.session_state["applied_coupon"] = None
                st.success(f"✅ Payment successful! Your order **#{new_id}** is now **Processing**.")
    st.stop()

# ------------------------------------------------
# MULTI-LANGUAGE SUPPORT
# ------------------------------------------------
if selected_feature == "Multi-language Support":
    st.subheader("🌍 Multi-language Support")
    st.write("Translate short shopping phrases into **French**, **Italian**, or **Punjabi**.")

    lang = st.selectbox("Choose language", ["French (français)", "Italiano", "Punjabi (ਪੰਜਾਬੀ)"])
    text = st.text_area("Enter a short message to translate (e.g., 'I want black sneakers under 80').")

    def translate_simple(s, target):
        base = s.strip()
        if not base:
            return ""
        common = {
            "hello": {"fr": "bonjour", "it": "ciao", "pa": "ਸਤ ਸ੍ਰੀ ਅਕਾਲ"},
            "i want": {"fr": "je veux", "it": "voglio", "pa": "ਮੈਨੂੰ ਚਾਹੀਦਾ ਹੈ"},
            "black sneakers": {"fr": "baskets noires", "it": "sneakers nere", "pa": "ਕਾਲੀਆਂ ਸਨੀਕਰਜ਼"},
            "under": {"fr": "moins de", "it": "meno di", "pa": "ਘੱਟ"},
            "blue jeans": {"fr": "jean bleu", "it": "jeans blu", "pa": "ਨੀਲੇ ਜੀਨਜ਼"},
            "dress": {"fr": "robe", "it": "abito", "pa": "ਡਰੈੱਸ"},
            "where is my order": {"fr": "où est ma commande", "it": "dov’è il mio ordine", "pa": "ਮੇਰਾ ਆਰਡਰ ਕਿੱਥੇ ਹੈ"},
            "thank you": {"fr": "merci", "it": "grazie", "pa": "ਧੰਨਵਾਦ"},
        }
        tgt = {"French (français)": "fr", "Italiano": "it", "Punjabi (ਪੰਜਾਬੀ)": "pa"}[target]
        out = base.lower()
        for en, maps in common.items():
            out = out.replace(en, maps.get(tgt, en))
        out = re.sub(r"under\s*\$?(\d+)", f"{common['under'][tgt]} \\1$", out)
        return out[:1].upper() + out[1:]

    if st.button("Translate"):
        res = translate_simple(text, lang)
        if res:
            st.success(res)
        else:
            st.info("Type a short shopping sentence to translate.")
    st.stop()

# ------------------------------------------------
# OTHER FEATURES PLACEHOLDER (keep unchanged list but include new features to skip placeholder)
# ------------------------------------------------
if selected_feature not in [
    "Search Products", "🧹 Clear Chat History", "Compare Products",
    "Personalized Recommendations", "Track Orders", "Availability by Location",
    "Cart Reminder", "Discounts & Promo Codes", "Back-in-Stock Alerts",
    "Size & Fit Help", "Product Reviews", "Bundle Suggestions",
    "Reorder Quickly", "Checkout Inside Chat", "Multi-language Support",
    "💱 Currency Converter", "🪄 Virtual Try-On (Prototype)"
]:
    st.subheader(f"🧠 {selected_feature}")
    st.info("✨ This feature is coming soon — it will include advanced chatbot interactions (e.g., apply discounts, show stock, or translate chat) 💬")
    st.stop()

# ------------------------------------------------
# NEW FEATURES ROUTER HANDLERS
# ------------------------------------------------
if selected_feature == "💱 Currency Converter":
    currency_converter_panel()
    st.stop()

if selected_feature == "🪄 Virtual Try-On (Prototype)":
    virtual_tryon_panel()
    st.stop()

# ------------------------------------------------
# SEARCH PRODUCTS (CHAT STYLE) — default screen
# ------------------------------------------------
def generate_reply(user_input):
    context = st.session_state["context"]
    text = (user_input or "").lower().strip()

    # quick exit phrases
    stop_words = ["no", "stop", "thanks", "thank you", "bye", "ok", "okay", "cancel"]
    if any(re.fullmatch(rf".*\b{re.escape(w)}\b.*", text) for w in stop_words):
        context.update({"step": "greet", "item": None, "color": None, "budget": None, "price_type": None})
        return "Alright 👋 Have a wonderful shopping day!"

    # if budget phrase present, run a search with current context
    if re.search(r"(?:under|less|below|more than|above|over|greater)\s*\$?(\d+)", text):
        _, _, budget, price_type = extract_filters(text)
        item, color = context.get("item"), context.get("color")
        context.update({"budget": budget, "price_type": price_type})
        results = search_products(item, color, budget, price_type)
        if results is not None and not results.empty:
            return respond_like_bot(results, item, color, budget, price_type)
        return f"I couldn’t find any {item or 'items'} in that range 😅"

    # state machine
    if context["step"] == "greet":
        context["step"] = "ask_item"
        return "Hey there 👋! What are you shopping for today? (e.g., jeans, shoes, dresses)"

    if context["step"] == "ask_item":
        item, color, _, _ = extract_filters(text)
        context.update({"item": item, "color": color, "step": "ask_color"})
        return f"Nice choice! 🎯 Do you have a color preference for your {item or 'item'}?"

    if context["step"] == "ask_color":
        _, color, _, _ = extract_filters(text)
        if color:
            context["color"] = color
        context["step"] = "ask_budget"
        return "Great! 💕 What’s your budget range? (e.g., under 100 or more than 150)"

    if context["step"] == "ask_budget":
        _, _, budget, price_type = extract_filters(text)
        context.update({"budget": budget, "price_type": price_type})
        results = search_products(context["item"], context["color"], context["budget"], context["price_type"])
        if results is not None and not results.empty:
            return respond_like_bot(results, context["item"], context["color"], context["budget"], context["price_type"])
        return "Hmm, I didn’t find anything in that range 😕 Maybe try another color or price range?"

    # fallback
    # allow “blue jeans under 80” in one go even if state isn’t set yet
    item, color, budget, price_type = extract_filters(text)
    if item or color or budget:
        results = search_products(item, color, budget, price_type)
        if results is not None and not results.empty:
            st.session_state["context"].update({"item": item, "color": color, "budget": budget, "price_type": price_type, "step": "ask_color" if not color else "ask_budget"})
            return respond_like_bot(results, item, color, budget, price_type)

    return "I didn’t quite get that — could you please clarify?"

# Show prior messages for this feature
for sender, msg in st.session_state["conversation"]:
    with st.chat_message("user" if sender == "You" else "assistant"):
        st.markdown(msg)

if selected_feature == "Search Products":
    user_input = st.chat_input("Type your message...")
    if user_input:
        st.session_state["conversation"].append(("You", user_input))
        bot_reply = generate_reply(user_input)
        st.session_state["conversation"].append(("Bot", bot_reply))
        st.rerun()
