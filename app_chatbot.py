import math
import time
import requests
import streamlit as st

# ==========================================
# 1. KONFIGURASI GROQ API & FEATURE LAYERS
# ==========================================
GROQ_API_KEY = st.secrets.get("GROQ_API_KEY", "").strip()

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODELS_URL = "https://api.groq.com/openai/v1/models"

# URL Feature Layers ArcGIS Portal
URL_REALTIME_BUS = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Live_Kedudukan_Bas/FeatureServer/0/query"
URL_STATIC_LALUAN = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Laluan_Bas/FeatureServer/0/query"
URL_STATIC_HENTIAN = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Hentian_Bas/FeatureServer/0/query"

st.set_page_config(
    page_title="myBAS Melaka AI - Command Center",
    page_icon="🚌",
    layout="centered"
)

# ==========================================
# 2. MODEL DISCOVERY (CHAT ONLY)
# ==========================================
def get_active_chat_models(api_key):
    if not api_key:
        return ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        res = requests.get(GROQ_MODELS_URL, headers=headers, timeout=5)
        if res.status_code == 200:
            data = res.json()
            all_models = [m.get("id") for m in data.get("data", []) if m.get("id")]
            chat_models = [
                m for m in all_models 
                if not any(banned in m.lower() for banned in ["whisper", "vision", "guard", "gpt-oss", "preview"])
            ]
            chat_models.sort(key=lambda x: ("llama-3.3" in x or "llama-3.1" in x), reverse=True)
            if chat_models:
                return chat_models
    except Exception:
        pass
    return ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"]

# ==========================================
# 3. FUNGSI GEOMETRI (HAVERSINE DISTANCE)
# ==========================================
def haversine_distance(lat1, lon1, lat2, lon2):
    if None in (lat1, lon1, lat2, lon2):
        return None
    try:
        R = 6371.0  # Jejari bumi dalam KM
        dlat = math.radians(float(lat2) - float(lat1))
        dlon = math.radians(float(lon2) - float(lon1))
        a = math.sin(dlat / 2)**2 + math.cos(math.radians(float(lat1))) * math.cos(math.radians(float(lat2))) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return round(R * c, 2)
    except Exception:
        return None

# ==========================================
# 4. TARIK & DENGAN CARIAN KONTEN FEATURE LAYER
# ==========================================
@st.cache_data(ttl=30)
def get_gis_raw_data():
    params = {'where': '1=1', 'outFields': '*', 'f': 'json', 'resultRecordCount': 1000}
    data = {"buses": [], "routes": [], "stops": []}

    # Bas Live
    try:
        res = requests.get(URL_REALTIME_BUS, params=params, verify=False, timeout=5).json()
        for f in res.get('features', []):
            attrs = f.get('attributes', {})
            geom = f.get('geometry', {})
            data["buses"].append({
                "plat": attrs.get('label_bas') or attrs.get('vehicle_id') or 'Bas Unknown',
                "kod": str(attrs.get('kod_laluan') or '').strip().upper() or 'N/A',
                "laju": attrs.get('kelajuan_kmh') or 30,
                "lat": geom.get('y'),
                "lon": geom.get('x')
            })
    except Exception:
        pass

    # Laluan
    try:
        res = requests.get(URL_STATIC_LALUAN, params=params, verify=False, timeout=5).json()
        for f in res.get('features', []):
            attrs = f.get('attributes', {})
            kod = str(attrs.get('kod_laluan') or '').strip().upper()
            nama = attrs.get('nama_laluan') or ''
            if kod:
                data["routes"].append(f"Laluan {kod}: {nama}")
    except Exception:
        pass

    # Hentian
    try:
        res = requests.get(URL_STATIC_HENTIAN, params=params, verify=False, timeout=5).json()
        for f in res.get('features', []):
            attrs = f.get('attributes', {})
            geom = f.get('geometry', {})
            nama_stop = attrs.get('nama_hentian') or attrs.get('nama_stop') or attrs.get('name')
            if nama_stop:
                data["stops"].append({
                    "nama": str(nama_stop).strip(),
                    "lat": geom.get('y'),
                    "lon": geom.get('x')
                })
    except Exception:
        pass

    return data

# ==========================================
# 5. GAYA UI CHAT
# ==========================================
st.markdown("""
    <style>
    .stApp { background-color: #0B0E14; }
    .digital-header {
        background: linear-gradient(135deg, #0D1B2A 0%, #1B263B 100%);
        border: 1px solid #00E5FF;
        padding: 12px;
        border-radius: 8px;
        text-align: center;
        margin-bottom: 15px;
    }
    .digital-title {
        color: #00E5FF;
        font-family: monospace;
        font-weight: bold;
        font-size: 18px;
        margin: 0;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown("""
    <div class="digital-header">
        <p class="digital-title">🚌 MYBAS MELAKA AI ASSISTANT</p>
    </div>
""", unsafe_allow_html=True)

# ==========================================
# 6. PEMPROSESAN CHATBOT
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Hai! Saya AI Pembantu myBAS Melaka. Boleh tanya saya pasal kedudukan bas live, carian hentian, atau anggaran masa tiba (ETA)!"
    }]

for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

if user_input := st.chat_input("Tanya lokasi hentian atau laluan bas di sini..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user", avatar="👤").write(user_input)

    with st.spinner("Memproses carian & data kedudukan bas..."):
        gis_data = get_gis_raw_data()
        user_query_lower = user_input.lower()

        # LOGIK CARIAN HENTIAN TERDEKAT BERDASARKAN INPUT PENGGUNA
        matched_stops = []
        for stop in gis_data["stops"]:
            if any(word in stop["nama"].lower() for word in user_query_lower.split() if len(word) > 2):
                matched_stops.append(stop)

        # KIRA ETA BAS AKTIF TERHADAP HENTIAN YANG DIJUMPAI
        eta_results = []
        if matched_stops and gis_data["buses"]:
            for target_stop in matched_stops[:3]:  # Ambil maksimum 3 hentian sepadan
                s_lat, s_lon = target_stop["lat"], target_stop["lon"]
                for bus in gis_data["buses"]:
                    b_lat, b_lon = bus["lat"], bus["lon"]
                    if s_lat and s_lon and b_lat and b_lon:
                        dist = haversine_distance(b_lat, b_lon, s_lat, s_lon)
                        if dist is not None:
                            speed = max(bus["laju"], 15)  # Anggaran kelajuan minimum 15 km/j
                            eta_min = round((dist / speed) * 60)
                            eta_results.append(f"Hentian '{target_stop['nama']}' -> Bas {bus['plat']} (Laluan {bus['kod']}): Jarak ~{dist}km, Anggaran ETA: {max(eta_min, 1)} minit (Laju: {bus['laju']} km/h)")

        # SUSUN TEXT SUMMARY UNTUK AI
        total_bas = len(gis_data["buses"])
        buses_list = [f"Plat: {b['plat']} | Laluan: {b['kod']} | Kelajuan: {b['laju']}km/h" for b in gis_data["buses"][:10]]
        buses_summary_text = "\n".join(buses_list) if buses_list else "Tiada bas live aktif."

        eta_summary_text = "\n".join(eta_results[:5]) if eta_results else "Tiada padanan bas berdekatan dikesan untuk lokasi soalan ini."

        # SYSTEM PROMPT MESRA & BERFOKUS KEPADA HASIL CARIAN
        system_instructions = f"""
        Anda ialah AI Pembantu rasmi myBAS Melaka. Jawab soalan pengguna secara rilex, santai, dan membantu dalam Bahasa Melayu.

        DATA LIVE MAKLUMAT GIS:
        - Jumlah Bas Aktif Masa Nyata: {total_bas} bas.
        - Senarai Bas Live:
        {buses_summary_text}

        ANALISIS HASIL CARIAN LOKASI & ETA UNTUK SOALAN PENGGUNA:
        {eta_summary_text}

        PANDUAN MENJAWAB:
        1. JIKA PENGGUNA BERTANYA PASAL LOKASI/HENTIAN (Contoh: "sy di hentian hospital alor gajah jauh lagi ke"):
           - Semak bahagian "ANALISIS HASIL CARIAN LOKASI & ETA".
           - Jika ada bas dikesan, beritahu status jarak (KM) dan anggaran masa tiba (ETA minit) bas terdekat dengan nada peramah dan tenang.
           - Jika tiada bas terdekat atau tiada padanan hentian, terangkan secara ringkas & jelas bahawa bas berkenaan belum menghantar isyarat live terdekat.
        2. JIKA TEGURAN MESRA (seperti "hi", "hello"):
           - Jawab salam mesra sahaja tanpa membebankan pengguna dengan data panjang.
        3. JANGAN sesekali menjawab "Apa" sahaja. Berikan jawapan lengkap dan peramah.
        """

        messages_payload = [{"role": "system", "content": system_instructions}]
        # Ambil 4 mesej perbualan terakhir untuk kekalkan konteks soalan
        for msg in st.session_state.messages[-4:]:
            role_type = "user" if msg["role"] == "user" else "assistant"
            messages_payload.append({"role": role_type, "content": msg["content"]})

        answer = None
        last_error_debug = ""

        if GROQ_API_KEY:
            active_chat_models = get_active_chat_models(GROQ_API_KEY)
            headers = {
                "Authorization": f"Bearer {GROQ_API_KEY}",
                "Content-Type": "application/json"
            }

            for model_name in active_chat_models:
                payload = {
                    "model": model_name,
                    "messages": messages_payload,
                    "max_tokens": 350
                }
                try:
                    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=10)
                    res_data = response.json()
                    
                    if response.status_code == 200 and "choices" in res_data:
                        answer = res_data["choices"][0]["message"]["content"]
                        break
                    else:
                        err_msg = res_data.get("error", {}).get("message", "Tiada maklumat ralat")
                        last_error_debug = f"HTTP {response.status_code} ({model_name}): {err_msg}"
                except Exception as e:
                    last_error_debug = f"Exception: {str(e)}"
                    continue

            if not answer:
                answer = f"⚠️ Ralat Groq API: {last_error_debug if last_error_debug else 'Gagal melepasi API'}"
        else:
            answer = "⚠️ GROQ_API_KEY tidak dijumpai dalam Streamlit Secrets."

    def stream_response(text):
        for word in text.split(" "):
            yield word + " "
            time.sleep(0.01)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant", avatar="🤖"):
        st.write_stream(stream_response(answer))
