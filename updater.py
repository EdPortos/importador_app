import urllib.request
import os
import sys
import json
import hashlib

GITHUB_USER  = "EdPortos"
GITHUB_REPO  = "importador_app"
BRANCH       = "master"
RAW_BASE     = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{BRANCH}"
UPDATE_URL   = f"{RAW_BASE}/update.json"

BASE_DIR     = os.path.join(os.path.dirname(os.path.abspath(__file__)))
APP_JSON     = os.path.join(BASE_DIR, "app.json")


# ── Leitura dos JSONs ─────────────────────────────────────────────────────────

def get_app_local():
    """Lê o app.json local."""
    try:
        with open(APP_JSON, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"app": "importador_app", "version": "0.0.0", "os": "windows", "arch": "x64"}


def get_update_remoto():
    """Busca o update.json do GitHub."""
    try:
        with urllib.request.urlopen(UPDATE_URL, timeout=5) as resp:
            return json.loads(resp.read().decode("utf-8")), None
    except Exception as e:
        return None, str(e)


# ── Comparação de versões ─────────────────────────────────────────────────────

def versao_maior(remota, local):
    try:
        r = tuple(int(x) for x in remota.split("."))
        l = tuple(int(x) for x in local.split("."))
        return r > l
    except Exception:
        return False


# ── Verificação de hash ───────────────────────────────────────────────────────

def calcular_hash(filepath):
    sha256 = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            sha256.update(chunk)
    return sha256.hexdigest().upper()


def validar_hash(filepath, hash_esperado):
    if not hash_esperado:
        return True  # sem hash no update.json = não valida
    return calcular_hash(filepath) == hash_esperado.upper()


# ── Download do executável ────────────────────────────────────────────────────

def baixar_exe(download_url, destino):
    try:
        urllib.request.urlretrieve(download_url, destino)
        return True, None
    except Exception as e:
        return False, str(e)


# ── API pública (usada pelo routes.py) ───────────────────────────────────────

def get_versao_local():
    """Compatibilidade com routes.py — retorna (versao, tipo)."""
    app = get_app_local()
    return app.get("version", "0.0.0"), "opcional"


def checar_atualizacao():
    app_local      = get_app_local()
    versao_local   = app_local.get("version", "0.0.0")
    update, erro   = get_update_remoto()

    if erro:
        return {"status": "erro", "mensagem": f"Não foi possível verificar: {erro}"}

    versao_remota = update.get("version", "0.0.0")

    if not versao_maior(versao_remota, versao_local):
        return {"status": "atualizado", "versao_local": versao_local}

    return {
        "status":        "disponivel",
        "tipo":          "obrigatorio" if update.get("mandatory") else "opcional",
        "versao_local":  versao_local,
        "versao_remota": versao_remota,
        "descricao":     update.get("description", ""),
        "download_url":  update.get("download_url", ""),
        "hash":          update.get("hash", ""),
    }


def aplicar_update():
    resultado = checar_atualizacao()

    if resultado["status"] != "disponivel":
        return {"status": "erro", "mensagem": "Nenhuma atualização disponível."}

    download_url  = resultado.get("download_url")
    hash_esperado = resultado.get("hash")
    versao_nova   = resultado.get("versao_remota")

    if not download_url:
        return {"status": "erro", "mensagem": "URL de download não definida no update.json."}

    # Baixa o novo .exe temporariamente
    destino_temp = os.path.join(BASE_DIR, f"importador_app_{versao_nova}.exe")
    ok, erro = baixar_exe(download_url, destino_temp)

    if not ok:
        return {"status": "erro", "mensagem": f"Falha ao baixar atualização: {erro}"}

    # Valida o hash
    if not validar_hash(destino_temp, hash_esperado):
        os.remove(destino_temp)
        return {"status": "erro", "mensagem": "Hash inválido — arquivo corrompido. Tente novamente."}

    return {
        "status":   "ok",
        "mensagem": f"Download concluído! Execute o arquivo '{os.path.basename(destino_temp)}' para instalar.",
        "arquivo":  destino_temp,
    }