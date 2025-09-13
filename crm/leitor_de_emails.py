# leitor_gmail_api.py
"""
Este script conecta-se à API do Gmail para ler e-mails de uma conta.
Ele pode listar e-mails de diferentes caixas (Recebidos, Enviados, etc.)
e exibe informações-chave de cada mensagem.
"""
import os
import base64
import logging
import argparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURAÇÕES ---

# O SCOPE define o nível de permissão que estamos solicitando.
# 'gmail.readonly' permite apenas ler e-mails, sem risco de modificar ou apagar nada.
SCOPES = ['https://www.googleapis.com/auth/gmail.readonly']

# Arquivo de log para registrar as operações
LOG_FILE = 'leitura_gmail_api.log'

# --- FIM DAS CONFIGURAções ---

# Configuração do logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)

def get_gmail_service():
    """
    Autentica com a API do Gmail e retorna um objeto de serviço para interagir com a API.
    Gerencia os arquivos credentials.json e token.json.
    """
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    
    # Se não houver credenciais válidas, solicita que o usuário faça login.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                logging.error(f"Erro ao atualizar o token. Tente remover o 'token.json' e rodar novamente. Erro: {e}")
                # Se o refresh falhar (pode ter sido revogado), removemos o token para gerar um novo
                os.remove('token.json')
                return get_gmail_service() # Tenta novamente
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Salva as credenciais para as próximas execuções
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
            
    try:
        service = build('gmail', 'v1', credentials=creds)
        logging.info("Serviço do Gmail autenticado com sucesso.")
        return service
    except HttpError as error:
        logging.error(f'Ocorreu um erro ao criar o serviço do Gmail: {error}')
        return None

def listar_e_ler_emails(service, label_id='INBOX', limite=10):
    """
    Lista e lê e-mails de uma determinada label (caixa de correio).
    
    Args:
        service: O objeto de serviço da API do Gmail.
        label_id (str): A ID da label a ser pesquisada (ex: 'INBOX', 'SENT', 'SPAM').
        limite (int): O número máximo de e-mails a serem buscados.
    """
    try:
        logging.info(f"Buscando os últimos {limite} e-mails da caixa '{label_id}'...")
        
        # 1. Listar as mensagens para obter seus IDs
        results = service.users().messages().list(
            userId='me', 
            labelIds=[label_id], 
            maxResults=limite
        ).execute()
        
        messages = results.get('messages', [])

        if not messages:
            logging.warning(f"Nenhum e-mail encontrado na caixa '{label_id}'.")
            return

        logging.info(f"Encontrados {len(messages)} e-mails. Exibindo detalhes:")
        print("\n" + "="*80)

        # 2. Para cada ID de mensagem, buscar o conteúdo completo
        for message_info in messages:
            msg_id = message_info['id']
            # O formato 'full' traz todo o conteúdo, incluindo corpo e cabeçalhos
            message = service.users().messages().get(userId='me', id=msg_id, format='full').execute()
            
            # Extrai os cabeçalhos (De, Para, Assunto, Data)
            payload = message.get('payload', {})
            headers = payload.get('headers', [])
            
            email_data = {
                'De': 'N/A',
                'Assunto': '(Sem assunto)',
                'Data': 'N/A'
            }
            
            for header in headers:
                if header['name'] == 'From':
                    email_data['De'] = header['value']
                elif header['name'] == 'Subject':
                    email_data['Assunto'] = header['value']
                elif header['name'] == 'Date':
                    email_data['Data'] = header['value']
            
            # Exibe os dados extraídos
            print(f"De: {email_data['De']}")
            print(f"Assunto: {email_data['Assunto']}")
            print(f"Data: {email_data['Data']}")
            
            # Exibe um trecho (snippet) do e-mail
            print(f"Snippet: {message.get('snippet', 'N/A')}")
            print("-" * 80)

    except HttpError as error:
        logging.error(f'Ocorreu um erro ao acessar os e-mails: {error}')
    except Exception as e:
        logging.error(f'Um erro inesperado ocorreu: {e}')

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Lê e-mails de uma conta do Gmail usando a API.")
    parser.add_argument(
        '-l', '--label',
        type=str,
        default='INBOX',
        help="A caixa de e-mails a ser lida. Padrão: 'INBOX'. Outras opções: 'SENT', 'DRAFTS', 'SPAM'."
    )
    parser.add_argument(
        '-n', '--limite',
        type=int,
        default=10,
        help="O número máximo de e-mails para ler. Padrão: 10."
    )
    args = parser.parse_args()

    # Inicia o processo
    gmail_service = get_gmail_service()
    if gmail_service:
        listar_e_ler_emails(service=gmail_service, label_id=args.label, limite=args.limite)