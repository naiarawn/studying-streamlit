import streamlit as st
import streamlit_authenticator as stauth
import yaml
from yaml.loader import SafeLoader
from home import pagina_inicial
from main import finance_app

st.set_page_config(page_title="Finanças", page_icon=":sparkles:", layout="wide")

with open('config.yaml') as file:
    config = yaml.load(file, Loader=SafeLoader)

authenticator = stauth.Authenticate(
    config['credentials'],
    config['cookie']['name'],
    config['cookie']['key'],
    config['cookie']['expiry_days']
)

authenticator.login()

if st.session_state["authentication_status"]:
    authenticator.logout('Logout', 'main')
    st.sidebar.title('Menu')
    st.sidebar.write(f'Welcome *{st.session_state["name"]}*')
    paginas = st.sidebar.selectbox("Selecione uma página", ["Página Inicial", "App Financeiro"])
    if paginas == "Página Inicial":
        pagina_inicial()
    elif paginas == "App Financeiro":
        finance_app()
elif st.session_state["authentication_status"] is False:
    st.error('Username/password is incorrect')
elif st.session_state["authentication_status"] is None:
    st.warning('Please enter your username and password')

# with st.form("signin_form"):
#   st.title("Sign In Page")
#   st.caption("Please enter your credentials to sign in.")

#   st.divider()
#   username = st.text_input("Username")
#   password = st.text_input("Password", type="password")

#   submit_btn = st.form_submit_button("Sign In", type="primary", use_container_width=True)

#   google_btn = st.form_submit_button("Sign in with Google", type="secondary", use_container_width=True)