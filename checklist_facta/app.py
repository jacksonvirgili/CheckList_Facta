# checklist_facta/app.py
# 🏠 HOME – Painel Diário

import streamlit as st
import gspread
from datetime import datetime
from zoneinfo import ZoneInfo
from google.oauth2.service_account import Credentials

# =====================
# CONFIGURAÇÕES GERAIS
# =====================
st.set_page_config(
    page_title="Painel Diário - Facta",
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
# FUNÇÕES
# =====================
@st.cache_data(ttl=300)
def carregar_roteiros_hoje():
    """
    Retorna um dict:
    {
        'Nome do Coordenador': 'Nome da Loja'
    }
    apenas para a DATA de hoje.
    """
    ws = gc.open_by_key(SHEET_ID).worksheet(ABA_ROTEIROS)
    dados = ws.get_all_records()

    hoje_iso = datetime.now(
        ZoneInfo("America/Sao_Paulo")
    ).strftime("%Y-%m-%d")

    mapa = {}

    for r in dados:
        data = r.get("DATA")
        coordenador = r.get("COORDENADOR")
        loja = r.get("LOJA")

        if data == hoje_iso and coordenador:
            mapa[coordenador] = loja or "Não informado"

    return mapa

# =====================
# INTERFACE
# =====================
st.title("🏠 Painel Diário")
st.markdown(
    "Visão rápida de **onde cada coordenador está hoje**, "
    "com base no roteiro planejado."
)

st.divider()

# Data amigável
hoje_br = datetime.now(
    ZoneInfo("America/Sao_Paulo")
).strftime("%d/%m/%Y")

st.subheader(f"📅 Hoje — {hoje_br}")

roteiros_hoje = carregar_roteiros_hoje()

if not roteiros_hoje:
    st.warning("Nenhum roteiro encontrado para hoje.")
else:
    col1, col2 = st.columns([3, 5])

    with col1:
        st.markdown("### 👤 Coordenador")
        for coord in sorted(roteiros_hoje.keys()):
            st.write(coord)

    with col2:
        st.markdown("### 🏬 Loja planejada")
        for loja in roteiros_hoje.values():
            st.write(loja)

st.divider()

st.markdown(
    """
### 🧭 Navegação
Use o menu lateral para acessar:
- 🗓️ **Roteiro** – Planejamento semanal
- ✅ **Checklist** – Execução em campo
"""
)
