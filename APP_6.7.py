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

st.info(
    """
ℹ️ **WorkScale**

Este sistema foi desenvolvido para auxiliar na organização dos dias de trabalho.  

Não é uma ferramenta oficial da empresa!!.

💡 **Dica:**  
Para quem trabalha aos finais de semana e folga durante a semana, utilize a opção **🔄 Folga Plantão**.
"""
)
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
                    "gestor": gestor.strip().lower() if tipo_usuario == "👤 Funcionário" else None,
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
# 1️⃣ Primeiro o estado
estado = st.selectbox("Estado", ["SP", "RJ", "MG", "PR", "SC", "RS"])

# 2️⃣ Depois o dicionário
cidades_por_estado = {
    "SP": ["São Paulo", "Campinas", "Santos"],
    "RJ": ["Rio de Janeiro", "Niterói"],
    "MG": ["Belo Horizonte"],
    "PR": ["Curitiba"],
    "SC": ["Florianópolis"],
    "RS": ["Porto Alegre"]
}

# 3️⃣ Depois a cidade (AGORA FUNCIONA)
cidade = st.selectbox(
    "Cidade",
    cidades_por_estado.get(estado, [])
)

tipo_dia = st.selectbox(
    "Tipo",
    [
        "🔵 Presencial",
        "🟡 Planejado Presencial",
        "🏠 Home Office",
        "🌴 Férias",
        "🟣 Banco",
        "🚑 Atestado Médico",
        "🎂 Day Off",
        "🔄 Folga Plantão",
        "🎁 Liberalidade" # 👈 NOVO
    ]
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
def calcular_pascoa(ano):
    a = ano % 19
    b = ano // 100
    c = ano % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19*a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2*e + 2*i - h - k) % 7
    m = (a + 11*h + 22*l) // 451
    mes = (h + l - 7*m + 114) // 31
    dia = ((h + l - 7*m + 114) % 31) + 1
    return date(ano, mes, dia)

def calcular_corpus_christi(ano):
    pascoa = calcular_pascoa(ano)
    return pascoa + timedelta(days=60)
@st.cache_data
def get_feriados(ano, estado, cidade=None):
    br = holidays.Brazil(years=ano, subdiv=estado)

    feriados = dict(br)

    # 🔥 GARANTE CORPUS CHRISTI
    corpus = calcular_corpus_christi(ano)
    feriados[corpus] = "Corpus Christi"

    # 🎯 MUNICIPAIS
    if cidade == "São Paulo":
        feriados[date(ano, 1, 25)] = "Aniversário de São Paulo"

    if cidade == "Rio de Janeiro":
        feriados[date(ano, 1, 20)] = "São Sebastião"

    return feriados

feriados = get_feriados(ano, estado, cidade)

feriados_mes = {
    d: nome
    for d, nome in feriados.items()
    if d.month == mes
}
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
# DIAS BLOQUEADOS (FERIADO + EMENDA)
# ------------------------
dias_bloqueados = {
    d.isoformat() for d in feriados_uteis + emendas_uteis
}
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
# AUTO PREENCHER
# ------------------------
def auto_preencher_home(eventos, ano, mes, dias_bloqueados):
    datas_com_evento = {e["start"] for e in eventos}

    datas_obj = sorted([
        date.fromisoformat(d)
        for d in datas_com_evento
        if date.fromisoformat(d).month == mes and date.fromisoformat(d).year == ano
    ])

    if not datas_obj:
        return eventos

    ultima_data = max(datas_obj)

    novas = []

    for d in range(1, ultima_data.day + 1):
        dia = date(ano, mes, d)

        if dia.weekday() < 5:  # só dias úteis
            iso = dia.isoformat()

            # 🚫 ignora feriados e emendas
            if iso in dias_bloqueados:
                continue

            # só adiciona se não tiver evento
            if iso not in datas_com_evento:
                novas.append({
                    "title": "🏠 Home (auto)",
                    "start": iso,
                    "color": "#90ee90"
                })

    return eventos + novas

# ------------------------
# EVENTOS EXIBIÇÃO
# ------------------------
hoje = date.today()

eventos_exibicao = []

# ------------------------
# CALENDÁRIO
# ------------------------
col1, col2, col3 = st.columns([1,2,1])

with col1:
    if st.button("⬅️ Mês anterior"):
        if mes == 1:
            st.session_state.mes = 12
            st.session_state.ano -= 1
        else:
            st.session_state.mes -= 1
        st.rerun()

with col3:
    if st.button("Próximo mês ➡️"):
        if mes == 12:
            st.session_state.mes = 1
            st.session_state.ano += 1
        else:
            st.session_state.mes += 1
        st.rerun()

with col2:
    st.markdown(f"### {calendar.month_name[mes]} / {ano}")
# AUTO PREENCHIMENTO CORRETO
eventos_usuario = auto_preencher_home(
    st.session_state.eventos,
    ano,
    mes,
    dias_bloqueados
)

events = eventos_fixos + eventos_usuario

eventos_exibicao = []

for e in events:
    novo_evento = e.copy()
    d = date.fromisoformat(novo_evento["start"])

    if "🟡" in novo_evento["title"] and d < hoje:
        novo_evento["title"] = "🟡 Planejado (⚠️)"
        novo_evento["color"] = "#ff4d4d"

    eventos_exibicao.append(novo_evento)

calendar_result = st_calendar(
    events=eventos_exibicao,
    options={
        "initialView": "dayGridMonth",
        "initialDate": f"{ano}-{mes:02d}-01",
        "headerToolbar": {
            "left": "",  # 🔥 remove navegação do calendário
            "center": "title",
            "right": ""
        }
    },
    key=f"calendar_{mes}_{ano}"
)
# 🔥 ADICIONE ESTE BLOCO AQUI
if calendar_result and calendar_result.get("view"):
    data_view = calendar_result["view"]["currentStart"]

    novo_ano = int(data_view[:4])
    novo_mes = int(data_view[5:7])

    if novo_mes != st.session_state.mes or novo_ano != st.session_state.ano:
        st.session_state.mes = novo_mes
        st.session_state.ano = novo_ano
        st.rerun()
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
        "🟣": "#9467bd",
        "🚑": "#ff4d4d",
        "🎂": "#ff69b4",
        "🔄": "#8c564b",
        "🎁": "#FFA500"
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
# DASHBOARD (CONTAGEM CORRETA COM AUTO)
# ------------------------

hoje = date.today()

presencial = planejado = planejado_vencido = home = ferias = banco = dayoff = atestado = liberalidade = folga_plantao = 0

for e in eventos_usuario:
    d = date.fromisoformat(e["start"])

    if d.month == mes and d.year == ano and d.weekday() < 5:

        t = e["title"]

        if "🔵" in t:
            presencial += 1

        elif "🟡" in t:
            if d < hoje:
                planejado_vencido += 1  # 👈 novo
            else:
                planejado += 1

        elif "Home" in t:
            home += 1

        elif "Férias" in t:
            ferias += 1

        elif "Banco" in t:
            banco += 1

        elif "Folga Plantão" in t:
            folga_plantao += 1

        elif "Day Off" in t:
            dayoff += 1

        elif "Atestado" in t:
            atestado += 1

        elif "Liberalidade" in t:
            liberalidade += 1

# ------------------------
# NÃO ÚTEIS
# ------------------------

total_nao_uteis = len(feriados_uteis) + len(emendas_uteis)

dias_validos = max(uteis - (total_nao_uteis + ferias + banco + atestado + dayoff + liberalidade), 0)
meta = int(dias_validos * 0.6)

restante = meta - presencial
restante_prev = meta - (presencial + planejado)

st.subheader("📊 Resultado")

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("📅 Úteis", uteis)
c2.metric("🎉 Feriados", len(feriados_uteis))
c3.metric("🔗 Emendas", len(emendas_uteis))
c4.metric("📊 Não úteis", total_nao_uteis)
c5.metric("🎁 Liberalidade", liberalidade)

c6, c7, c8, c9 = st.columns(4)
c6.metric("🌴 Férias", ferias)
c7.metric("🟣 Banco", banco)
c8.metric("📉 Válidos", dias_validos)
c9.metric("🏢 Meta", meta)

st.divider()

c10, c11, c12, c13, c14, c15, c16, c17 = st.columns(8)

c10.metric("🔵 Real", presencial)
c11.metric("🟡 Planejado", planejado)
c12.metric("⚠️ Vencido", planejado_vencido)
c13.metric("🏠 Home", home)
c14.metric("🚑 Atestado", atestado)
c15.metric("🎂 Day Off", dayoff)
c16.metric("🔄 Plantão", folga_plantao)

# 🔥 MÉTRICA DINÂMICA
if presencial > meta:
    excedente = presencial - meta
    c17.metric("📈 Excedente", excedente)

elif presencial == meta:
    c17.metric("✅ Meta", "OK")

else:
    faltam = meta - presencial
    c17.metric("📌 Faltam", faltam)

# 🔥 PREVISÃO
previsto = presencial + planejado

if previsto > meta:
    st.metric(
        "📊 Previsto",
        f"Excede {previsto - meta}"
    )

elif previsto == meta:
    st.metric("📊 Previsto", "Meta alcançada")

else:
    st.metric("📊 Previsto", meta - previsto)

# 🔥 STATUS FINAL
if presencial > meta:

    excedente = presencial - meta

    st.warning(
        f"⚠️ Você excedeu a meta em {excedente} dia(s) presencial(is)"
    )

elif presencial == meta:

    st.success("✅ Meta cumprida exatamente")

elif previsto >= meta:

    st.info("📌 Meta será cumprida se seguir o planejado")

else:

    faltam = meta - presencial

    st.warning(
        f"⚠️ Ainda faltam {faltam} dia(s) presencial(is)"
    )
# ------------------------
# NOVA FUNÇÃO
# ------------------------


def calcular_status(eventos, ano, mes, uteis, feriados_uteis, emendas_uteis):

    hoje = date.today()

    presencial = planejado = planejado_vencido = 0
    home = ferias = banco = atestado = dayoff = liberalidade = 0

    for e in eventos:
        d = date.fromisoformat(e["start"])

        if d.month == mes and d.year == ano and d.weekday() < 5:
            t = e["title"]

            if "🔵" in t:
                presencial += 1

            elif "🟡" in t:
                if d < hoje:
                    planejado_vencido += 1
                else:
                    planejado += 1

            elif "Home" in t:
                home += 1

            elif "Férias" in t:
                ferias += 1

            elif "Banco" in t:
                banco += 1

            elif "Atestado" in t:
                atestado += 1

            elif "Day Off" in t:
                dayoff += 1

            elif "Liberalidade" in t:
                liberalidade += 1

    total_nao_uteis = len(feriados_uteis) + len(emendas_uteis)

    dias_validos = max(uteis - (total_nao_uteis + ferias + banco + atestado + dayoff + liberalidade), 0)
    meta = int(dias_validos * 0.6)

    restante = meta - presencial
    restante_prev = meta - (presencial + planejado)

    if restante <= 0:
        return "ok"
    elif restante_prev <= 0:
        return "planejado"
    else:
        return "risco"
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

        pres = plan = home = ferias = banco = atestado = folga_plantao = liberalidade = 0

        dias_pres = []
        dias_home = []
        dias_plan = []
        dias_ferias = []
        dias_banco = []
        dias_atestado = []
        dias_dayoff = []
        dias_folga_plantao = []
        dias_liberalidade = []

        for e in eventos:
            d = date.fromisoformat(e["start"])

            if d.month == mes and d.year == ano and d.weekday() < 5:
                t = e["title"]

                if "🔵" in t:
                    pres += 1
                    dias_pres.append(d.day)

                elif "🟡" in t:
                    plan += 1
                    dias_plan.append(d.day)

                elif "Home" in t:
                    home += 1
                    dias_home.append(d.day)

                elif "Férias" in t:
                    ferias += 1
                    dias_ferias.append(d.day)

                elif "Banco" in t:
                    banco += 1
                    dias_banco.append(d.day)

                elif "Folga Plantão" in t:
                    folga_plantao += 1
                    dias_folga_plantao.append(d.day)

                elif "Atestado" in t:
                    atestado += 1
                    dias_atestado.append(d.day)

                elif "Day Off" in t:
                    dayoff += 1
                    dias_dayoff.append(d.day)

                elif "Liberalidade" in t:
                    liberalidade += 1
                    dias_liberalidade.append(d.day)


        # ✅ STATUS FORA DO LOOP INTERNO (CORRETO)
        status = calcular_status(
            eventos,
            ano,
            mes,
            uteis,
            feriados_uteis,
            emendas_uteis
        )

        # 👇 STATUS VISUAL
        if status == "ok":
            st.success(f"{nome} → Meta cumprida")
        elif status == "planejado":
            st.info(f"{nome} → Vai cumprir (planejado)")
        else:
            st.warning(f"{nome} → ⚠️ Risco de não bater meta")

        st.subheader(f"👤 {nome}")

        c1, c2, c3, c4, c5, c6, c7, c8, c9 = st.columns(9)

        c1.metric("🔵 Presencial", pres)
        c2.metric("🟡 Planejado", plan)
        c3.metric("🏠 Home", home)
        c4.metric("🌴 Férias", ferias)
        c5.metric("🟣 Banco", banco)
        c6.metric("🚑 Atestado", atestado)
        c7.metric("🎂 Day Off", dayoff)
        c8.metric("🔄 Plantão", folga_plantao)
        c9.metric("🎁 Liberalidade", liberalidade)

        # 🔥 detalhamento dos dias
        st.markdown("**📅 Detalhamento:**")

        if dias_pres:
            st.write(f"🔵 Presencial: {sorted(dias_pres)}")

        if dias_plan:
            st.write(f"🟡 Planejado: {sorted(dias_plan)}")

        if dias_home:
            st.write(f"🏠 Home: {sorted(dias_home)}")

        if dias_ferias:
            st.write(f"🌴 Férias: {sorted(dias_ferias)}")

        if dias_banco:
            st.write(f"🟣 Banco: {sorted(dias_banco)}")

        if dias_atestado:
            st.write(f"🚑 Atestado: {sorted(dias_atestado)}")

        if dias_dayoff:
            st.write(f"🎂 Day Off: {sorted(dias_dayoff)}")

        if dias_folga_plantao:
            st.write(f"🔄 Plantão: {sorted(dias_folga_plantao)}")

        if dias_liberalidade:
            st.write(f"🎁 Liberalidade: {sorted(dias_liberalidade)}")

        if not any([
            dias_pres,
            dias_plan,
            dias_home,
            dias_ferias,
            dias_banco,
            dias_atestado,
            dias_dayoff,
            dias_folga_plantao,
            dias_liberalidade
        ]):
            st.write("Nenhum registro no mês")

        st.divider()

    if not encontrou:
        st.info("Nenhum funcionário vinculado a você ainda")
