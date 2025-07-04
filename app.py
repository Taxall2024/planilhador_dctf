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

# Função para montar o DataFrame R10 com colunas solicitadas e junção com outros tipos

def montar_df_r10(conteudos):
    # Agrupa registros por tipo
    registros = {tipo: [] for tipo in LAYOUTS_COMPLETOS}
    for nome_arquivo, linhas in conteudos:
        for linha in linhas:
            tip = linha[:3].strip()
            if tip in LAYOUTS_COMPLETOS:
                reg = {campo: linha[ini-1:fim].strip() for campo, ini, fim in LAYOUTS_COMPLETOS[tip]}
                registros[tip].append(reg)

    # DataFrames por tipo
    df_r10 = pd.DataFrame(registros.get('R10', []))
    df_r11 = pd.DataFrame(registros.get('R11', []))
    df_r12 = pd.DataFrame(registros.get('R12', []))
    df_r14 = pd.DataFrame(registros.get('R14', []))
    df_r15 = pd.DataFrame(registros.get('R15', []))

    # Chaves de junção (ajuste conforme necessário)
    chaves = ['CNPJ', 'MOFG', 'GrupoTributo', 'CodReceita',
              'Periodicidade', 'AnoApuracao', 'MesPeriodo',
              'DiaPeriodo', 'OrdemEstab', 'CNPJIncorp']

    # Função auxiliar de merge
    def merge_valor(df_base, df_other, coluna):
        if df_other.empty:
            df_base[coluna] = 0.0
        else:
            df_base = df_base.merge(
                df_other[chaves + [coluna]],
                on=chaves,
                how='left'
            )
            df_base[coluna] = df_base[coluna].fillna(0).astype(float)
        return df_base

    # Junta colunas de crédito vinculados
    df = merge_valor(df_r10, df_r11, 'ValorPago')
    df = merge_valor(df,   df_r12, 'ValorCompensado')
    df = merge_valor(df,   df_r15, 'ValorParcelado')
    df = merge_valor(df,   df_r14, 'ValorSuspenso')

    # Campos calculados
    df['Vlr Total Crédito Vinculado'] = (
        df['ValorPago'] + df['ValorCompensado'] +
        df['ValorParcelado'] + df['ValorSuspenso']
    )
    df['Vlr Débito Apurado'] = df['ValorDebito'].astype(float)
    df['Vlr Saldo Pagar Débito'] = (
        df['Vlr Débito Apurado'] - df['Vlr Total Crédito Vinculado']
    )
    df['Vlr Total Imposto Apurado'] = df['Vlr Débito Apurado']

    # Colunas em branco
    df['Descrição DARF'] = ''
    df['Vlr Total Retenções'] = ''

    # === AQUI: transforma YYYYMM em DD/MM/AAAA com dia = 01 ===
    df['MOFG'] = pd.to_datetime(df['MOFG'], format='%Y%m').dt.strftime('01/%m/%Y')

    # —————————————————————————————
    # Mapeamento de GrupoTributo para descrição
    grupo_dict = {
        '01': '01 – IRPJ',
        '02': '02 – IRRF',
        '03': '03 – IPI',
        '04': '04 – IOF',
        '05': '05 – CSLL',
        '06': '06 – PIS/PASEP',
        '07': '07 – COFINS',
        '08': '08 – CPMF',
        '09': '09 – CIDE',
        '10': '10 – RET/PAGAMENTO UNIFICADO DE TRIBUTOS',
        '11': '11 – CSRF',
        '12': '12 – COSIRF',
        '13': '13 – CONTRIBUIÇÕES PREVIDENCIÁRIAS'
    }
    # Aplica o mapeamento, mantendo valores não encontrados inalterados
    df['GrupoTributo'] = df['GrupoTributo'].map(grupo_dict).fillna(df['GrupoTributo'])
    # —————————————————————————————

    # —————————————————————————————
    # Mapeamento de Balanço Redução
    balanco_dict = {
        '0': '0 – Sem Balanço de Redução',
        '1': '1 – Com Balanço de Redução'
    }
    # Aplica o mapeamento, mantendo valores não encontrados inalterados
    df['BalancoReducao'] = df['BalancoReducao'].map(balanco_dict).fillna(df['BalancoReducao'])
    # —————————————————————————————

    # —————————————————————————————
    # Mapeamento de Saldo Débito Quotas
    quotas_dict = {
        '0': '0 – Sem divisão em quotas',
        '1': '1 – Com divisão em quotas'
    }
    # Aplica o mapeamento, mantendo valores não encontrados inalterados
    df['DivisaoQuotas'] = df['DivisaoQuotas'].map(quotas_dict).fillna(df['DivisaoQuotas'])
    # —————————————————————————————

    # —————————————————————————————
    # Mapeamento de Débito SCP/INC
    scp_dict = {
        '0': '0 – Não é SCP nem INC',
        '1': '1 – SCP',
        '2': '2 – INC'
    }
    # Aplica o mapeamento, mantendo valores não encontrados inalterados
    df['DebitoSCP'] = df['DebitoSCP'].map(scp_dict).fillna(df['DebitoSCP'])
    # —————————————————————————————

    # Renomear para nomes finais
    df = df.rename(columns={
        'CNPJ': 'CNPJ',
        'MOFG': 'Período',
        'GrupoTributo': 'Grupo',
        'CodReceita': 'Código Receita DARF',
        'Periodicidade': 'Periodicidade',
        'AnoApuracao': 'Ano Apuração',
        'MesPeriodo': 'Mês/Bim/Trim/Quad/Sem Apuração',
        'DiaPeriodo': 'Dia/Sem/Quin/Dec',
        'OrdemEstab': 'Ordem',
        'CNPJIncorp': 'CNPJ Incorporação',
        'ValorPago': 'Vlr Crédito Vinculado Pagamento',
        'ValorCompensado': 'Vlr Crédito Vinculado Compensações',
        'ValorParcelado': 'Vlr Crédito Vinculado Parcelamento',
        'ValorSuspenso': 'Vlr Crédito Vinculado Suspensão',
        'BalancoReducao': 'Balanço Redução',
        'DivisaoQuotas': 'Saldo Débito Quotas',
        'DebitoSCP': 'Débito SCP/INC',
    })

    # —————————————————————————————
    # Ajuste de decimais (os 2 últimos dígitos são centavos)
    cols_decimal = [
        'Vlr Débito Apurado',
        'Vlr Crédito Vinculado Pagamento',
        'Vlr Crédito Vinculado Compensações',
        'Vlr Crédito Vinculado Parcelamento',
        'Vlr Crédito Vinculado Suspensão',
        'Vlr Total Crédito Vinculado',
        'Vlr Saldo Pagar Débito',
        'Vlr Total Imposto Apurado',
        'Vlr Total Retenções'
    ]

    # Converte strings em numérico, preenche vazios com 0 e divide por 100
    for col in cols_decimal:
        df[col] = (
            pd.to_numeric(df[col], errors='coerce')  # converte '' ou não-numérico em NaN
              .fillna(0)                            # NaN vira zero
              .divide(100)                          # milhar → real
        )
    # —————————————————————————————


    # Reordena colunas conforme solicitado
    colunas = [
        'CNPJ', 'Período', 'Grupo', 'Código Receita DARF',
        'Descrição DARF', 'Periodicidade', 'Ano Apuração',
        'Mês/Bim/Trim/Quad/Sem Apuração', 'Dia/Sem/Quin/Dec',
        'Ordem', 'CNPJ Incorporação', 'Vlr Débito Apurado',
        'Vlr Crédito Vinculado Pagamento', 'Vlr Crédito Vinculado Compensações',
        'Vlr Crédito Vinculado Parcelamento', 'Vlr Crédito Vinculado Suspensão',
        'Vlr Total Crédito Vinculado', 'Vlr Saldo Pagar Débito',
        'Vlr Total Imposto Apurado', 'Vlr Total Retenções',
        'Balanço Redução', 'Saldo Débito Quotas', 'Débito SCP/INC'
    ]
    return df[colunas]

# STREAMLIT: interface para R10 apenas
st.set_page_config(page_title="R10 Export", layout="centered")
st.title("Exportador R10 para Excel")

arquivos = st.file_uploader(
    "Selecione arquivos .dec para gerar o R10 Excel", type="dec", accept_multiple_files=True
)
if arquivos:
    conteudos = carregar_arquivos(arquivos)
    st.success(f"{len(conteudos)} arquivo(s) carregado(s). Preparando R10...")

    df_r10 = montar_df_r10(conteudos)

    # Gerar Excel em memória
    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
        df_r10.to_excel(writer, sheet_name='R10', index=False)
        # Formatação opcional (números, largura de colunas)
    buffer.seek(0)

    st.download_button(
        label="📥 Baixar R10.xlsx",
        data=buffer.getvalue(),
        file_name="R10_export.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
