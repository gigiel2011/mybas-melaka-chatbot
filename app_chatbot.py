import os
import requests
import streamlit as st

# ==========================================
# 1. KONFIGURASI OPENROUTER API (CLOUD)
# ==========================================
# Jangan simpan key sebenar di sini jika push ke GitHub Public
OPENROUTER_API_KEY = "sk-or-v1-TAMPAL_API_KEY_DI_SINI"

try:
    API_KEY = st.secrets.get("OPENROUTER_API_KEY", OPENROUTER_API_KEY)
except Exception:
    API_KEY = OPENROUTER_API_KEY

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

# Endpoint REST API dari ArcGIS Portal
URL_REALTIME_BUS = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Live_Kedudukan_Bas/FeatureServer/0/query"
URL_STATIC_LALUAN = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Laluan_Bas/FeatureServer/0/query"
URL_STATIC_HENTIAN = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Hentian_Bas/FeatureServer/0/query"

st.set_page_config(
    page_title="myBAS Melaka AI",
    page_icon="🤖",
    layout="centered",
)

# ==========================================
# GAYA CSS DIGITAL & DARK MODE
# ==========================================
st.markdown(
    """
    <style>
    /* Latar belakang utama */
    .stApp {
        background-color: #0B0E14;
    }
    /* Kad Header Digital Command */
    .digital-header {
        background: linear-gradient(135deg, #0D1B2A 0%, #1B263B 100%);
        border: 1px solid #00E5FF;
        box-shadow: 0 0 12px rgba(0, 229, 255, 0.25);
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 15px;
    }
    .digital-title {
        color: #00E5FF;
        font-family: 'Courier New', monospace;
        font-weight: bold;
        font-size: 18px;
        letter-spacing: 1.5px;
        margin: 0;
    }
    .digital-status {
        color: #39FF14;
        font-size: 11px;
        font-family: monospace;
    }
    </style>
""",
    unsafe_allow_html=True,
)

# Header Utama Visual
st.markdown(
    """
    <div class="digital-header">
        <p class="digital-title">🚌 MYBAS MELAKA</p>
        <span class="digital-status">● SYSTEM ONLINE (LIVE FEED)</span>
    </div>
""",
    unsafe_allow_html=True,
)


# ==========================================
# 2. FUNGSI TARIK DATA DARI ARCGIS PORTAL
# ==========================================
def get_arcgis_data():
    """Tarik data penuh dari Feature Layer ArcGIS Portal"""
    # Parameter resultRecordCount=2000 ditambah untuk mengatasi had query default ArcGIS
    params = {
        "where": "1=1",
        "outFields": "*",
        "f": "json",
        "resultRecordCount": 2000,
    }
    summary = {"realtime_bus": [], "static_laluan": [], "static_hentian": []}

    # 1. Data Kedudukan Bas Live
    try:
        res = requests.get(URL_REALTIME_BUS, params=params, verify=False).json()
        for f in res.get("features", []):
            attrs = f.get("attributes", {})
            summary["realtime_bus"].append({
                "Plat/Label": attrs.get("label_bas") or attrs.get("vehicle_id"),
                "Kod Laluan": attrs.get("kod_laluan"),
                "Nama Laluan": attrs.get("nama_laluan"),
                "Kelajuan (km/h)": attrs.get("kelajuan_kmh"),
                "Arah (Bearing)": attrs.get("bearing"),
                "Masa Kemaskini": attrs.get("last_updated"),
            })
    except Exception as e:
        summary["realtime_bus"] = f"Ralat: {e}"

    # 2. Data Garisan Laluan Static
    try:
        res = requests.get(URL_STATIC_LALUAN, params=params, verify=False).json()
        for f in res.get("features", []):
            attrs = f.get("attributes", {})
            summary["static_laluan"].append({
                "Kod Laluan": attrs.get("kod_laluan"),
                "Nama Laluan": attrs.get("nama_laluan"),
                "Jenis Perkhidmatan": attrs.get("jenis_perkhidmatan"),
                "Status Laluan": attrs.get("status_laluan"),
            })
    except Exception as e:
        summary["static_laluan"] = f"Ralat: {e}"

    # 3. Data Hentian Bas Static (SEMUA REKOD HENTIAN)
    try:
        res = requests.get(URL_STATIC_HENTIAN, params=params, verify=False).json()
        for f in res.get("features", []):
            attrs = f.get("attributes", {})
            summary["static_hentian"].append({
                "ID Hentian": attrs.get("stop_id"),
                "Nama Hentian": attrs.get("nama_hentian"),
                "Kod Laluan": attrs.get("kod_laluan")
                or attrs.get("route_id")
                or "N/A",
                "Waktu Operasi": (
                    f"{attrs.get('waktu_pertama')} - {attrs.get('waktu_terakhir')}"
                ),
            })
    except Exception as e:
        summary["static_hentian"] = f"Ralat: {e}"

    return summary


# ==========================================
# 3. ANTARAMUKA CHATBOT (STREAMLIT)
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": (
            "⚡ **Sistem AI myBAS Aktif.** Sedia membantu pertanyaan berkaitan laluan,"
            " hentian, dan status bas aktif."
        ),
    }]

# Papar Sembang dengan Avatar Digital
for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

if user_input := st.chat_input("Input arahan / soalan di sini..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user", avatar="👤").write(user_input)

    with st.spinner("Mengimbas data ArcGIS Portal..."):
        arcgis_data = get_arcgis_data()

    system_prompt = f"""
    Anda adalah sistem kecerdasan buatan (AI Urban Transit Assistant) untuk myBAS Melaka.
    Gunakan format maklum balas yang kemas, digital, tepat, dan mudah dibaca (gunakan jadual Markdown atau bullet points jika sesuai).

    --- DATA REALTIME (BASMY_REALTIME) ---
    Jumlah Bas Aktif Masa Kini: {len(arcgis_data['realtime_bus']) if isinstance(arcgis_data['realtime_bus'], list) else 0}
    Data Bas Live:
    {arcgis_data['realtime_bus']}

    --- DATA STATIC (BASMY - LALUAN & HENTIAN) ---
    Jumlah Laluan Berdaftar: {len(arcgis_data['static_laluan']) if isinstance(arcgis_data['static_laluan'], list) else 0}
    Senarai Laluan Bas:
    {arcgis_data['static_laluan']}

    Jumlah Keseluruhan Hentian Bas Berdaftar: {len(arcgis_data['static_hentian']) if isinstance(arcgis_data['static_hentian'], list) else 0}
    Senarai Penuh Hentian Bas:
    {arcgis_data['static_hentian']}

    --------------------------------------------------
    ARAHAN JAWAPAN:
    1. Jawab dalam Bahasa Melayu yang profesional, futuristik, dan padat.
    2. Apabila pengguna bertanyakan jumlah keseluruhan hentian bas, berikan angka tepat berdasarkan 'Jumlah Keseluruhan Hentian Bas Berdaftar'.
    3. Untuk memadankan hentian bas dengan sesuatu laluan, padankan atribut 'Kod Laluan' antara senarai hentian dan senarai laluan.
    4. Gunakan simbol/pencetus visual seperti 🚌, 📍, ⏱️, ⚡ untuk persembahan data digital.
    5. Jika maklumat tiada dalam data, nyatakan dengan jujur dan jelas.
    """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "myBAS Melaka AI",
    }

    FREE_MODELS = [
        "meta-llama/llama-3.1-8b-instruct:free",
        "google/gemini-2.0-flash-exp:free",
        "mistralai/mistral-7b-instruct:free",
        "openrouter/auto",
    ]

    answer = None
    last_error = ""

    for model_name in FREE_MODELS:
        payload = {
            "model": model_name,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_input},
            ],
            "temperature": 0.3,
        }

        try:
            response = requests.post(
                OPENROUTER_URL, headers=headers, json=payload, timeout=30
            )
            if response.status_code == 200:
                data = response.json()
                answer = data["choices"][0]["message"]["content"]
                break
            else:
                last_error = f"Model {model_name} ({response.status_code}): {response.text}"
        except Exception as e:
            last_error = str(e)

    if not answer:
        answer = f"⚠️ Ralat Sambungan Rangkaian: {last_error}"

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.chat_message("assistant", avatar="🤖").write(answer)
