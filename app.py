import streamlit as st
import pandas as pd
import io
from inputs.dctf_loader import carregar_arquivos
from calculos.dctf_layouts import LAYOUTS_COMPLETOS

def parse_registro(linha, layout):
    return {campo: linha[ini - 1:fim].strip() for campo, ini, fim in layout}

def processar_arquivos(conteudos):
    dataframes_por_tipo = {tipo: [] for tipo in LAYOUTS_COMPLETOS.keys()}

    for nome_arquivo, linhas in conteudos:
        for linha in linhas:
            tipo = linha[:3].strip()
            if tipo in LAYOUTS_COMPLETOS:
                layout = LAYOUTS_COMPLETOS[tipo]
                registro = parse_registro(linha, layout)
                registro["Arquivo_Origem"] = nome_arquivo
                dataframes_por_tipo[tipo].append(registro)

    dataframes_finais = {}
    for tipo, registros in dataframes_por_tipo.items():
        if registros:
            df = pd.DataFrame(registros)
            cols = ["Arquivo_Origem"] + [col for col in df.columns if col != "Arquivo_Origem"]
            df = df[cols]  # Garante que 'Arquivo_Origem' venha primeiro
            dataframes_finais[tipo] = df

    return dataframes_finais

# --- STREAMLIT APP ---
st.set_page_config(page_title="DCTF para Excel", layout="centered")
st.title("Conversor de Arquivos DCTF (.dec) para Excel")

arquivos_dec = st.file_uploader("Selecione os arquivos .dec", type="dec", accept_multiple_files=True)

if arquivos_dec:
    conteudos = carregar_arquivos(arquivos_dec)
    st.success(f"{len(conteudos)} arquivo(s) carregado(s).")

    dataframes = processar_arquivos(conteudos)

    if not dataframes:
        st.warning("Nenhum registro válido encontrado nos arquivos.")
    else:
        st.info("Gerando planilha Excel com abas por tipo de registro...")

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for tipo, df in dataframes.items():
                aba = tipo[:31]  # limite do Excel
                df.to_excel(writer, sheet_name=aba, index=False)

        st.success("Planilha gerada com sucesso!")
        st.download_button(
            label="📥 Baixar Planilha Excel",
            data=output.getvalue(),
            file_name="dctf_planilhada_unificada.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )
