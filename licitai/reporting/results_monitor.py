# monitor_resultados.py

import os
import sys
import threading
import time
from google.cloud import firestore

# --- Configuração ---
# Garante que o script use as credenciais corretas
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = os.path.join(os.getcwd(), "firebase-admin.json")
TAREFAS_COLLECTION_NAME = 'tarefasRaspagem'

# Evento para sinalizar quando o programa deve terminar
shutdown_event = threading.Event()

def get_firestore_client():
    """Inicializa e retorna o cliente do Firestore."""
    try:
        db = firestore.Client(project="pncp-insights-jewpf")
        print("Conexão com o Firestore estabelecida.")
        return db
    except Exception as e:
        print(f"Falha ao inicializar o cliente do Firestore: {e}", file=sys.stderr)
        raise

def on_snapshot(doc_snapshot, changes, read_time):
    """
    Função de callback que é executada toda vez que há uma mudança
    nos documentos que estão sendo observados.
    """
    print("\n--- DETECTADA ATUALIZAÇÃO ---")
    for change in changes:
        if change.type.name in ('ADDED', 'MODIFIED'):
            doc_data = change.document.to_dict()
            status = doc_data.get('status', 'N/A').upper()
            pncp = doc_data.get('numeroControlePNCP', 'N/A')
            resultado = doc_data.get('resultado', {})
            score = resultado.get('scoreRelevancia', 'N/A')
            assunto = resultado.get('assunto_principal', 'N/A')

            print(f"PNCP: {pncp}")
            print(f"Status: {status}")
            print(f"Score: {score}")
            print(f"Assunto: {assunto}")
            
            contatos = resultado.get('contatos')
            if contatos:
                print("Contatos Encontrados:")
                for i, contato in enumerate(contatos, 1):
                    nome = contato.get('nome_responsavel', 'N/A')
                    email = contato.get('email_contato', 'N/A')
                    print(f"  - {i}: {nome} ({email})")
            print("---------------------------------")

def main():
    """Inicia o monitoramento em tempo real."""
    db = get_firestore_client()

    # Query para observar apenas tarefas que já foram processadas (não estão mais pendentes)
    query = db.collection(TAREFAS_COLLECTION_NAME).where('status', 'not-in', ['pendente', 'analisando'])

    # Inicia o "listener" que ficará observando a query
    query_watch = query.on_snapshot(on_snapshot)

    print(f"\n✅ Monitoramento em tempo real iniciado para a coleção '{TAREFAS_COLLECTION_NAME}'.")
    print("Aguardando novos resultados do worker...")
    print("(Pressione CTRL+C para sair)")

    try:
        # Mantém o script principal rodando para que o listener continue ativo em segundo plano
        while not shutdown_event.is_set():
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nEncerrando o monitoramento...")
    finally:
        # Encerra o listener
        query_watch.unsubscribe()

if __name__ == "__main__":
    main()