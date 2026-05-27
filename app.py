import os
import sys
from flask import Flask, session

# Garante que o Python encontra os módulos a partir da raiz do projeto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

from flask import Flask
from import_data.routes import import_data_bp

app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static'),
)

app.secret_key = 'importador-app-local-2025'

# Registra o blueprint do import_data
app.register_blueprint(import_data_bp)


@app.before_request
def limpar_sessao_inicial():
    if not session.get('iniciado'):
        session.clear()
        session['iniciado'] = True

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000, debug=False)