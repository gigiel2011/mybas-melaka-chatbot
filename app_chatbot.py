import math
import os
import time
import requests
import streamlit as st
from google import genai

# ==========================================
# 1. KONFIGURASI GOOGLE GENAI SDK
# ==========================================
# Ambil API Key dari Streamlit Secrets
API_KEY = st.secrets.get("GEMINI_API_KEY", "")

# Inisialisasi Client GenAI Rasmi
try:
    client = genai.Client(api_key=API_KEY)
except Exception as e:
    client = None

# Endpoint REST API dari ArcGIS Portal
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
    .stApp {
        background-color: #0B0E14;
    }
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
""", unsafe_allow_html=True)

st.markdown("""
    <div class="digital-header">
        <p class="digital-title">🚌 MYBAS MELAKA // AI COMMAND</p>
        <span class="digital-status">● GOOGLE GENAI OFFICIAL SDK ACTIVE</span>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 3. TARIK DATA PENUH ARCGIS PORTAL
# ==========================================
@st.cache_data(ttl=30)
def get_arcgis_data():
    """Tarik data PENUH dari Feature Layer ArcGIS Portal"""
    params = {
        'where': '1=1',
        'outFields': '*',
        'f': 'json',
        'resultRecordCount': 2000
    }
    summary = {
        "realtime_bus": [],
        "static_laluan": [],
        "static_hentian": []
    }

    # 1. Data Kedudukan Bas Live
    try:
        res = requests.get(URL_REALTIME_BUS, params=params, verify=False).json()
        for f in res.get('features', []):
            attrs = f.get('attributes', {})
            geom = f.get('geometry', {})
            summary["realtime_bus"].append({
                "Plat/Label": attrs.get('label_bas') or attrs.get('vehicle_id'),
                "Kod Laluan": str(attrs.get('kod_laluan') or '').strip().upper(),
                "Nama Laluan": attrs.get('nama_laluan'),
                "Kelajuan (km/h)": attrs.get('kelajuan_kmh') or 30,
                "Lat": geom.get('y'),
                "Lon": geom.get('x')
            })
    except Exception as e:
        summary["realtime_bus"] = f"Ralat: {e}"

    # 2. Data Garisan Laluan Static
    try:
        res = requests.get(URL_STATIC_LALUAN, params=params, verify=False).json()
        for f in res.get('features', []):
            attrs = f.get('attributes', {})
            summary["static_laluan"].append({
                "Kod Laluan": str(attrs.get('kod_laluan') or '').strip().upper(),
                "Nama Laluan": attrs.get('nama_laluan')
            })
    except Exception as e:
        summary["static_laluan"] = f"Ralat: {e}"

    # 3. Data Hentian Bas Static
    try:
        res = requests.get(URL_STATIC_HENTIAN, params=params, verify=False).json()
        for f in res.get('features', []):
            attrs = f.get('attributes', {})
            geom = f.get('geometry', {})
            summary["static_hentian"].append({
                "ID Hentian": attrs.get('stop_id') or attrs.get('OBJECTID'),
                "Nama Hentian": attrs.get('nama_hentian') or attrs.get('nama_stop') or attrs.get('name'),
                "Lat": geom.get('y'),
                "Lon": geom.get('x')
            })
    except Exception as e:
        summary["static_hentian"] = f"Ralat: {e}"

    return summary

# ==========================================
# 4. CHATBOT INTERACTION
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "⚡ **Sistem AI myBAS Command Center Active.**\nSedia memproses pertanyaan laluan, penapisan bas tepat, dan carian semua hentian."
    }]

for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

if user_input := st.chat_input("Input arahan / soalan di sini..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user", avatar="👤").write(user_input)

    with st.spinner("🤖 AI sedang memproses jawapan & menganalisis data GIS..."):
        arcgis_data = get_arcgis_data()

        # Matriks Pengiraan ETA
        eta_info = []
        if isinstance(arcgis_data["realtime_bus"], list) and isinstance(arcgis_data["static_hentian"], list):
            for bus in arcgis_data["realtime_bus"]:
                b_lat, b_lon = bus.get("Lat"), bus.get("Lon")
                bus_route = bus.get("Kod Laluan")
                speed = bus.get("Kelajuan (km/h)") or 30
                
                if b_lat and b_lon:
                    for stop in arcgis_data["static_hentian"]:
                        s_lat, s_lon = stop.get("Lat"), stop.get("Lon")
                        dist = haversine_distance(b_lat, b_lon, s_lat, s_lon)
                        
                        if dist is not None and dist <= 5.0:
                            eta_minutes = round((dist / max(speed, 10)) * 60)
                            eta_info.append({
                                "Plat Bas": bus.get("Plat/Label"),
                                "Kod Laluan": bus_route,
                                "Hentian": stop.get("Nama Hentian"),
                                "Jarak (KM)": dist,
                                "ETA (Minit)": max(eta_minutes, 1)
                            })

        system_instructions = f"""
        Anda adalah sistem AI Urban Transit Assistant untuk myBAS Melaka. Jawab soalan pengguna dengan Bahasa Melayu yang sopan, profesional, dan berstruktur.

        --- DATA LIVE KEDUDUKAN BAS ---
        Bas Aktif: {arcgis_data['realtime_bus']}

        --- ANALISIS ETA HAVERSINE (JULAT 5KM) ---
        {eta_info if eta_info else "Tiada bas dikesan berdekatan hentian semasa."}

        --- DATA LALUAN BAS ---
        {arcgis_data['static_laluan']}

        --- KESELURUHAN SENARAI HENTIAN BAS BERDAFTAR ({len(arcgis_data['static_hentian']) if isinstance(arcgis_data['static_hentian'], list) else 0} Hentian) ---
        {arcgis_data['static_hentian']}

        --------------------------------------------------
        PERATURAN JAWAPAN TEPAT:
        1. UTAMAKAN KOD LALUAN: Apabila pengguna bertanyakan bas terdekat untuk hentian tertentu (contoh: Taman Kota Laksamana / CIMB di Laluan M100), HANYA kaitkan bas yang beroperasi pada Laluan M100. JANGAN berikan bas dari laluan berlainan (seperti M22).
        2. Jika tiada bas M100 aktif pada masa nyata, maklumkan secara jujur bahawa "Tiada bas M100 aktif pada masa ini" dan elakkan daripada salah beri maklumat bas M22.
        3. Gunakan senarai penuh hentian di atas untuk mengesahkan tempat yang ditanya pengguna.
        """

        full_prompt = f"SYSTEM INSTRUCTIONS:\n{system_instructions}\n\nSOALAN PENGGUNA: {user_input}"

        answer = None
        if client:
            try:
                # Penunjuk model rasmi yang disokong: gemini-1.5-flash
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=full_prompt
                )
                answer = response.text
            except Exception as e:
                answer = f"⚠️ Ralat API Gemini SDK: {e}"
        else:
            answer = "⚠️ Ralat: API Key tidak dijumpai dalam Streamlit Secrets."

    def stream_response(text):
        for word in text.split(" "):
            yield word + " "
            time.sleep(0.01)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant", avatar="🤖"):
        st.write_stream(stream_response(answer))
