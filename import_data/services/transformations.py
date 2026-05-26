import pandas as pd
import numpy as np
from import_data.config import DB_CONFIG, DATASET_CONFIG, SERVERS
import pyodbc



'''
    Aqui ficarão tratativas exclusivas para determinada rotina.
    Cada rotina, se precisa de uma tratativa de dados que seja pontual, será feita aqui
'''
def _VALIDADOS_CALLSENSE_MD(df, **kwargs):

    # df['data_recebimento'] = pd.to_datetime(df['data_recebimento'], dayfirst=True)
    # df['DATA_ENVIO'] = pd.to_datetime(df['DATA_ENVIO'], dayfirst=True)
    # df['data_retorno'] = pd.to_datetime(df['DATA RETORNO'], dayfirst=True)
    # df['DataHora'] = pd.to_datetime(df['data_hora'], dayfirst=True)
    df = df.astype(object).where(pd.notna(df), None)

    return df


def _TRATATIVAS_FINANCEIRO(df, **kwargs):
    conn = kwargs["conn"]

    cursor = conn.cursor()
    cursor.execute("""
        SELECT
            CR_FuncionarioRM as CR,
            HEAD_QUALIDADE as Gestor_Qualidade,
            GERENTE_QUALIDADE
            
        FROM DIRETORIA_CX.HUB_ESTRUTURANTE.DIM_CR_COMPLETA
        WHERE is_current = 1
    """)
    rows = cursor.fetchall()

    columns = [column[0] for column in cursor.description]
    df_dim_cr = pd.DataFrame.from_records(rows, columns=columns)

    total_linhas_antes = df.shape[0]

    df = df.replace([np.inf, -np.inf], None)
    df = df.where(pd.notnull(df), None)
    df = df.replace({np.nan: None})
    df = df.where(pd.notnull(df), None)

    df_result = df.merge(
        df_dim_cr[['CR', 'Gestor_Qualidade']],
        how='left',
        on='CR'
    )

    df_result = df_result.replace({np.nan: None})
    df_result = df_result.where(pd.notnull(df_result), None)

    total_linhas_depois = df_result.shape[0]

    print(total_linhas_antes)
    print(total_linhas_depois)
    return df_result

