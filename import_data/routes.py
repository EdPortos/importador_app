import os
import sys
import threading
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename

from import_data.services.schedules import (
    listar_agendamentos, criar_agendamento, editar_agendamento,
    excluir_agendamento, toggle_ativo
)

from import_data.config_loader import DATASET_CONFIG, UPLOAD_FOLDER, MAX_CONTENT_LENGTH
from import_data.services.loader import process_and_load, carregar_dados_do_banco, registrar_log_direto
from import_data.services.validator import validate_csv_structure
from import_data.services.auth import checar_acesso, ADMIN_EMAIL
from import_data.services.connections import (
    listar_conexoes, criar_conexao, editar_conexao,
    excluir_conexao, testar_conexao, get_conexao
)
import updater
from logger import log




os.makedirs(UPLOAD_FOLDER, exist_ok=True)

import_data_bp = Blueprint('import_data', __name__)

def get_acesso():
    session['acesso'] = checar_acesso()
    return session['acesso']


@import_data_bp.route('/')
def index():
    acesso = get_acesso()

    if acesso['status'] in ('nao_cadastrado', 'bloqueado'):
        return redirect(url_for('import_data.sem_acesso'))

    # Filtra datasets conforme perfil
    if acesso['datasets'] is None:
        datasets = DATASET_CONFIG  # admin vê tudo
    else:
        datasets = {k: v for k, v in DATASET_CONFIG.items() if k in acesso['datasets']}

    logs          = carregar_dados_do_banco(usuario=acesso['usuario'], perfil=acesso['perfil'])
    versao_local, _ = updater.get_versao_local()
    conexoes_lista  = listar_conexoes()

    return render_template('index.html',
        datasets=datasets,
        logs=logs,
        versao_local=versao_local,
        usuario=acesso['usuario'],
        perfil=acesso['perfil'],
        conexoes_lista=conexoes_lista,
    )


@import_data_bp.route('/sem-acesso')
def sem_acesso():
    usuario = os.environ.get('USERNAME') or os.environ.get('USER') or 'desconhecido'
    return render_template('sem_acesso.html', usuario=usuario, admin_email=ADMIN_EMAIL)


@import_data_bp.route('/upload', methods=['POST'])
def upload():
    acesso = get_acesso()
    if acesso['status'] != 'ok':
        return redirect(url_for('import_data.sem_acesso'))

    dataset_key  = request.form.get('dataset')
    file         = request.files.get('file')
    delimiter    = request.form.get('delimiter')
    tipo_arquivo = request.form.get('tipo_arquivo')
    conexao_id   = request.form.get('conexao_id')
    user_name    = acesso['usuario']

    if not conexao_id:
        flash('Selecione uma conexão de destino.', 'error')
        return redirect(url_for('import_data.index'))

    if dataset_key not in DATASET_CONFIG:
        flash('Dataset inválido.', 'error')
        return redirect(url_for('import_data.index'))

    # Valida permissão do dataset
    if acesso['datasets'] is not None and dataset_key not in acesso['datasets']:
        flash('Você não tem permissão para importar este dataset.', 'error')
        return redirect(url_for('import_data.index'))

    if not file or file.filename == '':
        flash('Nenhum arquivo enviado.', 'error')
        return redirect(url_for('import_data.index'))

    if file.content_length and file.content_length > MAX_CONTENT_LENGTH:
        flash('Arquivo excede o tamanho máximo permitido (20MB).', 'error')
        return redirect(url_for('import_data.index'))

    now = datetime.now()
    relative_path = os.path.join(str(now.year), str(now.month).zfill(2), str(now.day).zfill(2))
    target_dir = os.path.join(UPLOAD_FOLDER, relative_path)
    os.makedirs(target_dir, exist_ok=True)

    timestamp = now.strftime('%Y%m%d_%H%M%S')
    filename  = secure_filename(f'{timestamp}_{file.filename}')
    filepath  = os.path.join(target_dir, filename)
    file.save(filepath)

    expected_cols = DATASET_CONFIG[dataset_key]['columns']
    is_valid, message = validate_csv_structure(filepath, expected_cols, delimiter, tipo_arquivo)

    if not is_valid:
        registrar_log_direto(
            arquivo_nome=filename,
            tabela_destino=dataset_key,
            status='ERRO',
            usuario=user_name,
            mensagem=f'Falha na validação: {message}',
        )
        flash(f'Erro de validação: {message}', 'error')
        return redirect(url_for('import_data.index'))

    thread = threading.Thread(
        target=process_and_load,
        args=(filepath, dataset_key, delimiter, user_name, tipo_arquivo, conexao_id),
        daemon=True,
    )
    thread.start()

    log.info(f'Upload recebido: {filename} | dataset: {dataset_key} | usuario: {user_name}')
    flash('Arquivo recebido e enviado para processamento!', 'success')
    return redirect(url_for('import_data.index'))


@import_data_bp.route('/api/logs')
def get_logs():
    acesso = get_acesso()
    if acesso['status'] != 'ok':
        return jsonify([])
    logs = carregar_dados_do_banco(usuario=acesso['usuario'], perfil=acesso['perfil'])
    return jsonify(logs)


@import_data_bp.route('/api/checar-update')
def checar_update():
    return jsonify(updater.checar_atualizacao())


@import_data_bp.route('/api/aplicar-update', methods=['POST'])
def aplicar_update():
    resultado = updater.checar_atualizacao()
    if resultado['status'] != 'disponivel':
        return jsonify({"status": "erro", "mensagem": "Nenhuma atualização disponível."})
    return jsonify(updater.aplicar_update_via_launcher(resultado))


# ── Conexões ──────────────────────────────────────────────────────────────────

@import_data_bp.route('/conexoes')
def conexoes():
    acesso = get_acesso()
    if acesso['status'] != 'ok':
        return redirect(url_for('import_data.sem_acesso'))
    lista = listar_conexoes()
    return render_template('conexoes.html',
        conexoes=lista,
        usuario=acesso['usuario'],
        perfil=acesso['perfil'],
    )


@import_data_bp.route('/api/conexoes', methods=['GET'])
def api_listar_conexoes():
    return jsonify(listar_conexoes())


@import_data_bp.route('/api/conexoes/testar', methods=['POST'])
def api_testar_conexao():
    data     = request.get_json()
    servidor = data.get('servidor', '')
    banco    = data.get('banco', '')
    driver   = data.get('driver', '{ODBC Driver 17 for SQL Server}')
    ok, erro = testar_conexao(servidor, banco, driver)
    if ok:
        return jsonify({"status": "ok", "mensagem": "Conexão realizada com sucesso!"})
    return jsonify({"status": "erro", "mensagem": str(erro)})


@import_data_bp.route('/api/conexoes/criar', methods=['POST'])
def api_criar_conexao():
    data     = request.get_json()
    nome     = data.get('nome', '').strip()
    servidor = data.get('servidor', '').strip()
    banco    = data.get('banco', '').strip()
    driver   = data.get('driver', '{ODBC Driver 17 for SQL Server}')
    if not all([nome, servidor, banco]):
        return jsonify({"status": "erro", "mensagem": "Preencha todos os campos."})
    nova, erro = criar_conexao(nome, servidor, banco, driver)
    if erro:
        return jsonify({"status": "erro", "mensagem": erro})
    return jsonify({"status": "ok", "conexao": nova})


@import_data_bp.route('/api/conexoes/editar/<conn_id>', methods=['POST'])
def api_editar_conexao(conn_id):
    data     = request.get_json()
    nome     = data.get('nome', '').strip()
    servidor = data.get('servidor', '').strip()
    banco    = data.get('banco', '').strip()
    driver   = data.get('driver', '{ODBC Driver 17 for SQL Server}')
    if not all([nome, servidor, banco]):
        return jsonify({"status": "erro", "mensagem": "Preencha todos os campos."})
    atualizada, erro = editar_conexao(conn_id, nome, servidor, banco, driver)
    if erro:
        return jsonify({"status": "erro", "mensagem": erro})
    return jsonify({"status": "ok", "conexao": atualizada})


@import_data_bp.route('/api/conexoes/excluir/<conn_id>', methods=['DELETE'])
def api_excluir_conexao(conn_id):
    ok, erro = excluir_conexao(conn_id)
    if not ok:
        return jsonify({"status": "erro", "mensagem": erro})
    return jsonify({"status": "ok"})


# ── Agendamentos ─────────────────────────────────────────────────────────────


@import_data_bp.route('/agendamentos')
def agendamentos():
    acesso = get_acesso()
    if acesso['status'] != 'ok':
        return redirect(url_for('import_data.sem_acesso'))
    lista = listar_agendamentos()
    conexoes = listar_conexoes()
    datasets = DATASET_CONFIG if acesso['datasets'] is None else {
        k: v for k, v in DATASET_CONFIG.items() if k in acesso['datasets']
    }
    return render_template('agendamentos.html',
                           agendamentos=lista,
                           conexoes=conexoes,
                           datasets=datasets,
                           usuario=acesso['usuario'],
                           perfil=acesso['perfil'],
                           )


@import_data_bp.route('/api/agendamentos', methods=['GET'])
def api_listar_agendamentos():
    return jsonify(listar_agendamentos())


@import_data_bp.route('/api/agendamentos/criar', methods=['POST'])
def api_criar_agendamento():
    acesso = get_acesso()
    data = request.get_json()
    data['criado_por'] = acesso.get('usuario', '')
    novo, erro = criar_agendamento(data)
    if erro:
        return jsonify({"status": "erro", "mensagem": erro})
    return jsonify({"status": "ok", "agendamento": novo})


@import_data_bp.route('/api/agendamentos/editar/<ag_id>', methods=['POST'])
def api_editar_agendamento(ag_id):
    data = request.get_json()
    atualizado, erro = editar_agendamento(ag_id, data)
    if erro:
        return jsonify({"status": "erro", "mensagem": erro})
    return jsonify({"status": "ok", "agendamento": atualizado})


@import_data_bp.route('/api/agendamentos/excluir/<ag_id>', methods=['DELETE'])
def api_excluir_agendamento(ag_id):
    ok, erro = excluir_agendamento(ag_id)
    if not ok:
        return jsonify({"status": "erro", "mensagem": erro})
    return jsonify({"status": "ok"})


@import_data_bp.route('/api/agendamentos/toggle/<ag_id>', methods=['POST'])
def api_toggle_agendamento(ag_id):
    ag, erro = toggle_ativo(ag_id)
    if erro:
        return jsonify({"status": "erro", "mensagem": erro})
    return jsonify({"status": "ok", "ativo": ag['ativo']})
