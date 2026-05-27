import sys
import os
import time
import threading
import webbrowser
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

HOST     = '127.0.0.1'
PORT     = 5000
URL      = f'http://{HOST}:{PORT}'
ICON_PATH = os.path.join(BASE_DIR, 'configs', 'importador_app.ico')


# ── System Tray ───────────────────────────────────────────────────────────────

def criar_tray(server_thread):
    import pystray
    from PIL import Image

    icon_image = Image.open(ICON_PATH)

    def abrir_navegador(icon, item):
        webbrowser.open(URL)

    def fechar_app(icon, item):
        icon.stop()
        os._exit(0)

    menu = pystray.Menu(
        pystray.MenuItem('Abrir no navegador', abrir_navegador, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem('Fechar', fechar_app),
    )

    icon = pystray.Icon(
        name='ImportadorApp',
        icon=icon_image,
        title='Importador de Dados',
        menu=menu,
    )

    return icon


# ── Servidor Flask ────────────────────────────────────────────────────────────

def iniciar_servidor():
    from app import app
    from waitress import serve
    serve(app, host=HOST, port=PORT, threads=4)


# ── Update automático ─────────────────────────────────────────────────────────

def aplicar_update_e_reiniciar(download_url, versao_nova, hash_esperado, icon):
    """
    Baixa o novo .exe, valida o hash, cria um .bat que:
    1. Aguarda o processo atual fechar
    2. Substitui o .exe
    3. Abre o novo
    """
    import urllib.request
    import hashlib

    exe_atual  = os.path.abspath(sys.executable if getattr(sys, 'frozen', False) else __file__)
    exe_novo   = os.path.join(BASE_DIR, f'ImportadorApp_{versao_nova}.exe')
    bat_path   = os.path.join(BASE_DIR, '_update.bat')

    # Baixa o novo .exe
    try:
        urllib.request.urlretrieve(download_url, exe_novo)
    except Exception as e:
        print(f"[update] Falha no download: {e}")
        return False, f"Falha no download: {e}"

    # Valida o hash
    if hash_esperado:
        sha256 = hashlib.sha256()
        with open(exe_novo, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        if sha256.hexdigest().upper() != hash_esperado.upper():
            os.remove(exe_novo)
            return False, "Hash inválido — arquivo corrompido."

    # Cria o .bat de substituição
    bat_content = f"""@echo off
        echo Aguardando encerramento do app...
        timeout /t 2 /nobreak > nul
        move /Y "{exe_novo}" "{exe_atual}"
        echo Abrindo nova versao...
        start "" "{exe_atual}"
        del "%~f0"
        """
    with open(bat_path, 'w') as f:
        f.write(bat_content)

    # Fecha o tray e executa o .bat
    subprocess.Popen(
        ['cmd.exe', '/c', bat_path],
        creationflags=subprocess.CREATE_NO_WINDOW
    )
    icon.stop()
    os._exit(0)


# ── Inicialização ─────────────────────────────────────────────────────────────

def main():
    # Inicia o servidor Flask em background
    server_thread = threading.Thread(target=iniciar_servidor, daemon=True)
    server_thread.start()

    # Aguarda o servidor subir e abre o navegador
    time.sleep(1.5)
    webbrowser.open(URL)

    # Expõe a função de update para o routes.py usar
    import builtins
    builtins._aplicar_update_launcher = aplicar_update_e_reiniciar

    # Inicia o system tray (bloqueia até fechar)
    icon = criar_tray(server_thread)

    # Disponibiliza o icon para o routes.py
    builtins._tray_icon = icon

    print(f"[launcher] Importador de Dados iniciado em {URL}")
    icon.run()


if __name__ == '__main__':
    main()