"""
Gerenciamento de agendamentos de importação.
Persiste em AppData e cria tarefas no Windows Task Scheduler via schtasks.
"""
import os
import json
import uuid
import subprocess
from datetime import datetime

APP_NAME       = "ImportadorApp"
APPDATA_DIR    = os.path.join(os.environ.get('LOCALAPPDATA', ''), APP_NAME)
SCHED_FILE     = os.path.join(APPDATA_DIR, "agendamentos.json")

# Dias da semana para schtasks
DIAS_SCHTASKS = {
    0: "MON", 1: "TUE", 2: "WED",
    3: "THU", 4: "FRI", 5: "SAT", 6: "SUN"
}


def _garantir_pasta():
    os.makedirs(APPDATA_DIR, exist_ok=True)


def _carregar():
    _garantir_pasta()
    if not os.path.exists(SCHED_FILE):
        return []
    try:
        with open(SCHED_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _salvar(agendamentos):
    _garantir_pasta()
    with open(SCHED_FILE, 'w', encoding='utf-8') as f:
        json.dump(agendamentos, f, ensure_ascii=False, indent=2)


def _nome_tarefa(agendamento_id):
    """Nome único da tarefa no Task Scheduler."""
    return f"ImportadorApp_{agendamento_id}"


def _get_runner_path():
    """Caminho absoluto do scheduler_runner.py (ao lado do app)."""
    import sys
    if getattr(sys, 'frozen', False):
        base = os.path.dirname(sys.executable)
    else:
        base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base, 'scheduler_runner.py')


def _get_python_path():
    """Caminho do Python atual."""
    import sys
    return sys.executable


def _criar_tarefa_windows(agendamento):
    """Cria ou atualiza tarefa no Windows Task Scheduler."""
    nome_tarefa  = _nome_tarefa(agendamento['id'])
    runner_path  = _get_runner_path()
    python_path  = _get_python_path()
    horario      = agendamento['horario']  # "HH:MM"
    recorrencia  = agendamento['recorrencia']
    dias         = agendamento.get('dias_semana', [])

    # Monta o comando que o bat vai executar
    bat_path = _criar_bat(agendamento)

    # Deleta tarefa anterior se existir
    subprocess.run(
        ['schtasks', '/Delete', '/TN', nome_tarefa, '/F'],
        capture_output=True
    )

    if recorrencia == 'diario':
        cmd = [
            'schtasks', '/Create',
            '/TN', nome_tarefa,
            '/TR', f'"{bat_path}"',
            '/SC', 'DAILY',
            '/ST', horario,
            '/F'
        ]
    elif recorrencia == 'semanal':
        dias_str = ','.join([DIAS_SCHTASKS[d] for d in dias if d in DIAS_SCHTASKS])
        if not dias_str:
            return False, "Selecione pelo menos um dia da semana."
        cmd = [
            'schtasks', '/Create',
            '/TN', nome_tarefa,
            '/TR', f'"{bat_path}"',
            '/SC', 'WEEKLY',
            '/D', dias_str,
            '/ST', horario,
            '/F'
        ]
    else:
        return False, "Recorrência inválida."

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        return False, result.stderr or result.stdout

    return True, None


def _criar_bat(agendamento):
    """Cria o arquivo .bat que o Task Scheduler vai executar."""
    python_path = _get_python_path()
    runner_path = _get_runner_path()
    bat_dir     = APPDATA_DIR
    bat_path    = os.path.join(bat_dir, f"run_{agendamento['id']}.bat")

    conteudo = (
        f'@echo off\n'
        f'"{python_path}" "{runner_path}" --id {agendamento["id"]}\n'
    )

    with open(bat_path, 'w', encoding='utf-8') as f:
        f.write(conteudo)

    return bat_path


def _remover_tarefa_windows(agendamento_id):
    """Remove tarefa do Task Scheduler e o .bat."""
    nome_tarefa = _nome_tarefa(agendamento_id)
    subprocess.run(
        ['schtasks', '/Delete', '/TN', nome_tarefa, '/F'],
        capture_output=True
    )
    bat_path = os.path.join(APPDATA_DIR, f"run_{agendamento_id}.bat")
    if os.path.exists(bat_path):
        os.remove(bat_path)


# ── API pública ───────────────────────────────────────────────────────────────

def listar_agendamentos():
    return _carregar()


def get_agendamento(agendamento_id):
    for a in _carregar():
        if a['id'] == agendamento_id:
            return a
    return None


def criar_agendamento(dados):
    """
    dados: {
        nome, dataset_key, arquivo_csv, conexao_id,
        recorrencia, dias_semana, horario,
        email_notificacao, criado_por
    }
    """
    agendamentos = _carregar()

    # Nome duplicado
    nomes = [a['nome'].lower() for a in agendamentos]
    if dados.get('nome', '').lower() in nomes:
        return None, "Já existe um agendamento com esse nome."

    novo = {
        "id":                str(uuid.uuid4()),
        "nome":              dados['nome'],
        "dataset_key":       dados['dataset_key'],
        "arquivo_csv":       dados['arquivo_csv'],
        "conexao_id":        dados['conexao_id'],
        "recorrencia":       dados['recorrencia'],
        "dias_semana":       dados.get('dias_semana', []),
        "horario":           dados['horario'],
        "email_notificacao": dados.get('email_notificacao', ''),
        "ativo":             True,
        "criado_por":        dados.get('criado_por', ''),
        "criado_em":         datetime.now().strftime('%d/%m/%Y %H:%M'),
        "ultima_execucao":   None,
        "ultimo_status":     None,
    }

    ok, erro = _criar_tarefa_windows(novo)
    if not ok:
        return None, f"Erro ao criar tarefa no Windows: {erro}"

    agendamentos.append(novo)
    _salvar(agendamentos)
    return novo, None


def editar_agendamento(agendamento_id, dados):
    agendamentos = _carregar()

    # Nome duplicado em outro registro
    for a in agendamentos:
        if a['nome'].lower() == dados.get('nome', '').lower() and a['id'] != agendamento_id:
            return None, "Já existe um agendamento com esse nome."

    for a in agendamentos:
        if a['id'] == agendamento_id:
            a['nome']              = dados['nome']
            a['dataset_key']       = dados['dataset_key']
            a['arquivo_csv']       = dados['arquivo_csv']
            a['conexao_id']        = dados['conexao_id']
            a['recorrencia']       = dados['recorrencia']
            a['dias_semana']       = dados.get('dias_semana', [])
            a['horario']           = dados['horario']
            a['email_notificacao'] = dados.get('email_notificacao', '')

            ok, erro = _criar_tarefa_windows(a)
            if not ok:
                return None, f"Erro ao atualizar tarefa no Windows: {erro}"

            _salvar(agendamentos)
            return a, None

    return None, "Agendamento não encontrado."


def excluir_agendamento(agendamento_id):
    agendamentos = _carregar()
    novas = [a for a in agendamentos if a['id'] != agendamento_id]
    if len(novas) == len(agendamentos):
        return False, "Agendamento não encontrado."
    _remover_tarefa_windows(agendamento_id)
    _salvar(novas)
    return True, None


def toggle_ativo(agendamento_id):
    agendamentos = _carregar()
    for a in agendamentos:
        if a['id'] == agendamento_id:
            a['ativo'] = not a['ativo']
            nome_tarefa = _nome_tarefa(agendamento_id)
            if a['ativo']:
                _criar_tarefa_windows(a)
            else:
                subprocess.run(
                    ['schtasks', '/Change', '/TN', nome_tarefa, '/DISABLE'],
                    capture_output=True
                )
            _salvar(agendamentos)
            return a, None
    return None, "Agendamento não encontrado."


def registrar_execucao(agendamento_id, status):
    """Chamado pelo scheduler_runner após execução."""
    agendamentos = _carregar()
    for a in agendamentos:
        if a['id'] == agendamento_id:
            a['ultima_execucao'] = datetime.now().strftime('%d/%m/%Y %H:%M')
            a['ultimo_status']   = status
            _salvar(agendamentos)
            return