import requests
import time
from src.utils.github_parser import html_to_json, interpretar_issues, interpretar_comentarios, interpretar_pull_requests
# 1. Adicione a nova importação aqui
from config.settings import (
    GITHUB_BASE_URL, 
    GITHUB_ISSUES_PATH, 
    GITHUB_CLOSED_ISSUES_PATH,  # <--- ADICIONADO
    GITHUB_PULLS_PATH, 
    REQUEST_DELAY_SECONDS
)

class GithubCollector:
    def __init__(self, base_url=GITHUB_BASE_URL, delay_seconds=REQUEST_DELAY_SECONDS):
        self.base_url = base_url
        self.delay_seconds = delay_seconds
        self.session = requests.Session() 

    def _fetch_page_data(self, url, description="página"):
        """Método auxiliar para fazer requisições HTTP e parsear o JSON."""
        print(f"Coletando {description} da URL: {url}")
        try:
            response = self.session.get(url)
            response.raise_for_status() 
            time.sleep(self.delay_seconds) 
            return html_to_json(response)
        except requests.exceptions.RequestException as e:
            print(f"Erro na requisição para {url}: {e}")
            return None
        except Exception as e:
            print(f"Erro inesperado ao buscar {description} de {url}: {e}")
            return None

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
                         print(f"Página {page} não retornou issues. Interrompendo coleta.")
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
        """
        Coleta todas as issues ABERTAS, incluindo seus detalhes e comentários.
        Retorna uma lista de dicionários de issues.
        """
        print("--- Iniciando coleta de ISSUES ABERTAS ---")
        return self._collect_paginated_issues(
            GITHUB_ISSUES_PATH, 
            description="issues abertas"
        )

    # 2. Método NOVO adicionado
    def collect_closed_issues(self):
        """
        Coleta todas as issues FECHADAS, incluindo seus detalhes e comentários.
        Retorna uma lista de dicionários de issues.
        """
        print("--- Iniciando coleta de ISSUES FECHADAS ---")
        return self._collect_paginated_issues(
            GITHUB_CLOSED_ISSUES_PATH, 
            description="issues fechadas"
        )

    def collect_pull_requests(self):
        """
        Coleta todas as pull requests abertas.
        Retorna uma lista de dicionários de pull requests.
        """
        # (Este método não foi alterado, mas poderia ser refatorado de forma similar
        # ao _collect_paginated_issues se você também quisesse PRs fechadas)
        print("--- Iniciando coleta de PULL REQUESTS ---")
        all_pull_requests = []
        pull_requests_per_page = 25 

        initial_url = f"{self.base_url}{GITHUB_PULLS_PATH}?page=1"
        data_initial = self._fetch_page_data(initial_url, description="pull requests da página 1")
        
        if data_initial:
            result_initial = interpretar_pull_requests(data_initial)
            all_pull_requests.extend(result_initial.get('pull_requests', []))
            total_prs_count = result_initial.get('count', 0)
            print(f"Número total estimado de pull requests abertas: {total_prs_count}")
        else:
            print("Não foi possível coletar pull requests da primeira página.")
            return []

        if total_prs_count > len(all_pull_requests):
            pages_to_fetch = (total_prs_count // pull_requests_per_page) + (1 if total_prs_count % pull_requests_per_page > 0 else 0)
            if pages_to_fetch > 400:
                print(f"Atenção: Limite de paginação atingido. Coletando 400 páginas de {pages_to_fetch} estimadas.")
                pages_to_fetch = 400

            print(f"Coletando pull requests restantes das páginas 2 até {pages_to_fetch}...")
            for page in range(2, pages_to_fetch + 1):
                page_url = f"{self.base_url}{GITHUB_PULLS_PATH}?page={page}"
                page_data = self._fetch_page_data(page_url, description=f"pull requests da página {page}")
                if page_data:
                    parsed_page = interpretar_pull_requests(page_data)
                    if not parsed_page.get('pull_requests'):
                        print(f"Página {page} não retornou PRs. Interrompendo coleta.")
                        break
                    all_pull_requests.extend(parsed_page.get('pull_requests', []))
                else:
                    print(f"Atenção: Falha ao coletar pull requests da página {page}.")

        print(f"Número total de pull requests coletadas: {len(all_pull_requests)}")
        return all_pull_requests