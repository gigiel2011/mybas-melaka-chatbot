import google.genai as genai
import requests
import streamlit as st

# ==========================================
# 1. KONFIGURASI UTAMA
# ==========================================
# API Key Google Gemini Percuma anda:
GEMINI_API_KEY = "AQ.Ab8RN6IR-8X9--0Ck8y0-nkGcpSHYsMTh6Y4zSV3oXTZRTOURA"

# Endpoint REST API dari ArcGIS Portal anda
URL_REALTIME_BUS = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Live_Kedudukan_Bas/FeatureServer"
URL_STATIC_LALUAN = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Laluan_Bas/FeatureServer"
URL_STATIC_HENTIAN = "https://gisdev.planmalaysia.gov.my/server/rest/services/Hosted/myBAS_Melaka_Hentian_Bas/FeatureServer"

# Tetapan Model Gemini AI
client = genai.Client(api_key=GEMINI_API_KEY)

st.set_page_config(
    page_title="myBAS Melaka AI Assistant", page_icon="🚌", layout="centered"
)
st.title("🚌 Pembantu AI myBAS Melaka (Static & Realtime)")


# ==========================================
# 2. FUNGSI MENGAMBIL DATA DARI ARCGIS PORTAL
# ==========================================
def get_arcgis_data():
  """Tarik data dari ketiga-tiga Feature Layer ArcGIS Portal"""
  params = {"where": "1=1", "outFields": "*", "f": "json"}
  summary = {"realtime_bus": [], "static_laluan": [], "static_hentian": []}

  # 1. Data Kedudukan Bas Live (BASMY_REALTIME)
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

  # 2. Data Garisan Laluan Static (BASMY - Laluan)
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

  # 3. Data Hentian Bas Static (BASMY - Hentian)
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
          "Hai! Saya Pembantu AI myBAS Melaka. Saya boleh menjawab soalan"
          " berkaitan data **Static (Senarai Laluan & Hentian)** dan data"
          " **Realtime (Kedudukan & Kelajuan Bas Live)**. Ada soalan?"
      ),
  }]

# Paparkan mesej sembang terdahulu
for msg in st.session_state.messages:
  st.chat_message(msg["role"]).write(msg["content"])

# Menerima soalan pengguna
if user_input := st.chat_input("Tanya soalan (cth: Berapa bas di laluan M100?)..."):
  st.session_state.messages.append({"role": "user", "content": user_input})
  st.chat_message("user").write(user_input)

  # 1. Tarik data komprehensif dari ArcGIS Portal
  with st.spinner("Mengambil data Static & Realtime dari Portal..."):
    arcgis_data = get_arcgis_data()

  # 2. Bina Prompt Context untuk AI
  prompt = f"""
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
    Soalan Pengguna: {user_input}

    ARAHAN JAWAPAN:
    1. Jawab menggunakan Bahasa Melayu yang mesra, profesional, dan tepat.
    2. Jika soalan melibatkan status bas 'live', guna data REALTIME.
    3. Jika soalan melibatkan senarai laluan/hentian/waktu operasi, guna data STATIC.
    4. Jika maklumat tiada dalam data, nyatakan dengan jujur dan sopan.
    """

  # 3. Panggil Google Gemini AI
  try:
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )
    answer = response.text
  except Exception as e:
    answer = f"Maaf, berlaku ralat semasa memproses jawapan AI: {e}"

  st.session_state.messages.append({"role": "assistant", "content": answer})
  st.chat_message("assistant").write(answer)
