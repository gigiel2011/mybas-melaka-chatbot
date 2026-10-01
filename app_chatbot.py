import math
import time
import requests
import streamlit as st
from groq import Groq

# ==========================================
# 1. KONFIGURASI GROQ API & CLIENT
# ==========================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "")

# Inisialisasi SDK Rasmi Groq untuk elak Ralat 403
client = Groq(api_key=GROQ_API_KEY) if GROQ_API_KEY else None

# Endpoint REST API ArcGIS Portal
URL_REALTIME_BUS = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Live_Kedudukan_Bas/FeatureServer/0/query"
URL_STATIC_LALUAN = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Laluan_Bas/FeatureServer/0/query"
URL_STATIC_HENTIAN = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Hentian_Bas/FeatureServer/0/query"

st.set_page_config(
    page_title="myBAS Melaka AI - Digital Command",
    page_icon="🤖",
    layout="centered"
)

# ==========================================
# 2. FUNGSI GEOMETRI (HAVERSINE)
# ==========================================
def haversine_distance(lat1, lon1, lat2, lon2):
    """Mengira jarak sebenar antara dua koordinat (dalam kilometer)"""
    if None in (lat1, lon1, lat2, lon2):
        return None
    try:
        R = 6371.0
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)
    except Exception:
        return None

# ==========================================
# GAYA CSS DIGITAL & DARK MODE
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; }
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
    .digital-status { color: #39FF14; font-size: 11px; font-family: monospace; }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="digital-header">
        <p class="digital-title">🚌 MYBAS MELAKA // AI COMMAND</p>
        <span class="digital-status">● GROQ LLaMA 3.3 SDK (TOKEN OPTIMIZED)</span>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 3. TARIK DATA PENUH ARCGIS PORTAL
# ==========================================
@st.cache_data(ttl=30)
def get_arcgis_data():
    """Tarik data dari Feature Layer ArcGIS Portal"""
    params = {'where': '1=1', 'outFields': '*', 'f': 'json', 'resultRecordCount': 2000}
    summary = {"realtime_bus": [], "static_laluan": [], "static_hentian": []}

    try:
        res = requests.get(URL_REALTIME_BUS, params=params, verify=False).json()
        for f in res.get('features', []):
            attrs = f.get('attributes', {})
            geom = f.get('geometry', {})
            summary["realtime_bus"].append({
                "Plat": attrs.get('label_bas') or attrs.get('vehicle_id'),
                "Kod": str(attrs.get('kod_laluan') or '').strip().upper(),
                "Nama": attrs.get('nama_laluan'),
                "Laju": attrs.get('kelajuan_kmh') or 30,
                "Lat": geom.get('y'),
                "Lon": geom.get('x')
            })
    except Exception:
        summary["realtime_bus"] = []

    try:
        res = requests.get(URL_STATIC_LALUAN, params=params, verify=False).json()
        for f in res.get('features', []):
            attrs = f.get('attributes', {})
            summary["static_laluan"].append({
                "Kod": str(attrs.get('kod_laluan') or '').strip().upper(),
                "Nama": attrs.get('nama_laluan')
            })
    except Exception:
        summary["static_laluan"] = []

    try:
        res = requests.get(URL_STATIC_HENTIAN, params=params, verify=False).json()
        for f in res.get('features', []):
            attrs = f.get('attributes', {})
            geom = f.get('geometry', {})
            summary["static_hentian"].append({
                "ID": attrs.get('stop_id') or attrs.get('OBJECTID'),
                "Nama": attrs.get('nama_hentian') or attrs.get('nama_stop') or attrs.get('name'),
                "Lat": geom.get('y'),
                "Lon": geom.get('x')
            })
    except Exception:
        summary["static_hentian"] = []

    return summary

# ==========================================
# 4. CHATBOT INTERACTION
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "⚡ **Sistem AI myBAS Command Center Active.**\nSedia memproses pertanyaan laluan, penapisan bas tepat, dan carian hentian."
    }]

for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

if user_input := st.chat_input("Input arahan / soalan di sini..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user", avatar="👤").write(user_input)

    with st.spinner("🤖 AI sedang memproses jawapan & menganalisis data GIS..."):
        arcgis_data = get_arcgis_data()

        # Matriks Pengiraan ETA & Penapisan Hentian Berdekatan
        eta_info = []
        relevant_stops = []
        user_query_lower = user_input.lower()

        if isinstance(arcgis_data["realtime_bus"], list) and isinstance(arcgis_data["static_hentian"], list):
            for bus in arcgis_data["realtime_bus"]:
                b_lat, b_lon = bus.get("Lat"), bus.get("Lon")
                bus_route = bus.get("Kod")
                speed = bus.get("Laju") or 30

                if b_lat and b_lon:
                    for stop in arcgis_data["static_hentian"]:
                        s_lat, s_lon = stop.get("Lat"), stop.get("Lon")
                        dist = haversine_distance(b_lat, b_lon, s_lat, s_lon)
                        stop_name = str(stop.get("Nama") or "")

                        # Tapis hentian relevan untuk jimat token (julat 5km atau dipadankan dengan carian)
                        if dist is not None and dist <= 5.0:
                            eta_minutes = round((dist / max(speed, 10)) * 60)
                            eta_info.append({
                                "Plat": bus.get("Plat"),
                                "Kod": bus_route,
                                "Hentian": stop_name,
                                "Jarak_KM": dist,
                                "ETA_Minit": max(eta_minutes, 1)
                            })
                            if stop_name not in relevant_stops:
                                relevant_stops.append(stop_name)
                        elif any(word in stop_name.lower() for word in user_query_lower.split() if len(word) > 3):
                            if stop_name not in relevant_stops:
                                relevant_stops.append(stop_name)

        # Padatkan senarai hentian
        stops_summary = ", ".join(relevant_stops[:30]) if relevant_stops else "Tiada hentian spesifik berdekatan dikesan."

        system_instructions = f"""
        Anda AI Urban Transit Assistant myBAS Melaka. Jawab sopan & profesional dalam Bahasa Melayu.

        DATA BAS LIVE: {arcgis_data['realtime_bus']}
        ANALISIS ETA (<5KM): {eta_info if eta_info else "Tiada bas dalam julat 5km."}
        SENARAI LALUAN: {arcgis_data['static_laluan']}
        HENTIAN RELEVAN DIKESAN: {stops_summary}

        PERATURAN:
        1. UTAMAKAN KOD LALUAN: Jika pengguna tanya bas terdekat untuk hentian di Laluan M100, HANYA kaitkan bas Kod M100. JANGAN campur bas laluan lain (seperti M22).
        2. Jika tiada bas aktif untuk kod laluan berkenaan, jawab secara jujur.
        """

        # Ringkaskan muatan mesej (3 mesej perbualan terakhir)
        messages_payload = [{"role": "system", "content": system_instructions}]
        for msg in st.session_state.messages[-3:]:
            role_type = "user" if msg["role"] == "user" else "assistant"
            messages_payload.append({"role": role_type, "content": msg["content"]})

        answer = None
        if client:
            try:
                chat_completion = client.chat.completions.create(
                    messages=messages_payload,
                    model="llama-3.3-70b-versatile",
                    temperature=0.1,
                    max_tokens=600
                )
                answer = chat_completion.choices[0].message.content
            except Exception as e:
                answer = f"⚠️ Ralat API Groq: {e}"
        else:
            answer = "⚠️ Ralat: GROQ_API_KEY tidak dijumpai dalam Streamlit Secrets."

    def stream_response(text):
        for word in text.split(" "):
            yield word + " "
            time.sleep(0.01)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant", avatar="🤖"):
        st.write_stream(stream_response(answer))
