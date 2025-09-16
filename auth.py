# --- topo do arquivo ---
import streamlit as st
import pandas as pd
import streamlit_authenticator as stauth
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from main import finance_app

st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")

# ========= CONEXÃO COM POSTGRES =========
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
            "password": u["password_hash"],             # hash vindo do DB
            "roles": [] if not u.get("roles") else u["roles"].split(","),
        }
    return {"usernames": usernames}

# --- sessão: evita KeyError e usa o formato certo ---
if "credentials" not in st.session_state:
    st.session_state["credentials"] = build_credentials_dict()

# --- garanta a tabela criada ---
ensure_users_table()

# --- um único autenticador (padronize o cookie_cfg) ---
cookie_cfg = {"name": "finance_auth", "key": "troque-esta-chave", "expiry_days": 7}
authenticator = stauth.Authenticate(
    st.session_state["credentials"],
    cookie_cfg["name"], cookie_cfg["key"], cookie_cfg["expiry_days"],
    auto_hash=False
)

# ---------------- ESTADO DE AUTENTICAÇÃO ----------------
auth_status = st.session_state.get("authentication_status")

if auth_status:
    # ================== ÁREA LOGADA ==================
    # (nada de telas de login/signup aqui)
    authenticator.logout(location="sidebar", button_name="Sair")
    finance_app()  # seu app financeiro protegido
else:
    # ================== TELA DE LOGIN ==================
    st.title("Bem-vindo 👋")
    st.subheader("Faça login para continuar")

    with st.container(border=True):
        try:
            authenticator.login(
                location="main",
                fields={
                    "Form name": "Acesso",
                    "Username": "Usuário",
                    "Password": "Senha",
                    "Login": "Entrar",   # botão de submit
                },
            )
        except Exception as e:
            st.error(str(e))

    # Se acabou de logar com sucesso, recarrega para esconder formulários
    if st.session_state.get("authentication_status"):
        st.rerun()

    # ================== TELA DE CADASTRO ==================
    st.markdown("---")
    st.markdown("**Não tem conta? Registre-se**")
    with st.container(border=True):
        try:
            email, username, name = authenticator.register_user(
                location="main",
                fields={
                    "Form name": "Cadastro",
                    "Email": "E-mail",
                    "Username": "Usuário",
                    "First name": "Nome",
                    "Last name": "Sobrenome",
                    "Password": "Senha",
                    "Repeat password": "Repita a senha",
                    "Register": "Registrar",  # botão de submit
                },
                clear_on_submit=True,
            )

            if email and username:
                # pega as credenciais recém-criadas do session_state e persiste no Postgres
                urec = st.session_state["credentials"]["usernames"][username]
                upsert_user_to_db(
                    username=username,
                    email=email,
                    first_name=urec.get("first_name", ""),
                    last_name=urec.get("last_name", ""),
                    password_hash=urec["password"],  # hash gerado pela lib
                    roles="viewer",
                )
                st.success("Conta criada com sucesso! Você já pode fazer login.")
                # Opcional: já força um reload para manter a UI limpa
                st.rerun()
        except Exception as e:
            st.error(str(e))
