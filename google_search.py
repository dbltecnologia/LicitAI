# /root/ASM/LicitAI/google_search.py (Versão Corrigida)
"""
Módulo simples para abstrair a execução de buscas no Google.
Utiliza a biblioteca 'googlesearch-python' para realizar as buscas.
"""
import time
import logging
from collections import namedtuple
from googlesearch import search as google_search_lib

# Configuração do logger
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Estruturas de dados para os resultados
SearchResult = namedtuple('SearchResult', ['url', 'title', 'snippet'])
QueryResultSet = namedtuple('QueryResultSet', ['query', 'results'])

def search(queries: list, num_results: int = 5, lang: str = 'pt-br', pause: int = 2):
    """
    Executa uma lista de queries no Google e retorna os resultados.
    """
    all_results = []
    for query in queries:
        try:
            logger.info(f"Executando busca para a query: '{query}'")
            # A biblioteca retorna um gerador, então o convertemos para uma lista
            search_results_generator = google_search_lib(
                query,
                num_results=num_results,
                lang=lang
                # O argumento 'pause' foi removido daqui, pois não é suportado pela biblioteca.
            )
            
            # O snippet não é fornecido por esta biblioteca, então passamos um texto padrão.
            # O mais importante é a URL, que será usada para extrair o conteúdo da página.
            current_results = [
                SearchResult(url=url, title="N/A", snippet="Snippet não disponível") 
                for url in search_results_generator
            ]

            all_results.append(QueryResultSet(query=query, results=current_results))
            
        except Exception as e:
            logger.error(f"Erro ao executar a busca para a query '{query}': {e}")
            all_results.append(QueryResultSet(query=query, results=[]))
        
        # Mantemos uma pausa manual entre as diferentes queries para não sobrecarregar o serviço
        time.sleep(pause)
        
    return all_results