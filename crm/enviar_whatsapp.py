# enviar_whatsapp.py (Versão Final com Logs e Controle Semanal)

import os
import re
import sys
import time
import random
import pandas as pd
import requests
import json
from datetime import datetime
from dotenv import load_dotenv

# ==============================================================================
# --- ÁREA DE CONFIGURAÇÃO ---
# ==============================================================================
HISTORICO_FILE = 'historico_envios.csv'
LOG_DIRECTORY = 'logs'

MENSAGEM_PADRAO = """
Prezado(a) {nome},

Somos a ASM tecnologia, atendendo à órgãos públicos há mais de 10 anos.

Apresentamos uma oportunidade de aquisição simplificada, por meio de adesão ata de registro de preços vigente, referente ao seguinte produto:

*Produto:* Microsoft Office Professional Plus 2021 (PT-BR)
✔ *Licença:* Perpétua, sem Software Assurance
✔ *Compatibilidade:* Windows 10 ou superior | 32 e 64 bits
✔ *Instalação:* Desktop
✔ *Valor:* R$ 1800,00 (mil e oitocentos reais) por licença
✔ *Modelo de contratação:* Adesão direta via ata (sem necessidade de nova licitação)

*Condições:* Conforme Termo de Referência da ata vigente.

A aquisição por ata garante:
• *Agilidade no processo* (dispensa nova licitação);
• *Segurança jurídica*, conforme a Lei 14.133/2021;
• *Otimização de custos* operacionais, com valores já homologados.

Caso haja interesse, permanecemos à disposição para orientar o processo de adesão e dar andamento imediato.

Atenciosamente,

*FERNANDO ANDRE SILVA MACIEL*
CEO ASM Tecnologia

(WhatsApp e Ligações)
(61) 9832-3833
(WhatsApp Comercial)
(61) 3142-1273
"""
# ==============================================================================
# --- LÓGICA DO SCRIPT ---
# ==============================================================================

class Tee(object):
    """Classe para redirecionar o output para o console e um arquivo de log."""
    def __init__(self, name, mode):
        self.file = open(name, mode, encoding='utf-8')
        self.stdout = sys.stdout
        sys.stdout = self
    def __del__(self):
        sys.stdout = self.stdout
        self.file.close()
    def write(self, data):
        self.file.write(data)
        self.stdout.write(data)
    def flush(self):
        self.file.flush()

def setup_logging():
    """Configura o salvamento do output em um arquivo de log."""
    if not os.path.exists(LOG_DIRECTORY):
        os.makedirs(LOG_DIRECTORY)
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    log_filename = os.path.join(LOG_DIRECTORY, f"execucao_{timestamp}.log")
    sys.stdout = Tee(log_filename, 'a')
    print(f"Log iniciado em: {log_filename}")

def carregar_historico(arquivo):
    """Carrega o histórico de envios para um dicionário."""
    if not os.path.exists(arquivo):
        return {}
    historico = {}
    with open(arquivo, 'r', encoding='utf-8') as f:
        for line in f:
            parts = line.strip().split(',')
            if len(parts) == 2:
                telefone, data_str = parts
                historico[telefone] = data_str
    return historico

def registrar_envio(telefone, arquivo):
    """Registra um envio bem-sucedido no histórico."""
    data_hoje = datetime.now().strftime("%Y-%m-%d")
    with open(arquivo, 'a', encoding='utf-8') as f:
        f.write(f"{telefone},{data_hoje}\n")

def enviado_na_mesma_semana(telefone, historico):
    """Verifica se um número já recebeu mensagem na semana atual."""
    if telefone not in historico:
        return False
    
    data_ultimo_envio_str = historico[telefone]
    try:
        data_ultimo_envio = datetime.strptime(data_ultimo_envio_str, "%Y-%m-%d")
        hoje = datetime.now()
        
        # Compara o ano e o número da semana (ISO calendar)
        return hoje.isocalendar()[:2] == data_ultimo_envio.isocalendar()[:2]
    except ValueError:
        # Em caso de data mal formatada no histórico, considera como não enviado
        return False

def carregar_configuracao():
    load_dotenv()
    config = {
        "api_url": os.getenv('EVOLUTION_API_URL'),
        "api_key": os.getenv('EVOLUTION_API_KEY'),
        "instance_name": os.getenv('EVOLUTION_INSTANCE_NAME'),
        "min_delay": 30,
        "max_delay": 60
    }
    if not all([config["api_url"], config["api_key"], config["instance_name"]]):
        print("ERRO: Verifique as variáveis EVOLUTION_API_URL, EVOLUTION_API_KEY e EVOLUTION_INSTANCE_NAME no arquivo .env")
        return None
    return config

def enviar_mensagem_whatsapp(telefone, mensagem, config):
    headers = {"Content-Type": "application/json", "apikey": config["api_key"]}
    payload = {"number": telefone, "text": mensagem.strip()}
    url = f"{config['api_url']}/message/sendText/{config['instance_name']}"

    print(f"Enviando para {telefone}...")
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        response.raise_for_status()
        print("-> SUCESSO: Mensagem enviada para a fila de envio.")
        return "sucesso"
    except requests.exceptions.HTTPError as e:
        if e.response.status_code == 400:
            try:
                error_data = e.response.json()
                if "response" in error_data and "message" in error_data["response"]:
                    if isinstance(error_data["response"]["message"], list) and not error_data["response"]["message"][0].get("exists", True):
                        print("-> FALHA: O número não existe no WhatsApp.")
                        return "inexistente"
            except (json.JSONDecodeError, KeyError, IndexError):
                pass
        
        print(f"-> ERRO HTTP: {e.response.status_code} - {e.response.text}")
        return "erro"
    except requests.exceptions.RequestException as e:
        print(f"-> ERRO de Conexão: {e}")
        return "erro"

def main():
    setup_logging()
    print("--- Iniciando Envio de Mensagens ---")
    
    config = carregar_configuracao()
    if not config: return

    try:
        contatos_df = pd.read_csv('contatos.csv')
        print(f"Encontrados {len(contatos_df)} contatos no arquivo 'contatos.csv'.")
    except FileNotFoundError:
        print("ERRO: Arquivo 'contatos.csv' não encontrado.")
        return
    except Exception as e:
        print(f"ERRO ao ler o arquivo de contatos: {e}")
        return

    historico_envios = carregar_historico(HISTORICO_FILE)
    print(f"Carregados {len(historico_envios)} registros do histórico de envios.")
    
    sucesso, inexistente, erro_geral, ja_enviado = 0, 0, 0, 0
    total = len(contatos_df)

    for index, contato in contatos_df.iterrows():
        nome = contato.get('nome', '')
        telefone_original = str(contato.get('telefone', ''))

        if not nome or not telefone_original:
            print(f"AVISO: Linha {index + 2} ignorada por falta de nome ou telefone.")
            continue
            
        telefone_limpo = re.sub(r'\D', '', telefone_original)
        if len(telefone_limpo) >= 10 and not telefone_limpo.startswith('55'):
            telefone_limpo = '55' + telefone_limpo
        
        print(f"\n({index + 1}/{total}) Preparando para enviar para: {nome} ({telefone_limpo})")

        # --- NOVA VERIFICAÇÃO DE ENVIO SEMANAL ---
        if enviado_na_mesma_semana(telefone_limpo, historico_envios):
            print(f"AVISO: Contato já recebeu mensagem esta semana. Pulando.")
            ja_enviado += 1
            continue
        
        mensagem_final = MENSAGEM_PADRAO.format(nome=nome)
        status = enviar_mensagem_whatsapp(telefone_limpo, mensagem_final, config)

        pausar = True
        if status == "sucesso":
            sucesso += 1
            registrar_envio(telefone_limpo, HISTORICO_FILE)
            historico_envios[telefone_limpo] = datetime.now().strftime("%Y-%m-%d") # Atualiza o histórico em memória
        elif status == "inexistente":
            inexistente += 1
            pausar = False
        else:
            erro_geral += 1

        if pausar and index < total - 1:
            delay = random.randint(config["min_delay"], config["max_delay"])
            print(f"PAUSA: Aguardando {delay} segundos...")
            time.sleep(delay)
            
    print("\n--- Processo Finalizado ---")
    print(f"Resumo: {sucesso} sucesso(s), {inexistente} número(s) inexistente(s), {erro_geral} erro(s), {ja_enviado} já contatado(s) esta semana.")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nProcesso interrompido pelo usuário.")
    finally:
        # Garante que o log seja fechado corretamente
        if isinstance(sys.stdout, Tee):
            del sys.stdout