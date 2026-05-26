import os
import sys
import threading
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from werkzeug.utils import secure_filename

from import_data.config import DATASET_CONFIG, UPLOAD_FOLDER, MAX_CONTENT_LENGTH
from import_data.services.loader import process_and_load, carregar_dados_do_banco, registrar_log_direto
from import_data.services.validator import validate_csv_structure
import updater

os.makedirs(UPLOAD_FOLDER, exist_ok=True)

import_data_bp = Blueprint('import_data', __name__)


@import_data_bp.route('/')
def index():
    logs = carregar_dados_do_banco()
    versao_local, _ = updater.get_versao_local()
    return render_template('index.html', datasets=DATASET_CONFIG, logs=logs, versao_local=versao_local)


@import_data_bp.route('/upload', methods=['POST'])
def upload():
    dataset_key  = request.form.get('dataset')
    file         = request.files.get('file')
    delimiter    = request.form.get('delimiter')
    tipo_arquivo = request.form.get('tipo_arquivo')

    # Identifica a máquina do usuário
    user_name = os.environ.get('USERNAME') or os.environ.get('USER') or 'local'

    if dataset_key not in DATASET_CONFIG:
        flash('Dataset inválido.', 'error')
        return redirect(url_for('import_data.index'))

    if not file or file.filename == '':
        flash('Nenhum arquivo enviado.', 'error')
        return redirect(url_for('import_data.index'))

    if file.content_length and file.content_length > MAX_CONTENT_LENGTH:
        flash('Arquivo excede o tamanho máximo permitido (20MB).', 'error')
        return redirect(url_for('import_data.index'))

    # Salva organizado por data
    now = datetime.now()
    relative_path = os.path.join(
        str(now.year),
        str(now.month).zfill(2),
        str(now.day).zfill(2),
    )
    target_dir = os.path.join(UPLOAD_FOLDER, relative_path)
    os.makedirs(target_dir, exist_ok=True)

    timestamp = now.strftime('%Y%m%d_%H%M%S')
    filename  = secure_filename(f'{timestamp}_{file.filename}')
    filepath  = os.path.join(target_dir, filename)
    file.save(filepath)

    # Valida estrutura do arquivo
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

    # Processa em background
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
    logs = carregar_dados_do_banco()
    return jsonify(logs)


@import_data_bp.route('/api/checar-update')
def checar_update():
    resultado = updater.checar_atualizacao()
    return jsonify(resultado)


@import_data_bp.route('/api/aplicar-update', methods=['POST'])
def aplicar_update():
    resultado = updater.aplicar_update()
    return jsonify(resultado)