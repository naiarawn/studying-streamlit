import streamlit as st

import pandas as pd

# editando nome do título e ícone da página
st.set_page_config(page_title="Finanças", page_icon=":sparkles:")

st.markdown("""
# Boas vindas ao meu app de finanças!
## App financeiro
Espero que curta e aproveite o app!
""")

# widget de upload de arquivo
file_upload = st.file_uploader("Carregue seu arquivo CSV", type=["csv"])
# Verifica se um arquivo foi carregado
if file_upload is not None:
    # Lê o arquivo CSV
    df = pd.read_csv(file_upload)
    df["Data"] = pd.to_datetime(df["Data"], format="%d/%m/%Y").dt.date
    # Exibe o DataFrame
    exp1 = st.expander("Dados Brutos")
    # Formata a coluna "Valor" para exibição monetária
    columns_fmt = {"Valor": st.column_config.NumberColumn("Valor", format="R$ %.2f", help="Valor da transação")}
    exp1.dataframe(df, hide_index=True, column_config=columns_fmt)

    # Pivot table para visualizar os dados por Instituição
    exp2 = st.expander("Instituições")
    df_instituicao = df.pivot_table(index = "Data", columns = "Instituição", values = "Valor")

    # Abas para visualizar os dados
    tab_data, tab_history, tab_share = exp2.tabs(["Dados", "Histórico", "Distribuição"])

    with tab_data:
      # Exibe o DataFrame de Instituições
      st.dataframe(df_instituicao, hide_index=True)
  
    with tab_history:
      # Gráfico de linha para visualizar os dados por Instituição por Data
      st.markdown("### Gráfico de Instituições por Data")
      st.line_chart(df_instituicao)
    
    with tab_share:
      # Gráfico de barras para visualizar a última data por Instituição
      # Filtro
      date = st.date_input("Data para Distribuição",
                           min_value=df_instituicao.index.min(),
                           max_value=df_instituicao.index.max())
      # Obter a última data do DataFrame
      if date not in df_instituicao.index:
         st.warning("Selecione uma data válida.")
      st.bar_chart(df_instituicao.loc[date])