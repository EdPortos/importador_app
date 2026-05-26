import urllib.request
import os
import sys

GITHUB_USER = "EdPortos"
GITHUB_REPO = "importador_app"
BRANCH      = "master"
RAW_BASE    = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}"
TOML_URL    = f"{RAW_BASE}/pyproject.toml"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ARQUIVOS_UPDATE = [
    "launcher.py",
    "updater.py",
    "pyproject.toml",
    "import_data/routes.py",
    "import_data/config.py",
    "import_data/services/loader.py",
    "import_data/services/transformations.py",
    "import_data/services/validator.py",
    "import_data/sql_scripts/extra_sql.py",
    "templates/index.html",
    "static/css/import_data.css",
]


def _ler_versao_do_toml(conteudo):
    """Extrai versão e tipo do conteúdo de um pyproject.toml."""
    versao = None
    tipo   = "opcional"
    for linha in conteudo.splitlines():
        linha = linha.strip()
        if linha.startswith("version") and "=" in linha:
            versao = linha.split("=", 1)[1].strip().strip('"').strip("'")
        if linha.startswith("update_type") and "=" in linha:
            tipo = linha.split("=", 1)[1].strip().strip('"').strip("'")
    return versao or "0.0.0", tipo


def get_versao_local():
    path = os.path.join(BASE_DIR, "pyproject.toml")
    try:
        with open(path, "r", encoding="utf-8") as f:
            return _ler_versao_do_toml(f.read())
    except Exception:
        return "0.0.0", "opcional"


def get_versao_remota():
    try:
        with urllib.request.urlopen(TOML_URL, timeout=5) as resp:
            conteudo = resp.read().decode("utf-8")
            versao, tipo = _ler_versao_do_toml(conteudo)
            return versao, tipo, None
    except Exception as e:
        return None, None, str(e)


def versao_maior(remota, local):
    try:
        r = tuple(int(x) for x in remota.split("."))
        l = tuple(int(x) for x in local.split("."))
        return r > l
    except Exception:
        return False


def baixar_arquivo(caminho_relativo):
    url     = f"{RAW_BASE}/{caminho_relativo.replace(os.sep, '/')}"
    destino = os.path.join(BASE_DIR, caminho_relativo)
    os.makedirs(os.path.dirname(destino), exist_ok=True)
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            with open(destino, "wb") as f:
                f.write(resp.read())
        return True, None
    except Exception as e:
        return False, str(e)


def checar_atualizacao():
    versao_local, _ = get_versao_local()
    versao_remota, tipo_remoto, erro = get_versao_remota()

    if erro:
        return {"status": "erro", "mensagem": f"Não foi possível verificar: {erro}"}

    if versao_maior(versao_remota, versao_local):
        return {
            "status":        "disponivel",
            "tipo":          tipo_remoto,
            "versao_local":  versao_local,
            "versao_remota": versao_remota,
        }

    return {"status": "atualizado", "versao_local": versao_local}


def aplicar_update():
    erros = []
    for arquivo in ARQUIVOS_UPDATE:
        ok, erro = baixar_arquivo(arquivo)
        if not ok:
            erros.append({"arquivo": arquivo, "erro": erro})

    if erros:
        return {
            "status":   "erro",
            "erros":    erros,
            "mensagem": f"{len(erros)} arquivo(s) não puderam ser atualizados.",
        }

    return {"status": "ok", "mensagem": "Atualização concluída! Reinicie o app para aplicar."}