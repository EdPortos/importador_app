/**
 * Script de Gerenciamento do Importador de Dados
 */

document.addEventListener('DOMContentLoaded', function () {

    const tipoArquivo = document.getElementById('tipo_arquivo');
    const delimiterWrapper = document.getElementById('delimiter-wrapper');

    if (tipoArquivo && delimiterWrapper) {
        tipoArquivo.addEventListener('change', function () {
            delimiterWrapper.style.display = this.value === 'csv' ? 'block' : 'none';
        });
    }

    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('file-input');
    const dropText = document.getElementById('drop-text');

    if (dropZone && fileInput) {
        ['dragover', 'dragenter'].forEach(eventName => {
            dropZone.addEventListener(eventName, (e) => {
                e.preventDefault();
                dropZone.classList.add('active');
            });
        });

        ['dragleave', 'drop'].forEach(eventName => {
            dropZone.addEventListener(eventName, () => {
                dropZone.classList.remove('active');
            });
        });

        dropZone.addEventListener('drop', (e) => {
            e.preventDefault();
            const files = e.dataTransfer.files;
            if (files.length) {
                fileInput.files = files;
                updateFileName(files[0].name);
            }
        });

        fileInput.addEventListener('change', function() {
            if (this.files.length) {
                updateFileName(this.files[0].name);
            }
        });
    }
    // Filtro de busca
    const searchInput = document.getElementById('search-logs');
    if (searchInput) {
        searchInput.addEventListener('keyup', function () {
            const filtro = this.value.toUpperCase();
            const rows = document.querySelectorAll('#logs-body tr');
            rows.forEach(row => {
                const arquivo = row.cells[0]?.textContent.toUpperCase() || '';
                const destino = row.cells[1]?.textContent.toUpperCase() || '';
                row.style.display = (arquivo.includes(filtro) || destino.includes(filtro)) ? '' : 'none';
            });
        });
    }


    function updateFileName(name) {
        if (dropText) dropText.textContent = "Selecionado: " + name;
        if (dropZone) dropZone.style.borderColor = "var(--accent-blue)";
    }

    const logsBody = document.getElementById('logs-body');
    const overlay = document.getElementById('modal-overlay');
    const btnFechar = document.getElementById('btn-fechar-modal');

    if (logsBody) {
        logsBody.addEventListener('click', function (e) {
            const btn = e.target.closest('.btn-view-log');
            if (btn) {
                abrirModal(btn.dataset);
            }
        });
    }

    if (btnFechar) {
        btnFechar.addEventListener('click', fecharModal);
    }

    if (overlay) {
        overlay.addEventListener('click', function (e) {
            if (e.target === this) fecharModal();
        });
    }

    const btnRefresh = document.getElementById('btn-refresh-logs');
    if (btnRefresh) {
        btnRefresh.addEventListener('click', atualizarLogs);
    }

    // Desabilita botão ao enviar formulário
    const form = document.getElementById('form-upload');
    if (form) {
        form.addEventListener('submit', function (e) {
            console.log('[Submit] Evento disparado');

            const btn = document.getElementById('btn-submit');
            console.log('[Submit] Botão encontrado:', btn);

            if (btn) {
                btn.disabled = true;
                btn.style.opacity = '0.5';
                btn.style.cursor = 'not-allowed';
                console.log('[Submit] Botão desabilitado');
            }
        });
    }

});

/**
 * Abre o modal preenchendo os dados dinamicamente
*/
function abrirModal(data) {
    const overlay = document.getElementById('modal-overlay');
    const body = document.getElementById('modal-body');

    if (!overlay || !body) return;

    // Tratamento para o campo de erro (Django pode enviar "None" como string)
    const temErro = data.erro && data.erro !== 'None' && data.erro.trim() !== '';

    const erroHTML = temErro
        ? `<div style="margin-top:15px; padding:12px; background:#fef2f2; border-left:4px solid #ef4444; border-radius:4px; color:#991b1b; font-family: monospace; font-size:0.8rem; word-break: break-all;">
               <strong>LOG DE ERRO:</strong><br>${data.erro}
           </div>`
        : '';

    body.innerHTML = `
        <div style="margin-bottom:10px;"><strong style="color:var(--text-primary);">Data/Hora:</strong> ${data.data}</div>
        <div style="margin-bottom:10px;"><strong style="color:var(--text-primary);">Arquivo:</strong> ${data.arquivo}</div>
        <div style="margin-bottom:10px;"><strong style="color:var(--text-primary);">Status:</strong> ${data.status}</div>
        <div style="margin-bottom:10px;"><strong style="color:var(--text-primary);">Linhas Processadas:</strong> ${data.linhas}</div>
        ${erroHTML}
    `;

    overlay.style.display = 'flex';
}

function fecharModal() {
    const overlay = document.getElementById('modal-overlay');
    if (overlay) overlay.style.display = 'none';
}

/**
 * Busca novos logs na API e reconstrói a tabela
 */
async function atualizarLogs() {
    const btn = document.getElementById('btn-refresh-logs');
    const icon = btn ? btn.querySelector('i') : null;

    if (icon) icon.classList.add('ph-spin'); // Adiciona animação de girar

    try {
        const response = await fetch(LOGS_API_URL);
        if (!response.ok) throw new Error('Falha na requisição');

        const logs = await response.json();
        const tbody = document.getElementById('logs-body');

        if (!tbody) return;

        tbody.innerHTML = logs.map(log => {
            let badgeClass = 'badge-processing';
            if (log.status_processo === 'SUCESSO') badgeClass = 'badge-success';
            if (log.status_processo === 'ERRO') badgeClass = 'badge-error';

            const erroSanitizado = (log.mensagem_erro || '').replace(/"/g, '&quot;');

            return `
                <tr>
                    <td>${log.data}</td>
                    <td class="col-arquivo" title="${log.arquivo_nome}">${log.arquivo_nome}</td>
                    <td><span class="badge ${badgeClass}">${log.status_processo}</span></td>
                    <td>
                        <button class="btn-view-log"
                                data-data="${log.data}"
                                data-arquivo="${log.arquivo_nome}"
                                data-status="${log.status_processo}"
                                data-linhas="${log.linhas_inseridas || '0'}"
                                data-erro="${erroSanitizado}">
                            <i class="ph ph-eye"></i> Ver detalhes
                        </button>
                    </td>
                </tr>
            `;
        }).join('');

    } catch (err) {
        console.error('Erro ao atualizar logs:', err);
        alert('Não foi possível atualizar os logs.');
    } finally {
        if (icon) {
            setTimeout(() => icon.classList.remove('ph-spin'), 500);
        }
    }
}