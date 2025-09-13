from .pncp_client import ComprasNetAPIClient
import datetime

class Licitacoes:
    """
    Módulo para interagir com os endpoints de contratações (licitações) da API do PNCP.
    Lida com a busca de avisos de contratação e a paginação dos resultados.
    """

    _CONTRATACOES_PUBLICACAO_ENDPOINT = "/v1/contratacoes/publicacao"
    _CONTRATACOES_PROPOSTA_ENDPOINT = "/v1/contratacoes/proposta" # Para licitações com propostas abertas
    _CONTRATACOES_POR_ID_ENDPOINT = "/v1/orgaos/{cnpj}/compras/{ano}/{sequencial}" # Endpoint para buscar por ID

    def __init__(self, client: ComprasNetAPIClient):
        """
        Inicializa o módulo de Licitações.

        Args:
            client (ComprasNetAPIClient): Uma instância do cliente da API.
        """
        self._client = client
        print("Módulo Licitacoes inicializado.")

    def _get_all_pages(self, endpoint: str, initial_params: dict) -> list:
        """
        Método auxiliar para lidar com a paginação e coletar todos os resultados.

        Args:
            endpoint (str): O caminho do endpoint (e.g., "/v1/contratacoes/publicacao").
            initial_params (dict): Parâmetros iniciais da requisição.

        Returns:
            list: Uma lista de dicionários, cada um representando um item de contratação.
        """
        all_results = []
        page_number = initial_params.get("pagina", 1)
        page_size = initial_params.get("tamanhoPagina", 50) # <--- MUDANÇA AQUI: Reduzindo para 50
        
        # Remove pagina e tamanhoPagina dos params iniciais para evitar duplicação na iteração
        params_for_request = {k: v for k, v in initial_params.items() if k not in ["pagina", "tamanhoPagina"]}

        while True:
            current_params = {**params_for_request, "pagina": page_number, "tamanhoPagina": page_size}
            try:
                response_data = self._client._make_request(endpoint, params=current_params)
                
                items = response_data.get("data", [])
                total_count = response_data.get("count", None)

                if not items:
                    break

                all_results.extend(items)
                
                if total_count is not None:
                    print(f"Página {page_number} do endpoint '{endpoint}': {len(items)} itens recebidos. Total coletado: {len(all_results)} de {total_count}")
                else:
                    print(f"Página {page_number} do endpoint '{endpoint}': {len(items)} itens recebidos. Total coletado: {len(all_results)}")

                if len(items) < page_size or (total_count is not None and len(all_results) >= total_count):
                    break

                page_number += 1
            except Exception as e:
                print(f"Erro ao buscar página {page_number} do endpoint '{endpoint}': {e}")
                break

        return all_results

    def buscar_por_publicacao(self,
                              dataInicial: str,
                              dataFinal: str,
                              codigoModalidadeContratacao: int = None,
                              **kwargs) -> list:

        try:
            if not dataInicial:
                raise ValueError("dataInicial está vazio ou é nulo.")
            if not dataFinal:
                raise ValueError("dataFinal está vazio ou é nulo.")

            start_date_obj = datetime.datetime.strptime(dataInicial, "%Y-%m-%d").date()
            end_date_obj = datetime.datetime.strptime(dataFinal, "%Y-%m-%d").date()
            
            print(f"DEBUG_SDK: Data inicial parseada para objeto: {start_date_obj}")
            print(f"DEBUG_SDK: Data final parseada para objeto: {end_date_obj}")

            if start_date_obj > end_date_obj:
                raise ValueError("dataInicial não pode ser posterior a dataFinal.")
        except ValueError as e:
            print(f"ERROR_SDK_PARSE_DETAILS: Erro Original ao parsear data: {e}")
            if dataInicial:
                print(f"DEBUG_SDK_CHAR_CODES_INITIAL: Códigos ASCII/Unicode: {[ord(c) for c in dataInicial]}")
            if dataFinal:
                print(f"DEBUG_SDK_CHAR_CODES_FINAL: Códigos ASCII/Unicode: {[ord(c) for c in dataFinal]}")
            
            raise ValueError(f"SDK Validation Error: Formato de data inválido para dataInicial ou dataFinal. Use YYYY-MM-DD. Detalhe: {e}")
        
        if codigoModalidadeContratacao is None:
            raise ValueError("O parâmetro 'codigoModalidadeContratacao' é obrigatório para a busca por publicação na API do PNCP.")

        params = {
            "dataInicial": start_date_obj.strftime("%Y%m%d"),
            "dataFinal": end_date_obj.strftime("%Y%m%d"),
            "codigoModalidadeContratacao": codigoModalidadeContratacao,
            **kwargs
        }

        print(f"Buscando contratações por publicação entre {dataInicial} e {dataFinal} (Modalidade: {codigoModalidadeContratacao})...")
        contratacoes = self._get_all_pages(self._CONTRATACOES_PUBLICACAO_ENDPOINT, params)
        print(f"Busca de contratações concluída. Total geral: {len(contratacoes)}.")
        return contratacoes

    def buscar_propostas_abertas(self, 
                                 dataFinal: str, 
                                 codigoModalidadeContratacao: int = None,
                                 **kwargs) -> list:
        try:
            if not dataFinal:
                raise ValueError("dataFinal está vazio ou é nulo.")

            end_date_obj = datetime.datetime.strptime(dataFinal, "%Y-%m-%d").date()
        except ValueError as e:
            print(f"ERROR_SDK_PARSE_DETAILS: Erro Original ao parsear data (Propostas Abertas): {e}")
            if dataFinal:
                print(f"DEBUG_SDK_CHAR_CODES_FINAL: Códigos ASCII/Unicode (Propostas Abertas): {[ord(c) for c in dataFinal]}")
            raise ValueError(f"SDK Validation Error: Formato de data inválido para dataFinal. Use YYYY-MM-DD. Detalhe: {e}")
        
        if codigoModalidadeContratacao is None:
            raise ValueError("O parâmetro 'codigoModalidadeContratacao' é obrigatório para a busca de propostas abertas na API do PNCP.")

        params = {
            "dataFinal": end_date_obj.strftime("%Y%m%d"),
            "codigoModalidadeContratacao": codigoModalidadeContratacao,
            **kwargs
        }
        print(f"Buscando contratações com propostas abertas até {dataFinal} (Modalidade: {codigoModalidadeContratacao})...")
        contratacoes = self._get_all_pages(self._CONTRATACOES_PROPOSTA_ENDPOINT, params)
        print(f"Busca de propostas abertas concluída. Total geral: {len(contratacoes)}.")
        return contratacoes

    def buscar_contratacao_por_id(self, cnpj: str, ano: int, sequencial: int) -> dict:
        """
        Consulta uma contratação específica pelo CNPJ do órgão, ano e sequencial.

        Args:
            cnpj (str): CNPJ do órgão.
            ano (int): Ano da contratação.
            sequencial (int): Número sequencial da contratação.

        Returns:
            dict: Um dicionário representando a contratação, ou None se não encontrada.
        Raises:
            ValueError: Se os parâmetros não forem válidos.
        """
        if not (cnpj and ano and sequencial):
            raise ValueError("CNPJ, ano e sequencial são obrigatórios.")

        endpoint = self._CONTRATACOES_POR_ID_ENDPOINT.format(cnpj=cnpj, ano=ano, sequencial=sequencial)
        
        print(f"Buscando contratação {cnpj}/{ano}/{sequencial}...")
        try:
            contratacao_data = self._client._make_request(endpoint)
            if contratacao_data:
                print(f"Contratação {cnpj}/{ano}/{sequencial} encontrada.")
                return contratacao_data
            else:
                print(f"Contratação {cnpj}/{ano}/{sequencial} não encontrada ou resposta inesperada.")
                return None
        except ValueError as e:
            if "404" in str(e):
                print(f"Contratação {cnpj}/{ano}/{sequencial} não encontrada (Erro 404).")
                return None
            raise e
        except Exception as e:
            print(f"Erro ao buscar contratação {cnpj}/{ano}/{sequencial}: {e}")
            return None