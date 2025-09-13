# collector.py (Versão Aprimorada com Datas)

import sys
import os
import datetime
import logging
import argparse
from typing import List
from google.cloud import firestore

# Adiciona o diretório raiz ao path para resolver imports
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), "firebase-admin.json")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from licitai.data_collection.comprasnet_sdk.licitacoes_api import Licitacoes
from licitai.data_collection.comprasnet_sdk.pncp_client import ComprasNetAPIClient

# --- Configuração ---
log_dir = 'logs'
if not os.path.exists(log_dir):
    os.makedirs(log_dir)
log_filename = datetime.datetime.now().strftime('firestore_collector_log_%Y%m%d_%H%M%S.log')
log_filepath = os.path.join(log_dir, log_filename)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s', handlers=[logging.FileHandler(log_filepath, encoding='utf-8'), logging.StreamHandler(sys.stdout)])
logger = logging.getLogger(__name__)

# --- INICIALIZAÇÃO DO FIRESTORE ---
try:
    db = firestore.Client(project="pncp-insights-jewpf")
    logger.info(f"Conectado ao projeto Firestore: {db.project}")
except Exception as e:
    logger.error(f"Não foi possível conectar ao Firestore. Verifique as credenciais. Erro: {e}")
    sys.exit(1)
# --- FIM DA INICIALIZAÇÃO ---

BRAZILIAN_STATES = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"]

api_client = ComprasNetAPIClient()
licitacoes_module = Licitacoes(api_client)

def run_collector(data_inicial_sync: str, data_final_sync: str, uf_list: List[str] = BRAZILIAN_STATES):
    """
    Executa a coleta de contratações para um intervalo de datas e lista de UFs.
    """
    logger.info(f"--- Iniciando Coletor de Contratações para o período de {data_inicial_sync} a {data_final_sync} ---")
    
    total_new_contracts = 0
    contratacoes_ref = db.collection('contratacoes')

    for uf_code in uf_list:
        logger.info(f"\n===== Buscando licitações em: '{uf_code}' =====")
        try:
            # Modalidades: 1 (Pregão/Concorrência Eletrônica), 7 (Dispensa com Disputa)
            modalidades_a_buscar = [1, 7]
            for modalidade_id in modalidades_a_buscar:
                logger.info(f"  -- Verificando Modalidade: {modalidade_id} --")
                
                params = {
                    "dataInicial": data_inicial_sync,
                    "dataFinal": data_final_sync,
                    "codigoModalidadeContratacao": modalidade_id,
                    "uf": uf_code
                }
                
                resumos = licitacoes_module.buscar_por_publicacao(**params)
                
                if not resumos:
                    logger.info(f"  Nenhuma licitação encontrada para Modalidade {modalidade_id} em '{uf_code}' no período.")
                    continue

                logger.info(f"  {len(resumos)} licitações encontradas. Salvando no banco de dados...")
                
                for resumo in resumos:
                    pncp_control_number_raw = resumo.get('numeroControlePNCP')
                    if not pncp_control_number_raw: continue

                    # Substitui a barra "/" por hífen "-" para ser um ID de documento válido no Firestore
                    pncp_control_number = pncp_control_number_raw.replace('/', '-')

                    doc_ref = contratacoes_ref.document(pncp_control_number)
                    if doc_ref.get().exists:
                        continue # Pula se o contrato já foi salvo anteriormente

                    dados_contratacao = {
                        "numeroControlePNCP": pncp_control_number,
                        "objetoCompra": resumo.get('objetoCompra'),
                        "modalidadeNome": resumo.get('modalidadeNome'),
                        "orgaoRazaoSocial": resumo.get('orgaoEntidade', {}).get('razaoSocial'),
                        "ufSigla": resumo.get('unidadeOrgao', {}).get('ufSigla'),
                        "municipioNome": resumo.get('unidadeOrgao', {}).get('municipioNome'),
                        "dataPublicacaoPncp": resumo.get('dataPublicacaoPncp', '').split('T')[0],
                        "linkEditalDocumentos": resumo.get('linkAvisoPublicacaoPncp') or resumo.get('linkSistemaOrigem'),
                        "dataSincronizacao": datetime.datetime.now(datetime.timezone.utc)
                    }
                    
                    contratacoes_ref.document(pncp_control_number).set(dados_contratacao)
                    total_new_contracts += 1

        except Exception as e:
            logger.error(f"  Erro crítico ao processar {uf_code}: {e}", exc_info=True)

    logger.info("\n--- Coletor Finalizado ---")
    logger.info(f"Total de novos contratos adicionados: {total_new_contracts}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Coletor de Contratações do PNCP.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    parser.add_argument(
        '--meses-atras',
        type=int,
        default=None,
        help="Número de meses para buscar a partir de hoje (ex: 6). Ignorado se --data-inicial for usada."
    )
    parser.add_argument(
        '--data-inicial',
        type=str,
        default=None,
        help="Data inicial para a busca no formato AAAA-MM-DD."
    )
    parser.add_argument(
        '--data-final',
        type=str,
        default=None,
        help="Data final para a busca no formato AAAA-MM-DD. Padrão: hoje."
    )

    args = parser.parse_args()

    # Lógica para determinar o intervalo de datas
    today = datetime.date.today()
    
    if args.data_inicial:
        start_date_str = args.data_inicial
        end_date_str = args.data_final if args.data_final else today.strftime("%Y-%m-%d")
    elif args.meses_atras:
        # Aproximação para o número de dias
        start_date = today - datetime.timedelta(days=int(args.meses_atras * 30.5))
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = today.strftime("%Y-%m-%d")
    else:
        # Padrão: buscar apenas o mês atual
        start_date = today.replace(day=1)
        start_date_str = start_date.strftime("%Y-%m-%d")
        end_date_str = today.strftime("%Y-%m-%d")

    run_collector(data_inicial_sync=start_date_str, data_final_sync=end_date_str)