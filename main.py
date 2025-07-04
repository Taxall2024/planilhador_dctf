import streamlit as st
import pandas as pd
import io
from pathlib import Path
from inputs.dctf_loader import carregar_arquivos

# Carregar layouts
layout_code = Path("calculos/dctf_layouts.py").read_text()
layout_namespace = {}
exec(layout_code, layout_namespace)
LAYOUTS_COMPLETOS = layout_namespace["LAYOUTS_COMPLETOS"]

def parse_registro(linha, layout):
    return {campo: linha[ini - 1:fim].strip() for campo, ini, fim in layout}

def processar_e_formatar_para_excel(conteudos):
    dataframes_por_tipo = {tipo: [] for tipo in LAYOUTS_COMPLETOS.keys()}

    for nome_arquivo, linhas in conteudos:
        for linha in linhas:
            tipo = linha[:3].strip()
            if tipo in LAYOUTS_COMPLETOS:
                layout = LAYOUTS_COMPLETOS[tipo]
                registro = parse_registro(linha, layout)
                registro["Arquivo_Origem"] = nome_arquivo.split("/")[-1]
                dataframes_por_tipo[tipo].append(registro)

    dataframes_finais = {}
    for tipo, registros in dataframes_por_tipo.items():
        if registros:
            df = pd.DataFrame(registros)
            cols = ["Arquivo_Origem"] + [col for col in df.columns if col != "Arquivo_Origem"]
            df = df[cols]
            dataframes_finais[tipo] = df

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        workbook = writer.book
        format_brl = workbook.add_format({'num_format': '#,##0.00'})

        for tipo, df in dataframes_finais.items():
            for col in df.columns:
                if "valor" in col.lower() or "debito" in col.lower():
                    try:
                        df[col] = (
                            df[col]
                            .astype(str)
                            .str.zfill(15)
                            .str.lstrip("0")
                            .replace("", "0")
                            .astype(int) / 100
                        )
                    except:
                        pass

            df.to_excel(writer, sheet_name=tipo[:31], index=False)
            worksheet = writer.sheets[tipo[:31]]
            for i, col in enumerate(df.columns):
                if "valor" in col.lower() or "debito" in col.lower():
                    worksheet.set_column(i, i, 15, format_brl)
                else:
                    worksheet.set_column(i, i, 20)

    output.seek(0)
    return output

# STREAMLIT INTERFACE
st.set_page_config(page_title="Conversor DCTF", layout="centered")
st.title("Conversor de Arquivos DCTF (.dec) para Excel")

arquivos_dec = st.file_uploader("Selecione um ou mais arquivos .dec", type="dec", accept_multiple_files=True)

if arquivos_dec:
    conteudos = carregar_arquivos(arquivos_dec)
    st.success(f"{len(conteudos)} arquivo(s) carregado(s). Processando...")

    excel_bytesio = processar_e_formatar_para_excel(conteudos)

    st.download_button(
        label="📥 Baixar Excel formatado",
        data=excel_bytesio.getvalue(),
        file_name="dctf_unificado_formatado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
