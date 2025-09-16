import streamlit as st
import pandas as pd
import streamlit_authenticator as stauth
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# --- sessão: evita KeyError ao acessar st.session_state["credentials"] ---
if "credentials" not in st.session_state:
    # estrutura mínima esperada pelo Streamlit-Authenticator
    st.session_state["credentials"] = {"usernames": {}}

# ========= CONEXÃO COM POSTGRES =========
# Ajuste usuário/senha/host/porta/banco:
ENGINE_URL = "postgresql+psycopg2://postgres:admin@localhost:5432/postgres"
engine: Engine = create_engine(ENGINE_URL, future=True)

def ensure_users_table():
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
              username TEXT PRIMARY KEY,
              email TEXT NOT NULL UNIQUE,
              first_name TEXT NOT NULL,
              last_name TEXT NOT NULL,
              password_hash TEXT NOT NULL,
              roles TEXT,
              created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
              updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            );
        """))

def fetch_users_from_db():
    with engine.begin() as conn:
        rows = conn.execute(text("""
            SELECT username, email, first_name, last_name, password_hash, roles
            FROM users
        """)).mappings().all()
    return [dict(r) for r in rows]

def upsert_user_to_db(username, email, first_name, last_name, password_hash, roles="viewer"):
    with engine.begin() as conn:
        conn.execute(text("""
            INSERT INTO users (username, email, first_name, last_name, password_hash, roles)
            VALUES (:u, :e, :fn, :ln, :ph, :r)
            ON CONFLICT (username) DO UPDATE SET 
                email=EXCLUDED.email,
                first_name=EXCLUDED.first_name,
                last_name=EXCLUDED.last_name,
                password_hash=EXCLUDED.password_hash,
                roles=EXCLUDED.roles,
                updated_at=now();
        """), {"u": username, "e": email, "fn": first_name, "ln": last_name, "ph": password_hash, "r": roles})

def update_password_in_db(username, new_hash):
    with engine.begin() as conn:
        conn.execute(text("""
            UPDATE users SET password_hash=:ph, updated_at=now() WHERE username=:u
        """), {"ph": new_hash, "u": username})

def build_credentials_dict():
    users = fetch_users_from_db()
    usernames = {}
    for u in users:
        usernames[u["username"]] = {
            "email": u["email"],
            "first_name": u["first_name"],
            "last_name": u["last_name"],
            "password": u["password_hash"],  # já hash
            "roles": [] if not u.get("roles") else u["roles"].split(","),
        }
    return {"usernames": usernames}

# ========= SUA LÓGICA DO APP =========
def finance_app():
    # --- idêntico ao seu, apenas movido para cá ---
    def calc_general_stats(df):
        df_data = df.groupby(by="Data")[["Valor"]].sum()
        df_data["lag_1"] = df_data["Valor"].shift(1)
        df_data["Diferença Mensal"] = df_data["Valor"] - df_data["lag_1"]

        df_data["Avg 6M Diferença"] = df_data["Diferença Mensal"].rolling(6).mean()
        df_data["Avg 12M Diferença"] = df_data["Diferença Mensal"].rolling(12).mean()
        df_data["Avg 24M Diferença"] = df_data["Diferença Mensal"].rolling(24).mean()

        df_data["Diferença Mensal Rel."] = df_data["Valor"] / df_data["lag_1"] - 1
        df_data["Evolução 6M Relativa"] = df_data["Valor"].rolling(6).apply(lambda x: x[-1] / x[0] - 1)
        df_data["Evolução 12M Relativa"] = df_data["Valor"].rolling(12).apply(lambda x: x[-1] / x[0] - 1)
        df_data["Evolução 24M Relativa"] = df_data["Valor"].rolling(24).apply(lambda x: x[-1] / x[0] - 1)

        df_data = df_data.drop(columns=["lag_1"])
        return df_data

    st.markdown("""
    # Boas vindas ao meu app de finanças!
    ## App financeiro
    Espero que curta e aproveite o app!
    """)

    file_upload = st.file_uploader("Carregue seu arquivo CSV", type=["csv"])
    if file_upload is not None:
        df = pd.read_csv(file_upload)
        df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y").dt.date

        exp1 = st.expander("Dados Brutos")
        columns_fmt = {"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", help="Valor da transação")}
        exp1.dataframe(df, hide_index=True, column_config=columns_fmt)

        exp2 = st.expander("Instituições")
        df_instituicao = df.pivot_table(index="Data", columns="Instituição", values="Valor")

        tab_data, tab_history, tab_share = exp2.tabs(["Dados", "Histórico", "Distribuição"])

        with tab_data:
            st.dataframe(df_instituicao, hide_index=True)

        with tab_history:
            st.markdown("### Gráfico de Instituições por Data")
            st.line_chart(df_instituicao)

        with tab_share:
            date = st.date_input(
                "Data para Distribuição",
                min_value=df_instituicao.index.min(),
                max_value=df_instituicao.index.max()
            )
            if date not in df_instituicao.index:
                st.warning("Selecione uma data válida.")
            else:
                st.bar_chart(df_instituicao.loc[date])

        exp3 = st.expander("Estatísticas Gerais")
        df_stats = calc_general_stats(df)

        columns_config = {
            "Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", help="Valor total por Data"),
            "Diferença Mensal": st.column_config.NumberColumn("Diferença Mensal", format="R$ %.2f", help="Diferença mensal em relação ao mês anterior"),
            "Avg 6M Diferença": st.column_config.NumberColumn("Média 6M Diferença", format="R$ %.2f", help="Média da diferença mensal nos últimos 6 meses"),
            "Avg 12M Diferença": st.column_config.NumberColumn("Média 12M Diferença", format="R$ %.2f", help="Média da diferença mensal nos últimos 12 meses"),
            "Avg 24M Diferença": st.column_config.NumberColumn("Média 24M Diferença", format="R$ %.2f", help="Média da diferença mensal nos últimos 24 meses"),
            "Diferença Mensal Rel.": st.column_config.NumberColumn("Diferença Mensal Rel.", format="percent", help="Diferença mensal relativa em relação ao mês anterior")
        }
        tab_stats, tab_abs, tab_rel = exp3.tabs(tabs=["Dados", "Histórico de Evolução", "Crescimento Relativo"])

        with tab_stats:
            st.dataframe(df_stats, column_config=columns_config)

        with tab_abs:
            abs_cols = ["Diferença Mensal", "Avg 6M Diferença", "Avg 12M Diferença", "Avg 24M Diferença"]
            st.line_chart(df_stats[abs_cols])

        with tab_rel:
            rel_cols = ["Diferença Mensal Rel.", "Evolução 6M Relativa", "Evolução 12M Relativa", "Evolução 24M Relativa"]
            st.line_chart(data=df_stats[rel_cols])

        with st.expander("Metas"):
            col1, col2 = st.columns(2)

            data_inicio_meta = col1.date_input("Início da Meta", max_value=df_stats.index.max())
            data_filtrada = df_stats.index[df_stats.index <= data_inicio_meta][-1]

            custos_fixos = col1.number_input("Custos Fixos", min_value=0., format="%.2f", help="Valor dos custos fixos mensais")
            salario_bruto = col2.number_input("Salário Bruto", min_value=0., format="%.2f")
            salario_liquido = col2.number_input("Salário Líquido", min_value=0., format="%.2f")

            valor_inicio = df_stats.loc[data_filtrada]["Valor"]
            col1.markdown(f"**Patrimônio Inicial**: R$ {valor_inicio:.2f}")

            col1_pot, col2_pot = st.columns(2)
            mensal = salario_liquido - custos_fixos
            anual = mensal * 12

            with col1_pot.container(border=True):
                st.markdown(f"**Potencial Arredação Mensal**: \n \n R$ {mensal:.2f}")

            with col2_pot.container(border=True):
                st.markdown(f"**Potencial Arredação Anual**: \n \n R$ {anual:.2f}")

            with st.container(border=True):
                col1_meta, col2_meta = st.columns(2)
                with col1_meta:
                    meta_estipulada = st.number_input("Meta Estipulada", min_value=0., format="%.2f", value=anual)
                with col2_meta:
                    patrimonio_final = valor_inicio + meta_estipulada
                    st.markdown(f"**Patrimônio Final Estimado Pós Meta**: \n \n R$ {patrimonio_final:.2f}")

# ========= APP (LOGIN + CONTEÚDO) =========
st.set_page_config(page_title="Finanças", page_icon=":sparkles:")
ensure_users_table()

# Carrega credenciais a partir do banco e cria autenticador
credentials = build_credentials_dict()
cookie_cfg = {"name": "finance_auth", "key": "troque-esta-chave", "expiry_days": 7}
authenticator = stauth.Authenticate(credentials, cookie_cfg["name"], cookie_cfg["key"], cookie_cfg["expiry_days"], auto_hash=False)

st.sidebar.header("Acesso")
try:
    authenticator.login(location="sidebar", fields={
        "Form name": "Login",
        "Username": "Usuário",
        "Password": "Senha",
        "Login": "Entrar"
    })
except Exception as e:
    st.sidebar.error(str(e))

if st.session_state.get("authentication_status"):
    st.sidebar.success(f"Olá, {st.session_state.get('name')}!")
    authenticator.logout(location="sidebar", button_name="Sair")
    finance_app()
else:
    st.info("Faça login para continuar.")

st.divider()
st.subheader("Criar conta")

email_registered, username_registered, name_registered = authenticator.register_user()

if email_registered and username_registered:
    # segurança extra: pegue o registro diretamente do session_state se existir
    ucreds = st.session_state.get("credentials", {}).get("usernames", {})
    urec = ucreds.get(username_registered)

    if urec is not None:
        # senha já vem hash em urec["password"]
        upsert_user_to_db(
            username=username_registered,
            email=email_registered,
            first_name=urec.get("first_name", ""),
            last_name=urec.get("last_name", ""),
            password_hash=urec["password"],
            roles="viewer",
        )
        st.success("Usuário registrado e salvo no Postgres!")
    else:
        st.warning("Não foi possível ler as credenciais recém-criadas do session_state.")


# Reset de senha (se logado)
if st.session_state.get("authentication_status"):
    st.subheader("Trocar senha")
    try:
        if authenticator.reset_password(st.session_state["username"], location="main"):
            ucreds = st.session_state.get("credentials", {}).get("usernames", {})
            me = ucreds.get(st.session_state["username"])
            if me and "password" in me:
                update_password_in_db(st.session_state["username"], me["password"])
                st.success("Senha alterada com sucesso.")
            else:
                st.warning("Não foi possível localizar a nova senha no session_state.")
    except Exception as e:
        st.error(e)

