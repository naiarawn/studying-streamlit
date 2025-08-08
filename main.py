import streamlit as st
import pandas as pd


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
      abs_cols = [
          "Diferença Mensal",
          "Avg 6M Diferença",
          "Avg 12M Diferença",
          "Avg 24M Diferença"
      ]
      st.line_chart(df_stats[abs_cols])

    with tab_rel:
        rel_cols = [
            "Diferença Mensal Rel.",
            "Evolução 6M Relativa",
            "Evolução 12M Relativa",
            "Evolução 24M Relativa",
        ]
        st.line_chart(data=df_stats[rel_cols])
