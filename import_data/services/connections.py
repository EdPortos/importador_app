import os
import json
import uuid
from datetime import datetime

APP_NAME     = "ImportadorApp"
APPDATA_DIR  = os.path.join(os.environ.get('LOCALAPPDATA', ''), APP_NAME)
CONN_FILE    = os.path.join(APPDATA_DIR, "connections.json")


def _garantir_pasta():
    os.makedirs(APPDATA_DIR, exist_ok=True)


def _carregar():
    _garantir_pasta()
    if not os.path.exists(CONN_FILE):
        return []
    try:
        with open(CONN_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _salvar(conexoes):
    _garantir_pasta()
    with open(CONN_FILE, 'w', encoding='utf-8') as f:
        json.dump(conexoes, f, ensure_ascii=False, indent=2)


def listar_conexoes():
    """Retorna todas as conexões salvas."""
    return _carregar()


def get_conexao(conn_id):
    """Retorna uma conexão pelo ID."""
    for c in _carregar():
        if c['id'] == conn_id:
            return c
    return None


def criar_conexao(nome, servidor, banco, driver="{ODBC Driver 17 for SQL Server}"):
    """Cria uma nova conexão e salva no AppData."""
    conexoes = _carregar()

    # Verifica nome duplicado
    nomes = [c['nome'].lower() for c in conexoes]
    if nome.lower() in nomes:
        return None, "Já existe uma conexão com esse nome."

    nova = {
        "id":         str(uuid.uuid4()),
        "nome":       nome,
        "servidor":   servidor,
        "banco":      banco,
        "driver":     driver,
        "criado_em":  datetime.now().strftime('%d/%m/%Y %H:%M'),
    }
    conexoes.append(nova)
    _salvar(conexoes)
    return nova, None


def editar_conexao(conn_id, nome, servidor, banco, driver="{ODBC Driver 17 for SQL Server}"):
    """Edita uma conexão existente."""
    conexoes = _carregar()

    # Verifica nome duplicado em outros registros
    for c in conexoes:
        if c['nome'].lower() == nome.lower() and c['id'] != conn_id:
            return None, "Já existe uma conexão com esse nome."

    for c in conexoes:
        if c['id'] == conn_id:
            c['nome']     = nome
            c['servidor'] = servidor
            c['banco']    = banco
            c['driver']   = driver
            _salvar(conexoes)
            return c, None

    return None, "Conexão não encontrada."


def excluir_conexao(conn_id):
    """Remove uma conexão pelo ID."""
    conexoes = _carregar()
    novas    = [c for c in conexoes if c['id'] != conn_id]
    if len(novas) == len(conexoes):
        return False, "Conexão não encontrada."
    _salvar(novas)
    return True, None


def testar_conexao(servidor, banco, driver="{ODBC Driver 17 for SQL Server}"):
    """Testa se a conexão é válida antes de salvar."""
    import pyodbc
    conn_str = (
        f"DRIVER={driver};"
        f"SERVER={servidor};"
        f"DATABASE={banco};"
        f"Trusted_Connection=yes;"
    )
    try:
        conn = pyodbc.connect(conn_str, timeout=5)
        conn.close()
        return True, None
    except Exception as e:
        return False, str(e)


def montar_conn_str(conn_id):
    """Monta a connection string pyodbc a partir de um ID salvo."""
    conexao = get_conexao(conn_id)
    if not conexao:
        return None, "Conexão não encontrada."
    conn_str = (
        f"DRIVER={conexao['driver']};"
        f"SERVER={conexao['servidor']};"
        f"DATABASE={conexao['banco']};"
        f"Trusted_Connection=yes;"
    )
    return conn_str, None