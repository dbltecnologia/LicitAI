import requests
import argparse
import time
import pandas as pd # Biblioteca para criar o arquivo Excel
import os

# --- CONFIGURAÇÃO ---
CHATWOOT_URL = "http://chatai.dbltecnologia.com.br:3002"

def get_all_conversations_paginated(account_id, api_token):
    """Busca TODAS as conversas da conta, lidando com a paginação da API."""
    all_conversations = []
    page = 1
    
    print("Buscando todas as conversas (com paginação)...")
    while True:
        url = f"{CHATWOOT_URL}/api/v1/accounts/{account_id}/conversations"
        headers = {'api_access_token': api_token}
        params = {'page': page}
        
        print(f"Buscando página {page}...")
        try:
            response = requests.get(url, headers=headers, params=params)
            response.raise_for_status()
            
            current_page_conversations = response.json().get('data', {}).get('payload', [])
            
            if not current_page_conversations:
                print("Página vazia encontrada. Fim da busca.")
                break
            
            all_conversations.extend(current_page_conversations)
            page += 1
            time.sleep(0.5)

        except requests.exceptions.RequestException as e:
            print(f"ERRO ao buscar a página {page}: {e}")
            break

    print(f"SUCESSO: {len(all_conversations)} conversas encontradas no total em {page - 1} página(s).")
    return all_conversations

def filter_empty_and_open_conversations(conversations):
    """Filtra a lista de conversas, retornando apenas as que estão abertas e sem mensagens."""
    empty_conversations = []
    
    print("\nAnalisando conversas para encontrar as abertas e sem mensagens...")
    
    for conv in conversations:
        is_open = conv.get('status') == 'open'
        has_no_messages = not conv.get('messages')
        
        if is_open and has_no_messages:
            empty_conversations.append(conv)
            
    return empty_conversations

def save_to_excel(data, filename="conversas_vazias.xlsx"):
    """Salva os dados fornecidos em um arquivo Excel."""
    if not data:
        print("Nenhum dado para salvar no Excel.")
        return

    # Cria um DataFrame do Pandas, que é uma estrutura de tabela
    df = pd.DataFrame(data)
    
    try:
        # Salva o DataFrame em um arquivo .xlsx, sem o índice numérico do Pandas
        df.to_excel(filename, index=False)
        # os.path.abspath mostra o caminho completo do arquivo salvo
        print(f"\nSUCESSO: Resultados salvos em '{os.path.abspath(filename)}'")
    except Exception as e:
        print(f"\nERRO ao salvar o arquivo Excel: {e}")


def main():
    """Função principal que orquestra o processo."""
    parser = argparse.ArgumentParser(
        description="Encontra conversas no Chatwoot que foram criadas mas não possuem nenhuma mensagem."
    )
    parser.add_argument('--account-id', required=True, help="O ID da conta no Chatwoot a ser verificada.")
    parser.add_argument('--token', required=True, help="O token de acesso da API do Chatwoot.")
    
    args = parser.parse_args()
    
    all_conversations = get_all_conversations_paginated(args.account_id, args.token)
    
    if not all_conversations:
        print("Nenhuma conversa foi encontrada na conta para analisar.")
        return
        
    empty_conversations_list = filter_empty_and_open_conversations(all_conversations)
    
    if not empty_conversations_list:
        print("\nNenhuma conversa aberta e sem mensagens foi encontrada.")
    else:
        print("\n--- Conversas Abertas e Sem Mensagens Encontradas ---")
        
        # Lista para armazenar os dados para o Excel
        results_for_excel = []

        for conv in empty_conversations_list:
            sender_info = conv.get('meta', {}).get('sender', {})
            contact_name = sender_info.get('name', 'Nome não disponível')
            # Extraindo o número de telefone
            phone_number = sender_info.get('phone_number', 'Telefone não disponível')
            conversation_id = conv.get('id')
            
            print(f"  - ID: {conversation_id} | Contato: {contact_name} | Telefone: {phone_number}")

            # Adiciona os dados à lista para o Excel
            results_for_excel.append({
                "ID da Conversa": conversation_id,
                "Nome do Contato": contact_name,
                "Telefone": phone_number
            })
            
        print(f"\nTotal de conversas sem mensagens: {len(empty_conversations_list)}")
        
        # Chama a função para salvar os resultados no arquivo Excel
        save_to_excel(results_for_excel)

if __name__ == "__main__":
    main()