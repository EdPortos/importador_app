import os
import pyodbc
from logger import log
from import_data.config_loader import SERVERS, DB_CONFIG

ADMIN_EMAIL = "edilson.porto@aec.com.br"

# Servidor onde ficam as tabelas de usuários
AUTH_SERVER = DB_CONFIG['log_server']

def get_conexao():
    server = SERVERS[AUTH_SERVER]
    conn_str = (
        f"DRIVER={server['driver']};"
        f"SERVER={server['server']};"
        f"DATABASE={server['database']};"
        f"Trusted_Connection={server['trusted_connection']};"
    )
    if server.get('uid'):
        conn_str += f"UID={server['uid']};PWD={server.get('pwd', '')};"
        print(conn_str)
    return pyodbc.connect(conn_str)


def get_usuario_maquina():
    return os.environ.get('USERNAME') or os.environ.get('USER') or 'desconhecido'


def get_perfil_usuario(usuario_maquina):
    """
    Retorna dict com perfil do usuário ou None se não cadastrado.
    {
        'usuario_maquina': 'FULANO.SILVA',
        'perfil': 'admin',   # admin | usuario | bloqueado
        'ativo': True,
    }
    """
    conn = None
    try:
        conn = get_conexao()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT usuario_maquina, perfil, ativo
            FROM hub.importador_usuarios
            WHERE LOWER(usuario_maquina) = LOWER(?)
        """, (usuario_maquina,))
        row = cursor.fetchone()
        if not row:
            return None
        return {
            'usuario_maquina': row[0],
            'perfil':          row[1],
            'ativo':           bool(row[2]),
        }
    except Exception as e:
        log.error(f"[auth] Erro ao verificar usuário: {e}")
        return None
    finally:
        if conn:
            conn.close()


def get_datasets_permitidos(usuario_maquina, perfil):
    """
    Retorna lista de dataset_keys permitidos para o usuário.
    Admin retorna lista vazia (significa: tudo liberado).
    """
    if perfil == 'admin':
        return None  # None = sem restrição

    conn = None
    try:
        conn = get_conexao()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT dataset_key
            FROM HUB.IMPORTADOR_PERMISSOES
            WHERE LOWER(usuario_maquina) = LOWER(?)
            AND ativo = 1
        """, (usuario_maquina,))
        return [row[0] for row in cursor.fetchall()]
    except Exception as e:
        log.error(f"[auth] Erro ao buscar permissões: {e}")
        return []
    finally:
        if conn:
            conn.close()


def checar_acesso():
    """
    Verifica acesso do usuário atual.
    Retorna dict com resultado do check.
    """
    usuario = get_usuario_maquina()
    perfil  = get_perfil_usuario(usuario)


    if perfil is None:
        return {'status': 'nao_cadastrado', 'usuario': usuario}

    if not perfil['ativo'] or perfil['perfil'] == 'bloqueado':
        return {'status': 'bloqueado', 'usuario': usuario}

    datasets = get_datasets_permitidos(usuario, perfil['perfil'])

    return {
        'status':   'ok',
        'usuario':  usuario,
        'perfil':   perfil['perfil'],
        'datasets': datasets,  # None = tudo, lista = filtrado
    }


if __name__ == '__main__':
    checar_acesso()
    #get_conexao()