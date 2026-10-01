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
# 3. TARIK DATA DARI FEATURE LAYER ARCGIS
# ==========================================
@st.cache_data(ttl=30)
def get_feature_layer_data():
    params = {'where': '1=1', 'outFields': '*', 'f': 'json', 'resultRecordCount': 500}
    layer_data = {"bas_live": [], "laluan": [], "hentian": []}

    try:
        res = requests.get(URL_REALTIME_BUS, params=params, verify=False, timeout=5).json()
        for f in res.get('features', []):
            layer_data["bas_live"].append(f.get('attributes', {}))
    except Exception:
        pass

    try:
        res = requests.get(URL_STATIC_LALUAN, params=params, verify=False, timeout=5).json()
        for f in res.get('features', []):
            layer_data["laluan"].append(f.get('attributes', {}))
    except Exception:
        pass

    try:
        res = requests.get(URL_STATIC_HENTIAN, params=params, verify=False, timeout=5).json()
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
        "content": "Hai! Saya AI Pembantu myBAS Melaka. Boleh tanya saya pasal kedudukan bas live, laluan, atau senarai hentian hari ini!"
    }]

for msg in st.session_state.messages:
    avatar = "🤖" if msg["role"] == "assistant" else "👤"
    st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

if user_input := st.chat_input("Tanya apa sahaja tentang myBAS Melaka..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user", avatar="👤").write(user_input)

    with st.spinner("Semak data Feature Layer & memproses jawapan..."):
        features = get_feature_layer_data()

        total_bas = len(features["bas_live"])
        total_laluan = len(features["laluan"])
        total_hentian = len(features["hentian"])

        # Hadkan data sampel untuk memastikan saiz token sentiasa kecil
        data_bas_sample = features["bas_live"][:10]
        data_laluan_sample = features["laluan"][:10]

        # SYSTEM PROMPT SANTAI & FLEKSIBEL
        system_instructions = f"""
        Anda ialah AI Pembantu mesra myBAS Melaka. Jawab soalan pengguna dengan santai, rilex, dan mesra dalam Bahasa Melayu.

        DATA TERKINI FEATURE LAYER ARCGIS:
        - Jumlah Bas Live Aktif Masa Nyata: {total_bas} bas.
        - Ringkasan Data Bas Live: {data_bas_sample}
        - Ringkasan Data Laluan: {data_laluan_sample}
        - Jumlah Hentian Dikesan: {total_hentian} hentian.

        PANDUAN JAWAPAN:
        1. Sekiranya pengguna beri teguran mesra / umum (seperti "hi", "apa awak boleh bantu"), sambut mesra dan terangkan secara ringkas yang anda boleh bantu semak status bas live, laluan, dan hentian myBAS Melaka.
        2. Sekiranya soalan berkaitan bas/laluan/hentian, jawab berdasarkan data Feature Layer di atas secara terus.
        3. Sekiranya data tiada atau kosong, beritahu secara jujur dan rilex.
        """

        messages_payload = [{"role": "system", "content": system_instructions}]
        for msg in st.session_state.messages[-3:]:
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
                    "max_tokens": 300
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
                answer = f"⚠️ Ralat Groq API: {last_error_debug if last_error_debug else 'Gagal menghubungi API'}. Sila pastikan GROQ_API_KEY sah."
        else:
            answer = "⚠️ GROQ_API_KEY tidak dijumpai dalam Streamlit Secrets."

    def stream_response(text):
        for word in text.split(" "):
            yield word + " "
            time.sleep(0.01)

    st.session_state.messages.append({"role": "assistant", "content": answer})
    with st.chat_message("assistant", avatar="🤖"):
        st.write_stream(stream_response(answer))
