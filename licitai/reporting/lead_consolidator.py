# licitai/reporting/lead_consolidator.py (Versão Final com Leitura Direta do Firestore)
"""
Consolida os resultados diretamente do Firestore, gerando um relatório
final em Excel com os leads qualificados e enriquecidos.
"""
import datetime
import pandas as pd
import sys
import os
import logging
from pathlib import Path
from google.cloud import firestore

# --- Configuração Inicial ---
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), "firebase-admin.json")
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constantes ---
TAREFAS_COLLECTION_NAME = 'tarefasRaspagem'
CONTRATACOES_COLLECTION_NAME = 'contratacoes'

def get_firestore_client():
    """Inicializa e retorna o cliente do Firestore."""
    try:
        return firestore.Client(project="pncp-insights-jewpf")
    except Exception as e:
        logger.error(f"Falha ao inicializar o cliente do Firestore: {e}", exc_info=True)
        sys.exit(1)

def fetch_data_from_firestore(db):
    """Busca e combina os dados das coleções 'tarefasRaspagem' e 'contratacoes'."""
    logger.info("Buscando tarefas finalizadas no Firestore...")
    
    # Status que indicam que uma tarefa foi processada e pode ser um lead
    status_relevantes = ['analise_concluida', 'enriquecimento_concluido', 'falha_enriquecimento']
    
    tarefas_ref = db.collection(TAREFAS_COLLECTION_NAME)
    contratacoes_ref = db.collection(CONTRATACOES_COLLECTION_NAME)
    
    leads_data = []
    
    # Usamos 'in' para buscar múltiplos status de uma vez
    query = tarefas_ref.where('status', 'in', status_relevantes)
    
    for tarefa_doc in query.stream():
        tarefa_data = tarefa_doc.to_dict()
        pncp_number = tarefa_data.get("numeroControlePNCP")
        
        if not pncp_number:
            continue

        # Busca os dados da contratação original para complementar as informações
        contratacao_doc = contratacoes_ref.document(pncp_number).get()
        if contratacao_doc.exists:
            contratacao_data = contratacao_doc.to_dict()
        else:
            contratacao_data = {}

        # Combina os dados da tarefa e da contratação
        resultado_ia = tarefa_data.get('resultado', {})
        contatos_encontrados = tarefa_data.get('contatosEncontrados', [])
        
        # Pega o primeiro e-mail encontrado, se houver
        primeiro_email = contatos_encontrados[0]['email'] if contatos_encontrados else 'N/A'

        lead = {
            'PNCP': pncp_number,
            'Orgao': contratacao_data.get('orgaoRazaoSocial', 'N/A'),
            'Municipio': f"{contratacao_data.get('municipioNome', 'N/A')}/{contratacao_data.get('ufSigla', 'N/A')}",
            'Objeto da Compra': contratacao_data.get('objetoCompra', 'N/A'),
            'Link Edital': contratacao_data.get('linkEditalDocumentos', 'N/A'),
            'Gatilho de Venda': resultado_ia.get('gatilhoVenda', 'N/A'),
            'Palavras-Chave IA': ", ".join(resultado_ia.get('palavrasChave', [])),
            'Status Final': tarefa_data.get('status', 'N/A'),
            'Email Encontrado': primeiro_email,
            'Total Contatos': len(contatos_encontrados)
        }
        leads_data.append(lead)
        
    if not leads_data:
        return pd.DataFrame() # Retorna um DataFrame vazio se nada for encontrado

    return pd.DataFrame(leads_data)

def main():
    """Função principal para gerar o relatório consolidado."""
    db = get_firestore_client()
    df_leads = fetch_data_from_firestore(db)

    if df_leads.empty:
        logger.warning("Nenhum lead finalizado foi encontrado no Firestore para gerar o relatório.")
        return

    logger.info(f"Total de leads processados encontrados: {len(df_leads)}")

    # Define o caminho do arquivo de saída
    output_dir = Path("resultados")
    output_dir.mkdir(exist_ok=True)
    timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
    output_filepath = output_dir / f"Relatorio_Leads_{timestamp}.xlsx"

    # Salva o arquivo Excel final
    df_leads.to_excel(output_filepath, index=False, engine='openpyxl')
    logger.info(f"Relatório consolidado foi salvo com sucesso em: '{output_filepath}'")

if __name__ == "__main__":
    main()
