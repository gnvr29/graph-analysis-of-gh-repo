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
        print(f"Buscando dados da API: {url}")
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


    def _collect_paginated_issues(self, issues_path, description="issues"):
        """
        Método genérico para coletar issues (abertas ou fechadas) 
        de um path específico, incluindo detalhes e comentários.
        """
        all_issues = []
        issues_per_page = 25 

        base_url_path = f"{self.base_url}{issues_path}"
        separator = '&' if '?' in issues_path else '?'
        initial_url = f"{base_url_path}{separator}page=1"

        data_initial = self._fetch_page_data(initial_url, description=f"{description} da página 1")
        
        if data_initial:
            result_initial = interpretar_issues(data_initial)
            all_issues.extend(result_initial.get('issues', []))
            total_issues_count = result_initial.get('count', 0)
            print(f"Número total estimado de {description}: {total_issues_count}")
        else:
            print(f"Não foi possível coletar {description} da primeira página.")
            return []

        if total_issues_count > len(all_issues):
            pages_to_fetch = (total_issues_count // issues_per_page) + (1 if total_issues_count % issues_per_page > 0 else 0)
            if pages_to_fetch > 400: 
                print(f"Atenção: Limite de paginação atingido. Coletando 400 páginas de {pages_to_fetch} estimadas.")
                pages_to_fetch = 400

            print(f"Coletando {description} restantes das páginas 2 até {pages_to_fetch}...")
            for page in range(2, pages_to_fetch + 1):
                page_url = f"{base_url_path}{separator}page={page}"
                page_data = self._fetch_page_data(page_url, description=f"{description} da página {page}")
                if page_data:
                    parsed_page = interpretar_issues(page_data)
                    if not parsed_page.get('issues'):
                        print(f"Página {page} não retornou issues.")
                    all_issues.extend(parsed_page.get('issues', []))
                else:
                    print(f"Atenção: Falha ao coletar {description} da página {page}.")

        print(f"Número total de {description} coletadas (listagem): {len(all_issues)}")

        issues_with_details = []
        for issue_dict in all_issues:
            issue_number = issue_dict.get('number')
            if issue_number:
                detail_url = f"{self.base_url}{GITHUB_ISSUES_PATH}/{issue_number}"
                detalhes_coletados = self._fetch_page_data(detail_url, description=f"corpo e comentários da issue #{issue_number}")
                
                if detalhes_coletados:
                    parsed_details = interpretar_comentarios(detalhes_coletados)
                    issue_dict['body'] = parsed_details.get('issue_body')
                    issue_dict['comments'] = parsed_details.get('comments')
                else:
                    print(f"Atenção: Não foi possível coletar detalhes para a issue #{issue_number}.")
                issues_with_details.append(issue_dict)
            else:
                print(f"Skipping issue without valid number: {issue_dict.get('title')}")
        
        print(f"Coleta de {description} finalizada. Total com detalhes: {len(issues_with_details)}")
        return issues_with_details

    def collect_issues(self):
        """Coleta todas as issues ABERTAS."""
        print("--- Iniciando coleta de ISSUES ABERTAS ---")
        return self._collect_paginated_issues(GITHUB_ISSUES_PATH, description="issues abertas")

    def collect_closed_issues(self):
        """Coleta todas as issues FECHADAS."""
        print("--- Iniciando coleta de ISSUES FECHADAS ---")
        return self._collect_paginated_issues(GITHUB_CLOSED_ISSUES_PATH, description="issues fechadas")
    

    # --- MÉTODOS DE PULL REQUESTS (API) ---

    def _collect_paginated_api_data(self, page_url):
        """
        Um helper genérico para buscar TODOS os itens de um endpoint paginado da API.
        Usado para buscar comentários, revisões, etc.
        """
        all_items = []
        page_count = 1
        
        while page_url:
            print(f"Buscando sub-dados (pág {page_count})... URL: {page_url.replace('https://api.github.com', '...')}")
            json_data, pagination_links = self._fetch_api_page(page_url)
            
            if not json_data:
                break

            all_items.extend(json_data)
            
            if pagination_links and 'next' in pagination_links:
                page_url = pagination_links['next']['url']
                page_count += 1
            else:
                page_url = None 
                
        return all_items


    def collect_all_pull_requests_api(self):
        """
        Coleta TODOS os pull requests (abertos e fechados) do repositório
        usando a API oficial, incluindo seus comentários e revisões.
        """
        all_prs_data = []
        
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
                pr_issue_comments = self._collect_paginated_api_data(comments_url)
                
                review_comments_url = f"{self.base_api_url}/pulls/{pr_number}/comments?per_page=100"
                pr_review_comments = self._collect_paginated_api_data(review_comments_url)
                
                reviews_url = f"{self.base_api_url}/pulls/{pr_number}/reviews?per_page=100"
                pr_reviews = self._collect_paginated_api_data(reviews_url)
                
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
                all_prs_data.append(pr_dict)
            
            if pagination_links and 'next' in pagination_links:
                page_url = pagination_links['next']['url']
                page_count += 1
            else:
                page_url = None

        print(f"\n--- Coleta de PRs pela API finalizada ---")
        print(f"Total de Pull Requests (abertos e fechados) processados: {len(all_prs_data)}")
        return all_prs_data
