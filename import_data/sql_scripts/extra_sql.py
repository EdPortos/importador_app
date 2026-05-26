import os

SQL_DIR = os.path.join(os.path.dirname(__file__))

def executar(conn, nome_script):
    caminho = os.path.join(SQL_DIR, f"{nome_script}.sql")

    if not os.path.exists(caminho):
        raise FileNotFoundError(f"Script SQL não encontrado: {caminho}")

    with open(caminho, 'r', encoding='utf-8') as f:
        sql = f.read()

    cursor = conn.cursor()

    try:
        cursor.execute(sql)
        conn.commit()
        print(f"Script {nome_script}.sql executado com sucesso!")
    except Exception as e:
        conn.rollback()
        raise Exception(f"Erro ao executar {nome_script}.sql: {str(e)}")