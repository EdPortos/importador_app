"""
scheduler_runner.py
Executado pelo Windows Task Scheduler via .bat.
Roda independente do Flask.

Uso: python scheduler_runner.py --id <agendamento_id>
"""
import os
import sys
import argparse

# Garante que importa os módulos do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from logger import log
from import_data.config_loader import carregar_config
from import_data.services.schedules import get_agendamento, registrar_execucao
from import_data.services.loader import process_and_load_sync


def enviar_email_outlook(destinatario, assunto, corpo):
    """Envia email via Outlook instalado na máquina."""
    try:
        import win32com.client
        outlook = win32com.client.Dispatch("Outlook.Application")
        mail = outlook.CreateItem(0)
        mail.To      = destinatario
        mail.Subject = assunto
        mail.Body    = corpo
        mail.Send()
        log.info(f"[runner] Email enviado para {destinatario}")
    except Exception as e:
        log.error(f"[runner] Erro ao enviar email: {e}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--id', required=True, help='ID do agendamento')
    args = parser.parse_args()

    agendamento_id = args.id
    log.info(f"[runner] Iniciando execução do agendamento: {agendamento_id}")

    # Carrega config.json
    if not carregar_config():
        log.error("[runner] Falha ao carregar config.json")
        sys.exit(1)

    # Busca o agendamento
    agendamento = get_agendamento(agendamento_id)
    if not agendamento:
        log.error(f"[runner] Agendamento não encontrado: {agendamento_id}")
        sys.exit(1)

    if not agendamento.get('ativo', True):
        log.info(f"[runner] Agendamento inativo, pulando: {agendamento_id}")
        sys.exit(0)

    arquivo_csv  = agendamento['arquivo_csv']
    dataset_key  = agendamento['dataset_key']
    conexao_id   = agendamento['conexao_id']
    usuario      = agendamento.get('criado_por', 'agendamento')
    email        = agendamento.get('email_notificacao', '')
    nome         = agendamento.get('nome', agendamento_id)

    # Verifica se o arquivo existe
    if not os.path.exists(arquivo_csv):
        msg = f"Arquivo não encontrado: {arquivo_csv}"
        log.error(f"[runner] {msg}")
        registrar_execucao(agendamento_id, 'ERRO')
        if email:
            enviar_email_outlook(
                email,
                f"[Importador] ERRO — {nome}",
                f"O agendamento '{nome}' falhou.\n\nMotivo: {msg}"
            )
        sys.exit(1)

    # Executa a importação (versão síncrona, sem thread)
    try:
        log.info(f"[runner] Processando: {arquivo_csv} → {dataset_key}")
        sucesso, mensagem = process_and_load_sync(
            filepath    = arquivo_csv,
            dataset_key = dataset_key,
            delimiter   = ',',
            user_name   = usuario,
            tipo_arquivo= 'csv',
            conexao_id  = conexao_id,
        )

        if sucesso:
            status = 'SUCESSO'
            log.info(f"[runner] Importação concluída: {nome}")
        else:
            status = 'ERRO'
            log.error(f"[runner] Importação falhou: {mensagem}")

    except Exception as e:
        sucesso   = False
        mensagem  = str(e)
        status    = 'ERRO'
        log.error(f"[runner] Exceção durante importação: {e}")

    # Registra resultado
    registrar_execucao(agendamento_id, status)

    # Envia email de notificação
    if email:
        if sucesso:
            assunto = f"[Importador] ✅ SUCESSO — {nome}"
            corpo   = (
                f"O agendamento '{nome}' foi executado com sucesso.\n\n"
                f"Dataset: {dataset_key}\n"
                f"Arquivo: {arquivo_csv}\n"
                f"Resultado: {mensagem}"
            )
        else:
            assunto = f"[Importador] ❌ ERRO — {nome}"
            corpo   = (
                f"O agendamento '{nome}' falhou.\n\n"
                f"Dataset: {dataset_key}\n"
                f"Arquivo: {arquivo_csv}\n"
                f"Erro: {mensagem}"
            )
        enviar_email_outlook(email, assunto, corpo)

    sys.exit(0 if sucesso else 1)


if __name__ == '__main__':
    main()