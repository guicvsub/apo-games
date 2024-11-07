import os
import json
from flask import Flask, jsonify
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

app = Flask(__name__)

# Defina os escopos para a API do Google Drive (acesso completo aos arquivos)
SCOPES = ['https://www.googleapis.com/auth/drive']

# ID da pasta específica no Google Drive (configurável por variável de ambiente)
FOLDER_ID = os.environ.get('FOLDER_ID')


def authenticate():
    """Autentica e retorna o serviço da API Google Drive usando OAuth 2.0 com credenciais de ambiente"""
    creds = None

    # Carrega as credenciais do token se existirem
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)

    # Se não houver credenciais válidas ou se elas expiraram
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Carrega o client_secret do ambiente e cria o fluxo de autenticação
            client_secret_json = os.environ.get('GOOGLE_CLIENT_SECRET_JSON')
            if not client_secret_json:
                raise ValueError("A variável de ambiente 'GOOGLE_CLIENT_SECRET_JSON' não está configurada.")
            
            # Carrega o JSON do client_secret como dicionário
            client_config = json.loads(client_secret_json)
            
            # Cria o fluxo de autenticação a partir do dicionário de configurações
            flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
            creds = flow.run_local_server(port=0)

        # Salva as credenciais para a próxima execução
        with open('token.json', 'w') as token:
            token.write(creds.to_json())

    # Retorna o serviço da API Google Drive
    service = build('drive', 'v3', credentials=creds)
    return service


@app.route('/', methods=['GET'])
def root():
    """Texto simples na rota raiz"""
    return "Bem-vindo à API do Google Drive!"


@app.route('/list-files', methods=['GET'])
def list_files():
    """Lista os arquivos de uma pasta específica do Google Drive."""
    try:
        service = authenticate()

        if not service:
            return jsonify({"message": "Falha na autenticação!"}), 400

        # Realiza a listagem de arquivos na pasta especificada (usando o ID da pasta do ambiente)
        results = service.files().list(
            q=f"'{FOLDER_ID}' in parents",  # Filtra arquivos pela pasta com o ID específico
            pageSize=10,
            fields="nextPageToken, files(id, name, mimeType)").execute()

        items = results.get('files', [])

        if not items:
            return jsonify({"message": "Nenhum arquivo encontrado na pasta."}), 200
        else:
            file_list = [{
                "id": file['id'],
                "name": file['name'],
                "mimeType": file['mimeType']
            } for file in items]
            return jsonify({"files": file_list}), 200
    except HttpError as error:
        return jsonify(
            {"error": f"Erro ao acessar a API do Google Drive: {error}"}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', debug=True)
