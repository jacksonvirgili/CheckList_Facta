# -*- coding: utf-8 -*-
import time
from io import BytesIO
from datetime import datetime, timedelta, date as _date
from zoneinfo import ZoneInfo

import streamlit as st
import gspread
from gspread.exceptions import APIError, WorksheetNotFound
from streamlit_js_eval import streamlit_js_eval
from google.oauth2.service_account import Credentials

# =============================
# REPORTLAB (PDF)
# =============================
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# =============================
# CONFIG
# =============================
st.set_page_config(
    page_title="CheckList Gerencial Facta",
    layout="wide"
)

SHEET_ID = "11JaCc4y-htBW-cxbvbMBV28GHYlORbMM6345TSaXcgQ"
NOME_ABA = "Respostas"
NOME_ABA_ROTEIROS = "Roteiros"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

credentials = Credentials.from_service_account_info(
    dict(st.secrets["gcp_service_account"]),
    scopes=scope
)
gc = gspread.authorize(credentials)

# =============================
# GOOGLE SHEETS HELPERS
# =============================
def get_worksheet(gc_client, sheet_id: str, tab_name: str):
    try:
        sh = gc_client.open_by_key(sheet_id)
        return sh.worksheet(tab_name)
    except WorksheetNotFound:
        st.error(f"A aba '{tab_name}' não existe na planilha.")
        st.stop()

def append_with_retry(ws, row, retries: int = 4):
    for i in range(retries):
        try:
            ws.append_row(row)
            return True
        except APIError as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (429, 500, 503) and i < retries - 1:
                time.sleep((2 ** i) + 0.2)
            else:
                raise

def salvar_roteiro(gc, sheet_id, linha):
    ws = get_worksheet(gc, sheet_id, NOME_ABA_ROTEIROS)
    append_with_retry(ws, linha)

# =============================
# HIERARQUIA (COPIAR A SUA AQUI)
# =============================
hierarquia = {
    "MAYARA NOVAIS LOPES": {
        "ADRIELE FERNANDA VIEIRA DA SILVA": [
            "15002 - LOJA GOIANIA - GO",
            "17207 - LOJA SETOR CAMPINAS - GO",
            "15361 - LOJA SETOR GARAVELO - GO",
            "12200 - LOJA CAMPO GRANDE - MS",
            "19201 - LOJA CUIABA - MT",
            "24009 - LOJA PALMAS - TO",
        ],
        "THAINA MARCHI CONEJO": [
            "50550 - LOJA OSASCO - SP",
            "6000038 - LOJA ATIBAIA - SP",
            "54512 - LOJA JUNDIAI - SP",
            "6000034 - LOJA VALINHOS - SP",
            "600079 - LOJA FRANCO DA ROCHA - SP",
            "54465 - LOJA LIMEIRA - SP",
            "600045 - LOJA FRANCISCO MORATO - SP",
            "5502 - LOJA CAMPINAS - SP",
            "50850 - LOJA SUMARE - SP",
            "54467 - LOJA RIO CLARO - SP",
            "54444 - LOJA PIRACICABA - SP",
            
        ],
        "SILVANA DE FATIMA CENCI": [
            "600080 - LOJA MOGI DAS CRUZES - SP",
            "600081 - LOJA SAO PAULO - TATUAPE - SP",
            "600076 - LOJA DIADEMA - SP",
            "52012 - LOJA SAO BENTO - SP",
            "600075 - LOJA MAUA - SP",
            "600078 - LOJA SAO CAETANO - SP",
            "50400 - LOJA SAO VICENTE - SP",
            "600077 - LOJA SANTO ANDRE - SP",
            "50731 - LOJA SANTOS - SP",
            "5503 - LOJA PRAIA GRANDE - SP",
            "600085 - LOJA GUARUJA - SP",
            
        ],
        "NAYRA BASTOS DA SILVA": [
            "180007 - LOJA ANANINDEUA - PA",
            "17500 - LOJA BELEM - PA",
            "600098 - LOJA BRAGANCA - PA",
            "17514 - LOJA ICOARACI - PA",
            "22001 - LOJA MACAPA - AP",
        ],
        "KAICK FERNANDES PEIXOTO": [
            "25018 - LOJA JARU - RO",
            "25017 - LOJA JI PARANA - RO",
            "25021 - LOJA ARIQUEMES - RO",
            "25020 - LOJA VILHENA - RO",
            "25019 - LOJA PORTO VELHO - RO",
        ],
        "LUCIANE DA SILVA FONSECA PINHEIRO": [
            "13976 - LOJA ANJO DA GUARDA - MA",
            "12257 - LOJA JOAO PAULO - MA",
            "31381 - LOJA PACO DO LUMIAR - MA",
            "31388 - LOJA SAO JOSE DE RIBAMAR - MA",
            "13900 - LOJA SAO LUIS - MA",
            "20085 - LOJA TERESINA 2 - PI",
            "31382 - LOJA TIRIRICAL - MA",
            "13977 - LOJA BACABAL - MA",
        ],
        "ROSELY RAMALHO DA SILVA DIAS": [
            "96330 - LOJA MANAUS - ALVORADA - AM",
            "96329 - LOJA MANAUS - CHAPADA - AM",
            "96331 - LOJA MANAUS - CIDADE NOVA - AM",
            "96714 - LOJA MANAUS - COMPENSA - AM",
            "96328 - LOJA MANAUS - EDUCANDOS - AM",
            "96713 - LOJA MANAUS - SAO JOSE OPERARIO - AM ",
        ],
        "SILVANA PINTO CABRAL": [
            "600099 - LOJA MARABA - PA",
            "13980 - LOJA ACAILANDIA - MA",
            "13978 - LOJA IMPERATRIZ - MA",
            "24040 - LOJA ARAGUAINA - TO",
            "13979 - LOJA BARRA DO CORDA - MA",
            "13981 - LOJA BALSAS - MA",
        ],
    },

    "CINARA REGINA KEMERICH": {
        "ANA PICOLLI": [
            "2222 - LOJA BALNEARIO CAMBORIU - SC",
            "2913 - LOJA CHAPECO - SC",
            "2802 - LOJA FLORIANOPOLIS - SC",
            "200022 - LOJA ITAJAI - SC",
            "20959 - LOJA JOINVILLE - SC",
            "2918 - LOJA PALHOCA - SC",
            "2945 - LOJA SAO JOSE - SC",
            "200026 - LOJA BIGUACU - SC",
        ],
        "JULIE BARBOSA": [
            "20990 - LOJA ARARANGUA - SC",
            "20987 - LOJA CRICIUMA - SC",
            "2921 - LOJA LAGUNA - SC",
            "20989 - LOJA TUBARAO - SC",
            "1497 - LOJA TORRES - RS",
            "200025 - LOJA IMBITUBA - SC",
            "200027 - LOJA SOMBRIO - SC",
        ],
        "ANDREY COSTA DA ROCHA": [
            "54466 - LOJA MARILIA - SP",
            "50590 - LOJA SAO JOSE DO RIO PRETO - SP",
            "54468 - LOJA SAO CARLOS - SP",
            "54471 - LOJA OURINHOS - SP",
            "54464 - LOJA JAU - SP",
            "50499 - LOJA RIBEIRAO PRETO - SP",
            "50809 - LOJA ARARAQUARA - SP",
            "53556 - LOJA BAURU - SP",
        ],
        "JOAO GUALBERTO BRAZ JUNIOR": [
            "31174 - LOJA ALMIRANTE TAMANDARE - PR",
            "3802 - LOJA CURITIBA - PR",
            "3801 - LOJA FAZENDA RIO GRANDE - PR",
            "30110 - LOJA PARANAGUA - PR",
            "31220 - LOJA PONTA GROSSA - PR",
            "31175 - LOJA SAO JOSE DOS PINHAIS - PR",
            "31423 - LOJA ARAUCARIA - PR",
            "31425 - LOJA CAMPO LARGO - PR",
            "31424 - LOJA COLOMBO - PR",
            "31422 - LOJA PINHAIS - PR",
        ],
        "CARLOS VINICIUS TEIXEIRA FRANCA": [
            "31373 - LOJA CAMPO MOURAO - PR",
            "31276 - LOJA CASCAVEL - PR",
            "31226 - LOJA FOZ DO IGUACU - PR",
            "3817 - LOJA LONDRINA - PR",
            "3800 - LOJA MARINGA - PR",
            "3827 - LOJA MARINGA - ZONA 1 - PR 2",
            "31353 - LOJA TOLEDO - PR",
            "200020 - LOJA UMUARAMA - PR",
        ],
        "MIRIAM DE SALLES BARBIERI": [
            "6000033 - LOJA SAO ROQUE - SP",
            "6000036 - LOJA SAO MATEUS - SP",
            "600064 - LOJA SUZANO - SP",
            "50733 - LOJA SAO JOSE DOS CAMPOS - SP",
            "600057 - LOJA TAUBATE - SP",
            "5501 - LOJA SAO PAULO - ITAQUERA - SP",
            "50734 - LOJA GUARULHOS - SP",
            "5504 - LOJA ITAQUAQUECETUBA - SP",
            "6000040 - LOJA SAO MIGUEL - SP",
            "5506 - LOJA SAO PAULO - PENHA - SP",
        ],
    },

    "ADRIELE DA SILVA SOUZA": {
        "DANIELA DO CARMO CAMPARA": [
            "10331 - LOJA ERECHIM - RS",
            "10332 - LOJA CARAZINHO - RS",
            "19715 - LOJA CRUZ ALTA - RS",
            "19777 - LOJA PASSO FUNDO - RS",
            "10333 - LOJA PASSO FUNDO 2 - RS",
            "19890 - LOJA SOLEDADE - RS",
            "1407 - LOJA CACHOEIRA DO SUL - RS",
            "1449 - LOJA SANTA MARIA - RS",
        ],
        "FABIOLA DAL ROSSO": [
            "1423 - LOJA IJUI 1 - RS",
            "10650 - LOJA SANTA ROSA - RS",
            "19709 - LOJA SANTO ANGELO - RS",
            "10201 - LOJA ALEGRETE - RS",
            "10600 - LOJA ITAQUI - RS",
            "19710 - LOJA ROSARIO DO SUL - RS",
            "10604 - LOJA SANTIAGO - RS",
            "10897 - LOJA SAO BORJA - RS",
            "10330 - LOJA SAO GABRIEL - RS",
            "1485 - LOJA URUGUAIANA - RS",
        ],
        "JOSIANE DE SOUZA MONTEIRO DOS SANTOS": [
            "1500 - LOJA PORTO ALEGRE - ASSIS BRASIL - RS",
            "19778 - LOJA PORTO ALEGRE - VIGARIO - RS",
            "1427 - LOJA SANTO ANTONIO DA PATRULHA - RS",
            "1496 - LOJA TRAMANDAI - RS",
            "1434 - LOJA CACHOEIRINHA - RS",
            "1401 - LOJA PORTO ALEGRE - OSVALDO ARANHA I - RS",
            "1414 - LOJA VIAMAO - RS",
            "1525 - LOJA PORTO ALEGRE - OTTO NIEMEYER - RS",
            "601057 - LOJA PROTASIO ALVES - RS",
            "1404 - LOJA PORTO ALEGRE - RESTINGA - RS",
        ],
        "JIANINI MARIN": [
            "1416 - LOJA IGREJINHA - RS",
            "1424 - LOJA ROLANTE - RS",
            "1403 - LOJA SAPIRANGA - RS",
            "1420 - LOJA TAQUARA - RS",
            "19714 - LOJA TRES COROAS - RS",
            "1432 - LOJA GRAVATAI - RS",
            "1400 - LOJA PORTO ALEGRE - BORGES - RS",
            "1421 - LOJA ESTEIO - RS",
            "1417 - LOJA SAO LEOPOLDO - RS",
            "94390 - LOJA PORTO ALEGRE - MARECHAL - RS",
        ],
        "THAMIRES IZIDORO DO NASCIMENTO SILVA": [
            "1487 - LOJA CAMPO BOM - RS"
            "1402 - LOJA CANOAS - CENTRO - RS",
            "1458 - LOJA CANOAS - GUAJUVIRAS - RS",
            "1476 - LOJA NOVO HAMBURGO - RS",
            "10678 - LOJA NOVO HAMBURGO 2 - RS",
            "10627 - LOJA SAO LEOPOLDO II - RS",
            "1418 - LOJA SAPUCAIA DO SUL I - RS",
            "1419 - LOJA SAPUCAIA DO SUL II - RS",
            "1437 - LOJA MONTENEGRO - RS",
            "1439 - LOJA PORTAO - RS",
        ],
        "VIVIANE FAGUNDES DE MELLO": [
            "1405 - LOJA GUAIBA - RS",
            "1436 - LOJA CAMAQUA - RS",
            "1478 - LOJA PELOTAS - RS",
            "10200 - LOJA RIO GRANDE - RS",
            "1490 - LOJA SAO LOURENÇO - RS",
            "1422 - LOJA TAPES - RS",
        ],
        "MICHELE SANTOS": [
            "19701 - LOJA LAJEADO - RS",
            "19705 - LOJA VENANCIO AIRES - RS",
            "1435 - LOJA BUTIA - RS",
            "19901 - LOJA CHARQUEADAS - RS",
            "1409 - LOJA PORTO ALEGRE - AZENHA - RS",
            "10226 - LOJA SALGADO FILHO - RS",
            "1444 - LOJA SAO JERONIMO - RS",
            "1453 - LOJA BENTO GONCALVES - RS",
            "1443 - LOJA CAXIAS DO SUL - RS",
            "601055 - LOJA PORTO ALEGRE - CRISTOVAO COLOMBO - RS",
        ],
    },
    "CRISTIANE CARVALHO GEBELATTO": {
        "BRENO ROCHA HONORATO DA SILVA": [
            "9366 - LOJA CONJ CEARA - FORTALEZA - CE",
            "90900 - LOJA FORTALEZA - CE",
            "9370 - LOJA MESSEJANA - CE",
            "9368 - LOJA PARANGABA - CE",
            "97538 - LOJA MARACANAU - CE",
            "97616 - LOJA MARANGUAPE - CE",
            "97521 - LOJA CAUCAIA - CE",
            "97964 - LOJA ITAPIPOCA - CE",
            "97927 - LOJA SOBRAL - CE",
            "27894 - LOJA GUAIUBA - CE",
        ],
        "JESSICA ANDRADE DOS SANTOS": [
            "94438 - LOJA LAURO DE FREITAS - BA",
            "7763 - LOJA CANDEIAS - BA",
            "7758 - LOJA FEIRA DE SANTANA - BA",
            "7756 - LOJA SANTO ANTONIO DE JESUS - BA",
            "7760 - LOJA VALENCA - BA",
            "7768 - LOJA DIAS DAVILA - BA",
        ],
        "JOSE WELLINGTON DE SOUSA COSTA": [
            "49001 - LOJA ALMENARA - MG",
            "7752 - LOJA EUNAPOLIS - BA",
            "7751 - LOJA ILHEUS - BA",
            "7749 - LOJA ITABUNA - BA",
            "7750 - LOJA PORTO SEGURO - BA",
            "7753 - LOJA VITORIA DA CONQUISTA - BA",
            "7767 - LOJA DIVISOPOLIS - MG",
            "7769 - LOJA PEDRA AZUL - MG",
            "7770 - LOJA JEQUIE - BA",
        ],
        "LUANA SANTOS FURMANEK": [
            "7747 - LOJA CABULA - SALVADOR",
            "7800 - LOJA CAJAZEIRAS -  BA",
            "7748 - LOJA ITAPUÃ - SALVADOR",
            "7900 - LOJA SALVADOR - BA",
            "71002 - LOJA SALVADOR - COMERCIO",
            "7815 - LOJA SAO MARCOS - BA",
            "93826 - LOJA ARACAJU - SE",
            "23001 - LOJA MACEIO - AL",
            "7764 - LOJA CAMACARI - BA",
        ],
        "RUANA VIRGINIA DA SILVA SANTOS": [
            "97913 - LOJA JUAZEIRO DO NORTE - CE",
            "97926 - LOJA QUIXADA - CE",
            "97928 - LOJA QUIXERAMOBIM - CE",
            "98014 - LOJA CRATO - CE",
            "98970 - LOJA IGUATU - CE",
        ],
        "WHANDERSON MATHEUS ARAUJO DA COSTA": [
            "81006 - LOJA AFOGADOS - RECIFE",
            "18936 - LOJA BAYEUX - PB",
            "18105 - LOJA CAMPINA GRANDE - PB",
            "80969 - LOJA CARUARU - PE",
            "81075 - LOJA CRUZ DAS ARMAS - PB",
            "18900 - LOJA JOAO PESSOA - PB",
            "18937 - LOJA MANGABEIRA - PB",
            "14900 - LOJA NATAL - RN",
            "14932 - LOJA NATAL - CIDADE ALTA - RN",
            "9399 - LOJA RECIFE - PE",
            "96715 - LOJA SANTA RITA - PB",
        ],
    },
    "THAYSA SANDIM DE SOUZA": {
        "GISELLE MORAES SCHNEIDER": [
            "11303 - LOJA CARIACICA - ES",
            "11304 - LOJA GUARAPARI - ES",
            "9362 - LOJA LINHARES - ES",
            "9360 - LOJA SERRA - ES",
            "11950 - LOJA VILA VELHA - ES",
            "11900 - LOJA VITORIA - ES",
            "11962 - LOJA CACHOEIRO DE ITAPEMIRIM - ES",
            "11963 - LOJA LARANJEIRAS - ES",
        ],
        "JESSICA FERREIRA FIGUEIREDO": [
            "40325 - LOJA  JUIZ DE FORA - MG",
            "400013 - LOJA CATAGUASES - MG",
            "40324 - LOJA CONSELHEIRO LAFAIETE-MG",
            "400012 - LOJA MURIAE - MG",
            "400010 - LOJA SANTOS DUMONT - MG",
            "92760 - LOJA UBA - MG",
            "400011 - LOJA VIÇOSA - MG",
            "7761 - LOJA SAO JOAO DEL REI - MG",
            "7765 - LOJA BARBACENA - MG",
        ],
        "LOSANGELA HONORIO DE OLIVEIRA": [
            "6000031 - LOJA ANGRA DOS REIS - RJ",
            "61019 - LOJA BARRA DO PIRAI - RJ",
            "60495 - LOJA BARRA MANSA - RJ",
            "600046 - LOJA CRUZEIRO - SP",
            "600056 - LOJA GUARATINGUETA - SP",
            "600047 - LOJA LORENA - SP",
            "60498 - LOJA RESENDE - RJ",
            "60007 - LOJA VOLTA REDONDA - RJ",
            "60494 - LOJA VOLTA REDONDA II - RJ",
            "61050 - LOJA TRES RIOS - RJ",
        ],
        "MARILIA GABRIELA LOPES FARIA": [
            "60099 - LOJA BANGU - RJ",
            "61045 - LOJA CAMPO GRANDE - RJ",
            "60501 - LOJA MADUREIRA - RJ",
            "60502 - LOJA MEIER - RJ",
            "61061 - LOJA NILOPOLIS - RJ",
            "61064 - LOJA MESQUITA - RJ",
            "61060 - LOJA SAO JOAO DE MERITI - RJ",
        ],
        "MARIA EDUARDA DELGADO MENESES": [
            "60503 - LOJA DUQUE DE CAXIAS - RJ",
            "60500 - LOJA NITEROI - RJ",
            "60507 - LOJA NOVA IGUAÇU - RJ",
            "60900 - LOJA RIO DE JANEIRO - RJ",
            "61049 - LOJA SAO GONCALO - RJ",
            "61057 - LOJA ITABORAI - RJ",
        ],
        "RENATO SOUZA DO ESPIRITO SANTO LANGA": [
            "4900 - LOJA BELO HORIZONTE - MG",
            "45034 - LOJA CONTAGEM - MG",
            "45018 - LOJA SANTA LUZIA - MG",
            "7754 - LOJA BETIM - MG",
            "7759 - LOJA BELO HORIZONTE - BARRO PRETO - MG",
            "7755 - LOJA BELO HORIZONTE - BETANIA - MG",
            "7757 - LOJA BELO HORIZONTE - VENDA NOVA - MG",
        ],
        "YASMIM APARECIDA DOS ANJOS PARANHOS": [
            "61056 - LOJA MACAE - RJ",
            "61054 - LOJA RIO DAS OSTRAS - RJ",
            "61055 - LOJA SAQUAREMA - RJ",
            "61053 - LOJA CABO FRIO - RJ",
            "61052 - LOJA CAMPO DOS GOYTACAZES 1 - RJ",
            "61051 - LOJA ARARUAMA - RJ",
            "61058 - LOJA SAO PEDRO DA ALDEIA - RJ",
        ],

    }
}

def get_opcoes_hierarquia(hierarquia, regional, coordenador):
    regionais = ["Selecione"] + list(hierarquia.keys())

    coordenadores = ["Selecione"]
    lojas = ["Selecione"]

    if regional in hierarquia:
        coordenadores += list(hierarquia[regional].keys())

    if regional in hierarquia and coordenador in hierarquia[regional]:
        lojas += hierarquia[regional][coordenador]

    return regionais, coordenadores, lojas

# =============================
# PDF
# =============================
def gerar_pdf_checklist(
    agora, regional, coordenador, loja, supervisor,
    latitude, longitude, precisao,
    perguntas, respostas
):
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20*mm,
        rightMargin=20*mm,
        topMargin=15*mm,
        bottomMargin=15*mm,
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Titulo", fontSize=16, leading=18, spaceAfter=8, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="SubTitulo", fontSize=12, leading=14, spaceBefore=10, spaceAfter=4, fontName="Helvetica-Bold"))
    styles.add(ParagraphStyle(name="Normal10", fontSize=10, leading=12))
    styles.add(ParagraphStyle(name="Pergunta", fontSize=9, leading=11))

    elementos = []

    elementos.append(Paragraph("Check-list de Acompanhamento", styles["Titulo"]))
    elementos.append(Paragraph("Identificação", styles["SubTitulo"]))

    meta = [
        ["Data/Hora", agora],
        ["Regional", regional],
        ["Coordenador", coordenador],
        ["Loja", loja],
        ["Supervisor", supervisor],
    ]

    tabela_meta = Table(meta, colWidths=[40*mm, A4[0]-80*mm])
    tabela_meta.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.5, colors.grey),
        ("BACKGROUND", (0,0), (0,-1), colors.whitesmoke),
    ]))
    elementos.append(tabela_meta)

    if latitude and longitude:
        elementos.append(Spacer(1, 6))
        elementos.append(
            Paragraph(
                f"Localização: https://www.google.com/maps?q={latitude},{longitude}",
                styles["Normal10"]
            )
        )

    elementos.append(Spacer(1, 10))
    elementos.append(Paragraph("Perguntas e Respostas", styles["SubTitulo"]))

    dados = [["#", "Pergunta", "Resposta"]]
    for i, (p, r) in enumerate(zip(perguntas, respostas), start=1):
        dados.append([f"{i:02d}", p, r])

    tabela = Table(dados, colWidths=[15*mm, None, 30*mm], repeatRows=1)
    tabela.setStyle(TableStyle([
        ("GRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
    ]))
    elementos.append(tabela)

    doc.build(elementos)
    buffer.seek(0)
    return buffer

# =============================
# UI
# =============================
st.title("Check-list de Acompanhamento")
tab_roteiro, tab_checklist = st.tabs(["🗓️ Roteiro", "✅ Checklist"])

# ======================================================
# 🗓️ TAB ROTEIRO (COM LAYOUT DE CALENDÁRIO EM CARDS)
# ======================================================
with tab_roteiro:
    st.subheader("Roteiro Semanal de Visitas")

    # =========================
    # FUNÇÕES AUXILIARES
    # =========================
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

    def carregar_roteiros():
        try:
            ws = get_worksheet(gc, SHEET_ID, NOME_ABA_ROTEIROS)
            dados = ws.get_all_records()
            mapa = {}
            for r in dados:
                data = r.get("DATA")
                if data:
                    mapa[data] = {
                        "loja": r.get("LOJA", "Selecione"),
                        "obs": r.get("OBS", "")
                    }
            return mapa
        except Exception:
            return {}

    # =========================
    # ESTADO
    # =========================
    if "rot_agendamentos" not in st.session_state:
        st.session_state["rot_agendamentos"] = carregar_roteiros()

    # =========================
    # HIERARQUIA
    # =========================
    regionais, _, _ = get_opcoes_hierarquia(hierarquia, "Selecione", "Selecione")
    regional_r = st.selectbox("Regional", regionais, key="rot_regional")

    _, coordenadores, _ = get_opcoes_hierarquia(hierarquia, regional_r, "Selecione")
    coordenador_r = st.selectbox("Coordenador", coordenadores, key="rot_coordenador")

    _, _, lojas_da_coord = get_opcoes_hierarquia(
        hierarquia, regional_r, coordenador_r
    )
    lojas_opcoes = [l for l in lojas_da_coord if l != "Selecione"]

    if coordenador_r == "Selecione":
        st.info("Selecione **Regional** e **Coordenador** para visualizar a agenda.")
    else:

    # =========================
    # SEMANA
    # =========================
        hoje = datetime.now(ZoneInfo("America/Sao_Paulo")).date()
    
        if "rot_week_start" not in st.session_state:
            st.session_state["rot_week_start"] = proximo_domingo(hoje)
    
        week_start = st.session_state["rot_week_start"]
        week_days = [week_start + timedelta(days=i) for i in range(7)]
    
        st.markdown(
            f"**Semana de {week_start.strftime('%d/%m/%Y')} até "
            f"{(week_start + timedelta(days=6)).strftime('%d/%m/%Y')}**"
        )
    
        # =========================
        # FERIADOS
        # =========================
        feriados_map = feriados_br(week_start.year)
        if (week_start + timedelta(days=6)).year != week_start.year:
            feriados_map.update(
                feriados_br((week_start + timedelta(days=6)).year)
            )
    
        # =========================
        # CALENDÁRIO (SEU LAYOUT)
        # =========================
        cols_days = st.columns(7)
        weekday_labels = ["Dom", "Seg", "Ter", "Qua", "Qui", "Sex", "Sáb"]
    
        for i, dia in enumerate(week_days):
            box = cols_days[i]
            dia_iso = dia.strftime("%Y-%m-%d")
            dia_label = weekday_labels[i]
    
            is_weekend = i in (0, 6)
            is_feriado = dia in feriados_map
            bloqueado = is_weekend or is_feriado
    
            agendamento = st.session_state["rot_agendamentos"].get(dia_iso, {})
            loja_valor = agendamento.get("loja", "Selecione")
            obs_valor = agendamento.get("obs", "")
    
            border_color = "#F2A6A6" if bloqueado else "#DDD"
            bg_color = "#FFF5F5" if bloqueado else "#FFFFFF"
            text_color = "#C62828" if bloqueado else "#0A0A0A"
    
            box.markdown(
                f"""
                <div style="
                    border:1.5px solid {border_color};
                    background:{bg_color};
                    border-radius:12px;
                    padding:10px;
                    min-height:190px;
                ">
                    <div style="
                        text-align:center;
                        font-weight:600;
                        font-size:13px;
                        margin-bottom:8px;
                        color:{text_color};
                    ">
                        {dia_label} • {dia.strftime('%d/%m')}
                    </div>
                """,
                unsafe_allow_html=True,
            )
    
            if bloqueado:
                if is_feriado:
                    box.markdown(
                        f"<div style='font-size:11px;color:#C62828'>{feriados_map[dia]}</div>",
                        unsafe_allow_html=True,
                    )
                else:
                    box.markdown(
                        "<div style='font-size:11px;color:#C62828'>Fim de semana</div>",
                        unsafe_allow_html=True,
                    )
            else:
                opcoes = ["Selecione"] + lojas_opcoes
                index = opcoes.index(loja_valor) if loja_valor in opcoes else 0
    
                loja_escolhida = box.selectbox(
                    "Loja",
                    opcoes,
                    index=index,
                    key=f"loja_{dia_iso}",
                    label_visibility="collapsed",
                )
    
                obs = box.text_area(
                    "Obs",
                    value=obs_valor,
                    key=f"obs_{dia_iso}",
                    height=60,
                    label_visibility="collapsed",
                )
    
                if loja_escolhida != "Selecione":
                    if box.button("Agendar", key=f"ag_{dia_iso}"):
                        linha = [
                            regional_r,
                            coordenador_r,
                            loja_escolhida,
                            "",
                            dia_iso,
                            obs,
                        ]
                        salvar_roteiro(gc, SHEET_ID, linha)
                        st.session_state["rot_agendamentos"][dia_iso] = {
                            "loja": loja_escolhida,
                            "obs": obs,
                        }
                        st.success("Agendado ✅")
                        time.sleep(0.5)
                        st.rerun()
                else:
                    box.button("Agendar", disabled=True, key=f"ag_dis_{dia_iso}")
    
            box.markdown("</div>", unsafe_allow_html=True)
    
        # =========================
        # NAVEGAÇÃO
        # =========================
        st.markdown("<br>", unsafe_allow_html=True)
    
        nav = st.columns([1, 2, 1])[1]
        c1, c2 = nav.columns(2)
    
        with c1:
            if st.button("◀️ Semana anterior"):
                st.session_state["rot_week_start"] -= timedelta(days=7)
                st.rerun()
    
        with c2:
            if st.button("Próxima semana ▶️"):
                st.session_state["rot_week_start"] += timedelta(days=7)
                st.rerun()

# ======================================================
# ✅ TAB CHECKLIST (INALTERADO)
# ======================================================
with tab_checklist:

    st.subheader("Identificação")

    # =====================
    # SELETORES
    # =====================
    regional = st.selectbox(
        "Regional",
        ["Selecione"] + list(hierarquia.keys()),
        key="chk_regional"
    )

    coordenador = "Selecione"
    loja = "Selecione"

    if regional != "Selecione":
        coordenador = st.selectbox(
            "Coordenador",
            ["Selecione"] + list(hierarquia[regional].keys()),
            key="chk_coordenador"
        )

    if coordenador != "Selecione":
        loja = st.selectbox(
            "Loja",
            ["Selecione"] + hierarquia[regional][coordenador],
            key="chk_loja"
        )

    supervisor = st.text_input(
        "Supervisor de Loja",
        key="chk_supervisor"
    )

    st.divider()

    # =====================
    # LOCALIZAÇÃO (ROBUSTA)
    # =====================
    if "localizacao" not in st.session_state:
        st.session_state["localizacao"] = streamlit_js_eval(
            js_expressions="""
            new Promise((resolve) => {
                if (!navigator.geolocation) {
                    resolve({ error: true, message: "Geolocalização não suportada" });
                    return;
                }

                navigator.geolocation.getCurrentPosition(
                    (pos) => resolve({
                        latitude: pos.coords.latitude,
                        longitude: pos.coords.longitude,
                        accuracy: pos.coords.accuracy
                    }),
                    (err) => resolve({
                        error: true,
                        message: err.message || "Erro ao obter localização"
                    }),
                    {
                        enableHighAccuracy: true,
                        timeout: 12000,
                        maximumAge: 0
                    }
                );
            })
            """,
            key="get_location_once"
        )

    localizacao = st.session_state["localizacao"]

    if isinstance(localizacao, dict) and localizacao.get("error"):
        st.warning(
            "⚠️ Não foi possível capturar a localização automaticamente. "
            "Verifique as permissões do navegador."
        )

    # =====================
    # PERGUNTAS
    # =====================
    perguntas = [
        "01. Analisa os indicadores quantitativos diariamente D-1 e INTRADAY e Registra e compartilha os resultados com o consultor?",
        "02. Aplica o CLAV semanalmente com base em evidências",
        "03. Aplica e mantem atualizado o diagnóstico do colaborador, usando as informações de maneira estratégica",
        "04. Realiza microtreinamentos com a equipe",
        "05. Está presente corrigindo execuções em tempo real",
        "06. Utiliza o Teatro de Vendas e Aplica dinâmicas rápidas e criativas durante o dia",
        "07. Aplica Feedback SAR com frequência",
        "08. Supervisor consegue ser claro quanto as evidências de aplicação que serão verificadas nos próximos atendimentos/dias.",
        "09. A equipe domina técnica de pesquisa (perguntas abertas e SPIN)",
        "10. A equipe sabe destacar vantagens e benefícios dos produtos comercializados",
        "11. A equipe sabe destacar as vantagens e benefícios da empresa para o cliente",
        "12. A equipe em loja possui total domínio nas técnicas de neutralização de objeções e as utilizam quando necessária nos atendimentos",
        "13. A equipe em loja tem habilidade necessária para realizar o cross de todos os produtos para cada cliente.",
        "14. Os Consultores pedem indicação ao final do atendimento",
        "15. Os Consultores seguem os passos da jornada",
        "16. Reconhece avanços da equipe",
        "17. Utiliza linguagem positiva e motivadora",
        "18. Supervisor conhece sonhos e objetivos de cada colaborador",
        "19. Acompanha indicadores técnicos semanalmente (ATIVA)",
        "20. Analisa comportamento da equipe com base em dados (CLAV e Observação Direta)",
        "21. Garante que o que foi treinado esteja sendo aplicado através da observação de evidências de aplicação.",
        "22. Faz reuniões 1:1 com os consultores semanalmente",
        "23. Atualiza e utiliza o PDI individual customizando as ações de treinamento em loja",
        "24. Supervisor tem ciência de todas as pendências de contrato, e propostas negadas",
        "25. Consultores sabem sua meta diária, acumulado, tkm, etc e sabem a importância destes números",
        "26. O Supervisor de Loja possui de forma clara e objetiva o controle da informação de agendamentos",
        "27. A equipe na loja conhece e domina todos os campos e funcionalidades de todos os sistemas operacionais?",
        "28. A equipe da loja possui boa apresentação pessoal, de acordo com as políticas e normas de conduta da empresa",
        "29. O Supervisor de Loja organiza e acompanha diariamente o rodízio de acionamentos de sua equipe?",
        "30. O Supervisor de Loja tem acompanhado os comunicados internos, lendo entendendo, repassando e orientando sua equipe, garantindo entendimento e a execução imediata?",
        "31. O Supervisor acompanha e trata o não pagamento da 1ª parcela débito.",
        "32. O Supervisor atua diariamente sobre os saldos de portabilidade - aprovando, cancelando e analisando os motivos dos saldos cancelados.",
        "33. O Supervisor de Loja conhece a particularidade de sua carteira de clientes de FF, como potencial, população da cidade e carteira de cliente ativos e inativos por produto?",
        "34. Supervisor faz a gestão e controle das horas extras diariamente?",
        "35. A equipe mantém assiduidade em loja (pontualidade e frequência).",
        "36. Todos os chamados necessários para reparo, manutenção, infraestrutura, etc... estão abertos e aguardando solução."
    ]

    # =====================
    # FORMULÁRIO
    # =====================
    with st.form("checklist_form"):
        respostas = []

        for i, p in enumerate(perguntas):
            respostas.append(
                st.radio(
                    p,
                    ["Sim", "Não"],
                    horizontal=True,
                    key=f"q{i}"
                )
            )

        confirmar = st.checkbox(
            "Autorizo a captura da minha localização para envio do checklist"
        )

        enviar = st.form_submit_button("Enviar Checklist")

        if enviar:

            # 🔒 Valida autorização
            if not confirmar:
                st.error("Você precisa autorizar a captura da localização.")
                st.stop()

            # 🔒 Valida localização capturada
            if not isinstance(localizacao, dict) or localizacao.get("error"):
                st.error(
                    "Não foi possível capturar sua localização. "
                    "Atualize a página e verifique as permissões do navegador."
                )
                st.stop()

            latitude = localizacao["latitude"]
            longitude = localizacao["longitude"]
            precisao = localizacao["accuracy"]

            agora = datetime.now(
                ZoneInfo("America/Sao_Paulo")
            ).strftime("%Y-%m-%d %H:%M:%S")

            ws = get_worksheet(gc, SHEET_ID, NOME_ABA)
            append_with_retry(
                ws,
                [
                    agora,
                    regional,
                    coordenador,
                    loja,
                    supervisor,
                    latitude,
                    longitude,
                    precisao,
                    *respostas
                ]
            )

            pdf = gerar_pdf_checklist(
                agora,
                regional,
                coordenador,
                loja,
                supervisor,
                latitude,
                longitude,
                precisao,
                perguntas,
                respostas
            )

            st.success("Checklist enviado com sucesso ✅")
            st.download_button(
                "📄 Baixar PDF do checklist",
                data=pdf.getvalue(),
                file_name=f"checklist_{agora.replace(':','-').replace(' ','_')}.pdf",
                mime="application/pdf"
            )
