# licitai/processing/lead_enricher.py (Versão Final com Busca Real)
"""
Worker responsável por enriquecer os leads qualificados pela IA.
Busca contatos (e-mail, telefone) de departamentos-chave nos sites dos órgãos públicos.
"""
import sys
import os
import logging
import datetime
import asyncio
import re
from google.cloud import firestore
from google_search import search # Importa a ferramenta de busca

# --- Configuração Inicial ---
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), "firebase-admin.json")

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# --- Constantes ---
TAREFAS_COLLECTION_NAME = 'tarefasRaspagem'
CONTRATACOES_COLLECTION_NAME = 'contratacoes'
STATUS_TO_ENRICH = 'analise_concluida'
STATUS_SUCCESS = 'enriquecimento_concluido'
STATUS_FAIL = 'falha_enriquecimento'
EMAIL_REGEX = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'

def get_firestore_client():
    """Inicializa e retorna o cliente do Firestore."""
    try:
        db = firestore.Client(project="pncp-insights-jewpf")
        logger.info("Cliente do Firestore inicializado com sucesso.")
        return db
    except Exception as e:
        logger.error(f"Falha ao inicializar o cliente do Firestore: {e}", exc_info=True)
        raise

async def enrich_task(db, task_doc):
    """Processa uma única tarefa, buscando contatos para o órgão associado."""
    task_id = task_doc.id
    task_data = task_doc.to_dict()
    task_ref = db.collection(TAREFAS_COLLECTION_NAME).document(task_id)
    
    pncp_number = task_data.get("numeroControlePNCP")
    if not pncp_number:
        logger.error(f"Tarefa {task_id} não possui 'numeroControlePNCP'. Marcando como falha.")
        task_ref.update({'status': STATUS_FAIL, 'logErro': 'PNCP não encontrado na tarefa.'})
        return

    try:
        logger.info(f"--- Iniciando Enriquecimento | Tarefa ID: {task_id} | PNCP: {pncp_number} ---")
        await asyncio.to_thread(task_ref.update, {'status': 'enriquecendo'})

        # 1. Buscar dados da contratação original
        contratacao_ref = db.collection(CONTRATACOES_COLLECTION_NAME).document(pncp_number)
        contratacao_doc = await asyncio.to_thread(contratacao_ref.get)
        if not contratacao_doc.exists:
            raise FileNotFoundError(f"Documento de contratação {pncp_number} não encontrado.")
        
        contratacao_data = contratacao_doc.to_dict()
        orgao_nome = contratacao_data.get("orgaoRazaoSocial", "")
        municipio_nome = contratacao_data.get("municipioNome", "")
        uf_sigla = contratacao_data.get("ufSigla", "")

        if not orgao_nome or not municipio_nome:
            raise ValueError("Órgão ou município não encontrados nos dados da contratação.")

        logger.info(f"Órgão alvo: {orgao_nome} - {municipio_nome}/{uf_sigla}")

        # 2. Montar as queries de busca
        departamentos_alvo = ["departamento de TI", "secretaria de administração", "setor de compras", "licitações"]
        queries = [f'email contato "{depto}" "{orgao_nome}"' for depto in departamentos_alvo]
        
        # 3. Executar a busca e extrair contatos
        logger.info(f"Executando {len(queries)} buscas para encontrar contatos...")
        search_results = await asyncio.to_thread(search, queries=queries)
        
        found_contacts = []
        seen_emails = set()

        for result_set in search_results:
            if result_set.results:
                for res in result_set.results:
                    # Extrai e-mails do snippet
                    emails_in_snippet = re.findall(EMAIL_REGEX, res.snippet)
                    for email in emails_in_snippet:
                        if email.lower() not in seen_emails:
                            contact_info = {
                                "email": email.lower(),
                                "fonte": res.url,
                                "trecho": res.snippet
                            }
                            found_contacts.append(contact_info)
                            seen_emails.add(email.lower())
        
        if found_contacts:
            logger.info(f"Sucesso! {len(found_contacts)} contatos de e-mail encontrados.")
        else:
            logger.warning("Nenhum contato de e-mail encontrado para este órgão.")

        # 4. Atualizar a tarefa com o resultado
        dados_atualizacao = {
            'status': STATUS_SUCCESS,
            'dataEnriquecimento': datetime.datetime.now(datetime.timezone.utc),
            'contatosEncontrados': found_contacts
        }
        await asyncio.to_thread(task_ref.update, dados_atualizacao)
        logger.info(f"Tarefa {task_id} enriquecida com {len(found_contacts)} contatos.")

    except Exception as e:
        logger.error(f"ERRO CRÍTICO no enriquecimento da tarefa {task_id}: {e}", exc_info=True)
        await asyncio.to_thread(task_ref.update, {'status': STATUS_FAIL, 'logErro': str(e)})

async def main():
    """Função principal do worker que busca e enriquece tarefas."""
    logger.info("--- Lead Enricher v1.0 (Busca Real) Iniciado ---")
    db = get_firestore_client()
    
    while True:
        try:
            # Resetar tarefas que estavam 'enriquecendo' caso o script tenha parado
            reset_query = db.collection(TAREFAS_COLLECTION_NAME).where('status', '==', 'enriquecendo').limit(10)
            for task in await asyncio.to_thread(reset_query.stream):
                logger.warning(f"Resetando status da tarefa {task.id} de 'enriquecendo' para '{STATUS_TO_ENRICH}'.")
                await asyncio.to_thread(task.reference.update, {'status': STATUS_TO_ENRICH})

            logger.info(f"Buscando lote de tarefas com status '{STATUS_TO_ENRICH}'...")
            tarefas_query = db.collection(TAREFAS_COLLECTION_NAME).where('status', '==', STATUS_TO_ENRICH).limit(5)
            tarefas_pendentes = list(await asyncio.to_thread(tarefas_query.stream))

            if not tarefas_pendentes:
                logger.info("Nenhuma tarefa para enriquecer. Aguardando 60 segundos...")
                await asyncio.sleep(60)
                continue

            tasks_to_process = [enrich_task(db, doc) for doc in tarefas_pendentes]
            await asyncio.gather(*tasks_to_process)
            
            logger.info("Lote de enriquecimento processado. Buscando o próximo...")
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Erro no loop principal do enricher: {e}", exc_info=True)
            await asyncio.sleep(60)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Enricher interrompido pelo usuário.")