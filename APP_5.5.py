import streamlit as st
import calendar
from datetime import date, datetime, timedelta
import holidays
from streamlit_calendar import calendar as st_calendar
from firebase_config import db

st.set_page_config(page_title="WorkScale", layout="wide")

# ------------------------
# SIDEBAR
# ------------------------
st.sidebar.title("🔐 WorkScale")

modo = st.sidebar.radio("Acesso", ["Login", "Cadastro"], key="menu_principal")
email = st.sidebar.text_input("Email", key="email_input")

# ------------------------
# CADASTRO
# ------------------------
if modo == "Cadastro":

    nome = st.sidebar.text_input("Nome", key="nome")

    tipo_usuario = st.sidebar.selectbox(
        "Tipo de usuário",
        ["👤 Funcionário", "👨‍💼 Gestor"],
        key="tipo"
    )

    gestor = None

    if tipo_usuario == "👤 Funcionário":
        usuarios = db.collection("usuarios").stream()
        gestores = [
            u.to_dict()["email"]
            for u in usuarios
            if u.to_dict().get("tipo") == "gestor"
        ]

        if gestores:
            gestor = st.sidebar.selectbox("Escolha o Gestor", gestores, key="gestor_select")
        else:
            st.sidebar.warning("Nenhum gestor cadastrado ainda")

    if st.sidebar.button("Cadastrar", key="btn_cadastrar"):

        if email and nome:

            ref = db.collection("usuarios").document(email).get()

            if ref.exists:
                st.sidebar.warning("Usuário já existe")
            else:
                db.collection("usuarios").document(email).set({
                    "nome": nome,
                    "email": email,
                    "tipo": "gestor" if tipo_usuario == "👨‍💼 Gestor" else "funcionario",
                    "gestor": gestor,
                    "eventos": []
                })

                st.sidebar.success("Usuário cadastrado com sucesso")

        else:
            st.sidebar.error("Preencha todos os campos")

# ------------------------
# LOGIN
# ------------------------
if modo == "Login":
    if st.sidebar.button("Entrar", key="btn_login"):

        ref = db.collection("usuarios").document(email).get()

        if ref.exists:
            st.session_state.user = ref.to_dict()
            st.sidebar.success("Login realizado")
        else:
            st.sidebar.error("Usuário não encontrado")

# ------------------------
# CONTROLE DE ACESSO
# ------------------------
if "user" not in st.session_state:
    st.warning("Faça login para continuar")
    st.stop()

user = st.session_state.user
st.success(f"👋 Bem-vindo {user['nome']}")

# ------------------------
# EVENTOS
# ------------------------
if "eventos" not in st.session_state:
    doc = db.collection("usuarios").document(user["email"]).get()
    st.session_state.eventos = doc.to_dict().get("eventos", []) if doc.exists else []

# ------------------------
# DATA
# ------------------------
hoje = datetime.today()
ano = hoje.year
mes = hoje.month

st.title("🏢 WorkScale 60/40")
st.subheader(f"{calendar.month_name[mes]} / {ano}")

# ------------------------
# INPUTS
# ------------------------
estado = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS"], key="estado")

tipo_dia = st.selectbox(
    "Tipo",
    [
        "🔵 Presencial",
        "🟡 Planejado Presencial",
        "🏠 Home Office",
        "🌴 Férias",
        "🟣 Banco"
    ],
    key="tipo_dia"
)

usar_emenda = st.checkbox("Considerar emendas", value=True, key="emenda")

# ------------------------
# DIAS ÚTEIS
# ------------------------
def dias_uteis(ano, mes):
    return sum(
        1 for d in range(1, calendar.monthrange(ano, mes)[1] + 1)
        if date(ano, mes, d).weekday() < 5
    )

uteis = dias_uteis(ano, mes)

# ------------------------
# FERIADOS
# ------------------------
@st.cache_data
def get_feriados(ano, estado):
    return holidays.Brazil(years=ano, subdiv=estado)

feriados = get_feriados(ano, estado)
feriados_mes = {d: nome for d, nome in feriados.items() if d.month == mes}

# ------------------------
# EMENDAS CORRETAS
# ------------------------
emendas = {}
for d in feriados_mes:
    if d.weekday() == 3:
        emendas[d + timedelta(days=1)] = "Emenda"
    elif d.weekday() == 1:
        emendas[d - timedelta(days=1)] = "Emenda"

feriados_uteis = [d for d in feriados_mes if d.weekday() < 5]

emendas_uteis = [
    d for d in emendas
    if d.weekday() < 5 and d not in feriados_uteis
] if usar_emenda else []

# ------------------------
# EVENTOS FIXOS
# ------------------------
eventos_fixos = [
    {"title": f"🎉 {nome}", "start": d.isoformat(), "color": "#d62728"}
    for d, nome in feriados_mes.items()
]

if usar_emenda:
    eventos_fixos += [
        {"title": "🔗 Emenda", "start": d.isoformat(), "color": "#9467bd"}
        for d in emendas_uteis
    ]

# ------------------------
# CALENDÁRIO
# ------------------------
events = eventos_fixos + st.session_state.eventos

calendar_result = st_calendar(
    events=events,
    options={"initialView": "dayGridMonth"},
    key="calendar"
)

# ------------------------
# BOTÃO LIMPAR
# ------------------------
colA, colB = st.columns([1, 4])
with colA:
    if st.button("🗑️ Limpar"):
        st.session_state.eventos = []
        db.collection("usuarios").document(user["email"]).update({"eventos": []})
        st.rerun()

# ------------------------
# CLICK
# ------------------------
if calendar_result.get("dateClick"):
    data_str = calendar_result["dateClick"]["date"].split("T")[0]

    st.session_state.eventos = [
        e for e in st.session_state.eventos if e["start"] != data_str
    ]

    cores = {
        "🔵": "#1f77b4",
        "🟡": "#ffcc00",
        "🏠": "#2ca02c",
        "🌴": "#ff7f0e",
        "🟣": "#9467bd"
    }

    cor = next((cores[k] for k in cores if k in tipo_dia), "#000000")

    st.session_state.eventos.append({
        "title": tipo_dia,
        "start": data_str,
        "color": cor
    })

    db.collection("usuarios").document(user["email"]).update({
        "eventos": st.session_state.eventos
    })

    st.rerun()

# ------------------------
# CONTAGEM CORRETA
# ------------------------
presencial = planejado = home = ferias = banco = 0

for e in st.session_state.eventos:
    d = date.fromisoformat(e["start"])

    if d.weekday() < 5:
        t = e["title"]
        if "🔵" in t:
            presencial += 1
        elif "🟡" in t:
            planejado += 1
        elif "Home" in t:
            home += 1
        elif "Férias" in t:
            ferias += 1
        elif "Banco" in t:
            banco += 1

total_nao_uteis = len(feriados_uteis) + len(emendas_uteis)

dias_validos = max(uteis - (total_nao_uteis + ferias + banco), 0)
meta = int(dias_validos * 0.6)

restante = meta - presencial
restante_prev = meta - (presencial + planejado)

# ------------------------
# DASHBOARD USER
# ------------------------
st.subheader("📊 Resultado")

c1, c2, c3, c4 = st.columns(4)
c1.metric("📅 Úteis", uteis)
c2.metric("🎉 Feriados", len(feriados_uteis))
c3.metric("🔗 Emendas", len(emendas_uteis))
c4.metric("📊 Não úteis", total_nao_uteis)

c5, c6, c7, c8 = st.columns(4)
c5.metric("🌴 Férias", ferias)
c6.metric("🟣 Banco", banco)
c7.metric("📉 Válidos", dias_validos)
c8.metric("🏢 Meta", meta)

st.divider()

c9, c10, c11, c12 = st.columns(4)
c9.metric("🔵 Real", presencial)
c10.metric("🟡 Planejado", planejado)
c11.metric("🏠 Home", home)
c12.metric("📌 Faltam", max(restante, 0))

st.metric("📊 Previsto", max(restante_prev, 0))

if restante <= 0:
    st.success("Meta cumprida")
elif restante_prev <= 0:
    st.info("Meta será cumprida se seguir o planejado")
else:
    st.warning("Risco de não bater meta")

# ------------------------
# DASHBOARD GESTOR
# ------------------------
if user.get("tipo") == "gestor":

    st.divider()
    st.header("👨‍💼 Equipe")

    equipe = db.collection("usuarios").where("gestor", "==", user["email"]).stream()

    for membro in equipe:
        dados = membro.to_dict()

        nome = dados.get("nome")
        eventos = dados.get("eventos", [])

        pres = plan = 0
        dias_pres = []
        dias_plan = []

        for e in eventos:
            d = date.fromisoformat(e["start"])

            if d.weekday() < 5:
                if "🔵" in e["title"]:
                    pres += 1
                    dias_pres.append(d.strftime("%d/%m"))
                elif "🟡" in e["title"]:
                    plan += 1
                    dias_plan.append(d.strftime("%d/%m"))

        st.subheader(f"👤 {nome}")

        c1, c2 = st.columns(2)
        c1.metric("Real", pres)
        c2.metric("Planejado", plan)

        col1, col2 = st.columns(2)

        with col1:
            st.markdown("**🔵 Dias Presenciais:**")
            st.write(", ".join(dias_pres) if dias_pres else "-")

        with col2:
            st.markdown("**🟡 Dias Planejados:**")
            st.write(", ".join(dias_plan) if dias_plan else "-")

        st.divider()