# pages/01_Roteiro.py
# 🗓️ ROTEIRO SEMANAL

import time
from datetime import datetime, timedelta, date as _date
from zoneinfo import ZoneInfo

import streamlit as st
import gspread
from google.oauth2.service_account import Credentials
from gspread.exceptions import APIError, WorksheetNotFound

# =====================
# CONFIG
# =====================
st.set_page_config(
    page_title="Roteiro Semanal - Facta",
    layout="wide"
)

SHEET_ID = "11JaCc4y-htBW-cxbvbMBV28GHYlORbMM6345TSaXcgQ"
ABA_ROTEIROS = "Roteiros"

# =====================
# GOOGLE SHEETS
# =====================
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

credentials = Credentials.from_service_account_info(
    dict(st.secrets["gcp_service_account"]),
    scopes=scope
)
gc = gspread.authorize(credentials)

# =====================
# HELPERS
# =====================
def get_worksheet(tab):
    try:
        sh = gc.open_by_key(SHEET_ID)
        return sh.worksheet(tab)
    except WorksheetNotFound:
        st.error(f"A aba '{tab}' não existe.")
        st.stop()

def append_with_retry(ws, row, retries=4):
    for i in range(retries):
        try:
            ws.append_row(row)
            return
        except APIError:
            time.sleep((2 ** i) + 0.2)

# =====================
# HIERARQUIA (COPIE A MESMA)
# =====================
from utils import hierarquia, get_opcoes_hierarquia

# =====================
# FUNÇÕES DE DATA
# =====================
def proximo_domingo(d):
    return d + timedelta(days=(6 - d.weekday() + 7) % 7 or 7)

def feriados_br(ano):
    return {
        _date(ano, 1, 1): "Confraternização Universal",
        _date(ano, 4, 21): "Tiradentes",
        _date(ano, 5, 1): "Dia do Trabalho",
        _date(ano, 9, 7): "Independência",
        _date(ano, 10, 12): "Nossa Senhora Aparecida",
        _date(ano, 11, 2): "Finados",
        _date(ano, 11, 15): "Proclamação da República",
        _date(ano, 12, 25): "Natal",
    }

# =====================
# CARREGAR ROTEIROS
# =====================
@st.cache_data(ttl=300)
def carregar_roteiros():
    ws = get_worksheet(ABA_ROTEIROS)
    dados = ws.get_all_records()
    mapa = {}
    for r in dados:
        data = r.get("DATA")
        if data:
            mapa[data] = {
                "coordenador": r.get("COORDENADOR"),
                "loja": r.get("LOJA"),
                "obs": r.get("OBS", "")
            }
    return mapa

# =====================
# UI
# =====================
st.title("🗓️ Roteiro Semanal de Visitas")

roteiros = carregar_roteiros()

regionais, _, _ = get_opcoes_hierarquia(hierarquia, "Selecione", "Selecione")
regional = st.selectbox("Regional", regionais)

_, coordenadores, _ = get_opcoes_hierarquia(hierarquia, regional, "Selecione")
coordenador = st.selectbox("Coordenador", coordenadores)

if coordenador == "Selecione":
    st.info("Selecione Regional e Coordenador.")
    st.stop()

hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()

if "week_start" not in st.session_state:
    st.session_state["week_start"] = proximo_domingo(hoje)

week_start = st.session_state["week_start"]
week_days = [week_start + timedelta(days=i) for i in range(7)]

st.markdown(
    f"**Semana de {week_start.strftime('%d/%m/%Y')} até "
    f"{(week_start + timedelta(days=6)).strftime('%d/%m/%Y')}**"
)

feriados = feriados_br(week_start.year)

cols = st.columns(7)
labels = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]

for i, dia in enumerate(week_days):
    box = cols[i]
    dia_iso = dia.strftime("%Y-%m-%d")
    bloqueado = i in (0, 6) or dia in feriados

    ag = roteiros.get(dia_iso, {})
    loja = ag.get("loja", "Selecione")
    obs = ag.get("obs", "")

    box.markdown(f"### {labels[i]} {dia.strftime('%d/%m')}")

    if bloqueado:
        box.warning("Bloqueado")
        continue

    lojas = get_opcoes_hierarquia(hierarquia, regional, coordenador)[2]
    loja_sel = box.selectbox(
        "Loja",
        ["Selecione"] + lojas,
        index=(["Selecione"] + lojas).index(loja) if loja in lojas else 0,
        key=f"loja_{dia_iso}"
    )

    obs_txt = box.text_area(
        "Obs",
        value=obs,
        key=f"obs_{dia_iso}"
    )

    if box.button("Agendar", key=f"btn_{dia_iso}") and loja_sel != "Selecione":
        ws = get_worksheet(ABA_ROTEIROS)
        append_with_retry(
            ws,
            [regional, coordenador, loja_sel, "", dia_iso, obs_txt]
        )
        st.success("Agendado ✅")
        st.cache_data.clear()
        st.rerun()

nav1, nav2 = st.columns(2)

with nav1:
    if st.button("◀️ Semana anterior"):
        st.session_state["week_start"] -= timedelta(days=7)
        st.rerun()

with nav2:
    if st.button("Próxima semana ▶️"):
        st.session_state["week_start"] += timedelta(days=7)
        st.rerun()
