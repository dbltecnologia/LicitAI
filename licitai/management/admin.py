# licitai_management_unificado.py
"""
Script unificado para administração do LicitAI.
Inclui: limpeza de fila, pesquisa inicial, diagnóstico, geração e gerenciamento de tarefas.
"""
import sys
import os
import argparse
import logging
import datetime
import re
from collections import Counter
from pathlib import Path

# Aponta para o arquivo de credenciais do Firebase/Google Cloud
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), "firebase-admin.json")


from typing import List
from google.cloud import firestore




# --- Configuração de Log ---
log_dir = 'logs'
Path(log_dir).mkdir(exist_ok=True)
log_filename = datetime.datetime.now().strftime('licitai_management_log_%Y%m%d_%H%M%S.log')
log_filepath = os.path.join(log_dir, log_filename)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler(log_filepath, encoding='utf-8'), logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- Constantes ---
TAREFAS_COLLECTION_NAME = 'tarefasRaspagem'
CONTRATACOES_COLLECTION_NAME = 'contratacoes'
PESQUISAS_COLLECTION_NAME = 'pesquisas'

PESQUISA_INICIAL = {
    'nomePesquisa': 'Pesquisa Estratégica de Software e Gatilhos v3',
    'clienteId': 'licitai-admin',
    'ativo': True,
    'palavrasChave': [
        # --- 1. Compra Direta e Concorrentes ---
        # Foco total em produtos de escritório e licenciamento.
        "microsoft office",
        "office ltsc",           # Nome técnico da versão perpétua
        "pacote de escritório",
        "suite de produtividade",
        "licença perpétua",
        "licenciamento de software",
        "google workspace",      # Concorrente direto (oportunidade de migração)
        "office 365",            # Concorrente direto (oportunidade de migração para perpétuo)
        "m365",                  # Sigla para o concorrente

        # --- 2. Gatilhos de Hardware (Novos Equipamentos = Nova Demanda) ---
        # A compra de hardware quase sempre exige a compra de software.
        "aquisição de computadores",
        "compra de notebooks",
        "estações de trabalho",
        "desktop",
        "microcomputadores",
        "equipamentos de informática",
        "parque tecnológico",

        # --- 3. Gatilhos de Renovação e Contratos (Janela de Oportunidade) ---
        # Indica que um contrato está vencendo e o cliente está aberto a novas propostas.
        "renovação de licenças",
        "software assurance",      # Contrato de suporte Microsoft que expira
        "enterprise agreement",    # Modelo de contrato por volume que expira
        "expiração de licença",
        "atualização de software",
        "suporte técnico de software",
        "regularização de licenças",

        # --- 4. Infraestrutura e Segurança (Projetos Maiores que Incluem Software) ---
        # Termos de projetos maiores onde licenças Office são frequentemente incluídas no "pacote".
        "antivírus corporativo",
        "firewall",
        "servidor",
        "solução de backup",
        "storage",
        "segurança da informação",
        "infraestrutura de TI",
        "virtualização"
    ]
}

STATUS_PARA_REPROCESSAR = [
    'indefinido', 'analise_parcial_erro_validacao', 'erro_extracao_ia', 'erro_geral_adapter',
    'falha_worker', 'erro_raspagem', 'analise_concluida', 'erro_formato_ia'
]

STOP_WORDS = {'processo', 'contratação', 'edital', 'serviços', 'aquisição', 'fornecimento', 'preços', 'registro', 'futura', 'eventual', 'objetivo', 'municipal', 'prefeitura', 'secretaria', 'conforme', 'município', 'nº', 'n.º', 'para', 'de', 'do', 'da', 'dos', 'das', 'com', 'sem', 'sob', 'por', 'pelo', 'pela'}

# --- Firestore ---
def get_firestore_client():
    try:
        return firestore.Client(project="pncp-insights-jewpf")
    except Exception as e:
        logger.error(f"Falha ao inicializar o cliente do Firestore: {e}", exc_info=True)
        sys.exit(1)

# --- Limpar Fila ---
def limpar_fila(db):
    collection_ref = db.collection(TAREFAS_COLLECTION_NAME)
    logger.info(f"Iniciando a limpeza da coleção '{TAREFAS_COLLECTION_NAME}'...")
    deleted_count = 0
    while True:
        docs = list(collection_ref.limit(200).stream())
        if not docs: break
        batch = db.batch()
        for doc in docs: batch.delete(doc.reference)
        batch.commit()
        deleted_count += len(docs)
        logger.info(f"{deleted_count} tarefas deletadas...")
    logger.info(f"Limpeza concluída. Total de {deleted_count} tarefas deletadas.")

# --- Criar Pesquisa Inicial ---
def garantir_pesquisa(db):
    pesquisas_ref = db.collection(PESQUISAS_COLLECTION_NAME)
    nome_pesquisa = PESQUISA_INICIAL['nomePesquisa']
    query = pesquisas_ref.where('nomePesquisa', '==', nome_pesquisa).limit(1)
    if list(query.stream()):
        logger.info(f"A pesquisa inicial '{nome_pesquisa}' já existe.")
    else:
        logger.info(f"Criando a pesquisa inicial '{nome_pesquisa}'...")
        pesquisas_ref.add(PESQUISA_INICIAL)
        logger.info("Pesquisa inicial criada com sucesso!")

# --- Diagnóstico do Sistema ---
def diagnostico_sistema(db):
    logger.info("Iniciando diagnóstico do sistema...")
    tarefas_ref = db.collection(TAREFAS_COLLECTION_NAME)
    contratacoes_ref = db.collection(CONTRATACOES_COLLECTION_NAME)
    try:
        total_contratacoes = next(contratacoes_ref.count().get())[0].value
    except Exception:
        total_contratacoes = "N/A"
    status_counter = Counter(tarefa.to_dict().get('status', 'desconhecido') for tarefa in tarefas_ref.stream())
    total_tarefas = sum(status_counter.values())
    query_sucesso = tarefas_ref.where('status', 'in', ['analise_concluida', 'analise_parcial_erro_validacao'])
    docs_sucesso = list(query_sucesso.stream())
    top_30_termos = []
    # Linhas para SUBSTITUIR em admin.py

    if docs_sucesso:
        termos_counter = Counter()
        for doc in docs_sucesso:
            resultado = doc.to_dict().get('resultado', {})
            # <<< CORRIGIDO: Ler da lista de palavrasChave em vez do inexistente assunto_principal
            palavras_chave_ia = resultado.get('palavrasChave', [])
            tokens_filtrados = [
                palavra.lower() for palavra in palavras_chave_ia 
                if palavra.lower() not in STOP_WORDS and len(palavra) > 3
            ]
            termos_counter.update(tokens_filtrados)
        top_30_termos = [{'termo': termo, 'ocorrencias': count} for termo, count in termos_counter.most_common(30)]
    print("\n===========================================")
    print("        RESUMO GERAL DO SISTEMA")
    print("===========================================")
    print(f"Total de Contratações na Base: {total_contratacoes}")
    print(f"Total de Tarefas na Fila: {total_tarefas}\n")
    print("--- Distribuição de Status das Tarefas ---")
    for status, count in sorted(status_counter.items()):
        print(f"  - {status.upper()}: {count} tarefa(s)")
    print(f"\n--- Análise de Termos (baseado em {len(docs_sucesso)} tarefas com resultado de IA) ---")
    if top_30_termos:
        print("\n--- TOP 30 TERMOS MAIS COMUNS NOS SUCESSOS ---")
        for item in top_30_termos:
            print(f"  - {item['termo']}: {item['ocorrencias']} ocorrência(s)")
    else:
        print("Nenhum termo relevante encontrado nas tarefas com sucesso.")
    print("===========================================")

# --- Gerar Tarefas ---
def gerar_tarefas(db):
    logger.info("Iniciando motor de geração de tarefas a partir de pesquisas salvas...")
    pesquisas_ref = db.collection(PESQUISAS_COLLECTION_NAME)
    contratacoes_ref = db.collection(CONTRATACOES_COLLECTION_NAME)
    tarefas_ref = db.collection(TAREFAS_COLLECTION_NAME)
    query_pesquisas = pesquisas_ref.where('ativo', '==', True)
    pesquisas_ativas = list(query_pesquisas.stream())
    if not pesquisas_ativas:
        logger.warning("Nenhuma pesquisa ativa encontrada na coleção 'pesquisas'. Abortando.")
        return
    logger.info(f"{len(pesquisas_ativas)} pesquisa(s) ativa(s) encontrada(s).")
    logger.info("Mapeando tarefas existentes para evitar duplicatas...")
    tarefas_existentes = set()
    for tarefa in tarefas_ref.stream():
        tarefa_data = tarefa.to_dict()
        contratacao_id = tarefa_data.get('contratacaoId')
        cliente_id = tarefa_data.get('clienteId')
        if contratacao_id and cliente_id:
            tarefas_existentes.add((contratacao_id, cliente_id))
    logger.info(f"{len(tarefas_existentes)} vínculos tarefa-cliente já existem.")
    logger.info("Varrendo a base de contratações...")
    novas_tarefas_criadas = 0
    batch = db.batch()
    commit_counter = 0
    todas_contratacoes = list(contratacoes_ref.stream())
    logger.info(f"Analisando {len(todas_contratacoes)} contratações...")
    for contratacao_doc in todas_contratacoes:
        contratacao_id = contratacao_doc.id
        contratacao_data = contratacao_doc.to_dict()
        objeto_compra = contratacao_data.get('objetoCompra')
        pncp_number = contratacao_data.get('numeroControlePNCP')
        if not all([objeto_compra, pncp_number]):
            logger.warning(f"Contratação '{contratacao_id}' pulada por não conter 'objetoCompra' ou 'numeroControlePNCP'.")
            continue
        objeto_lower = objeto_compra.lower()
        for pesquisa_doc in pesquisas_ativas:
            pesquisa_id = pesquisa_doc.id
            pesquisa_data = pesquisa_doc.to_dict()
            cliente_id = pesquisa_data.get('clienteId')
            palavras_chave = pesquisa_data.get('palavrasChave', [])
            if not cliente_id or not palavras_chave:
                continue
            if (contratacao_id, cliente_id) in tarefas_existentes:
                continue
            for keyword in palavras_chave:
                if keyword.lower() in objeto_lower:
                    logger.info(f"  > Match encontrado para Contratação '{pncp_number}' (Keyword: '{keyword}'). Agendando tarefa.")
                    dados_tarefa = {
                        "contratacaoId": contratacao_id,
                        "numeroControlePNCP": pncp_number,
                        "clienteId": cliente_id,
                        "pesquisaId": pesquisa_id,
                        "status": "pendente",
                        "data_criacao": datetime.datetime.now(datetime.timezone.utc)
                    }
                    nova_tarefa_ref = tarefas_ref.document()
                    batch.set(nova_tarefa_ref, dados_tarefa)
                    novas_tarefas_criadas += 1
                    commit_counter += 1
                    tarefas_existentes.add((contratacao_id, cliente_id))
                    break
            if commit_counter >= 499:
                logger.info(f"Enviando lote de {commit_counter} novas tarefas para o Firestore...")
                batch.commit()
                batch = db.batch()
                commit_counter = 0
    if commit_counter > 0:
        logger.info(f"Enviando lote final de {commit_counter} novas tarefas para o Firestore...")
        batch.commit()
    logger.info("\n--- Geração de Tarefas Finalizada ---")
    logger.info(f"Total de NOVAS tarefas criadas: {novas_tarefas_criadas}")

# --- Verificar Fila ---
def verificar_fila(db):
    tarefas_ref = db.collection(TAREFAS_COLLECTION_NAME)
    logger.info("Executando query para buscar tarefas com status == 'pendente'...")
    query = tarefas_ref.where('status', '==', 'pendente')
    try:
        tarefas_pendentes = list(query.stream())
        count = len(tarefas_pendentes)
        logger.info("--- RESULTADO DA VERIFICAÇÃO ---")
        logger.info(f"A query encontrou {count} tarefa(s) com o status 'pendente'.")
        if count > 0:
            logger.info("O worker deveria estar funcionando. O problema pode ser no script 'worker_raspagem.py'.")
        else:
            logger.info("O worker está se comportando corretamente, pois a fila de tarefas 'pendente' está de fato vazia.")
            logger.info("Verifique no console do Firestore se as tarefas realmente existem com o status 'pendente'.")
    except Exception as e:
        logger.error("Ocorreu um erro ao executar a query. Isso pode indicar um problema de índice no Firestore.")
        logger.error(f"Detalhes do erro: {e}")
        logger.error("Verifique o console do Google Cloud por avisos de 'Índice Necessário' para a coleção 'tarefasRaspagem'.")

# --- Main ---
def main():
    parser = argparse.ArgumentParser(description="Administração Unificada LicitAI")
    subparsers = parser.add_subparsers(dest='command', required=True)
    subparsers.add_parser('limpar-fila', help='Deleta todas as tarefas da fila.')
    subparsers.add_parser('garantir-pesquisa', help='Cria a pesquisa inicial se não existir.')
    subparsers.add_parser('diagnostico', help='Executa diagnóstico do sistema.')
    subparsers.add_parser('gerar-tarefas', help='Gera tarefas de raspagem a partir das contratações e pesquisas.')
    subparsers.add_parser('verificar-fila', help='Verifica o número de tarefas pendentes.')
    args = parser.parse_args()
    db = get_firestore_client()
    if args.command == 'limpar-fila':
        limpar_fila(db)
    elif args.command == 'garantir-pesquisa':
        garantir_pesquisa(db)
    elif args.command == 'diagnostico':
        diagnostico_sistema(db)
    elif args.command == 'gerar-tarefas':
        gerar_tarefas(db)
    elif args.command == 'verificar-fila':
        verificar_fila(db)

if __name__ == "__main__":
    main()
