"""
Instala o pre-commit hook no repositório Git local.
Execute uma vez na raiz do projeto:

    python install_hooks.py
"""
import os
import shutil
import stat

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
HOOK_SRC   = os.path.join(BASE_DIR, "pre-commit")
HOOKS_DIR  = os.path.join(BASE_DIR, ".git", "hooks")
HOOK_DEST  = os.path.join(HOOKS_DIR, "pre-commit")


def main():
    if not os.path.exists(os.path.join(BASE_DIR, ".git")):
        print("Erro: esta pasta não é um repositório Git.")
        print("Rode 'git init' primeiro.")
        input("\nPressione ENTER para fechar...")
        return

    if not os.path.exists(HOOK_SRC):
        print("Erro: arquivo 'pre-commit' não encontrado na raiz do projeto.")
        input("\nPressione ENTER para fechar...")
        return

    os.makedirs(HOOKS_DIR, exist_ok=True)
    shutil.copy2(HOOK_SRC, HOOK_DEST)

    # Garante permissão de execução (Linux/Mac)
    current = stat.S_IMODE(os.lstat(HOOK_DEST).st_mode)
    os.chmod(HOOK_DEST, current | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

    print("=" * 45)
    print("  Hook instalado com sucesso!")
    print("=" * 45)
    print()
    print("  A partir de agora, todo commit verifica")
    print("  se a versão no pyproject.toml foi")
    print("  incrementada.")
    print()
    print("  Para desinstalar, delete o arquivo:")
    print(f"  {HOOK_DEST}")
    print("=" * 45)
    input("\nPressione ENTER para fechar...")


if __name__ == "__main__":
    main()