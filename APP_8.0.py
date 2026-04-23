import streamlit as st
import calendar
from datetime import date, datetime, timedelta
import holidays
from streamlit_calendar import calendar as st_calendar
from firebase_config import db
import bcrypt
import time


st.set_page_config(page_title="WorkScale", layout="wide")

# ------------------------
# SESSION STATE (GLOBAL)
# ------------------------
if "last_action_time" not in st.session_state:
    st.session_state.last_action_time = 0
# ------------------------
# SESSION (MÊS/ANO)
# ------------------------
if "mes" not in st.session_state:
    hoje = datetime.today()
    st.session_state.mes = hoje.month
    st.session_state.ano = hoje.year

mes = st.session_state.mes
ano = st.session_state.ano

# ------------------------
# SENHA
# ------------------------
def hash_senha(senha):
    return bcrypt.hashpw(senha.encode(), bcrypt.gensalt()).decode()

def verificar_senha(senha, hash_salvo):
    return bcrypt.checkpw(senha.encode(), hash_salvo.encode())

# ------------------------
# SIDEBAR
# ------------------------
st.sidebar.title("🔐 WorkScale")

modo = st.sidebar.radio("Acesso", ["Login", "Cadastro"])
email = st.sidebar.text_input("Email").strip().lower()

# ------------------------
# CADASTRO
# ------------------------
if modo == "Cadastro":

    nome = st.sidebar.text_input("Nome")
    senha = st.sidebar.text_input("Senha", type="password")

    tipo_usuario = st.sidebar.selectbox(
        "Tipo de usuário",
        ["👤 Funcionário", "👨‍💼 Gestor"]
    )

    gestor = None
    if tipo_usuario == "👤 Funcionário":
        gestor = st.sidebar.text_input("Email do Gestor")

    if st.sidebar.button("Cadastrar"):

        if email and nome and senha and (tipo_usuario == "👨‍💼 Gestor" or gestor):

            ref = db.collection("usuarios").document(email).get()

            if ref.exists:
                st.sidebar.warning("Usuário já existe")
            else:
                if tipo_usuario == "👤 Funcionário":
                    if not db.collection("usuarios").document(gestor).get().exists:
                        st.sidebar.error("Gestor inválido")
                        st.stop()

                db.collection("usuarios").document(email).set({
                    "nome": nome,
                    "email": email.strip().lower(),
                    "senha": hash_senha(senha),
                    "tipo": "gestor" if tipo_usuario == "👨‍💼 Gestor" else "funcionario",
                    "gestor": gestor.strip().lower(),
                    "eventos": []
                })

                st.sidebar.success("Usuário cadastrado")

# ------------------------
# LOGIN
# ------------------------
if modo == "Login":

    senha_login = st.sidebar.text_input("Senha", type="password")

    if st.sidebar.button("Entrar"):

        ref = db.collection("usuarios").document(email).get()

        if ref.exists:
            user_data = ref.to_dict()

            senha_salva = user_data.get("senha")

            if not senha_salva:
                st.sidebar.warning("Usuário sem senha. Crie uma abaixo.")
            elif verificar_senha(senha_login, senha_salva):
                st.session_state.user = user_data
                st.sidebar.success("Login OK")
            else:
                st.sidebar.error("Senha incorreta")
        else:
            st.sidebar.error("Usuário não encontrado")

# ------------------------
# ALTERAR SENHA (SEGURO)
# ------------------------
st.sidebar.divider()
st.sidebar.subheader("🔒 Alterar senha")

if "user" in st.session_state:

    senha_atual = st.sidebar.text_input("Senha atual", type="password")
    nova_senha = st.sidebar.text_input("Nova senha", type="password")

    if st.sidebar.button("Atualizar senha"):

        if not senha_atual or not nova_senha:
            st.sidebar.error("Preencha os campos")
        else:
            senha_salva = user.get("senha")

            if not senha_salva or verificar_senha(senha_atual, senha_salva):

                db.collection("usuarios").document(user["email"]).update({
                    "senha": hash_senha(nova_senha)
                })

                st.sidebar.success("Senha atualizada com sucesso")

            else:
                st.sidebar.error("Senha atual incorreta")

# ------------------------
# BLOQUEIO
# ------------------------
if "user" not in st.session_state:
    st.warning("Faça login")
    st.stop()

user = st.session_state.user
st.success(f"👋 {user['nome']}")

# ------------------------
# EVENTOS
# ------------------------
if "eventos" not in st.session_state:
    doc = db.collection("usuarios").document(user["email"]).get()
    st.session_state.eventos = doc.to_dict().get("eventos", []) if doc.exists else []

# ------------------------
# INPUTS
# ------------------------
estado = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS"])

tipo_dia = st.selectbox(
    "Tipo",
    ["🔵 Presencial", "🟡 Planejado Presencial", "🏠 Home Office", "🌴 Férias", "🟣 Banco"]
)

usar_emenda = st.checkbox("Considerar emendas", value=True)

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
# EMENDAS
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
    options={
        "initialView": "dayGridMonth",
        "initialDate": f"{ano}-{mes:02d}-01",
        "headerToolbar": {
            "left": "prev,next today",
            "center": "title",
            "right": ""
        }
    },
    key="calendar"
)
# ------------------------
# SAVE (FIREBASE OTIMIZADO)
# ------------------------
def salvar_eventos(email, eventos):
    try:
        db.collection("usuarios").document(email).update({
            "eventos": eventos
        })
    except Exception as e:
        print("Erro ao salvar:", e)
# ------------------------
# CLICK (ESTÁVEL)
# ------------------------
if calendar_result and calendar_result.get("dateClick"):

    agora = time.time()

    if agora - st.session_state.last_action_time < 0.3:
        st.stop()

    st.session_state.last_action_time = agora

    data_str = calendar_result["dateClick"]["date"].split("T")[0]

    cores = {
        "🔵": "#1f77b4",
        "🟡": "#ffcc00",
        "🏠": "#2ca02c",
        "🌴": "#ff7f0e",
        "🟣": "#9467bd"
    }

    cor = next((cores[k] for k in cores if k in tipo_dia), "#000")

    evento = next((e for e in st.session_state.eventos if e["start"] == data_str), None)

    # ✅ LÓGICA ÚNICA (SEM DUPLICAÇÃO)
    if evento:
        if evento["title"] == tipo_dia:
            st.session_state.eventos.remove(evento)
            mensagem = "Removido"
            icone = "🗑️"
        else:
            evento["title"] = tipo_dia
            evento["color"] = cor
            mensagem = f"{tipo_dia} atualizado"
            icone = "♻️"
    else:
        st.session_state.eventos.append({
            "title": tipo_dia,
            "start": data_str,
            "color": cor
        })
        mensagem = f"{tipo_dia} aplicado"
        icone = "📅"

    salvar_eventos(user["email"], st.session_state.eventos)

    st.toast(mensagem, icon=icone)

    st.rerun()
# ------------------------
# DASHBOARD
# ------------------------
presencial = planejado = home = ferias = banco = 0

for e in st.session_state.eventos:
    d = date.fromisoformat(e["start"])

    if d.month == mes and d.year == ano and d.weekday() < 5:
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

    encontrou = False

    for membro in equipe:
        encontrou = True
        dados = membro.to_dict()

        nome = dados.get("nome", "Sem nome")
        eventos = dados.get("eventos", [])

        pres = plan = home = 0

        for e in eventos:
            d = date.fromisoformat(e["start"])

            if d.month == mes and d.year == ano and d.weekday() < 5:
                t = e["title"]
                if "🔵" in t:
                    pres += 1
                elif "🟡" in t:
                    plan += 1
                elif "Home" in t:
                    home += 1

        st.subheader(f"👤 {nome}")

        c1, c2, c3 = st.columns(3)
        c1.metric("🔵 Presencial", pres)
        c2.metric("🟡 Planejado", plan)
        c3.metric("🏠 Home", home)

        st.divider()

    if not encontrou:
        st.info("Nenhum funcionário vinculado a você ainda")



