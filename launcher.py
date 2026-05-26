import sys
import os
import time
import threading
import webbrowser
# teste de bloqueio
# Garante que o Python encontra os módulos a partir da raiz
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

HOST = '127.0.0.1'
PORT = 5000
URL  = f'http://{HOST}:{PORT}'


def abrir_browser():
    """Aguarda o servidor subir e abre o navegador."""
    time.sleep(1.5)
    webbrowser.open(URL)


def iniciar():
    from app import app
    from waitress import serve

    print(f"Iniciando Importador de Dados...")
    print(f"Acesse: {URL}")
    print(f"Para encerrar, feche esta janela.")

    threading.Thread(target=abrir_browser, daemon=True).start()

    serve(app, host=HOST, port=PORT, threads=4)


if __name__ == '__main__':
    iniciar()