import os
import sys
import subprocess

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
VENV_DIR = os.path.join(BASE_DIR, '.venv')
REQ_FILE = os.path.join(BASE_DIR, 'requirements.txt')


def passo(numero, descricao):
    print(f"\n[{numero}] {descricao}")
    print("-" * 40)


def main():
    print("=" * 40)
    print("  Setup do Ambiente Virtual")
    print("=" * 40)

    # Passo 1 — Verifica versão do Python
    passo(1, "Verificando Python...")
    versao = sys.version_info
    print(f"Python {versao.major}.{versao.minor}.{versao.micro} encontrado.")
    if versao.major < 3 or versao.minor < 9:
        print("AVISO: Recomendado Python 3.9 ou superior.")

    # Passo 2 — Cria o .venv
    passo(2, "Criando ambiente virtual (.venv)...")
    if os.path.exists(VENV_DIR):
        print(".venv já existe. Pulando criação.")
    else:
        subprocess.run([sys.executable, "-m", "venv", ".venv"], check=True)
        print(".venv criado com sucesso!")

    # Define o caminho do pip dentro do .venv
    if sys.platform == "win32":
        pip_path = os.path.join(VENV_DIR, "Scripts", "pip.exe")
    else:
        pip_path = os.path.join(VENV_DIR, "bin", "pip")

    # Passo 3 — Atualiza o pip
    passo(3, "Atualizando pip...")
    subprocess.run([pip_path, "install", "--upgrade", "pip"], check=True)

    # Passo 4 — Instala requirements se existir
    passo(4, "Verificando requirements.txt...")
    if os.path.exists(REQ_FILE):
        print("requirements.txt encontrado! Instalando pacotes...")
        subprocess.run([pip_path, "install", "-r", REQ_FILE], check=True)
        print("Pacotes instalados com sucesso!")
    else:
        print("requirements.txt não encontrado. Pulando instalação.")

    # Conclusão
    print("\n" + "=" * 40)
    print("  Ambiente pronto!")
    print("=" * 40)

    if sys.platform == "win32":
        print("\nPara ativar o ambiente virtual:")
        print("  .venv\\Scripts\\activate")
    else:
        print("\nPara ativar o ambiente virtual:")
        print("  source .venv/bin/activate")

    input("\nPressione ENTER para fechar...")


if __name__ == "__main__":
    main()