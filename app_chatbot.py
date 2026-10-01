import math
import os
import time
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
    page_title="myBAS Melaka AI - Digital Command",
    page_icon="🤖",
    layout="centered",
)


# ==========================================
# 2. FUNGSI GEOMETRI & PENGIRAAN JARAK (HAVERSINE)
# ==========================================
def haversine_distance(lat1, lon1, lat2, lon2):
  """Mengira jarak sebenar antara dua koordinat (dalam kilometer)"""
  if None in (lat1, lon1, lat2, lon2):
    return None
  try:
    R = 6371.0  # Jejari bumi dalam KM
    dlat = math.radians(float(lat2) - float(lat1))
    dlon = math.radians(float(lon2) - float(lon1))
    a = (
        math.sin(dlat / 2) ** 2
        + math.cos(math.radians(float(lat1)))
        * math.cos(math.radians(float(lat2)))
        * math.sin(dlon / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)
  except Exception:
    return None


# ==========================================
# GAYA CSS DIGITAL & DARK MODE
# ==========================================
st.markdown(
    """
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
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="digital-header">
        <p class="digital-title">🚌 MYBAS MELAKA // AI COMMAND</p>
        <span class="digital-status">● SYSTEM ONLINE (ROUTE-FILTERED ETA ACTIVE)</span>
    </div>
""",
    unsafe_allow_html=True,
)


# ==========================================
# 3. FUNGSI TARIK DATA DARI ARCGIS PORTAL
# ==========================================
def get_arcgis_data():
  """Tarik data penuh dari Feature Layer ArcGIS Portal termasuk koordinat geometri"""
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
      geom = f.get("geometry", {})
      summary["realtime_bus"].append({
          "Plat/Label": attrs.get("label_bas") or attrs.get("vehicle_id"),
          "Kod Laluan": str(attrs.get("kod_laluan") or "").strip().upper(),
          "Nama Laluan": attrs.get("nama_laluan"),
          "Kelajuan (km/h)": attrs.get("kelajuan_kmh") or 30,
          "Lat": geom.get("y"),
          "Lon": geom.get("x"),
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
          "Kod Laluan": str(attrs.get("kod_laluan") or "").strip().upper(),
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
      geom = f.get("geometry", {})
      summary["static_hentian"].append({
          "ID Hentian": attrs.get("stop_id") or attrs.get("OBJECTID"),
          "Nama Hentian": attrs.get("nama_hentian")
          or attrs.get("nama_stop")
          or attrs.get("name"),
          "Lat": geom.get("y"),
          "Lon": geom.get("x"),
          "Waktu Operasi": (
              f"{attrs.get('waktu_pertama', '')} -"
              f" {attrs.get('waktu_terakhir', '')}"
          ),
      })
  except Exception as e:
    summary["static_hentian"] = f"Ralat: {e}"

  return summary


# ==========================================
# 4. ANTARAMUKA CHATBOT & INGATAN SEJARAH
# ==========================================
if "messages" not in st.session_state:
  st.session_state.messages = [{
      "role": "assistant",
      "content": (
          "⚡ **Sistem AI myBAS Command Center Active.**\nSedia memproses"
          " kueri spatial, penapisan laluan bas, dan pengiraan ETA tepat."
      ),
  }]

# Papar Mesej Perbualan Terdahulu
for msg in st.session_state.messages:
  avatar = "🤖" if msg["role"] == "assistant" else "👤"
  st.chat_message(msg["role"], avatar=avatar).write(msg["content"])

if user_input := st.chat_input("Input arahan / soalan di sini..."):
  st.session_state.messages.append({"role": "user", "content": user_input})
  st.chat_message("user", avatar="👤").write(user_input)

  # PAPARAN AMUM "AI SEDANG MEMPROSES JAWAPAN..."
  with st.spinner("🤖 AI sedang memproses jawapan & menganalisis data GIS..."):
    arcgis_data = get_arcgis_data()

    # Matriks Pengiraan ETA Mengikut Kod Laluan Terhadap Hentian
    eta_info = []
    if isinstance(arcgis_data["realtime_bus"], list) and isinstance(
        arcgis_data["static_hentian"], list
    ):
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
                  "Kod Laluan Bas": bus_route,
                  "Nama Laluan Bas": bus.get("Nama Laluan"),
                  "Hentian Berdekatan": stop.get("Nama Hentian"),
                  "Jarak (KM)": dist,
                  "Anggaran ETA (Minit)": max(eta_minutes, 1),
              })

    system_prompt = f"""
        Anda adalah sistem kecerdasan buatan (AI Urban Transit Assistant) untuk myBAS Melaka.
        Gunakan format maklum balas yang kemas, digital, tepat, dan berstruktur (jadual/bullet points).

        --- DATA REALTIME (BASMY_REALTIME) ---
        Jumlah Bas Aktif Masa Kini: {len(arcgis_data['realtime_bus']) if isinstance(arcgis_data['realtime_bus'], list) else 0}
        Data Bas Live (Sertakan Kod Laluan Bas):
        {arcgis_data['realtime_bus']}

        --- ANALISIS ETA MASA NYATA (HAVERSINE GEOMETRY MATRIX) ---
        {eta_info if eta_info else "Tiada bas dikesan berdekatan hentian buat masa ini."}

        --- DATA STATIC (BASMY - LALUAN & HENTIAN) ---
        Jumlah Laluan Berdaftar: {len(arcgis_data['static_laluan']) if isinstance(arcgis_data['static_laluan'], list) else 0}
        Senarai Laluan Bas:
        {arcgis_data['static_laluan']}

        Jumlah Keseluruhan Hentian Bas Berdaftar: {len(arcgis_data['static_hentian']) if isinstance(arcgis_data['static_hentian'], list) else 0}
        Senarai Hentian Bas:
        {arcgis_data['static_hentian'][:120]}

        --------------------------------------------------
        ARAHAN PERATURAN TEPAT (ROUTE MATCHING STRICT RULE):
        1. UTAMAKAN KOD LALUAN: Apabila pengguna bertanyakan bas terdekat untuk sesuatu hentian atau laluan (contoh: Taman Kota Laksamana / Laluan M100), HANYA kaitkan bas yang beroperasi di laluan berkenaan (Kod Laluan M100). JANGAN padankan bas dari laluan berlainan (seperti M22) walaupun lokasinya berdekatan, melainkan pengguna bertanyakan SEMUA bas yang lalu di hentian tersebut.
        2. Jika tiada Bas M100 yang aktif dalam sistem live, beritahu pengguna secara jelas bahawa "Tiada bas M100 aktif buat masa ini" dan elakkan daripada tersalah beri maklumat Bas M22.
        3. Jawab dalam Bahasa Melayu yang profesional, futuristik, dan padat.
        4. Gunakan simbol visual seperti 🚌, 📍, ⏱️, ⚡.
        """

    recent_history = st.session_state.messages[-6:]
    messages_payload = [{"role": "system", "content": system_prompt}]

    for msg in recent_history:
      messages_payload.append({"role": msg["role"], "content": msg["content"]})

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "http://localhost:8501",
        "X-Title": "myBAS Melaka AI",
    }

    FREE_MODELS = [
        "google/gemini-2.0-flash-exp:free",
        "meta-llama/llama-3.1-8b-instruct:free",
        "mistralai/mistral-7b-instruct:free",
        "openrouter/auto",
    ]

    answer = None
    last_error = ""

    for model_name in FREE_MODELS:
      payload = {
          "model": model_name,
          "messages": messages_payload,
          "temperature": 0.1,
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
          last_error = (
              f"Model {model_name} ({response.status_code}): {response.text}"
          )
      except Exception as e:
        last_error = str(e)

    if not answer:
      answer = f"⚠️ Ralat Sambungan Rangkaian: {last_error}"

  # FUNGSI EFEK TYPING ANIMATION BILA MEMAPARKAN JAWAPAN
  def stream_response(text):
    for word in text.split(" "):
      yield word + " "
      time.sleep(0.02)  # Kelajuan menaip

  # Papar maklum balas AI secara dinamik
  st.session_state.messages.append({"role": "assistant", "content": answer})
  with st.chat_message("assistant", avatar="🤖"):
    st.write_stream(stream_response(answer))
