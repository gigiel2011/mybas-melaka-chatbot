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
        return []
    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        res = requests.get(GROQ_MODELS_URL, headers=headers, timeout=10)
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
    return ["llama-3.3-70b-versatile", "llama-3.1-8b-instant", "mixtral-8x7b-32768"]

# ==========================================
# 3. TARIK DATA DARI FEATURE LAYER ARCGIS
# ==========================================
@st.cache_data(ttl=30)
def get_feature_layer_data():
    params = {'where': '1=1', 'outFields': '*', 'f': 'json', 'resultRecordCount': 1000}
    layer_data = {"bas_live": [], "laluan": [], "hentian": []}

    # 1. Feature Layer Bas Live
    try:
        res = requests.get(URL_REALTIME_BUS, params=params, verify=False, timeout=10).json()
        for f in res.get('features', []):
            layer_data["bas_live"].append(f.get('attributes', {}))
    except Exception:
        pass

    # 2. Feature Layer Laluan
    try:
        res = requests.get(URL_STATIC_LALUAN, params=params, verify=False, timeout=10).json()
        for f in res.get('features', []):
            layer_data["laluan"].append(f.get('attributes', {}))
    except Exception:
        pass

    # 3. Feature Layer Hentian
    try:
        res = requests.get(URL_STATIC_HENTIAN, params=params, verify=False, timeout=10).json()
        for f in res.get('features', []):
            layer_data["hentian"].append(f.get('attributes', {}))
    except Exception:
        pass

    return layer_data

# ==========================================
# 4. GAYA UI CHAT
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
# 5. PEMPROSESAN CHATBOT
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = [{
        "role": "assistant",
        "content": "Hai! Saya AI myBAS Melaka. Ada apa-apa nak tanya pasal kedudukan bas, laluan, atau hentian hari ini?"
    }]

for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

if user_input := st.chat_input("Tanya apa sahaja tentang myBAS Melaka..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user", avatar="👤").write(user_input)

    with st.spinner("Semak data Feature Layer..."):
        features = get_feature_layer_data()

        # Dapatkan ringkasan jumlah
        total_bas = len(features["bas_live"])
        total_laluan = len(features["laluan"])
        total_hentian = len(features["hentian"])

        # Hadkan data untuk dimasukkan dalam prompt supaya tak overflow token
        data_bas_sample = features["bas_live"][:20]
        data_laluan_sample = features["laluan"][:20]
        data_hentian_sample = features["hentian"][:20]

        # SYSTEM PROMPT SANTAI & RILEX
        system_instructions = f"""
        Anda ialah pembantu AI mesra untuk myBAS Melaka. Jawab soalan pengguna secara rilex, santai, mesra, dan terus kepada point.

        DATA SEBENAR DARI FEATURE LAYER ARCGIS:
        - Jumlah Bas Live Aktif Sekarang: {total_bas} bas.
        - Data Atribut Bas Live: {data_bas_sample}
        - Data Atribut Laluan: {data_laluan_sample}
        - Data Atribut Hentian: {data_hentian_sample}

        PANDUAN JAWAPAN:
        1. Jawab soalan berdasarkan data Feature Layer di atas sahaja.
        2. Gunakan nada percakapan harian yang santai (contoh: "Sekarang ada X bas tengah jalan...", "Untuk laluan tu ada...").
        3. Jika data tiada atau kosong dalam Feature Layer, beritahu terus secara jujur dan rilex.
        4. Jangan mereka-reka maklumat luar atau mengulang ayat yang sama.
        """

        messages_payload = [{"role": "system", "content": system_instructions}]
        for msg in st.session_state.messages[-3:]:
            role_type = "user" if msg["role"] == "user" else "assistant"
            messages_payload.append({"role": role_type, "content": msg["content"]})

        answer = None
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
                    "temperature": 0.4,  # Lebih fleksibel dan santai
                    "max_tokens": 400
                }
                try:
                    response = requests.post(GROQ_API_URL, headers=headers, json=payload, timeout=15)
                    res_data = response.json()
                    if response.status_code == 200 and "choices" in res_data:
                        answer = res_data["choices"][0]["message"]["content"]
                        break
                except Exception:
                    continue

            if not answer:
                answer = "Maaf, sistem AI tak dapat respons sekejap. Boleh cuba tanya lagi?"
        else:
            answer = "⚠️ GROQ_API_KEY tak dijumpai dalam Streamlit Secrets."

    def stream_response(text):
        for word in text.split(" "):
            yield word + " "
            time.sleep(0.01)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant", avatar="🤖"):
        st.write_stream(stream_response(answer))
