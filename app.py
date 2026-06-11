
import streamlit as st
import gspread
import re
from gspread.exceptions import APIError, WorksheetNotFound
from streamlit_js_eval import streamlit_js_eval
from google.oauth2.service_account import Credentials


st.set_page_config(page_title="CheckList Gerencial Facta")

# =====================
# CONFIGURAÇÕES
# =====================


SHEET_ID = st.secrets["SHEET_ID"]
NOME_ABA = st.secrets["NOME_ABA"]


scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =====================
# GOOGLE SHEETS 
# =====================

service_account_info = dict(st.secrets["gcp_service_account"])

credentials = Credentials.from_service_account_info(
    service_account_info,
    scopes=scope
)
gc = gspread.authorize(credentials)

# =====================
# FUNÇÕES AUXILIARES 
# =====================

def get_worksheet(gc_client, sheet_id: str, tab_name: str):
    """
    Abre a planilha e retorna a worksheet (aba) desejada.
    Exibe mensagens amigáveis em caso de falha.
    """
    try:
        sh = gc_client.open_by_key(sheet_id)
    except APIError as e:
        code = getattr(getattr(e, "response", None), "status_code", None)
        detail = ""
        try:
            detail = e.response.json()
        except Exception:
            body = getattr(getattr(e, "response", None), "text", "")[:400]
            detail = f"status={code} body={body}"
        st.error(
            "❌ Erro ao abrir a planilha no Google Sheets.\n\n"
            "• Verifique se a Service Account tem acesso (Compartilhar como Editor)\n"
            "• Confirme se o SHEET_ID está correto\n"
            "• Garanta que as APIs Google Sheets e Google Drive estão habilitadas no projeto da credencial\n\n"
            f"Detalhes técnicos: {detail}"
        )
        st.stop()

    try:
        ws = sh.worksheet(tab_name)
    except WorksheetNotFound:
        st.error(f"❌ A aba '{tab_name}' não existe na planilha. Crie essa aba ou ajuste NOME_ABA.")
        st.stop()

    return ws


def append_with_retry(ws, row, retries: int = 4):
    """
    Faz append_row com tentativas (retry) e backoff exponencial
    em caso de erros transitórios como 429/500/503.
    """
    for i in range(retries):
        try:
            ws.append_row(row)
            return True
        except APIError as e:
            code = getattr(getattr(e, "response", None), "status_code", None)
            if code in (429, 500, 503) and i < retries - 1:
                time.sleep((2 ** i) + 0.2)  
                continue
            raise


def extrair_codigo_loja(loja_completa):
    """
    Extrai só o código da loja a partir da string completa.
    Ex: '1421 - LOJA ESTEIO - RS' -> '1421'
    Retorna como texto, para servir de chave de cruzamento com outras bases.
    """
    if not loja_completa or loja_completa == "Selecione":
        return ""
    # pega o que vem antes do primeiro ' - ' e limpa espaços
    return str(loja_completa).split(" - ")[0].strip()

    
  

   
# INTERFACE
# =====================

st.title("Check-list de Acompanhamento")
st.subheader("Identificação")

# =====================
# HIERARQUIA
# =====================

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
            "1487 - LOJA CAMPO BOM - RS",
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
            "61051 - LOJA ARARAUAMA - RJ",
            "61058 - LOJA SAO PEDRO DA ALDEIA - RJ",
        ],

    }
}

# ===== SELECTS FORA DO FORM =====
regional = st.selectbox(
    "Regional",
    options=["Selecione"] + list(hierarquia.keys())
)

coordenador = "Selecione"
loja = "Selecione"

if regional != "Selecione":
    coordenador = st.selectbox(
        "Coordenador",
        options=["Selecione"] + list(hierarquia[regional].keys())
    )

if coordenador != "Selecione":
    loja = st.selectbox(
        "Loja",
        options=["Selecione"] + hierarquia[regional][coordenador]
    )

# =====================
# SUPERVISOR DE LOJA
# Formata em maiúsculas enquanto a pessoa digita (on_change)
# e remove caracteres inválidos diretamente na entrada.
# =====================

def formatar_supervisor():
    valor = st.session_state.supervisor
    # remove tudo que não for letra ou espaço, e deixa em maiúsculas
    valor_limpo = re.sub(r"[^A-Za-zÀ-ÿ\s]", "", valor).upper()
    st.session_state.supervisor = valor_limpo

st.text_input(
    "Supervisor de Loja",
    key="supervisor",
    on_change=formatar_supervisor
)

# Variável usada no envio e no PDF (já limpa e em maiúsculas)
supervisor = st.session_state.get("supervisor", "").strip()

# Avisa só se faltar nome e sobrenome
if supervisor and len(supervisor.split()) < 2:
    st.warning("Informe nome e sobrenome do Supervisor de Loja.")

st.divider()


# =====================
# FORMULÁRIO
# =====================
st.subheader("Perguntas")

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

with st.form("checklist_form"):

    respostas = []

    for i, pergunta in enumerate(perguntas, start=1):

        # Títulos de seção 
        if i == 1:
            st.subheader("AVALIAR")
        elif i == 4:
            st.subheader("TREINAR")
        elif i == 9:
            st.subheader("DOMÍNIO DE METODO POR PARTE DA EQUIPE")
        elif i == 16:
            st.subheader("INCENTIVAR")
        elif i == 19:
            st.subheader("VERIFICAR")
        elif i == 22:
            st.subheader("ACOMPANHAR")
        elif i == 26:
            st.subheader("ACOMPANHAMENTO - OPERAÇÃO")
        elif i == 37:
            st.subheader("ACOMPANHAMENTO - ESTRUTURA")

        resposta = st.radio(
            pergunta,
            ["Sim", "Não"],
            horizontal=True,
            key=f"q{i}"
        )
        respostas.append(resposta)


    enviar = st.form_submit_button("Enviar Checklist")

    # =====================
    # SALVAR NO GOOGLE SHEETS + GERAR PDF
    # =====================
    if enviar:

        if (
            regional == "Selecione"
            or coordenador == "Selecione"
            or loja == "Selecione"
            or not supervisor.strip()
        ):
            st.error("Preencha todos os campos obrigatórios antes de enviar.")
            st.stop()

        # Exige nome e sobrenome do supervisor
        if len(supervisor.split()) < 2:
            st.error("O Supervisor de Loja deve conter nome e sobrenome.")
            st.stop()

        agora = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")

        # Extrai só o código da loja (ex: '1421 - LOJA ESTEIO - RS' -> '1421')
        codigo_loja = extrair_codigo_loja(loja)

        linha = [
            agora,
            regional,
            coordenador,
            loja,
            supervisor,
            latitude,
            longitude,
            precisao,
            *respostas,
            codigo_loja        # <-- nova coluna no FINAL (não desloca as existentes)
        ]

        #  Abre a planilha/aba só no envio 
        ws = get_worksheet(gc, SHEET_ID, NOME_ABA)
        append_with_retry(ws, linha)

     