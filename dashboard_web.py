import html
import os
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import streamlit as st
from supabase import create_client


BASE_DIR = Path(__file__).resolve().parent
RECONHECEDOR_PATH = BASE_DIR / "reconhecedor.py"
TABELA_LOGS = "log_acesso"
MINUTOS_CACIFO_OCUPADO = 5


st.set_page_config(
    page_title="PAP | Operacoes Biometricas",
    page_icon="\U0001F916",
    layout="wide",
    initial_sidebar_state="expanded",
)


def obter_config_supabase():
    return "https://mmovdgqpwrurcrddyrqx.supabase.co", "sb_publishable_vAnSaWRiCmKdTRyHIpcHfw_YUFBkkH7"


@st.cache_resource(show_spinner=False)
def obter_cliente_supabase(url, key):
    """Cria o cliente Supabase uma unica vez por sessao."""
    return create_client(url, key)


def obter_supabase():
    """Inicializa a ligacao a base de dados."""
    url, key = obter_config_supabase()
    return obter_cliente_supabase(url, key)


def consultar_logs(supabase, limite=100):
    """Consulta os registos mais recentes da tabela log_acesso."""
    resposta = (
        supabase.table(TABELA_LOGS)
        .select("id,data_hora,nome_utilizador,status,cacifo_id")
        .order("data_hora", desc=True)
        .limit(limite)
        .execute()
    )
    return resposta.data or []


def consultar_metricas(supabase):
    """Calcula os indicadores principais diretamente no Supabase."""
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

    total_acessos = resposta_total.count or 0
    acessos_negados = resposta_negados.count or 0

    return total_acessos, acessos_negados


def converter_data_supabase(valor):
    """Converte a data vinda do Supabase para datetime."""
    if not valor:
        return None

    try:
        return datetime.fromisoformat(str(valor).replace("Z", "+00:00"))
    except ValueError:
        return None


def obter_estado_cacifos(logs):
    """Define se cada cacifo esta livre ou ocupado com base em acessos recentes."""
    estados = {
        cacifo_id: {
            "ocupado": False,
            "utilizador": None,
            "data_hora": None,
        }
        for cacifo_id in range(1, 5)
    }

    agora = datetime.now(timezone.utc)
    limite_recente = timedelta(minutes=MINUTOS_CACIFO_OCUPADO)

    for log in logs:
        status = str(log.get("status", "")).upper()
        cacifo_id = int(log.get("cacifo_id") or 1)
        data_log = converter_data_supabase(log.get("data_hora"))

        if cacifo_id not in estados:
            continue

        if status != "AUTORIZADO" or data_log is None:
            continue

        if data_log.tzinfo is None:
            data_log = data_log.replace(tzinfo=timezone.utc)

        data_utc = data_log.astimezone(timezone.utc)

        if agora - data_utc <= limite_recente:
            estados[cacifo_id] = {
                "ocupado": True,
                "utilizador": log.get("nome_utilizador") or "Utilizador",
                "data_hora": data_log,
            }

    return estados


def formatar_hora(valor):
    """Formata a hora para o feed de monitorizacao."""
    data = converter_data_supabase(valor)
    if data is None:
        return "--:--:--"
    return data.strftime("%H:%M:%S")


def formatar_numero(valor):
    """Formata numeros grandes sem quebrar os cards."""
    return f"{valor:,}".replace(",", " ")


def texto_seguro(valor):
    """Evita que dados externos sejam interpretados como HTML."""
    return html.escape(str(valor or ""))


def aplicar_estilo_visual():
    """Aplica uma camada visual premium ao Streamlit."""
    st.markdown(
        """
        <style>
            .stApp {
                background:
                    radial-gradient(circle at top left, rgba(15, 118, 110, 0.14), transparent 32rem),
                    linear-gradient(180deg, #070b14 0%, #0b1120 45%, #070b14 100%);
            }

            [data-testid="stSidebar"] {
                background: #080d18;
                border-right: 1px solid rgba(148, 163, 184, 0.14);
            }

            .block-container {
                padding-top: 1.45rem;
                padding-bottom: 2.5rem;
                max-width: 1280px;
            }

            div[data-testid="stVerticalBlockBorderWrapper"] {
                border-color: rgba(148, 163, 184, 0.18);
                background: rgba(15, 23, 42, 0.48);
                box-shadow: 0 18px 50px rgba(0, 0, 0, 0.20);
            }

            .ops-title {
                margin: 0;
                font-size: clamp(1.35rem, 2vw, 1.85rem);
                line-height: 1.1;
                font-weight: 800;
                letter-spacing: 0;
                color: #f8fafc;
            }

            .ops-subtitle {
                margin-top: 0.35rem;
                color: #94a3b8;
                font-size: 0.92rem;
            }

            .online-badge {
                display: inline-flex;
                align-items: center;
                justify-content: center;
                width: 100%;
                min-height: 2.55rem;
                border-radius: 999px;
                border: 1px solid rgba(34, 197, 94, 0.30);
                background: rgba(20, 83, 45, 0.34);
                color: #bbf7d0;
                font-size: 0.82rem;
                font-weight: 800;
                text-transform: uppercase;
            }

            .lux-widget {
                display: flex;
                align-items: center;
                gap: 1rem;
                min-height: 7.2rem;
            }

            .lux-icon {
                display: grid;
                place-items: center;
                width: 3.4rem;
                height: 3.4rem;
                border-radius: 1rem;
                background: rgba(56, 189, 248, 0.12);
                color: #7dd3fc;
                font-size: 1.65rem;
                border: 1px solid rgba(125, 211, 252, 0.18);
            }

            .lux-icon.danger {
                background: rgba(248, 113, 113, 0.12);
                color: #fca5a5;
                border-color: rgba(252, 165, 165, 0.18);
            }

            .lux-label {
                margin: 0;
                color: #94a3b8;
                font-size: 0.82rem;
                text-transform: uppercase;
                font-weight: 800;
            }

            .lux-value {
                margin: 0.05rem 0 0 0;
                color: #f8fafc;
                font-size: clamp(2.1rem, 4vw, 3.35rem);
                line-height: 1;
                font-weight: 850;
            }

            .section-kicker {
                color: #64748b;
                text-transform: uppercase;
                font-size: 0.76rem;
                font-weight: 850;
                margin-bottom: 0.25rem;
            }

            .section-title {
                color: #f8fafc;
                font-size: 1.15rem;
                font-weight: 850;
                margin: 0 0 0.85rem 0;
            }

            .locker-row {
                display: flex;
                align-items: center;
                gap: 0.9rem;
                padding: 0.95rem 1rem;
                min-height: 5.2rem;
                border-radius: 0.95rem;
                background: rgba(2, 6, 23, 0.34);
                border: 1px solid rgba(148, 163, 184, 0.12);
            }

            .locker-row.free {
                border-left: 4px solid #22c55e;
            }

            .locker-row.busy {
                border-color: rgba(248, 113, 113, 0.38);
                border-left: 4px solid #ef4444;
            }

            .locker-number {
                display: grid;
                place-items: center;
                min-width: 2.45rem;
                height: 2.45rem;
                border-radius: 0.8rem;
                background: rgba(15, 23, 42, 0.86);
                color: #e2e8f0;
                font-weight: 900;
                border: 1px solid rgba(148, 163, 184, 0.16);
            }

            .locker-main {
                flex: 1;
                min-width: 0;
            }

            .locker-name {
                color: #f8fafc;
                font-weight: 850;
                font-size: 0.98rem;
                margin-bottom: 0.1rem;
            }

            .locker-meta {
                color: #94a3b8;
                font-size: 0.86rem;
                white-space: nowrap;
                overflow: hidden;
                text-overflow: ellipsis;
            }

            .locker-state {
                white-space: nowrap;
                font-size: 0.86rem;
                font-weight: 850;
            }

            .locker-state.free {
                color: #86efac;
            }

            .locker-state.busy {
                color: #fca5a5;
            }

            .timeline-row {
                display: grid;
                grid-template-columns: minmax(5.5rem, 0.8fr) minmax(9rem, 1.5fr) minmax(8rem, 1fr) minmax(5rem, 0.7fr);
                align-items: center;
                gap: 0.8rem;
                padding: 0.72rem 0.9rem;
                border-radius: 0.82rem;
                background: rgba(2, 6, 23, 0.32);
                border: 1px solid rgba(148, 163, 184, 0.10);
                margin-bottom: 0.48rem;
            }

            .timeline-row:hover {
                background: rgba(15, 23, 42, 0.62);
                border-color: rgba(148, 163, 184, 0.20);
            }

            .timeline-muted {
                color: #94a3b8;
                font-size: 0.86rem;
            }

            .timeline-strong {
                color: #f8fafc;
                font-weight: 780;
            }

            .status-pill {
                display: inline-flex;
                justify-content: center;
                align-items: center;
                border-radius: 999px;
                min-height: 1.85rem;
                padding: 0 0.72rem;
                font-size: 0.78rem;
                font-weight: 900;
            }

            .status-pill.ok {
                background: rgba(22, 163, 74, 0.16);
                color: #86efac;
                border: 1px solid rgba(134, 239, 172, 0.18);
            }

            .status-pill.bad {
                background: rgba(220, 38, 38, 0.16);
                color: #fca5a5;
                border: 1px solid rgba(252, 165, 165, 0.18);
            }

            @media (max-width: 760px) {
                .timeline-row {
                    grid-template-columns: 1fr;
                }
            }
        </style>
        """,
        unsafe_allow_html=True,
    )


def ligar_sistema():
    """Executa o reconhecedor facial num processo separado."""
    if not RECONHECEDOR_PATH.exists():
        st.sidebar.error("O ficheiro reconhecedor.py nao foi encontrado.")
        return

    processo = st.session_state.get("processo_reconhecedor")

    if processo and processo.poll() is None:
        st.sidebar.info("O sistema ja esta ligado.")
        return

    creationflags = subprocess.CREATE_NEW_CONSOLE if sys.platform.startswith("win") else 0
    supabase_url, supabase_key = obter_config_supabase()
    ambiente = {
        **os.environ,
        "SUPABASE_URL": supabase_url,
        "SUPABASE_KEY": supabase_key,
        "SUPABASE_TABLE": TABELA_LOGS,
    }

    st.session_state["processo_reconhecedor"] = subprocess.Popen(
        [sys.executable, str(RECONHECEDOR_PATH)],
        cwd=str(BASE_DIR),
        env=ambiente,
        creationflags=creationflags,
    )
    st.sidebar.success("Sistema ligado com sucesso.")


def renderizar_sidebar():
    """Renderiza o menu lateral do centro de comando."""
    st.sidebar.title("Cyber Locker")
    st.sidebar.caption("Painel administrativo da PAP")
    st.sidebar.divider()

    if st.sidebar.button("Ligar Sistema", use_container_width=True, type="primary"):
        ligar_sistema()

    if st.sidebar.button("Atualizar", use_container_width=True):
        st.rerun()

    st.sidebar.divider()

    with st.sidebar.container(border=True):
        st.markdown("**Estado Operacional**")
        st.success("Supabase ligado")
        st.caption("Tabela: log_acesso")
        st.caption("Canal: monitorizacao em tempo real")


def renderizar_topo_compacto():
    """Renderiza um topo compacto e corporativo."""
    coluna_titulo, coluna_estado = st.columns([4.2, 1])

    with coluna_titulo:
        st.markdown(
            """
            <div>
                <h1 class="ops-title">&#129302; OPERACOES BIOMETRICAS</h1>
                <div class="ops-subtitle">Centro de controlo de acessos e seguranca de cacifos</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with coluna_estado:
        st.markdown('<div class="online-badge">&#9679; ONLINE</div>', unsafe_allow_html=True)

    st.write("")


def renderizar_widget_luxo(icone, titulo, valor, classe_extra=""):
    """Renderiza um contador visual premium sem st.metric."""
    with st.container(border=True):
        st.markdown(
            f"""
            <div class="lux-widget">
                <div class="lux-icon {classe_extra}">{icone}</div>
                <div>
                    <p class="lux-label">{titulo}</p>
                    <p class="lux-value">{formatar_numero(valor)}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def renderizar_metricas(total_acessos, acessos_negados):
    """Renderiza os contadores principais como widgets de luxo."""
    coluna_total, coluna_intrusos = st.columns(2)

    with coluna_total:
        renderizar_widget_luxo("&#128202;", "Total de Acessos", total_acessos)

    with coluna_intrusos:
        renderizar_widget_luxo("&#128680;", "Intrusos Detetados", acessos_negados, "danger")


def renderizar_cacifo(cacifo_id, estado):
    """Renderiza uma linha compacta para cada cacifo."""
    utilizador = texto_seguro(estado.get("utilizador") or "Sem utilizador")

    if estado["ocupado"]:
        classe = "busy"
        status = "&#128308; Ocupado"
        meta = f"&#128100; {utilizador}"
    else:
        classe = "free"
        status = "&#128994; Livre"
        meta = "&#128275; Disponivel para uso"

    st.markdown(
        f"""
        <div class="locker-row {classe}">
            <div class="locker-number">{cacifo_id}</div>
            <div class="locker-main">
                <div class="locker-name">Cacifo {cacifo_id}</div>
                <div class="locker-meta">{meta}</div>
            </div>
            <div class="locker-state {classe}">{status}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_cacifos(estados):
    """Renderiza o compact tracker dos cacifos."""
    with st.container(border=True):
        st.markdown('<div class="section-kicker">Locker Status</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Compact Tracker</div>', unsafe_allow_html=True)

        linha_1_col_1, linha_1_col_2 = st.columns(2)
        linha_2_col_1, linha_2_col_2 = st.columns(2)

        with linha_1_col_1:
            renderizar_cacifo(1, estados[1])
        with linha_1_col_2:
            renderizar_cacifo(2, estados[2])
        with linha_2_col_1:
            renderizar_cacifo(3, estados[3])
        with linha_2_col_2:
            renderizar_cacifo(4, estados[4])


def renderizar_item_timeline(log):
    """Renderiza um registo do historico em linha minimalista."""
    hora = texto_seguro(formatar_hora(log.get("data_hora")))
    utilizador = texto_seguro(log.get("nome_utilizador") or "Desconhecido")
    status = texto_seguro(str(log.get("status", "INDEFINIDO")).upper())
    cacifo_id = texto_seguro(log.get("cacifo_id") or 1)
    classe_status = "ok" if status == "AUTORIZADO" else "bad"
    icone_status = "&#128994;" if status == "AUTORIZADO" else "&#128308;"

    st.markdown(
        f"""
        <div class="timeline-row">
            <div class="timeline-muted">&#128338; {hora}</div>
            <div class="timeline-strong">&#128100; {utilizador}</div>
            <div><span class="status-pill {classe_status}">{icone_status} {status}</span></div>
            <div class="timeline-muted">Cacifo {cacifo_id}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def renderizar_historico(logs):
    """Renderiza uma timeline minimalista dos eventos recentes."""
    with st.container(border=True):
        st.markdown('<div class="section-kicker">Security Stream</div>', unsafe_allow_html=True)
        st.markdown('<div class="section-title">Historico de Acessos</div>', unsafe_allow_html=True)

        if not logs:
            st.info("Ainda nao existem registos na tabela log_acesso.")
            return

        for log in logs[:12]:
            renderizar_item_timeline(log)


def main():
    aplicar_estilo_visual()
    renderizar_sidebar()
    renderizar_topo_compacto()

    try:
        supabase = obter_supabase()
        logs = consultar_logs(supabase)
        total_acessos, acessos_negados = consultar_metricas(supabase)
    except Exception as erro:
        st.error("Nao foi possivel carregar os dados do Supabase.")
        st.exception(erro)
        return

    estados_cacifos = obter_estado_cacifos(logs)

    renderizar_metricas(total_acessos, acessos_negados)
    st.write("")

    coluna_cacifos, coluna_historico = st.columns([1, 1.35])

    with coluna_cacifos:
        renderizar_cacifos(estados_cacifos)

    with coluna_historico:
        renderizar_historico(logs)


if __name__ == "__main__":
    main()
