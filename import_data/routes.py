import os
import sys
import threading
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify, session
from werkzeug.utils import secure_filename

from import_data.config import DATASET_CONFIG, UPLOAD_FOLDER, MAX_CONTENT_LENGTH
from import_data.services.loader import process_and_load, carregar_dados_do_banco, registrar_log_direto
from import_data.services.validator import validate_csv_structure
from import_data.services.auth import checar_acesso, ADMIN_EMAIL
import updater

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

import_data_bp = Blueprint('import_data', __name__)


def get_acesso():
    """Verifica acesso e armazena na sessão."""
    if 'acesso' not in session:
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

    logs = carregar_dados_do_banco(usuario=acesso['usuario'], perfil=acesso['perfil'])
    versao_local, _ = updater.get_versao_local()

    return render_template('index.html',
        datasets=datasets,
        logs=logs,
        versao_local=versao_local,
        usuario=acesso['usuario'],
        perfil=acesso['perfil'],
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
    user_name    = acesso['usuario']

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
        args=(filepath, dataset_key, delimiter, user_name, tipo_arquivo),
        daemon=True,
    )
    thread.start()

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
    return jsonify(updater.aplicar_update())