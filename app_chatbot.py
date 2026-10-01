import os
import requests
import streamlit as st

# ==========================================
# 1. KONFIGURASI OPENROUTER API (CLOUD)
# ==========================================
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
    page_title="myBAS Melaka AI Assistant", page_icon="🚌", layout="centered"
)
st.title("🚌 Pembantu AI myBAS Melaka")


# ==========================================
# 2. FUNGSI TARIK DATA DARI ARCGIS PORTAL
# ==========================================
def get_arcgis_data():
    """Tarik data dari ketiga-tiga Feature Layer ArcGIS Portal"""
    params = {"where": "1=1", "outFields": "*", "f": "json"}
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

    # 3. Data Hentian Bas Static
    try:
        res = requests.get(URL_STATIC_HENTIAN, params=params, verify=False).json()
        for f in res.get("features", []):
            attrs = f.get("attributes", {})
            summary["static_hentian"].append({
                "ID Hentian": attrs.get("stop_id"),
                "Nama Hentian": attrs.get("nama_hentian"),
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
            "Hai! Saya Pembantu AI myBAS Melaka. Sedia menjawab soalan berkaitan"
            " laluan, hentian, dan kedudukan bas live."
        ),
    }]

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

if user_input := st.chat_input("Tanya soalan (cth: Berapa bas di laluan M100?)..."):
    st.session_state.messages.append({"role": "user", "content": user_input})
    st.chat_message("user").write(user_input)

    with st.spinner("Mengambil data live dari ArcGIS Portal..."):
        arcgis_data = get_arcgis_data()

    system_prompt = f"""
    Anda adalah pembantu pakar Perancang Bandar (Urban Planning AI) bagi projek myBAS Melaka.
    Berikut adalah maklumat penuh terkini dari sistem ArcGIS Portal:

    --- DATA REALTIME (BASMY_REALTIME - KEDUDUKAN BAS LIVE) ---
    Jumlah Bas Aktif Masa Kini: {len(arcgis_data['realtime_bus']) if isinstance(arcgis_data['realtime_bus'], list) else 0}
    Data Bas Live:
    {arcgis_data['realtime_bus']}

    --- DATA STATIC (BASMY - LALUAN & HENTIAN) ---
    Jumlah Laluan Berdaftar: {len(arcgis_data['static_laluan']) if isinstance(arcgis_data['static_laluan'], list) else 0}
    Senarai Laluan Bas:
    {arcgis_data['static_laluan']}

    Senarai Hentian Bas (Sampel):
    {arcgis_data['static_hentian'][:30]}

    --------------------------------------------------
    ARAHAN JAWAPAN:
    1. Jawab menggunakan Bahasa Melayu yang mesra, profesional, dan tepat.
    2. Jika soalan melibatkan status bas 'live', guna data REALTIME.
    3. Jika soalan melibatkan senarai laluan/hentian/waktu operasi, guna data STATIC.
    4. Jika maklumat tiada dalam data, nyatakan dengan jujur dan sopan.
    """

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "myBAS Melaka AI",
    }

    # Senarai model percuma aktif OpenRouter terkini + auto routing
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
        answer = f"Maaf, berlaku ralat sambungan ke OpenRouter. Detail: {last_error}"

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.chat_message("assistant").write(answer)
