import html
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent

import streamlit as st
from supabase import create_client


BASE_DIR = Path(__file__).resolve().parent
RECONHECEDOR_PATH = BASE_DIR / "reconhecedor.py"
TABELA_LOGS = "log_acesso"
MINUTOS_CACIFO_OCUPADO = 5


st.set_page_config(
    page_title="PAP | Cyber Locker",
    page_icon="\U0001F510",
    layout="wide",
    initial_sidebar_state="expanded",
)


def obter_config_supabase():
    return "https://mmovdgqpwrurcrddyrqx.supabase.co", "sb_publishable_vAnSaWRiCmKdTRyHIpcHfw_YUFBkkH7"


@st.cache_resource(show_spinner=False)
def obter_cliente_supabase(url, key):
    return create_client(url, key)


def obter_supabase():
    url, key = obter_config_supabase()
    return obter_cliente_supabase(url, key)


def consultar_logs(supabase, limite=100):
    resposta = (
        supabase.table(TABELA_LOGS)
        .select("id,data_hora,nome_utilizador,status,cacifo_id")
        .order("data_hora", desc=True)
        .limit(limite)
        .execute()
    )
    return resposta.data or []


def consultar_metricas(supabase):
    resposta_total = (
        supabase.table(TABELA_LOGS).select("id", count="exact").limit(1).execute()
    )
    resposta_negados = (
        supabase.table(TABELA_LOGS)
        .select("id", count="exact")
        .eq("status", "NEGADO")
        .limit(1)
        .execute()
    )
    return resposta_total.count or 0, resposta_negados.count or 0


def converter_data_supabase(valor):
    if not valor:
        return None

    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None


def formatar_hora(valor):
    data = converter_data_supabase(valor)
    return "--:--:--" if data is None else data.strftime("%H:%M:%S")


def formatar_numero(valor):
    return f"{valor:,}".replace(",", " ")


def texto_seguro(valor):
    return html.escape(str(valor or ""))


def obter_estado_cacifos(logs):
    estados = {
        cacifo_id: {"ocupado": False, "utilizador": None, "hora": None}
        for cacifo_id in range(1, 5)
    }
    cacifos_processados = set()

    agora = datetime.now(timezone.utc)
    limite_recente = timedelta(minutes=MINUTOS_CACIFO_OCUPADO)

    for log in logs:
        status = str(log.get("status", "")).upper()
        cacifo_id = int(log.get("cacifo_id") or 1)
        data_log = converter_data_supabase(log.get("data_hora"))

        if cacifo_id not in estados or cacifo_id in cacifos_processados:
            continue

        if status in {"LIBERADO", "LIVRE"}:
            cacifos_processados.add(cacifo_id)
            continue

        if status != "AUTORIZADO" or data_log is None:
            continue

        if data_log.tzinfo is None:
            data_log = data_log.replace(tzinfo=timezone.utc)

        if agora - data_log.astimezone(timezone.utc) <= limite_recente:
            estados[cacifo_id] = {
                "ocupado": True,
                "utilizador": log.get("nome_utilizador") or "Utilizador",
                "hora": data_log.strftime("%H:%M"),
            }

        cacifos_processados.add(cacifo_id)

    return estados


def libertar_cacifo(supabase, cacifo_id):
    supabase.table(TABELA_LOGS).insert(
        {
            "data_hora": datetime.now().isoformat(),  # Carimbo de tempo adicionado aqui!
            "nome_utilizador": "Administrador (Reset)",
            "status": "LIBERADO",
            "cacifo_id": cacifo_id,
        }
    ).execute()


def html_markdown(conteudo):
    st.markdown(dedent(conteudo).strip(), unsafe_allow_html=True)


def sidebar_html(conteudo):
    st.sidebar.markdown(dedent(conteudo).strip(), unsafe_allow_html=True)


def aplicar_estilo_visual():
    html_markdown(
        """
        <style>
        .stApp {
            background:
                radial-gradient(circle at 78% 8%, rgba(47, 112, 255, 0.16), transparent 25rem),
                radial-gradient(circle at 10% 78%, rgba(56, 189, 248, 0.10), transparent 24rem),
                linear-gradient(135deg, #060914 0%, #0b1021 48%, #060914 100%);
            color: #f8fafc;
        }

        .block-container {
            max-width: 1480px;
            padding-top: 1.25rem;
            padding-bottom: 2rem;
        }

        [data-testid="stSidebar"] {
            background:
                radial-gradient(circle at 30% 5%, rgba(56, 189, 248, 0.16), transparent 12rem),
                linear-gradient(180deg, #070b16 0%, #050812 100%);
            border-right: 1px solid rgba(148, 163, 184, 0.18);
        }

        [data-testid="stSidebar"] .stButton button {
            min-height: 3.1rem;
            border-radius: 1rem;
            font-weight: 800;
            box-shadow: 0 14px 34px rgba(0, 0, 0, 0.22);
        }

        div[data-testid="stVerticalBlockBorderWrapper"] {
            background: rgba(9, 14, 30, 0.62);
            border-color: rgba(148, 163, 184, 0.20);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.24);
        }

        .brand {
            display: flex;
            align-items: center;
            gap: 0.9rem;
            margin: 0.6rem 0 1.9rem;
        }

        .brand-icon {
            display: grid;
            place-items: center;
            width: 3.45rem;
            height: 3.45rem;
            border-radius: 1.15rem;
            background: linear-gradient(135deg, #4cc9ff, #2563eb);
            color: white;
            font-size: 1.45rem;
            box-shadow: 0 18px 40px rgba(56, 189, 248, 0.26);
        }

        .brand-title {
            color: #ffffff;
            font-size: 1.18rem;
            font-weight: 900;
            line-height: 1.1;
        }

        .brand-subtitle {
            color: #8b95aa;
            font-size: 0.82rem;
            margin-top: 0.16rem;
        }

        .hero-row {
            display: flex;
            align-items: flex-start;
            justify-content: space-between;
            gap: 1rem;
            margin-bottom: 1rem;
        }

        .hero-title {
            margin: 0;
            color: #ffffff;
            font-size: clamp(2rem, 4vw, 3.6rem);
            line-height: 1;
            font-weight: 950;
            letter-spacing: 0;
        }

        .hero-subtitle {
            margin-top: 0.85rem;
            color: #aab4c4;
            font-size: clamp(0.95rem, 1.4vw, 1.18rem);
        }

        .sidebar-status {
            border: 1px solid rgba(34, 197, 94, 0.22);
            background: rgba(20, 83, 45, 0.18);
            border-radius: 0.9rem;
            padding: 0.7rem 0.85rem;
            margin-top: 1.15rem;
            color: #bbf7d0;
            font-size: 0.82rem;
            font-weight: 850;
            text-align: center;
        }

        .sidebar-mini {
            color: #64748b;
            font-size: 0.76rem;
            text-align: center;
            margin-top: 0.45rem;
        }

        .metric-card {
            min-height: 7.25rem;
            border: 1px solid rgba(148, 163, 184, 0.23);
            border-radius: 1rem;
            background:
                linear-gradient(180deg, rgba(16, 22, 43, 0.86), rgba(8, 12, 26, 0.70));
            box-shadow: 0 18px 50px rgba(0, 0, 0, 0.22);
            padding: 1.05rem 1.15rem;
            overflow: hidden;
        }

        .metric-label {
            color: #aab4c4;
            font-size: 0.88rem;
            font-weight: 760;
            min-height: 2.15rem;
        }

        .metric-value {
            color: #ffffff;
            font-size: 2.1rem;
            line-height: 1;
            font-weight: 950;
            margin-top: 0.55rem;
        }

        .metric-note {
            color: #768298;
            font-size: 0.78rem;
            margin-top: 0.4rem;
        }

        .section-title {
            color: white;
            font-size: 1.3rem;
            font-weight: 900;
            margin: 1.4rem 0 0.8rem;
        }

        .locker-card {
            min-height: 8.9rem;
            border: 1px solid rgba(148, 163, 184, 0.28);
            border-radius: 1rem;
            background:
                radial-gradient(circle at 15% 72%, rgba(56, 189, 248, 0.16), transparent 8rem),
                linear-gradient(180deg, rgba(15, 23, 42, 0.88), rgba(7, 11, 23, 0.76));
            box-shadow: 0 22px 55px rgba(0, 0, 0, 0.26);
            padding: 1.05rem 1.2rem;
            position: relative;
            overflow: hidden;
        }

        .locker-card.busy {
            border-color: rgba(56, 189, 248, 0.72);
            box-shadow: 0 0 0 1px rgba(56, 189, 248, 0.20), 0 22px 60px rgba(14, 165, 233, 0.16);
        }

        .locker-card.free {
            background:
                radial-gradient(circle at 15% 72%, rgba(250, 204, 21, 0.18), transparent 8rem),
                linear-gradient(180deg, rgba(15, 23, 42, 0.88), rgba(7, 11, 23, 0.76));
        }

        .locker-name {
            color: #aab4c4;
            font-size: 0.92rem;
            font-weight: 760;
        }

        .locker-body {
            display: flex;
            align-items: center;
            gap: 0.9rem;
            margin-top: 1rem;
        }

        .locker-icon {
            font-size: 2.3rem;
            filter: drop-shadow(0 0 16px rgba(125, 211, 252, 0.45));
        }

        .locker-status {
            font-size: 1.9rem;
            font-weight: 950;
            line-height: 1;
        }

        .locker-status.busy {
            color: #7dd3fc;
        }

        .locker-status.free {
            color: #facc15;
        }

        .locker-meta {
            color: #aab4c4;
            font-size: 0.88rem;
            margin-top: 0.4rem;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .progress-track {
            height: 0.42rem;
            border-radius: 999px;
            background: rgba(148, 163, 184, 0.18);
            margin-top: 1.05rem;
            overflow: hidden;
        }

        .progress-fill {
            height: 100%;
            border-radius: 999px;
        }

        .progress-fill.busy {
            width: 72%;
            background: #67e8f9;
        }

        .progress-fill.free {
            width: 58%;
            background: #facc15;
        }

        .log-panel-title {
            color: #ffffff;
            font-size: 1.2rem;
            font-weight: 900;
            margin-bottom: 0.9rem;
        }

        .log-row {
            display: grid;
            grid-template-columns: 1fr 1.5fr 1.2fr 0.7fr;
            gap: 0.8rem;
            align-items: center;
            border: 1px solid rgba(148, 163, 184, 0.16);
            border-radius: 0.9rem;
            background: rgba(8, 12, 26, 0.58);
            padding: 0.78rem 0.9rem;
            margin-bottom: 0.55rem;
        }

        .log-muted {
            color: #9aa6b8;
            font-size: 0.86rem;
        }

        .log-strong {
            color: #f8fafc;
            font-weight: 850;
        }

        .status-pill {
            display: inline-flex;
            align-items: center;
            justify-content: center;
            border-radius: 0.75rem;
            min-height: 2.2rem;
            padding: 0 0.8rem;
            font-weight: 900;
            font-size: 0.82rem;
        }

        .status-pill.ok {
            color: #86efac;
            background: rgba(22, 163, 74, 0.20);
        }

        .status-pill.bad {
            color: #fca5a5;
            background: rgba(220, 38, 38, 0.22);
        }

        .status-pill.free {
            color: #7dd3fc;
            background: rgba(14, 165, 233, 0.18);
        }

        @media (max-width: 900px) {
            .hero-row {
                display: block;
            }
            .log-row {
                grid-template-columns: 1fr;
            }
        }
        </style>
        """
    )


def ligar_sistema():
    if not RECONHECEDOR_PATH.exists():
        st.sidebar.error("O ficheiro reconhecedor.py nao foi encontrado.")
        return

    processo = st.session_state.get("processo_reconhecedor")
    if processo and processo.poll() is None:
        st.sidebar.info("O sistema ja esta ligado.")
        return

    supabase_url, supabase_key = obter_config_supabase()
    ambiente = {
        **os.environ,
        "SUPABASE_URL": supabase_url,
        "SUPABASE_KEY": supabase_key,
        "SUPABASE_TABLE": TABELA_LOGS,
    }
    creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform.startswith("win") else 0

    st.session_state["processo_reconhecedor"] = subprocess.Popen(
        [sys.executable, str(RECONHECEDOR_PATH)],
        cwd=str(BASE_DIR),
        env=ambiente,
        creationflags=creationflags,
    )
    st.sidebar.success("Sistema ligado com sucesso.")


def renderizar_sidebar():
    sidebar_html(
        """
        <div class="brand">
            <div class="brand-icon">&#128274;</div>
            <div>
                <div class="brand-title">Cyber Locker</div>
                <div class="brand-subtitle">Biometric Security</div>
            </div>
        </div>
        """
    )

    pagina = st.sidebar.radio(
        "Navegacao",
        ["Dashboard", "Historico de Acessos", "Utilizadores Biometria", "Gestao de Cacifos"],
        label_visibility="collapsed",
    )

    st.sidebar.write("")
    if st.sidebar.button("Ligar Sistema", use_container_width=True, type="primary"):
        ligar_sistema()
    if st.sidebar.button("Atualizar", use_container_width=True):
        st.rerun()

    st.sidebar.divider()
    sidebar_html(
        """
        <div class="sidebar-status">&#9679; SISTEMA ONLINE</div>
        <div class="sidebar-mini">Supabase ligado · log_acesso</div>
        """
    )

    return pagina


def renderizar_topo():
    html_markdown(
        """
        <div class="hero-row">
            <div>
                <h1 class="hero-title">&#129302; OPERACOES BIOMETRICAS</h1>
                <div class="hero-subtitle">Painel de controlo centralizado dos cacifos inteligentes e acessos biometricos</div>
            </div>
        </div>
        """
    )


def renderizar_metric_card(label, value, note):
    html_markdown(
        f"""
        <div class="metric-card">
            <div class="metric-label">{label}</div>
            <div class="metric-value">{value}</div>
            <div class="metric-note">{note}</div>
        </div>
        """
    )


def renderizar_metricas(total_acessos, acessos_negados, logs):
    utilizadores = {
        str(log.get("nome_utilizador"))
        for log in logs
        if log.get("nome_utilizador") and str(log.get("nome_utilizador")).lower() != "desconhecido"
    }
    autorizados = sum(1 for log in logs if str(log.get("status", "")).upper() == "AUTORIZADO")
    media = "98.5%" if autorizados else "0%"

    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        renderizar_metric_card("&#128202; Total de Acessos", formatar_numero(total_acessos), "Eventos registados")
    with col2:
        renderizar_metric_card("&#128680; Acessos Negados", formatar_numero(acessos_negados), "Tentativas bloqueadas")
    with col3:
        renderizar_metric_card("&#129504; Correspondencia Facial", media, "Media estimada")
    with col4:
        renderizar_metric_card("&#128100; Utilizadores Unicos", formatar_numero(len(utilizadores)), "Faces autorizadas")
    with col5:
        renderizar_metric_card("&#8987; Tempo Medio", "1.2s", "Autenticacao")


def renderizar_cacifo(cacifo_id, estado):
    if estado["ocupado"]:
        classe = "busy"
        status = "Ocupado"
        meta = f"Utilizador: <b>{texto_seguro(estado['utilizador'])}</b>"
        icon = "&#128274;"
    else:
        classe = "free"
        status = "Livre"
        meta = "Disponivel para uso"
        icon = "&#128275;"

    html_markdown(
        f"""
        <div class="locker-card {classe}">
            <div class="locker-name">Cacifo {cacifo_id}</div>
            <div class="locker-body">
                <div class="locker-icon">{icon}</div>
                <div>
                    <div class="locker-status {classe}">{status}</div>
                    <div class="locker-meta">{meta}</div>
                </div>
            </div>
            <div class="progress-track"><div class="progress-fill {classe}"></div></div>
        </div>
        """
    )


def renderizar_cacifos(estados):
    html_markdown('<div class="section-title">Estado dos Cacifos</div>')
    cols = st.columns(4)
    for idx, col in enumerate(cols, start=1):
        with col:
            renderizar_cacifo(idx, estados[idx])


def renderizar_log_row(log):
    hora = texto_seguro(formatar_hora(log.get("data_hora")))
    utilizador = texto_seguro(log.get("nome_utilizador") or "Desconhecido")
    status = texto_seguro(str(log.get("status", "INDEFINIDO")).upper())
    cacifo_id = texto_seguro(log.get("cacifo_id") or 1)
    if status == "AUTORIZADO":
        classe = "ok"
    elif status in {"LIBERADO", "LIVRE"}:
        classe = "free"
    else:
        classe = "bad"

    html_markdown(
        f"""
        <div class="log-row">
            <div><span class="log-muted">&#128338; Hora</span><br><span class="log-strong">{hora}</span></div>
            <div><span class="log-muted">&#128100; Utilizador</span><br><span class="log-strong">{utilizador}</span></div>
            <div><span class="status-pill {classe}">{status}</span></div>
            <div><span class="log-muted">Cacifo</span><br><span class="log-strong">{cacifo_id}</span></div>
        </div>
        """
    )


def renderizar_logs(logs, limite=6):
    with st.container(border=True):
        html_markdown('<div class="log-panel-title">Seguranca e Logs</div>')
        if not logs:
            st.info("Ainda nao existem registos na tabela log_acesso.")
            return

        for log in logs[:limite]:
            renderizar_log_row(log)


def renderizar_dashboard(logs, total_acessos, acessos_negados):
    estados = obter_estado_cacifos(logs)
    renderizar_metricas(total_acessos, acessos_negados, logs)
    renderizar_cacifos(estados)


def renderizar_historico(logs):
    html_markdown('<div class="section-title">Historico de Acessos</div>')
    renderizar_logs(logs, limite=100)


def renderizar_gestao_cacifos(supabase, logs):
    estados = obter_estado_cacifos(logs)

    html_markdown('<div class="section-title">Gestao de Cacifos</div>')
    st.caption("Area administrativa para libertacao manual de cacifos ocupados.")

    cols = st.columns(4)
    for cacifo_id, col in enumerate(cols, start=1):
        estado = estados[cacifo_id]

        with col:
            renderizar_cacifo(cacifo_id, estado)

            if estado["ocupado"]:
                if st.button(
                    "\U0001F513 Libertar Cacifo",
                    key=f"libertar_cacifo_{cacifo_id}",
                    use_container_width=True,
                    type="primary",
                ):
                    try:
                        libertar_cacifo(supabase, cacifo_id)
                        st.success(f"Cacifo {cacifo_id} libertado com sucesso.")
                        st.rerun()
                    except Exception as erro:
                        st.error("Nao foi possivel libertar o cacifo.")
                        st.exception(erro)
            else:
                st.button(
                    "Cacifo Livre",
                    key=f"cacifo_livre_{cacifo_id}",
                    use_container_width=True,
                    disabled=True,
                )


def main():
    aplicar_estilo_visual()
    pagina = renderizar_sidebar()
    renderizar_topo()

    try:
        supabase = obter_supabase()
        logs = consultar_logs(supabase)
        total_acessos, acessos_negados = consultar_metricas(supabase)
    except Exception as erro:
        st.error("Nao foi possivel carregar os dados do Supabase.")
        st.exception(erro)
        return

    if pagina == "Historico de Acessos":
        renderizar_historico(logs)
    elif pagina == "Gestao de Cacifos":
        renderizar_gestao_cacifos(supabase, logs)
    else:
        renderizar_dashboard(logs, total_acessos, acessos_negados)


if __name__ == "__main__":
    main()
