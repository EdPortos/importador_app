"""
Script de build — gera o ImportadorApp.exe
Execute na raiz do projeto:
    python build.py
"""
import os
import subprocess
import sys

BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
ICON_PATH = os.path.join(BASE_DIR, 'configs', 'importador_app.ico')


def main():
    print("=" * 45)
    print("  Build — ImportadorApp.exe")
    print("=" * 45)

    cmd = [
        'pyinstaller',
        '--noconfirm',
        '--onefile',
        '--windowed',
        '--name', 'ImportadorApp',
        '--icon', ICON_PATH,
        '--add-data', 'templates;templates',
        '--add-data', 'static;static',
        '--add-data', 'import_data;import_data',
        '--add-data', 'configs;configs',
        'launcher.py',
    ]

    print(f"\nExecutando PyInstaller...")
    result = subprocess.run(cmd, cwd=BASE_DIR)

    if result.returncode == 0:
        # Copia o config.py para ao lado do .exe
        import shutil
        config_src = os.path.join(BASE_DIR, 'import_data', 'config.py')
        config_dst_dir = os.path.join(BASE_DIR, 'dist', 'import_data')
        os.makedirs(config_dst_dir, exist_ok=True)
        shutil.copy2(config_src, os.path.join(config_dst_dir, 'config.py'))
        print("\n  config.py copiado para dist/import_data/")

        exe_path = os.path.join(BASE_DIR, 'dist', 'ImportadorApp.exe')
        print("\n" + "=" * 45)
        print("  Build concluído!")
        print(f"  {exe_path}")
        print("=" * 45)

        # Calcula o hash do .exe gerado
        import hashlib
        sha256 = hashlib.sha256()
        with open(exe_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        hash_exe = sha256.hexdigest().upper()

        print(f"\n  Hash SHA256:")
        print(f"  {hash_exe}")
        print("\n  Cole este hash no configs/update.json")
        print("=" * 45)
    else:
        print("\nErro durante o build!")

    input("\nPressione ENTER para fechar...")


if __name__ == '__main__':
    main()