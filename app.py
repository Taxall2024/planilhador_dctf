import streamlit as st
import pandas as pd
import io
import zipfile

from inputs.dctf_loader import carregar_arquivos
from calculos.dctf_layouts import LAYOUTS_COMPLETOS

def parse_registro(linha, layout):
    return {campo: linha[ini - 1:fim].strip() for campo, ini, fim in layout}

def gerar_dataframes_por_registro(nome_arquivo, linhas):
    registros_por_tipo = {tipo: [] for tipo in LAYOUTS_COMPLETOS.keys()}
    for linha in linhas:
        tipo = linha[:3].strip()
        if tipo in LAYOUTS_COMPLETOS:
            layout = LAYOUTS_COMPLETOS[tipo]
            registro = parse_registro(linha, layout)
            registros_por_tipo[tipo].append(registro)

    dataframes = {}
    for tipo, registros in registros_por_tipo.items():
        if registros:  # Só cria aba se houver dados
            df = pd.DataFrame(registros)
            dataframes[tipo] = df
    return dataframes

# --- STREAMLIT APP ---

st.set_page_config(page_title="DCTF para Excel", layout="centered")
st.title("Conversor de Arquivo DCTF (.dec) para Excel")

arquivo_dec = st.file_uploader("Selecione um arquivo .dec", type="dec")

if arquivo_dec:
    conteudos = carregar_arquivos([arquivo_dec])
    nome_arquivo, linhas = conteudos[0]

    st.success(f"Abrindo {nome_arquivo}...")

    dataframes = gerar_dataframes_por_registro(nome_arquivo, linhas)

    if not dataframes:
        st.warning("Nenhum registro válido encontrado no arquivo.")
    else:
        st.info("Gerando planilha Excel com abas por tipo de registro...")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for tipo, df in dataframes.items():
                df.to_excel(writer, sheet_name=tipo, index=False)

        st.success("Planilha gerada com sucesso!")
        st.download_button(
            label="📥 Baixar Planilha Excel",
            data=output.getvalue(),
            file_name="dctf_planilhada.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
