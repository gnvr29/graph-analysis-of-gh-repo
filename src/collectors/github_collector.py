import requests
import time
from src.utils.github_parser import (
    html_to_json, 
    interpretar_issues, 
    interpretar_comentarios
)
from config.settings import (
    GITHUB_BASE_URL, 
    GITHUB_ISSUES_PATH, 
    GITHUB_CLOSED_ISSUES_PATH,
    REQUEST_DELAY_SECONDS,
    REPO_OWNER,
    REPO_NAME,
    GITHUB_API_TOKEN
)

class GithubCollector:
    def __init__(self, base_url=GITHUB_BASE_URL, delay_seconds=REQUEST_DELAY_SECONDS):
        
        # --- Configuração de SCRAPING (para Issues) ---
        self.base_url = base_url 
        self.delay_seconds = delay_seconds
        self.session = requests.Session() # Sessão para scraping

        # --- Configuração da API (para Pull Requests) ---
        self.repo_owner = REPO_OWNER
        self.repo_name = REPO_NAME
        self.api_token = GITHUB_API_TOKEN
        self.base_api_url = f"https://api.github.com/repos/{self.repo_owner}/{self.repo_name}"
        
        self.session_api = requests.Session()
        self.session_api.headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28"
        }
        if self.api_token:
            print("Usando Token da API para autenticação de PRs.")
            self.session_api.headers["Authorization"] = f"token {self.api_token}"
        else:
            print("Aviso: Coletando PRs sem Token. Sujeito a limites baixos (60/hora).")


    def _fetch_page_data(self, url, description="página", json_expected=True):
        """Método auxiliar para fazer requisições HTTP (SCRAPING) e parsear o JSON."""
        print(f"Coletando {description} da URL: {url}")
        try:
            response = self.session.get(url) 
            response.raise_for_status() 
            time.sleep(self.delay_seconds)
            if json_expected:
                return html_to_json(response)
            return response.text
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição para {url}: {e}")
            return None
        except Exception as e:
            print(f"Erro inesperado ao buscar {description} de {url}: {e}")
            return None

    
    def _fetch_api_page(self, url):
        """
        Método auxiliar para fazer uma única requisição à API (PRs) e
        retornar o JSON e os links de paginação.
        """
        # Reduz o ruído no log, mostrando uma URL mais curta
        print(f"Buscando dados da API: {url.replace('https://api.github.com', '...')}")
        try:
            response = self.session_api.get(url) 
            response.raise_for_status() 
            
            remaining = int(response.headers.get('X-RateLimit-Remaining', 5000))
            if remaining < 50: 
                print(f"Aviso: Limite de API baixo ({remaining}). Aguardando 1 minuto...")
                time.sleep(60) 
            
            time.sleep(self.delay_seconds) 
            
            return response.json(), response.links
            
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição da API para {url}: {e}")
            if '401' in str(e): print("ERRO: Token inválido ou expirado.")
            if '403' in str(e): print("ERRO: Limite de requisições da API atingido.")
            return None, None
        except Exception as e:
            print(f"Erro inesperado ao buscar dados da API: {e}")
            return None, None

    # --- MÉTODOS DE ISSUES (SCRAPING) ---

    def _collect_paginated_issues(self, issues_path, description="issues", state="open", start_page=1):
        """
        **VERSÃO GERADOR (HÍBRIDA)**
        Tenta coletar via scraping e muda para API em caso de falha.
        'state' (open/closed) é necessário para o fallback da API.
        """
        issues_per_page = 25 

        base_url_path = f"{self.base_url}{issues_path}"
        separator = '&' if '?' in issues_path else '?'
        initial_url = f"{base_url_path}{separator}page=1"

        # 1. Buscar a primeira página para descobrir o total
        data_initial = self._fetch_page_data(initial_url, description=f"{description} da página 1")
        
        if not data_initial:
            print(f"Não foi possível coletar {description} da primeira página. Encerrando.")
            return # 'return' vazio em um gerador encerra a iteração

        result_initial = interpretar_issues(data_initial)
        total_issues_count = result_initial.get('count', 0)
        
        if total_issues_count == 0:
            print("Nenhuma issue encontrada.")
            return

        print(f"Número total estimado de {description}: {total_issues_count}")
        
        # Calcular total de páginas
        pages_to_fetch = (total_issues_count // issues_per_page) + (1 if total_issues_count % issues_per_page > 0 else 0)
        if pages_to_fetch > 400: 
            print(f"Atenção: Limite de paginação atingido. Coletando 400 páginas de {pages_to_fetch} estimadas.")
            pages_to_fetch = 400

        # 2. Processar a primeira página (que já buscamos)
        print("--- Processando issues da Página 1 ---")
        if start_page == 1:
            for issue_dict in result_initial.get('issues', []):
                issue_with_details = self._fetch_issue_details(issue_dict)
                if issue_with_details:
                    yield issue_with_details
        else:
            print(f"--- Pulando processamento da Página 1 (iniciando em {start_page}) ---")


        # 3. Iterar sobre as páginas restantes
        # Define a página inicial do loop, garantindo que seja no mínimo 2
        loop_start_page = max(2, start_page)

        if pages_to_fetch >= loop_start_page:
            print(f"Coletando {description} restantes das páginas {loop_start_page} até {pages_to_fetch}...")
            
            for page in range(loop_start_page, pages_to_fetch + 1):
                page_url = f"{base_url_path}{separator}page={page}"
                page_data = self._fetch_page_data(page_url, description=f"{description} da página {page}")
                
                # Se 'page_data' for None (ex: 404), é um erro real de request. Apenas pule a página.
                if not page_data:
                    print(f"Atenção: Falha ao coletar dados do scraping da página {page}. Pulando...")
                    continue
                # --- FIM DA LÓGICA DE FALLBACK ---

                parsed_page = interpretar_issues(page_data)
                page_issues = parsed_page.get('issues', [])
                
                # --- NOVA LÓGICA DE FALLBACK DA API ---
                # Se 'page_data' foi OK, mas o parser não encontrou issues (página bugada)
                if not page_issues:
                    print(f"Atenção: Scraping não encontrou issues na página {page} (pode estar bugada).")
                    print(f"--- ACIONANDO FALLBACK: Mudando para coleta via API a partir da página {page} ---")
                    
                    # Chama o novo método de API para issues, passando o estado e a página onde paramos
                    yield from self.collect_issues_api(
                        state=state, 
                        start_page=page
                    )
                    
                    # Após o fallback da API (que coleta tudo restante), paramos o loop de scraping.
                    break 
                # --- FIM DA LÓGICA DE FALLBACK ---

                # 4. Para cada issue na página, buscar detalhes e fazer yield
                for issue_dict in page_issues:
                    issue_with_details = self._fetch_issue_details(issue_dict)
                    if issue_with_details:
                        yield issue_with_details
                        
        print(f"Coleta de {description} finalizada.")

    
    def _fetch_issue_details(self, issue_dict):
        """Helper que busca detalhes e comentários de uma única issue."""
        issue_number = issue_dict.get('number')
        if not issue_number:
            print(f"Skipping issue without valid number: {issue_dict.get('title')}")
            return None

        detail_url = f"{self.base_url}{GITHUB_ISSUES_PATH}/{issue_number}"
        detalhes_coletados = self._fetch_page_data(
            detail_url, 
            description=f"corpo e comentários da issue #{issue_number}"
        )
        
        if detalhes_coletados:
            parsed_details = interpretar_comentarios(detalhes_coletados)
            issue_dict['body'] = parsed_details.get('issue_body')
            issue_dict['comments'] = parsed_details.get('comments')
        else:
            print(f"Atenção: Não foi possível coletar detalhes para a issue #{issue_number}.")
            # Retornamos a issue mesmo sem detalhes para não perder o registro
            issue_dict['body'] = ""
            issue_dict['comments'] = []
            
        return issue_dict


    def collect_issues(self, start_page=1):
        """Coleta todas as issues ABERTAS (como um gerador)."""
        print(f"--- Iniciando coleta de ISSUES ABERTAS (Streaming) a partir da página {start_page} ---")
        # 'yield from' passa cada item do gerador interno para o chamador
        yield from self._collect_paginated_issues(
            GITHUB_ISSUES_PATH, 
            description="issues abertas",
            state="open",
            start_page=start_page
        )

    def collect_closed_issues(self, start_page=1):
        """Coleta todas as issues FECHADAS (como um gerador)."""
        print(f"--- Iniciando coleta de ISSUES FECHADAS (Streaming) a partir da página {start_page} ---")
        yield from self._collect_paginated_issues(
            GITHUB_CLOSED_ISSUES_PATH, 
            description="issues fechadas",
            state="closed",
            start_page=start_page
        )
    

    # --- MÉTODOS DE PULL REQUESTS (API) ---

    def _collect_paginated_api_data(self, page_url):
        """
        Um helper genérico para buscar itens de um endpoint paginado da API.
        Usado para buscar comentários, revisões, etc.
        """
        page_count = 1
        
        while page_url:
            print(f"Buscando sub-dados (pág {page_count})... URL: {page_url.replace('https://api.github.com', '...')}")
            json_data, pagination_links = self._fetch_api_page(page_url)
            
            if not json_data:
                break # Falha ou fim

            # Retorna cada item individualmente
            for item in json_data:
                yield item
            
            if pagination_links and 'next' in pagination_links:
                page_url = pagination_links['next']['url']
                page_count += 1
            else:
                page_url = None 
    

    def collect_issues_api(self, state='all', start_page=1):
        """
        **VERSÃO GERADOR (API)**
        Coleta issues (abertas ou fechadas) via API, paginado.
        Usado como fallback para o scraping.
        """
        print(f"--- Iniciando coleta de ISSUES via API (State: {state}, Start Page: {start_page}) ---")
        
        # Assumindo 25 issues/pág no scraping e 100 issues/pág na API
        api_start_page = ((start_page - 1) * 25) // 100 + 1
        print(f"Página de scraping {start_page} convertida para página de API {api_start_page}.")

        page_url = f"{self.base_api_url}/issues?state={state}&per_page=100&sort=created&direction=desc&page={api_start_page}"
        page_count = api_start_page

        while page_url:
            print(f"\n--- Coletando página API {page_count} de Issues ---")
            json_data, pagination_links = self._fetch_api_page(page_url)
            
            if not json_data:
                print("Falha ou não há mais dados. Encerrando coleta de Issues API.")
                break

            print(f"Recebidas {len(json_data)} issues nesta página.")

            for issue in json_data:
                if 'pull_request' in issue:
                    continue 
                
                issue_number = issue['number']
                print(f"Processando Issue API #{issue_number}: {issue['title'][:50]}...")
                
                status = issue.get('state', 'UNKNOWN').upper()

                # Buscar comentários da issue
                comments_url = f"{self.base_api_url}/issues/{issue_number}/comments?per_page=100"
                issue_comments = list(self._collect_paginated_api_data(comments_url))
                
                # Monta um dicionário compatível com o que o Neo4j espera
                issue_dict = {
                    'id': issue.get('id'),
                    'number': issue_number,
                    'title': issue.get('title'),
                    'author': issue.get('user', {}).get('login'),
                'createdAt': issue.get('created_at'),
                    'closedAt': issue.get('closed_at'),
                    'status': status,
                    'body': issue.get('body'),
                    'comments': issue_comments,
                    'labels': [label['name'] for label in issue.get('labels', [])],
                    'url': issue.get('html_url'),
                    'source': 'api' # Campo para sabermos a origem
                }
                
                yield issue_dict
            
            # Paginação da API
            if pagination_links and 'next' in pagination_links:
                page_url = pagination_links['next']['url']
                page_count += 1
            else:
                page_url = None

        print(f"\n--- Coleta de Issues (API) finalizada ---")


    def collect_all_pull_requests_api(self):
        """
        Coleta TODOS os pull requests (abertos e fechados) e faz 'yield' de CADA UM.
        """
        
        page_url = f"{self.base_api_url}/pulls?state=all&per_page=100&sort=created&direction=desc"
        page_count = 1

        print("--- Iniciando coleta de TODOS os Pull Requests via API ---")

        while page_url:
            print(f"\n--- Coletando página PRINCIPAL {page_count} de PRs ---")
            
            json_data, pagination_links = self._fetch_api_page(page_url)
            
            if not json_data:
                print("Falha ao buscar dados ou não há mais dados. Encerrando coleta de PRs.")
                break

            print(f"Recebidos {len(json_data)} PRs nesta página.")

            for pr in json_data:
                pr_number = pr['number']
                print(f"Processando PR #{pr_number}: {pr['title'][:50]}...")
                
                status = pr.get('state', 'UNKNOWN').upper()
                if pr.get('merged_at'):
                    status = 'MERGED'
                
                comments_url = f"{self.base_api_url}/issues/{pr_number}/comments?per_page=100"
                pr_issue_comments = list(self._collect_paginated_api_data(comments_url))
                
                review_comments_url = f"{self.base_api_url}/pulls/{pr_number}/comments?per_page=100"
                pr_review_comments = list(self._collect_paginated_api_data(review_comments_url))
                
                reviews_url = f"{self.base_api_url}/pulls/{pr_number}/reviews?per_page=100"
                pr_reviews = list(self._collect_paginated_api_data(reviews_url))
                
                pr_dict = {
                    'id': pr.get('id'),
                    'number': pr_number,
                    'title': pr.get('title'),
                    'author': pr.get('user', {}).get('login'),
                    'createdAt': pr.get('created_at'),
                    'closedAt': pr.get('closed_at'),
                    'mergedAt': pr.get('merged_at'),
                    'mergedBy': pr.get('merged_by', {}).get('login') if pr.get('merged_by') else None, 
                    'status': status,
                    'body': pr.get('body'),
                    'comments': pr_issue_comments,     
                    'review_comments': pr_review_comments,
                    'reviews': pr_reviews
                }
                
                yield pr_dict
            
            # Próxima página principal
            if pagination_links and 'next' in pagination_links:
                page_url = pagination_links['next']['url']
                page_count += 1
            else:
                page_url = None

        print(f"\n--- Coleta de PRs pela API finalizada ---")