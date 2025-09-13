# main.py
"""
Ponto de entrada único para o LicitAI.
Permite controlar coleta, geração de tarefas, processamento, relatórios e administração via CLI.
"""
import argparse
import sys
import subprocess
import textwrap

# Mapeamento de comandos amigáveis para os scripts e seus módulos
COMMANDS = {
    "coletar-dados": {
        "module": "licitai.data_collection.collector",
        "description": textwrap.dedent("""
            Busca novas licitações no PNCP e as salva no banco de dados.
            Uso:
              --meses-atras <N>   : Busca licitações dos últimos N meses.
              --data-inicial <D>  : Define uma data de início (AAAA-MM-DD).
              --data-final <D>    : Define uma data de fim (AAAA-MM-DD).
        """)
    },
    "gerar-tarefas": {
        "module": "licitai.management.admin",
        "args": ["gerar-tarefas"],
        "description": "Cria tarefas de análise para a IA com base nas licitações coletadas e pesquisas ativas."
    },
    "diagnostico": {
        "module": "licitai.management.admin",
        "args": ["diagnostico"],
        "description": "Executa um diagnóstico do sistema, verificando a conexão com o Firestore e o status das coleções."
    },
    "limpar-fila": {
        "module": "licitai.management.admin",
        "args": ["limpar-fila"],
        "description": "Limpa a fila de tarefas, resetando o status das tarefas 'em_processamento' para 'pendente'."
    },
    "garantir-pesquisa": {
        "module": "licitai.management.admin",
        "args": ["garantir-pesquisa"],
        "description": "Garante que uma pesquisa inicial de software exista no banco de dados para a geração de tarefas."
    },
    "processar-tarefas": {
        "module": "licitai.processing.ai_worker",
        "description": "Inicia o worker de IA para processar as tarefas pendentes na fila."
    },
    "consolidar-leads": {
        "module": "licitai.reporting.lead_consolidator",
        "description": "Consolida os resultados das tarefas processadas em um relatório de leads."
    },
    "monitorar-resultados": {
        "module": "licitai.reporting.results_monitor",
        "description": "Exibe um painel com o status atual das tarefas de raspagem."
    },
    "enriquecer-leads": {
        "module": "licitai.processing.lead_enricher",
        "description": "Inicia o worker para buscar contatos (e-mails, telefones) para os leads qualificados."
    },
}

def run_command(command_key, remaining_args):
    """Executa o comando selecionado como um módulo Python."""
    command_info = COMMANDS[command_key]
    module_path = command_info["module"]
    
    # Constrói o comando base
    # Usar 'python -m' é crucial para que os imports relativos do projeto funcionem corretamente
    cmd_list = [sys.executable, "-m", module_path]
    
    # Adiciona argumentos fixos, se houver
    if "args" in command_info:
        cmd_list.extend(command_info["args"])
        
    # Adiciona os argumentos passados pelo usuário
    cmd_list.extend(remaining_args)
    
    command_str = " ".join(cmd_list)
    print(f"Executando: {command_str}")
    
    try:
        # Usar subprocess.run com a lista de argumentos é mais seguro que shell=True
        result = subprocess.run(cmd_list, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Erro ao executar o comando '{command_key}'. Código de saída: {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)
    except FileNotFoundError:
        print(f"Erro: O interpretador Python '{sys.executable}' não foi encontrado.", file=sys.stderr)
        sys.exit(1)

def main():
    # Cria um parser que formata a ajuda de forma mais legível
    parser = argparse.ArgumentParser(
        description="LicitAI - CLI unificada para automação de licitações.",
        formatter_class=argparse.RawTextHelpFormatter
    )
    
    # Gera a lista de comandos e suas descrições para a mensagem de ajuda
    command_help = "\nComandos disponíveis:\n"
    for key, value in COMMANDS.items():
        command_help += f"  {key:<20} {value['description'].strip()}\n"

    parser.add_argument(
        'command', 
        choices=COMMANDS.keys(), 
        help=command_help,
        metavar="comando"
    )
    
    # 'parse_known_args' divide os argumentos entre os conhecidos pelo parser e o restante
    args, remaining_args = parser.parse_known_args()
    
    run_command(args.command, remaining_args)

if __name__ == "__main__":
    main()