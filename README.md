# LicitAI Pro: Automação Inteligente para Prospecção B2G

![Versão Python](https://img.shields.io/badge/python-3.12-blue.svg) ![Firebase](https://img.shields.io/badge/Firebase-Firestore-orange) ![Google AI](https://img.shields.io/badge/Google%20AI-Gemini-blueviolet) ![Docker](https://img.shields.io/badge/Docker-Ready-blue)

[Read this in English](#licitai-pro-intelligent-automation-for-b2g-prospecting)

## 🎯 O Problema

Prospectar no setor público (B2G) no Brasil é um desafio complexo. O volume de dados em portais como o Portal Nacional de Contratações Públicas (PNCP) é imenso, e identificar oportunidades de negócio relevantes para o setor de TI é como procurar uma agulha num palheiro. Este processo manual é lento, ineficiente e propenso a erros, fazendo com que empresas percam oportunidades valiosas.

## 💡 A Solução: LicitAI

LicitAI é um pipeline de automação inteligente que transforma este desafio numa vantagem competitiva. A plataforma foi construída para varrer, analisar e qualificar licitações públicas de forma autónoma, entregando um relatório final de leads de alto potencial, prontos para a equipa de vendas.

Este projeto demonstra uma arquitetura de software robusta, com automação de processos (RPA), consumo de APIs, integração com Inteligência Artificial (Google Gemini) e, crucialmente, práticas de desenvolvimento seguro (DevSecOps).

---

## 🏛️ Arquitetura e Fluxo de Trabalho

O sistema opera através de um pipeline modular e orquestrado, onde cada etapa refina os dados até se tornarem inteligência acionável:

1.  **Coleta (`collector.py`):** Um worker robusto conecta-se à API do PNCP para coletar e armazenar novas licitações de TI no Firestore.
2.  **Geração de Tarefas (`admin.py`):** Um módulo de gestão cruza os dados coletados com palavras-chave estratégicas para identificar oportunidades e criar tarefas de análise.
3.  **Qualificação com IA (`ai_worker.py`):** O coração do sistema. Utiliza a API do Google Gemini para analisar o objeto de cada licitação, extrair termos técnicos e classificar o "gatilho de venda" (ex: nova aquisição, renovação de contrato).
4.  **Enriquecimento (`lead_enricher.py`):** Um robô de web scraping que realiza buscas na web para encontrar contatos (e-mails, telefones) e os links de "fontes de ouro" (Portal da Transparência, Diário Oficial) associados ao órgão licitante.
5.  **Consolidação (`lead_consolidator.py`):** Gera um relatório final em formato Excel, apresentando um dossiê completo de cada lead qualificado para a equipa de vendas.

---

## 🚀 Como Executar o Projeto

### Pré-requisitos
* Python 3.10+
* Conta de Serviço do Google Cloud com acesso ao Firestore.
* Chave de API do Google Gemini.
* `git` e `gcloud` CLI instalados no seu ambiente.

### 1. Instalação

```bash
# Clone o repositório
git clone <url-do-seu-novo-repositorio>
cd LicitAI

# Crie e ative o ambiente virtual
python3 -m venv venv_licitai
source venv_licitai/bin/activate

# Instale as dependências
pip install -r requirements.txt
````

### 2\. Configuração de Segurança (Crucial)

Este projeto segue as melhores práticas de segurança e **não utiliza ficheiros de credenciais `.json` no código**. A autenticação é gerida pelo ambiente.

```bash
# 1. Autentique-se com a Google Cloud CLI.
#    Isto irá criar as Application Default Credentials (ADC) na sua máquina.
gcloud auth application-default login

# 2. Exporte a sua chave da API do Gemini como uma variável de ambiente.
#    Adicione esta linha ao seu ficheiro ~/.bashrc ou ~/.zshrc para torná-la permanente.
export GEMINI_API_KEY="SUA_CHAVE_API_AQUI"
```

### 3\. Executando o Pipeline

O `main.py` é o ponto de entrada centralizado para todas as operações.

```bash
# Para executar o pipeline completo em sequência:
python main.py limpar-fila && \
python main.py gerar-tarefas && \
python main.py processar-tarefas && \
python main.py enriquecer-leads && \
python main.py consolidar-leads

# Para executar comandos individuais:
python main.py <comando>
```

**Comandos Disponíveis:** `coletar-dados`, `gerar-tarefas`, `processar-tarefas`, `enriquecer-leads`, `consolidar-leads`, `diagnostico`, `limpar-fila`.

-----

## 🤝 Contribua e Faça Parte\!

Este projeto é um ponto de partida poderoso, mas o potencial de crescimento é enorme. Sinta-se à vontade para fazer um **fork** do repositório, explorar o código e submeter as suas melhorias\!

**Algumas ideias para futuras contribuições:**

  * **Novos Scrapers:** Desenvolver scrapers específicos para Portais da Transparência ou Diários Oficiais de grandes capitais.
  * **Integração com CRM:** Criar um worker que envia os leads consolidados diretamente para um CRM como Pipedrive ou HubSpot via API.
  * **Dashboard de Visualização:** Construir uma interface web simples com Streamlit ou Flask para exibir os resultados do diagnóstico e o status da fila.
  * **Melhorar a IA:** Refinar os prompts do Gemini para extrair ainda mais informações, como valores estimados ou nomes de responsáveis.

Abra uma *Issue* para discutir novas ideias ou submeta um *Pull Request* com as suas implementações. Toda a contribuição é bem-vinda\!

-----

## 👤 Contato

**Diego Bezerra de Lima**

  * **LinkedIn:** [linkedin.com/in/dbltecnologia](https://www.linkedin.com/in/dbltecnologia)
  * **WhatsApp:** [+55 (61) 98301-3768](https://www.google.com/search?q=https://wa.me/5561983013768)
  * **Email:** [admin@dbltecnologia.com.br](mailto:admin@dbltecnologia.com.br)

-----

-----

# LicitAI Pro: Intelligent Automation for B2G Prospecting

   

[Leia em Português](https://www.google.com/search?q=%23licitai-pro-automa%C3%A7%C3%A3o-inteligente-para-prospec%C3%A7%C3%A3o-b2g)

## 🎯 The Problem

Prospecting in Brazil's public sector (B2G) is a complex challenge. The volume of data on procurement portals like the PNCP (National Public Procurement Portal) is immense, and identifying relevant IT business opportunities is like finding a needle in a haystack. This manual process is slow, inefficient, and error-prone, causing companies to miss valuable opportunities.

## 💡 The Solution: LicitAI

LicitAI is an intelligent automation pipeline that transforms this challenge into a competitive advantage. The platform is built to autonomously scan, analyze, and qualify public tenders, delivering a final report of high-potential leads ready for the sales team.

This project showcases a robust software architecture, featuring process automation (RPA), API consumption, Artificial Intelligence integration (Google Gemini), and, crucially, secure development practices (DevSecOps).

-----

## 🏛️ Architecture and Workflow

The system operates through a modular and orchestrated pipeline, where each stage refines the data until it becomes actionable intelligence:

1.  **Collection (`collector.py`):** A robust worker connects to the PNCP API to collect and store new IT tenders in Firestore.
2.  **Task Generation (`admin.py`):** A management module cross-references the collected data with strategic keywords to identify business opportunities and create analysis tasks.
3.  **AI Qualification (`ai_worker.py`):** The heart of the system. It uses the Google Gemini API to analyze the "object of purchase" of each tender, extract technical terms, and classify the "sales trigger" (e.g., new acquisition, contract renewal).
4.  **Enrichment (`lead_enricher.py`):** A web scraping bot that performs searches to find contact information (emails, phone numbers) and links to "golden sources" (Transparency Portals, Official Gazettes) associated with the bidding entity.
5.  **Consolidation (`lead_consolidator.py`):** Generates a final Excel report, presenting a complete dossier for each qualified lead for the sales team.

-----

## 🚀 How to Run the Project

### Prerequisites

  * Python 3.10+
  * Google Cloud Service Account with Firestore access.
  * Google Gemini API Key.
  * `git` and `gcloud` CLI installed in your environment.

### 1\. Installation

```bash
# Clone the repository
git clone <your-new-repository-url>
cd LicitAI

# Create and activate the virtual environment
python3 -m venv venv_licitai
source venv_licitai/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2\. Security Setup (Crucial)

This project follows security best practices and **does not use `.json` credential files in the code**. Authentication is managed by the environment.

```bash
# 1. Authenticate with the Google Cloud CLI.
#    This will create the Application Default Credentials (ADC) on your machine.
gcloud auth application-default login

# 2. Export your Gemini API key as an environment variable.
#    Add this line to your ~/.bashrc or ~/.zshrc file to make it permanent.
export GEMINI_API_KEY="YOUR_API_KEY_HERE"
```

### 3\. Running the Pipeline

The `main.py` script is the centralized entry point for all operations.

```bash
# To run the full pipeline in sequence:
python main.py limpar-fila && \
python main.py gerar-tarefas && \
python main.py processar-tarefas && \
python main.py enriquecer-leads && \
python main.py consolidar-leads

# To run individual commands:
python main.py <command>
```

**Available Commands:** `coletar-dados`, `gerar-tarefas`, `processar-tarefas`, `enriquecer-leads`, `consolidar-leads`, `diagnostico`, `limpar-fila`.

-----

## 🤝 Contribute and Get Involved\!

This project is a powerful starting point, but the potential for growth is enormous. Feel free to **fork** the repository, explore the code, and submit your improvements\!

**A few ideas for future contributions:**

  * **New Scrapers:** Develop specific scrapers for the Transparency Portals or Official Gazettes of major capital cities.
  * **CRM Integration:** Create a worker that sends consolidated leads directly to a CRM like Pipedrive or HubSpot via their API.
  * **Visualization Dashboard:** Build a simple web interface with Streamlit or Flask to display diagnostic results and the task queue status.
  * **Improve the AI:** Refine the Gemini prompts to extract even more information, such as estimated values or the names of responsible parties.

Open an *Issue* to discuss new ideas or submit a *Pull Request* with your implementations. All contributions are welcome\!

-----

## 👤 Contact

**Diego Queiroz dos Santos**

  * **LinkedIn:** [linkedin.com/in/dbltecnologia](https://www.linkedin.com/in/dbltecnologia)
  * **WhatsApp:** [+55 (61) 98301-3768](https://www.google.com/search?q=https://wa.me/5561983013768)
  * **Email:** [admin@dbltecnologia.com.br](mailto:admin@dbltecnologia.com.br)

