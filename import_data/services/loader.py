import pandas as pd
import pyodbc
from import_data.config import DB_CONFIG, DATASET_CONFIG, SERVERS
import import_data.services.transformations as tf
from import_data.sql_scripts.extra_sql import executar as exsql
from import_data.services.connections import montar_conn_str
import numpy as np
import hashlib
import os
from logger import log
pd.options.display.float_format = '{:.6f}'.format


def get_db_connection(server_key):
    server = SERVERS[server_key]
    conn_str = (
        f"DRIVER={server['driver']};"
        f"SERVER={server['server']};"
        f"DATABASE={server['database']};"
        f"Trusted_Connection={server['trusted_connection']};"
    )
    return pyodbc.connect(conn_str)


def get_db_connection_from_id(conexao_id):
    """Conecta usando uma conexão salva pelo usuário."""
    conn_str, erro = montar_conn_str(conexao_id)
    if erro:
        raise Exception(f"Conexão não encontrada: {erro}")
    return pyodbc.connect(conn_str)


def registrar_log_direto(arquivo_nome, tabela_destino, status, usuario, mensagem=""):
    conn = None
    try:
        conn = get_db_connection(DB_CONFIG['log_server'])
        cursor = conn.cursor()
        cursor.execute(f"""
            INSERT INTO {DB_CONFIG['log_table']}
            (arquivo_nome, tabela_destino, status_processo, usuario_maquina, mensagem_erro, data_execucao)
            VALUES (?, ?, ?, ?, ?, GETDATE())
        """, (arquivo_nome, tabela_destino, status, usuario, mensagem))
        conn.commit()
    except Exception as e:
        log.error(f"Erro ao registrar log direto: {e}")
    finally:
        if conn:
            conn.close()


def generate_hash(row):
    text_row = "|".join([str(val) if val is not None and pd.notna(val) else "" for val in row])
    return hashlib.sha256(text_row.encode('utf-8')).hexdigest()


def process_and_load(filepath, dataset_key, delimiter, user_name, tipo_arquivo, conexao_id=None):
    conn = None
    log_id = None
    try:
        table_name       = DATASET_CONFIG[dataset_key]["table"]
        mapeamento       = DATASET_CONFIG[dataset_key]["columns"]
        usar_scd2        = DATASET_CONFIG[dataset_key].get("usar_scd2", False)
        delete_historico = DATASET_CONFIG[dataset_key].get("delete_historico", False)
        coluna_data      = DATASET_CONFIG[dataset_key].get("coluna_data", False)
        colunas_texto    = DATASET_CONFIG[dataset_key].get("colunas_texto", False)

        # ── Conexão de destino ────────────────────────────────────────────────
        # Prioridade: conexao_id do usuário > server_key do config
        if conexao_id:
            conn = get_db_connection_from_id(conexao_id)
        else:
            server_key = DATASET_CONFIG[dataset_key]["server"]
            conn = get_db_connection(server_key)

        # Leitura do arquivo
        if tipo_arquivo == 'csv':
            df = pd.read_csv(filepath, sep=delimiter, dtype=dict.fromkeys(colunas_texto, str), encoding='utf-8')
        else:
            df = pd.read_excel(filepath, sheet_name='base')

        df.columns = [c.strip() for c in df.columns]

        # Mapeamento das colunas válidas
        df = df[list(mapeamento.keys())]
        df.rename(columns=mapeamento, inplace=True)
        df = df.replace({np.nan: None})

        # Padroniza datas
        log.info("Padronizando formatos de data...")
        for col in df.columns:
            if 'data' in col.lower() or 'dt_' in col.lower() or '_start' in col.lower() or 'datahora' in col.lower():
                try:
                    df[col] = pd.to_datetime(df[col], dayfirst=True, errors='coerce')
                    df[col] = df[col].dt.strftime('%Y-%m-%d %H:%M:%S').where(df[col].notnull(), None)
                    log.info(f"Coluna [{col}]: Padronizada.")
                except Exception as e:
                    log.warning(f"Não foi possível padronizar [{col}]: {e}")

        cursor = conn.cursor()

        kwargs = {"conn": conn}

        transform_name = DATASET_CONFIG[dataset_key].get("transform")
        if transform_name:
            func = getattr(tf, transform_name)
            df = func(df, **kwargs)

        if usar_scd2:
            hash_cols = DATASET_CONFIG[dataset_key]["hash_columns"]
            df['hash_diff'] = df[hash_cols].apply(generate_hash, axis=1)

        df = df.replace({np.nan: None})
        df = df.where(pd.notnull(df), None)

        # Converte notação científica
        colunas_decimais = DATASET_CONFIG[dataset_key].get("colunas_decimais", [])
        for col in colunas_decimais:
            if col in df.columns:
                df[col] = df[col].apply(
                    lambda x: f"{float(x):.6f}" if x is not None else None
                )

        # Log inicial
        log_conn = get_db_connection(DB_CONFIG['log_server'])
        log_cursor = log_conn.cursor()
        log_cursor.execute(f"""
            INSERT INTO {DB_CONFIG['log_table']}
            (arquivo_nome, tabela_destino, status_processo, usuario_maquina)
            VALUES (?, ?, ?, ?)
        """, (os.path.basename(filepath), table_name, 'PROCESSANDO', user_name))
        log_cursor.execute("SELECT @@IDENTITY")
        log_id = log_cursor.fetchone()[0]
        log_conn.commit()

        # Carga na temp
        log.info("Carga na temporária...")
        cursor.fast_executemany = True
        cols_to_insert = list(df.columns)
        temp_columns   = ", ".join([f"[{c}] NVARCHAR(MAX)" for c in cols_to_insert])
        cursor.execute(f"CREATE TABLE #stg_silver_{dataset_key} ({temp_columns})")
        cursor.setinputsizes([(pyodbc.SQL_WVARCHAR, 0, 0)] * len(cols_to_insert))
        placeholders = ", ".join(["?"] * len(cols_to_insert))
        insert_temp  = f"INSERT INTO #stg_silver_{dataset_key} ({', '.join([f'[{c}]' for c in cols_to_insert])}) VALUES ({placeholders})"
        params       = [tuple(x) for x in df.values]

        log.info("Executando inserção na temporária...")
        cursor.executemany(insert_temp, params)
        log.info("Carga na temporária concluída!")
        cols_str = ", ".join([f"[{c}]" for c in cols_to_insert])

        def montar_cols_select(cols_to_insert, colunas_decimais):
            cols_select = []
            for c in cols_to_insert:
                if c in colunas_decimais:
                    cols_select.append(f"TRY_CAST([{c}] AS DECIMAL(18,4)) AS [{c}]")
                else:
                    cols_select.append(f"[{c}]")
            return ", ".join(cols_select)

        assert usar_scd2 != delete_historico, "Erro: usar_scd2 e delete_historico não podem ter o mesmo valor."

        if usar_scd2:
            nk_column       = DATASET_CONFIG[dataset_key]["pk_origem"]
            cols_select_str = montar_cols_select(cols_to_insert, colunas_decimais)
            update_sql = f"""
                UPDATE target
                SET target.dt_fim = GETDATE(), target.is_current = 0
                FROM {table_name} AS target
                INNER JOIN #stg_silver_{dataset_key} AS source ON target.[{nk_column}] = source.[{nk_column}]
                WHERE target.is_current = 1 AND target.hash_diff <> source.hash_diff;
            """
            insert_sql = f"""
                INSERT INTO {table_name} ({cols_str}, dt_inicio, is_current, dt_carga)
                SELECT {cols_select_str}, GETDATE(), 1, GETDATE()
                FROM #stg_silver_{dataset_key} AS source
                WHERE NOT EXISTS (
                    SELECT 1 FROM {table_name} AS target
                    WHERE target.[{nk_column}] = source.[{nk_column}]
                    AND target.is_current = 1
                ) OR EXISTS (
                    SELECT 1 FROM {table_name} AS target
                    WHERE target.[{nk_column}] = source.[{nk_column}]
                    AND target.is_current = 1
                    AND target.hash_diff <> source.hash_diff
                );
            """
            cursor.execute(update_sql)
            cursor.execute(insert_sql)

        elif delete_historico:
            if coluna_data:
                df[coluna_data] = pd.to_datetime(df[coluna_data])
                data_min = df[coluna_data].min().date()
                data_max = df[coluna_data].max().date()
                delete_sql = f"DELETE FROM {table_name} WHERE {coluna_data} between ? and ?"
                cursor.execute(delete_sql, (data_min, data_max))
                conn.commit()
            else:
                ano     = df['Ano'].max()
                mes_min = df['Mes'].min()
                mes_max = df['Mes'].max()
                delete_sql = f"""
                    DELETE FROM {table_name}
                    WHERE Ano = {ano}
                    AND Mes BETWEEN {mes_min} AND {mes_max}
                """
                cursor.execute(delete_sql)
                conn.commit()

            cols_select_str = montar_cols_select(cols_to_insert, colunas_decimais)
            log.info("Temporária → Tabela final")
            append_sql = f"""
                INSERT INTO {table_name} ({cols_str}, dt_carga)
                SELECT {cols_select_str}, GETDATE()
                FROM #stg_silver_{dataset_key}
            """
            cursor.execute(append_sql)

        else:
            cols_select_str = montar_cols_select(cols_to_insert, colunas_decimais)
            append_sql = f"""
                INSERT INTO {table_name} ({cols_str}, dt_carga)
                SELECT {cols_select_str}, GETDATE()
                FROM #stg_silver_{dataset_key}
            """
            cursor.execute(append_sql)

        conn.commit()

        # Log de sucesso
        log_cursor.execute(f"""
            UPDATE {DB_CONFIG['log_table']}
            SET status_processo = 'SUCESSO', linhas_inseridas = ?
            WHERE id = ?
        """, (len(df), log_id))
        log_conn.commit()
        log_conn.close()

        # Extra SQL se existir
        extra_sql_name = DATASET_CONFIG[dataset_key].get("extra_sql")
        if extra_sql_name:
            log.info(f"Executando extra_sql: {extra_sql_name}...")
            exsql(conn, extra_sql_name)

        log.info(f"Importação concluída: {table_name} | {len(df)} linhas")
        return True

    except Exception as e:
        log.error(f"Erro no Loader: {str(e)}")
        if log_id:
            try:
                log_conn   = get_db_connection(DB_CONFIG['log_server'])
                log_cursor = log_conn.cursor()
                log_cursor.execute(f"""
                    UPDATE {DB_CONFIG['log_table']}
                    SET status_processo = 'ERRO', mensagem_erro = ?
                    WHERE id = ?
                """, (str(e)[:500], log_id))
                log_conn.commit()
                log_conn.close()
            except Exception as log_err:
                log.error(f"Erro ao registrar log de erro: {log_err}")
        return False
    finally:
        if conn:
            conn.close()


def carregar_dados_do_banco(usuario=None, perfil=None):
    conn = None
    try:
        conn = get_db_connection(DB_CONFIG['log_server'])
        cursor = conn.cursor()

        if perfil == 'admin' or usuario is None:
            cursor.execute("""
                SELECT TOP 50
                    id,
                    FORMAT(data_execucao, 'dd/MM/yyyy HH:mm:ss') as data,
                    usuario_maquina,
                    arquivo_nome,
                    tabela_destino,
                    status_processo,
                    linhas_inseridas,
                    mensagem_erro
                FROM dbo.LOG_IMPORTADOR
                ORDER BY data_execucao DESC
            """)
        else:
            cursor.execute("""
                SELECT TOP 50
                    id,
                    FORMAT(data_execucao, 'dd/MM/yyyy HH:mm:ss') as data,
                    usuario_maquina,
                    arquivo_nome,
                    tabela_destino,
                    status_processo,
                    linhas_inseridas,
                    mensagem_erro
                FROM dbo.LOG_IMPORTADOR
                WHERE LOWER(usuario_maquina) = LOWER(?)
                ORDER BY data_execucao DESC
            """, (usuario,))

        columns = [column[0] for column in cursor.description]
        logs    = [dict(zip(columns, row)) for row in cursor.fetchall()]
        return logs
    except Exception as e:
        log.error(f"Erro ao buscar logs: {e}")
        return []
    finally:
        if conn:
            conn.close()