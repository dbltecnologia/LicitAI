
import asyncio
import logging
from google.cloud import firestore
import os
import datetime
import sys

# --- Configuração Profissional ---

# 1. Adiciona o diretório raiz ao path para garantir que os imports funcionem
#    corretamente quando o script é executado de qualquer lugar.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# 2. Importa o módulo de análise após a configuração do path.
from licitai.processing.regex_extractor import analisar_objeto_com_ia

# 3. Configuração do logging para um output claro e informativo.
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 4. Carregamento de Segredos a partir de Variáveis de Ambiente (MELHOR PRÁTICA)
#    O código nunca armazena chaves de API. Ele espera que o ambiente de execução
#    (seja local, Docker ou um servidor na nuvem) forneça a chave.
API_TOKEN = os.getenv("GEMINI_API_KEY")
if not API_TOKEN:
    logger.error("CRÍTICO: A variável de ambiente GEMINI_API_KEY não está definida.")
    sys.exit(1) # O script para se a configuração de segurança não estiver presente.

# 5. A autenticação do Google Cloud (Firestore) agora também é gerenciada pelo ambiente.
#    O desenvolvedor deve usar `gcloud auth application-default login` localmente,
#    ou configurar uma Conta de Serviço no ambiente de produção.
#    A linha que apontava para o "firebase-admin.json" foi REMOVIDA.

# --- Constantes do Sistema ---
TAREFAS_COLLECTION_NAME = 'tarefasRaspagem'
CONTRATACOES_COLLECTION_NAME = 'contratacoes'
PROJECT_ID = "pncp-insights-jewpf" # É seguro manter o ID do projeto no código.

def get_firestore_client():
    """Inicializa e retorna o cliente do Firestore de forma segura."""
    try:
        db = firestore.Client(project=PROJECT_ID)
        logger.info("Cliente do Firestore inicializado com sucesso.")
        return db
    except Exception as e:
        logger.error(f"Falha ao inicializar o cliente do Firestore. Verifique se as credenciais do ambiente (ADC) estão configuradas. Erro: {e}", exc_info=True)
        raise

async def processar_tarefa(db, tarefa_doc):
    """
    Orquestra o processamento de uma única tarefa: busca dados, chama a IA,
    e atualiza o status no Firestore, com tratamento de erros robusto.
    """
    task_id = tarefa_doc.id
    tarefa_data = tarefa_doc.to_dict()
    pncp_number = tarefa_data.get("numeroControlePNCP")
    tarefa_ref = db.collection(TAREFAS_COLLECTION_NAME).document(task_id)

    if not pncp_number:
        logger.error(f"Tarefa {task_id} sem 'numeroControlePNCP'. Marcando como falha.")
        await asyncio.to_thread(tarefa_ref.update, {'status': 'falha_dados_insuficientes', 'fimAnalise': datetime.datetime.now(datetime.timezone.utc)})
        return

    try:
        logger.info(f"--- Iniciando Análise | Tarefa: {task_id} | PNCP: {pncp_number} ---")
        await asyncio.to_thread(tarefa_ref.update, {
            'status': 'analisando',
            'inicioAnalise': datetime.datetime.now(datetime.timezone.utc),
            'workerVersion': '3.0-portfolio'
        })

        # Etapa 1: Buscar dados da licitação original
        contratacao_ref = db.collection(CONTRATACOES_COLLECTION_NAME).document(pncp_number)
        contratacao_doc = await asyncio.to_thread(contratacao_ref.get)
        if not contratacao_doc.exists:
            raise FileNotFoundError(f"Documento de contratação {pncp_number} não encontrado.")
        
        objeto_compra = contratacao_doc.to_dict().get("objetoCompra")
        if not objeto_compra:
            raise ValueError(f"Campo 'objetoCompra' vazio para a contratação {pncp_number}.")

        # Etapa 2: Chamar a IA para análise
        logger.info(f"Enviando objeto para análise da IA: '{objeto_compra[:100]}...'")
        resultado_analise = await analisar_objeto_com_ia(objeto_compra, API_TOKEN)

        # Etapa 3: Estruturar e salvar o resultado
        dados_resultado = {
            'palavrasChave': resultado_analise.get("palavrasChave", []),
            'gatilhoVenda': resultado_analise.get("gatilhoVenda", "Não informado")
        }

        dados_atualizacao = {
            'status': 'analise_concluida',
            'fimAnalise': datetime.datetime.now(datetime.timezone.utc),
            'resultado': dados_resultado
        }
        
        await asyncio.to_thread(tarefa_ref.update, dados_atualizacao)
        logger.info(f"Tarefa {task_id} concluída com sucesso. Gatilho: {dados_resultado['gatilhoVenda']}")

    except Exception as e:
        # Tratamento de erro que marca a tarefa com falha para revisão posterior
        logger.error(f"ERRO CRÍTICO no processamento da tarefa {task_id}: {e}", exc_info=True)
        try:
            dados_erro = {
                'status': 'falha_api',
                'logErro': f"Erro: {type(e).__name__} - {e}",
                'fimAnalise': datetime.datetime.now(datetime.timezone.utc)
            }
            await asyncio.to_thread(tarefa_ref.update, dados_erro)
        except Exception as update_e:
            logger.error(f"Falha ao tentar atualizar o status de erro da tarefa {task_id}: {update_e}")

async def main():
    """Função principal do worker que opera em loop, buscando e processando tarefas."""
    logger.info("--- Worker de Análise de Licitações v3.0 (Portfolio Edition) Iniciado ---")
    db = get_firestore_client()
    
    while True:
        try:
            logger.info("Buscando lote de tarefas pendentes...")
            tarefas_ref = db.collection(TAREFAS_COLLECTION_NAME).where('status', '==', 'pendente').limit(5)
            tarefas_pendentes = list(await asyncio.to_thread(tarefas_ref.stream))

            if not tarefas_pendentes:
                logger.info("Nenhuma tarefa pendente encontrada. Aguardando 60 segundos...")
                await asyncio.sleep(60)
                continue

            tasks_to_process = [processar_tarefa(db, doc) for doc in tarefas_pendentes]
            await asyncio.gather(*tasks_to_process)
            
            logger.info("Lote de tarefas processado. Buscando o próximo...")
            await asyncio.sleep(5)

        except Exception as e:
            logger.error(f"Erro inesperado no loop principal do worker: {e}", exc_info=True)
            await asyncio.sleep(60) # Pausa antes de tentar novamente

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Worker interrompido pelo usuário.")
    except Exception as e:
        logger.critical(f"Erro fatal que impediu a inicialização do worker: {e}", exc_info=True)