import os
import csv
import time
import re
import base64
import argparse
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from urllib.parse import quote

# Importações da biblioteca do Google
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# --- CONFIGURAÇÕES DA CAMPANHA ---

# 1. Arquivo CSV com a lista de e-mails dos destinatários.
CSV_FILE_PATH = 'emails.csv'

# 2. Arquivo PDF da Ata que será anexado ao e-mail.
ATTACHMENT_FILE_PATH = 'Ata de Registro de Preço nº 0350.2024 ASSINADA.pdf'

# 3. O e-mail do remetente (sua conta do Gmail).
FROM_EMAIL = 'admin@asm-tecnologia.com'

# 4. Assunto do e-mail (versão original).
EMAIL_SUBJECT = 'Aquisição simplificada - Microsoft Office Professional Plus 2021'

# 5. Preparando os links do WhatsApp
WHATSAPP_NUM_1 = '556198323833'
WHATSAPP_TEXT_1 = 'Olá, Fernando. Tenho interesse na Ata de Registro de Preços e gostaria de ligar.'
WHATSAPP_URL_1 = f"https://wa.me/{WHATSAPP_NUM_1}?text={quote(WHATSAPP_TEXT_1)}"
WHATSAPP_NUM_2 = '556131421273'
WHATSAPP_TEXT_2 = 'Olá, Fernando. Tenho interesse na Ata de Registro de Preços do Microsoft Office.'
WHATSAPP_URL_2 = f"https://wa.me/{WHATSAPP_NUM_2}?text={quote(WHATSAPP_TEXT_2)}"

# 6. Corpo do e-mail em HTML.
EMAIL_BODY_HTML = f"""
<html>
<body>
    <p>Prezado(a),</p>
    <p>Somos a ASM tecnologia, atendendo à órgãos públicos há mais de 10 anos. </p>
    <p>Apresentamos uma oportunidade de aquisição simplificada, por meio de adesão ata de registro de preços vigente, referente ao seguinte produto:</p>
    <p>
        <b>Produto:</b> Microsoft Office Professional Plus 2021 (PT-BR)<br>
        <b>✔ Licença:</b> Perpétua, sem Software Assurance<br>
        <b>✔ Compatibilidade:</b> Windows 10 ou superior | 32 e 64 bits<br>
        <b>✔ Instalação:</b> Desktop<br>
        <b>✔ Modelo de contratação:</b> Adesão direta via ata (sem necessidade de nova licitação)
    </p>
    <p><b>Condições:</b> Conforme Termo de Referência da ata vigente (documento em anexo)</p>
    <p>A aquisição por ata garante:</p>
    <ul>
        <li><b>Agilidade no processo</b> (dispensa nova licitação);</li>
        <li><b>Segurança jurídica</b>, conforme a Lei 14.133/2021;</li>
        <li><b>Otimização de custos</b> operacionais, com valores já homologados.</li>
    </ul>
    <p>Caso haja interesse, permanecemos à disposição para orientar o processo de adesão e dar andamento imediato.</p>
    <p>Atenciosamente,<br><br>
    <b>FERNANDO ANDRE SILVA MACIEL</b><br>
    CEO ASM Tecnologia<br><br>
    (WhatsApp e Ligações)<br>
    <a href="{WHATSAPP_URL_1}"><u>(61) 9832-3833</u></a><br>
    (WhatsApp Comercial)<br>
    <a href="{WHATSAPP_URL_2}"><u>(61) 3142-1273</u></a>
    </p>
</body>
</html>
"""

# 7. Lista de e-mails para o modo de desenvolvimento (--dev)
DEV_EMAIL_LIST = [
    'diego.freebsd@gmail.com',
    'hardhatshaman@gmail.com',
    'pythinking@gmail.com',
    'coproducaoinfinita01@gmail.com'
]

# --- NOVAS CONFIGURAÇÕES DE LOG ---
LOG_FILE = 'envio_emails.log'
CSV_DEBUG_FILE = 'depuracao_envios.csv'
SENT_LOG_FILE = 'sent_emails.log.csv'

# --- FIM DAS CONFIGURAÇÕES ---

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(LOG_FILE), logging.StreamHandler()])

def log_to_csv(nome, email, status):
    file_exists = os.path.isfile(CSV_DEBUG_FILE)
    with open(CSV_DEBUG_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(['Nome', 'Email', 'DataHoraEnvio', 'Status'])
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        writer.writerow([nome, email, timestamp, status])

def log_sent_email(email):
    with open(SENT_LOG_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        writer.writerow([email])

def get_sent_emails():
    if not os.path.isfile(SENT_LOG_FILE):
        return set()
    with open(SENT_LOG_FILE, mode='r', encoding='utf-8') as f:
        return set(row[0] for row in csv.reader(f))

SCOPES = ['https://www.googleapis.com/auth/gmail.send']

def get_gmail_service():
    creds = None
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=0)
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    try:
        service = build('gmail', 'v1', credentials=creds)
        logging.info("Serviço do Gmail autenticado com sucesso.")
        return service
    except HttpError as error:
        logging.error(f'Ocorreu um erro ao criar o serviço do Gmail: {error}')
        return None

def create_message_with_attachment(sender, to, subject, message_html, attachment_path):
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    message.attach(MIMEText(message_html, 'html'))
    try:
        with open(attachment_path, 'rb') as f:
            part = MIMEApplication(f.read(), Name=os.path.basename(attachment_path))
        part['Content-Disposition'] = f'attachment; filename="{os.path.basename(attachment_path)}"'
        message.attach(part)
    except FileNotFoundError:
        logging.error(f"ERRO DE ANEXO: Arquivo não encontrado em '{attachment_path}'")
        return None
    raw_message = base64.urlsafe_b64encode(message.as_bytes()).decode()
    return {'raw': raw_message}

def send_emails(is_dev_mode=False, limit=None): # NOVO: Parâmetro limit
    service = get_gmail_service()
    if not service:
        logging.critical("Não foi possível autenticar com o Gmail. Saindo.")
        return

    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    recipients_to_send = []
    
    sent_emails = get_sent_emails()

    if is_dev_mode:
        logging.info("="*50 + "\n=== EXECUTANDO EM MODO DE DESENVOLVIMENTO (--dev) ===\n" + "="*50)
        all_recipients = list(set(DEV_EMAIL_LIST))
    else:
        logging.info("="*50 + f"\n=== EXECUTANDO EM MODO DE PRODUÇÃO (Arquivo: {CSV_FILE_PATH}) ===\n" + "="*50)
        try:
            emails_lidos = []
            with open(CSV_FILE_PATH, mode='r', encoding='latin-1') as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if row and row[0]:
                        emails_lidos.append(row[0].strip().lower())
            
            total_lidos = len(emails_lidos)
            all_recipients = list(set(emails_lidos))
            total_unicos_na_lista = len(all_recipients)

            logging.info(f"Arquivo CSV lido. Total de e-mails encontrados: {total_lidos}.")
            if total_lidos > total_unicos_na_lista:
                logging.warning(f"Foram removidos {total_lidos - total_unicos_na_lista} e-mails duplicados da lista de entrada.")
        except FileNotFoundError:
            logging.error(f"Erro: Arquivo CSV não encontrado em '{CSV_FILE_PATH}'")
            return
        except Exception as e:
            logging.error(f"Ocorreu um erro inesperado ao ler o CSV: {e}")
            return

    recipients_to_send = [email for email in all_recipients if email not in sent_emails]
    
    num_ja_enviados = len(all_recipients) - len(recipients_to_send)
    if num_ja_enviados > 0:
        logging.info(f"{num_ja_enviados} e-mail(s) já foram enviados em sessões anteriores e serão ignorados.")

    if not recipients_to_send:
        logging.warning("Nenhum novo e-mail para enviar.")
    else:
        logging.info(f"Total de novos e-mails a serem enviados nesta sessão: {len(recipients_to_send)}")
        
        # NOVO: Lógica do --limit
        sent_in_session_count = 0
        
        for i, to_email_address in enumerate(recipients_to_send):
            if limit is not None and sent_in_session_count >= limit:
                logging.info(f"Limite de --limit={limit} envios para esta sessão foi atingido. Parando.")
                break

            nome_destinatario = to_email_address.split('@')[0]
            
            if not re.match(email_regex, to_email_address):
                logging.warning(f"Item {i+1}: '{to_email_address}' ignorado. Formato de e-mail inválido.")
                log_to_csv(nome_destinatario, to_email_address, 'Formato Inválido')
                continue

            email_message = create_message_with_attachment(FROM_EMAIL, to_email_address, EMAIL_SUBJECT, EMAIL_BODY_HTML, ATTACHMENT_FILE_PATH)
            
            if email_message is None:
                logging.critical("Processo interrompido porque o arquivo de anexo não foi encontrado.")
                break

            try:
                sent_message = service.users().messages().send(userId='me', body=email_message).execute()
                status = "Enviado com Sucesso"
                logging.info(f"Item {i+1}: E-mail enviado para {to_email_address}. ID: {sent_message['id']}")
                log_to_csv(nome_destinatario, to_email_address, status)
                log_sent_email(to_email_address)
                sent_in_session_count += 1 # NOVO: Incrementa o contador da sessão
            except HttpError as error:
                status = f"Erro: {error}"
                logging.error(f"!!! Erro ao enviar para {to_email_address}: {error}")
                log_to_csv(nome_destinatario, to_email_address, status)

            time.sleep(0.5)

    logging.info("\nProcesso de envio finalizado.")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Envia e-mails em massa com anexo usando a API do Gmail.")
    parser.add_argument('--dev', action='store_true', help="Ativa o modo de desenvolvimento.")
    parser.add_argument('--reset', action='store_true', help=f"Apaga o arquivo de controle de envios ({SENT_LOG_FILE}) para reenviar para todos.")
    parser.add_argument('--limit', type=int, help="Define um número máximo de e-mails a serem enviados nesta sessão.") # NOVO
    args = parser.parse_args()

    if args.reset:
        if os.path.exists(SENT_LOG_FILE):
            os.remove(SENT_LOG_FILE)
            logging.info(f"Arquivo de controle de envios '{SENT_LOG_FILE}' foi apagado. A campanha foi resetada.")
        else:
            logging.info(f"Arquivo de controle de envios '{SENT_LOG_FILE}' não encontrado. Nenhuma ação de reset necessária.")

    send_emails(is_dev_mode=args.dev, limit=args.limit) # NOVO: Passa o limit para a função