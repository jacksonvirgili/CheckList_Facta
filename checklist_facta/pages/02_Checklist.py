# -*- coding: utf-8 -*-
import time
from io import BytesIO
from datetime import datetime
from zoneinfo import ZoneInfo

import streamlit as st
import gspread
from gspread.exceptions import APIError, WorksheetNotFound
from streamlit_js_eval import streamlit_js_eval
from google.oauth2.service_account import Credentials

# ReportLab - PDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

st.set_page_config(page_title="CheckList Gerencial Facta")

# =====================
# CONFIGURAÇÕES
# =====================

SHEET_ID = "11JaCc4y-htBW-cxbvbMBV28GHYlORbMM6345TSaXcgQ"
NOME_ABA = "Respostas"

scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# =====================
# GOOGLE SHEETS (credenciais)
# =====================

# Certifique-se de ter configurado st.secrets["gcp_service_account"] corretamente
service_account_info = dict(st.secrets["gcp_service_account"])

credentials = Credentials.from_service_account_info(
    service_account_info,
    scopes=scope
)
gc = gspread.authorize(credentials)

# =====================
# FUNÇÕES AUXILIARES (Sheets)
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
                time.sleep((2 ** i) + 0.2)  # backoff exponencial simples
                continue
            raise

# =====================
# FUNÇÃO PARA GERAR PDF (Resumo por Seção após Perguntas e Respostas)
# =====================

def gerar_pdf_checklist(
    agora, regional, coordenador, loja, supervisor,
    latitude, longitude, precisao,  # mantidos por compatibilidade
    perguntas, respostas
):
    """
    Gera um PDF em memória com:
    - Identificação (sem lat/long/precisão)
    - Link da localização logo abaixo da Identificação (se houver)
    - Resumo geral (Sim/Não/Total/% Sim)
    - Perguntas e Respostas (com quebra de linha)
    - Resumo por Seção (Sim/Não/Total/% Sim) -> POSICIONADO APÓS a tabela
    Retorna um BytesIO pronto para download.
    """
    buffer = BytesIO()

    # --- ReportLab imports locais ---
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors

    # ---- Documento e estilos ----
    left, right, top, bottom = 20*mm, 20*mm, 15*mm, 15*mm
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=left,
        rightMargin=right,
        topMargin=top,
        bottomMargin=bottom
    )

    styles = getSampleStyleSheet()
    styles.add(ParagraphStyle(name="Titulo", fontName="Helvetica-Bold", fontSize=16, leading=18, spaceAfter=8))
    styles.add(ParagraphStyle(name="SubTitulo", fontName="Helvetica-Bold", fontSize=12, leading=14, spaceBefore=10, spaceAfter=4))
    styles.add(ParagraphStyle(name="Normal10", fontName="Helvetica", fontSize=10, leading=12))
    styles.add(ParagraphStyle(name="Pergunta", fontName="Helvetica", fontSize=9, leading=11, spaceAfter=0, wordWrap="LTR"))

    elementos = []

    # Largura útil da página
    page_w, _ = A4
    content_w = page_w - left - right

    # -------------------------------
    # Cabeçalho e Identificação
    # -------------------------------
    elementos.append(Paragraph("Check-list de Acompanhamento", styles["Titulo"]))
    elementos.append(Paragraph("Identificação", styles["SubTitulo"]))

    # -> Removidos lat/long/precisão do quadro
    meta_data = [
        ["Data/Hora", agora],
        ["Regional", regional],
        ["Coordenador", coordenador],
        ["Loja", loja],
        ["Supervisor", supervisor],
    ]
    tabela_meta = Table(meta_data, colWidths=[40*mm, content_w - 40*mm], hAlign="LEFT")
    tabela_meta.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,0), (-1,-1), 10),
        ("ALIGN", (0,0), (-1,-1), "LEFT"),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("BACKGROUND", (0,0), (0,-1), colors.whitesmoke),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BOX", (0,0), (-1,-1), 0.5, colors.grey),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    elementos.append(tabela_meta)

    # Link de localização logo abaixo (se houver)
    if (latitude is not None) and (longitude is not None):
        url_map = f"https://www.google.com/maps?q={latitude},{longitude}"
        elementos.append(Spacer(1, 4))
        elementos.append(Paragraph(f"Localização: {url_map}", styles["Normal10"]))

    elementos.append(Spacer(1, 8))

    # -------------------------------
    # Normalização das respostas (para contar Sim/Não com robustez)
    # -------------------------------
    import unicodedata
    def normaliza(txt):
        if txt is None:
            return ""
        s = str(txt).strip().lower()
        s = "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")
        return s

    respostas_norm = [normaliza(r) for r in respostas]

    # -------------------------------
    # Resumo geral
    # -------------------------------
    total_perguntas = len(perguntas)
    total_sim = sum(1 for r in respostas_norm if r == "sim")
    total_nao = sum(1 for r in respostas_norm if r == "nao")
    perc_sim = (total_sim / total_perguntas) * 100 if total_perguntas else 0.0

    elementos.append(Paragraph("Resumo", styles["SubTitulo"]))
    elementos.append(Paragraph(
        f"Sim: {total_sim}  |  Não: {total_nao}  |  Total: {total_perguntas}  |  Sim: {perc_sim:.1f}%",
        styles["Normal10"]
    ))
    elementos.append(Spacer(1, 6))

    # -------------------------------
    # Perguntas e respostas (com wrap)
    # -------------------------------
    elementos.append(Paragraph("Perguntas e Respostas", styles["SubTitulo"]))

    num_w = 12*mm
    resp_w = 25*mm
    pergunta_w = content_w - (num_w + resp_w)

    # Cabeçalho
    linhas_qa = [
        [Paragraph("#", styles["Normal10"]),
         Paragraph("Pergunta", styles["Normal10"]),
         Paragraph("Resposta", styles["Normal10"])]
    ]

    # Linhas com as perguntas como Paragraph (wrap automático)
    for idx, (p, r) in enumerate(zip(perguntas, respostas), start=1):
        p_par = Paragraph(p, styles["Pergunta"])
        r_par = Paragraph(r, styles["Normal10"])
        linhas_qa.append([Paragraph(f"{idx:02d}", styles["Normal10"]), p_par, r_par])

    tabela_qa = Table(
        linhas_qa,
        colWidths=[num_w, pergunta_w, resp_w],
        repeatRows=1,      # repete cabeçalho em cada página
        splitByRow=1,      # permite quebrar linhas entre páginas
        hAlign="LEFT"
    )
    tabela_qa.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),

        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,1), (-1,-1), 9),

        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.whitesmoke, colors.white]),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BOX", (0,0), (-1,-1), 0.5, colors.grey),

        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))

    elementos.append(tabela_qa)
    elementos.append(Spacer(1, 8))

    # -------------------------------
    # Resumo por Seção (AGORA AQUI, APÓS A TABELA)
    # -------------------------------
    secoes = [
        ("AVALIAR", 1, 3),
        ("TREINAR", 4, 8),
        ("DOMÍNIO DE METODO POR PARTE DA EQUIPE", 9, 15),
        ("INCENTIVAR", 16, 18),
        ("VERIFICAR", 19, 21),
        ("ACOMPANHAR", 22, 25),
        ("ACOMPANHAMENTO - OPERAÇÃO", 26, 36),
        ("ACOMPANHAMENTO - ESTRUTURA", 37, 37),
    ]
    elementos.append(Paragraph("Resumo por Seção", styles["SubTitulo"]))

    linhas_sec = [["Seção", "Sim", "Não", "Total", "% Sim"]]
    for nome, ini, fim in secoes:
        sub_rsps = respostas_norm[ini-1:fim]  # slice 0-based
        tot = len(sub_rsps)
        sim = sum(1 for r in sub_rsps if r == "sim")
        nao = sum(1 for r in sub_rsps if r == "nao")
        pct = (sim / tot) * 100 if tot else 0.0
        linhas_sec.append([nome, f"{sim}", f"{nao}", f"{tot}", f"{pct:.1f}%"])

    col_sec_sim = 18*mm
    col_sec_nao = 18*mm
    col_sec_tot = 18*mm
    col_sec_pct = 18*mm
    col_sec_nome = content_w - (col_sec_sim + col_sec_nao + col_sec_tot + col_sec_pct)

    tabela_sec = Table(
        linhas_sec,
        colWidths=[col_sec_nome, col_sec_sim, col_sec_nao, col_sec_tot, col_sec_pct],
        hAlign="LEFT"
    )
    tabela_sec.setStyle(TableStyle([
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("FONTSIZE", (0,0), (-1,0), 10),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("TEXTCOLOR", (0,0), (-1,0), colors.black),
        ("ALIGN", (1,1), (-1,-1), "CENTER"),
        ("FONTNAME", (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE", (0,1), (-1,-1), 9),
        ("INNERGRID", (0,0), (-1,-1), 0.25, colors.grey),
        ("BOX", (0,0), (-1,-1), 0.5, colors.grey),
        ("LEFTPADDING", (0,0), (-1,-1), 4),
        ("RIGHTPADDING", (0,0), (-1,-1), 4),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]))
    elementos.append(tabela_sec)
    elementos.append(Spacer(1, 8))

    # Rodapé
    elementos.append(Paragraph("Documento gerado automaticamente pelo Check-list de Acompanhamento.", styles["Normal10"]))

    # Build
    doc.build(elementos)
    buffer.seek(0)
    return buffer

# =====================
# INTERFACE
# =====================

st.title("Check-list de Acompanhamento")
st.subheader("Identificação")

# Hierarquia
from utils import hierarquia, get_opcoes_hierarquia

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

supervisor = st.text_input("Supervisor de Loja")

st.divider()

# =====================
# VALIDAÇÃO DE LOCALIZAÇÃO
# =====================
# Key estável para não reexecutar a cada rerun sem necessidade
localizacao = streamlit_js_eval(
    js_expressions="""
    new Promise((resolve) => {
        if (!('geolocation' in navigator)) {
            resolve(null);
            return;
        }
        navigator.geolocation.getCurrentPosition(
            (pos) => resolve({
                latitude: pos.coords.latitude,
                longitude: pos.coords.longitude,
                accuracy: pos.coords.accuracy
            }),
            (err) => resolve({ error: err.code || true, message: err.message || 'erro' }),
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

# Mostra aviso se o navegador retornou erro
if isinstance(localizacao, dict) and localizacao.get("error"):
    st.warning(
        "Não foi possível obter a localização necessária. "
        "Antes de iniciar o preenchimento, habilite permissões de localização para este site e atualiza a página. \n\n"
        f"Detalhe técnico: {localizacao.get('message', 'sem detalhes')}"
    )

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

        # Títulos de seção (apenas visual)
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

    st.divider()

    confirmar_localizacao = st.checkbox(
        "Autorizo a captura da minha localização para envio do checklist"
    )

    enviar = st.form_submit_button("Enviar Checklist")

    # =====================
    # SALVAR NO GOOGLE SHEETS + GERAR PDF
    # =====================
    if enviar:

        # 🔒 Valida checkbox
        if not confirmar_localizacao:
            st.error("Você precisa autorizar a captura da localização para enviar.")
            st.stop()

        # 🔒 Valida captura real da localização
        if not localizacao or (isinstance(localizacao, dict) and localizacao.get("error")):
            st.error("Não foi possível capturar sua localização. Verifique as permissões do navegador e tente novamente.")
            st.stop()

        latitude = localizacao["latitude"]
        longitude = localizacao["longitude"]
        precisao = localizacao["accuracy"]

        if (
            regional == "Selecione"
            or coordenador == "Selecione"
            or loja == "Selecione"
            or not supervisor.strip()
        ):
            st.error("Preencha todos os campos obrigatórios antes de enviar.")
            st.stop()

        agora = datetime.now(ZoneInfo("America/Sao_Paulo")).strftime("%Y-%m-%d %H:%M:%S")

        linha = [
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

        # 🔐 Abre a planilha/aba só no envio (evita estourar cota de leitura)
        ws = get_worksheet(gc, SHEET_ID, NOME_ABA)
        append_with_retry(ws, linha)

        # ✅ Gera o PDF com try/except (se falhar, mostra o erro)
        pdf_bytes = None
        try:
            pdf_buffer = gerar_pdf_checklist(
                agora=agora,
                regional=regional,
                coordenador=coordenador,
                loja=loja,
                supervisor=supervisor,
                latitude=latitude,
                longitude=longitude,
                precisao=precisao,
                perguntas=perguntas,
                respostas=respostas
            )
            pdf_bytes = pdf_buffer.getvalue()
        except Exception as e:
            st.error("⚠️ Ocorreu um erro ao gerar o PDF.")
            st.exception(e)

        if pdf_bytes:
            st.session_state["pdf_bytes"] = pdf_bytes
            st.session_state["pdf_name"] = f"checklist_{agora.replace(':','-').replace(' ', '_')}.pdf"
            st.session_state["just_submitted"] = True
        else:
            st.session_state["pdf_bytes"] = None
            st.session_state["pdf_name"] = None
            st.session_state["just_submitted"] = False

# =====================
# FEEDBACK (SUCESSO + DOWNLOAD) FORA DO FORM — LOGO ABAIXO DO SUBMIT
# =====================
if st.session_state.get("pdf_bytes") and st.session_state.get("just_submitted"):
    # Colocando o feedback *depois* do bloco do form garante que apareça abaixo do submit
    st.success("Checklist enviado com sucesso ✅")
    # Espaçamento para destacar o botão
    st.markdown("<div style='height: 8px;'></div>", unsafe_allow_html=True)
    st.download_button(
        label="📄 Baixar PDF do checklist",
        data=st.session_state["pdf_bytes"],
        file_name=st.session_state.get("pdf_name", "checklist.pdf"),
        mime="application/pdf",
        key="download_pdf_together"
    )
    # Evita repetir a mensagem em interações futuras
    st.session_state["just_submitted"] = False
elif st.session_state.get("pdf_bytes"):
    # Opcional: manter um botão de último envio (sem mensagem)
    st.download_button(
        label="📄 Baixar PDF do checklist (último envio)",
        data=st.session_state["pdf_bytes"],
        file_name=st.session_state.get("pdf_name", "checklist.pdf"),
        mime="application/pdf",
        key="download_pdf_last"
    )

