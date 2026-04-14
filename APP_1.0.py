import streamlit as st
import calendar
from datetime import date, datetime, timedelta
import holidays
from streamlit_calendar import calendar as st_calendar
from firebase_config import db

# ------------------------
# LOGIN / CADASTRO
# ------------------------
st.sidebar.title("🔐 Acesso WorkScale")

modo = st.sidebar.selectbox("Escolha", ["Login", "Cadastro"])
email = st.sidebar.text_input("Email")

if modo == "Cadastro":
    nome = st.sidebar.text_input("Nome")
    gestor = st.sidebar.text_input("Email do Gestor")

    if st.sidebar.button("Cadastrar"):
        if email and nome and gestor:

            user_ref = db.collection("usuarios").document(email).get()

            if user_ref.exists:
                st.sidebar.warning("Usuário já existe!")
            else:
                db.collection("usuarios").document(email).set({
                    "nome": nome,
                    "email": email,
                    "gestor": gestor,
                    "eventos": []
                })
                st.sidebar.success("Usuário cadastrado!")
        else:
            st.sidebar.error("Preencha todos os campos!")

if modo == "Login":
    if st.sidebar.button("Entrar"):
        user_ref = db.collection("usuarios").document(email).get()

        if user_ref.exists:
            st.session_state.user = user_ref.to_dict()
            st.sidebar.success("Login realizado!")
        else:
            st.sidebar.error("Usuário não encontrado!")

# ------------------------
# CONTROLE DE ACESSO
# ------------------------
if "user" in st.session_state:
    user = st.session_state.user
    st.success(f"👋 Bem-vindo {user['nome']}")
else:
    st.warning("🔐 Faça login para acessar o sistema")
    st.stop()

# ------------------------
# CARREGAR EVENTOS DO FIREBASE
# ------------------------
if "eventos" not in st.session_state:
    user_doc = db.collection("usuarios").document(user["email"]).get()

    if user_doc.exists:
        dados = user_doc.to_dict()
        st.session_state.eventos = dados.get("eventos", [])
    else:
        st.session_state.eventos = []

# ------------------------
# CONFIG
# ------------------------
st.set_page_config(page_title="WorkScale", layout="wide")

hoje = datetime.today()
ano = hoje.year
mes = hoje.month

st.title("🏢 WorkScale 60/40")
st.subheader(f"📅 {calendar.month_name[mes]} / {ano}")

# ------------------------
# INPUTS
# ------------------------
estado = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS"])
tipo_dia = st.selectbox("Tipo", ["🏢 Presencial", "🏠 Home Office", "🌴 Férias", "🟣 Banco"])
usar_emenda = st.checkbox("Considerar emendas")

# ------------------------
# DIAS ÚTEIS
# ------------------------
def dias_uteis(ano, mes):
    cal = calendar.monthcalendar(ano, mes)
    return sum(1 for semana in cal for dia in semana[:5] if dia != 0)

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
# EMENDAS
# ------------------------
emendas = {}
for d in feriados_mes:
    if d.weekday() == 3:
        emendas[d + timedelta(days=1)] = "Emenda"
    elif d.weekday() == 1:
        emendas[d - timedelta(days=1)] = "Emenda"

# ------------------------
# EVENTOS FIXOS
# ------------------------
eventos_fixos = []

for d, nome in feriados_mes.items():
    eventos_fixos.append({
        "title": f"🎉 {nome}",
        "start": d.isoformat(),
        "color": "#d62728"
    })

if usar_emenda:
    for d in emendas:
        eventos_fixos.append({
            "title": "🔗 Emenda",
            "start": d.isoformat(),
            "color": "#9467bd"
        })

# ------------------------
# CALENDÁRIO
# ------------------------
events = eventos_fixos + st.session_state.eventos

calendar_result = st_calendar(
    events=events,
    options={"initialView": "dayGridMonth", "selectable": True},
    key="calendar"
)

# ------------------------
# CLIQUE
# ------------------------
if calendar_result.get("dateClick"):
    data_str = calendar_result["dateClick"]["date"].split("T")[0]

    # Remove antigo
    st.session_state.eventos = [
        e for e in st.session_state.eventos
        if e["start"] != data_str
    ]

    cores = {
        "Presencial": "#1f77b4",
        "Home": "#2ca02c",
        "Férias": "#ff7f0e",
        "Banco": "#9467bd"
    }

    cor = "#000000"
    for k in cores:
        if k in tipo_dia:
            cor = cores[k]

    # Adiciona novo
    st.session_state.eventos.append({
        "title": tipo_dia,
        "start": data_str,
        "color": cor
    })

    # 🔥 SALVAR NO FIREBASE
    db.collection("usuarios").document(user["email"]).update({
        "eventos": st.session_state.eventos
    })

    st.rerun()

# ------------------------
# CONTAGEM
# ------------------------
presencial = home = ferias = banco = 0

for e in st.session_state.eventos:
    d = date.fromisoformat(e["start"])

    if d.weekday() < 5:
        if "Presencial" in e["title"]:
            presencial += 1
        elif "Home" in e["title"]:
            home += 1
        elif "Férias" in e["title"]:
            ferias += 1
        elif "Banco" in e["title"]:
            banco += 1

feriados_count = len([d for d in feriados_mes if d.weekday() < 5])
emendas_count = len([d for d in emendas if d.weekday() < 5]) if usar_emenda else 0

total_nao_uteis = feriados_count + emendas_count

dias_validos = uteis - (total_nao_uteis + ferias + banco)
presencial_obrigatorio = int(dias_validos * 0.6)
restante = presencial_obrigatorio - presencial

# ------------------------
# DASHBOARD
# ------------------------
st.subheader("📊 Resultado")

c1, c2, c3, c4 = st.columns(4)
c1.metric("📅 Úteis", uteis)
c2.metric("🎉 Feriados", feriados_count)
c3.metric("🔗 Emendas", emendas_count)
c4.metric("📊 Não úteis", total_nao_uteis)

c5, c6, c7, c8 = st.columns(4)
c5.metric("🌴 Férias", ferias)
c6.metric("🟣 Banco", banco)
c7.metric("📉 Válidos", dias_validos)
c8.metric("🏢 Meta", presencial_obrigatorio)

st.divider()

c9, c10, c11 = st.columns(3)
c9.metric("🏢 Presencial", presencial)
c10.metric("🏠 Home", home)
c11.metric("📌 Faltam", max(restante, 0))

# ------------------------
# STATUS
# ------------------------
if restante > 0:
    st.warning(f"Faltam {restante} dias presenciais")
else:
    st.success("Meta cumprida!")

# ------------------------
# LIMPAR
# ------------------------
if st.button("🗑️ Limpar calendário"):
    st.session_state.eventos = []

    db.collection("usuarios").document(user["email"]).update({
        "eventos": []
    })

    st.rerun()