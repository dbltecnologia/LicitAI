# licitai/processing/regex_extractor.py (Versão Corrigida e Completa)

import logging
import google.generativeai as genai
import json
import re

logger = logging.getLogger(__name__)

# PROMPT ATUALIZADO PARA INCLUIR A ANÁLISE DE GATILHO DE VENDA
PROMPT_ANALISE_LICITACAO = """
Você é um assistente de análise de licitações para uma empresa de tecnologia que vende software, como "Office Professional 2021".

Sua tarefa é analisar o "objeto da compra" de uma licitação e extrair duas informações cruciais:
1.  **Palavras-chave Relevantes**: Identifique termos técnicos, nomes de software, hardware ou serviços de TI.
2.  **Gatilho de Venda**: Com base no objeto, classifique a principal intenção da compra. Este é o ponto mais importante.

**Objeto da Compra para Análise**:
"{objeto_compra}"

**Instruções Detalhadas**:
1.  **Palavras-chave**: Extraia até 10 palavras-chave que descrevam tecnicamente a licitação. Foque em substantivos e termos específicos.
2.  **Gatilho de Venda**: Analise o texto e escolha **UMA** das seguintes categorias que melhor representa a oportunidade de venda:
    * `Compra de Hardware`: A licitação é para comprar computadores, servidores, notebooks, etc. (Isso é um gatilho, pois hardware novo precisa de software novo).
    * `Renovação/Expiração de Licença de Software`: O texto menciona termos como "renovação", "subscrição", "expiração", "suporte técnico" ou "atualização" de um software existente.
    * `Nova Aquisição de Software`: A licitação é para comprar licenças de software pela primeira vez, sem menção à renovação.
    * `Serviços de TI`: A licitação é para contratar serviços como consultoria, desenvolvimento, suporte técnico, outsourcing, etc.
    * `Outros`: A licitação não se encaixa em nenhuma das categorias acima (ex: compra de material de escritório, obras, etc.).
    * `Não se aplica`: O objeto da compra é muito vago, genérico ou não relacionado a TI.

**Formato da Resposta**:
Responda **APENAS** com um objeto JSON válido, sem nenhum texto adicional antes ou depois. Use o seguinte formato:
```json
{{
  "palavrasChave": ["palavra1", "palavra2", "palavra3"],
  "gatilhoVenda": "Categoria Escolhida"
}}
```
"""

def clean_json_response(text: str) -> str:
    """Tenta limpar a resposta da IA para extrair um JSON válido."""
    match = re.search(r'\{.*\}', text, re.DOTALL)
    if match:
        return match.group(0)
    return text  # Retorna o texto original se nenhum JSON for encontrado

async def analisar_objeto_com_ia(objeto_compra: str, api_key: str) -> dict:
    """
    Usa a API do Google Gemini para analisar o objeto da compra.
    Retorna um dicionário com as palavras-chave e o gatilho de venda.
    """
    if not objeto_compra:
        logger.warning("Objeto da compra está vazio. Retornando análise vazia.")
        return {"palavrasChave": [], "gatilhoVenda": "Não informado"}

    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-pro-latest')
        
        prompt = PROMPT_ANALISE_LICITACAO.format(objeto_compra=objeto_compra)
        
        response = await model.generate_content_async(prompt)
        
        cleaned_text = clean_json_response(response.text)
        
        analysis_result = json.loads(cleaned_text)
        
        if "palavrasChave" not in analysis_result:
            analysis_result["palavrasChave"] = []
        if "gatilhoVenda" not in analysis_result:
            analysis_result["gatilhoVenda"] = "Não informado pela IA"
            
        return analysis_result

    except Exception as e:
        logger.error(f"Erro ao chamar a API da IA: {e}", exc_info=False) # exc_info=False para não poluir o log
        # Relança a exceção para que o worker possa tratá-la adequadamente
        raise e
