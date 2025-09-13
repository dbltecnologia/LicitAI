import requests
import time

class ComprasNetAPIClient:
    """
    Cliente Python para a API de Dados Abertos do PNCP (Compras.gov.br).
    """
    _BASE_URL = "https://pncp.gov.br/pncp-consulta" # A URL base da API
    _MAX_RETRIES = 3 # Número máximo de tentativas em caso de erro
    _RETRY_DELAY = 1 # Atraso em segundos entre as tentativas

    def __init__(self):
        """
        Inicializa o cliente da API.
        """
        self._base_url = self._BASE_URL
        self._max_retries = self._MAX_RETRIES
        self._retry_delay = self._RETRY_DELAY
        self._session = requests.Session()
        self._retries_left = self._max_retries

    def _make_request(self, endpoint, method="GET", params=None, json_data=None, headers=None):
        """
        Método interno para fazer requisições à API, com lógica de retentativa.
        """
        url = f"{self._base_url}{endpoint}"
        current_headers = {
            "Accept": "application/json",
            "Content-Type": "application/json"
        }
        if headers:
            current_headers.update(headers)

        last_exception = None
        for attempt in range(1, self._max_retries + 1):
            self._retries_left = self._max_retries - attempt + 1
            try:
                print(f"Fazendo requisição para: {url} com parâmetros: {params} (Tentativa {attempt}/{self._max_retries})")
                response = self._session.request(
                    method,
                    url,
                    params=params,
                    json=json_data,
                    headers=current_headers,
                    timeout=30
                )
                
                print(f"DEBUG: Status Code: {response.status_code}")
                print(f"DEBUG: Content-Type: {response.headers.get('Content-Type')}")

                if response.status_code == 204:
                    print("DEBUG: Resposta 204 No Content. Nenhum dado disponível para os filtros.")
                    return {"data": [], "count": 0}

                response.raise_for_status()

                if 'application/json' in response.headers.get('Content-Type', ''):
                    response_json = response.json()
                    print(f"DEBUG: Resposta Bruta (primeiros 500 chars): {str(response_json)[:500]}")
                    return response_json
                else:
                    raise ValueError(f"Resposta da API não é JSON. Content-Type: {response.headers.get('Content-Type')}. Resposta: {response.text[:500]}")

            except requests.exceptions.Timeout as e:
                last_exception = e
                print(f"Timeout na requisição (Tentativa {attempt}/{self._max_retries}): {e}")
            except requests.exceptions.ConnectionError as e:
                last_exception = e
                print(f"Erro de conexão (Tentativa {attempt}/{self._max_retries}): {e}")
            except requests.exceptions.HTTPError as e:
                last_exception = e
                print(f"Erro HTTP {e.response.status_code} (Tentativa {attempt}/{self._max_retries}): {e.response.text}")
                if 400 <= e.response.status_code < 500 and e.response.status_code != 429:
                    raise ValueError(f"Erro na requisição à API: {e.response.status_code} - {e.response.text}")
            except ValueError as e:
                last_exception = e
                print(f"Erro de formato de resposta (Tentativa {attempt}/{self._max_retries}): {e}")
            except Exception as e:
                last_exception = e
                print(f"Erro inesperado na requisição (Tentativa {attempt}/{self._max_retries}): {e}")

            if attempt < self._max_retries:
                time.sleep(self._RETRY_DELAY)
        
        if last_exception:
            raise Exception(f"Falha na requisição após {self._max_retries} tentativas. Último erro: {last_exception}")
        else:
            raise Exception(f"Falha desconhecida na requisição após {self._max_retries} tentativas.")