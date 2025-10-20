import requests
import time
from src.utils.github_parser import html_to_json, interpretar_issues, interpretar_comentarios, interpretar_pull_requests
from config.settings import GITHUB_BASE_URL, GITHUB_ISSUES_PATH, GITHUB_PULLS_PATH, REQUEST_DELAY_SECONDS

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

    def collect_issues(self):
        """
        Coleta todas as issues abertas, incluindo seus detalhes e comentários.
        Retorna uma lista de dicionários de issues.
        """
        all_issues = []
        issues_per_page = 25 

        initial_url = f"{self.base_url}{GITHUB_ISSUES_PATH}?page=1"
        data_initial = self._fetch_page_data(initial_url, description="issues da página 1")
        
        if data_initial:
            result_initial = interpretar_issues(data_initial)
            all_issues.extend(result_initial.get('issues', []))
            total_issues_count = result_initial.get('count', 0)
            print(f"Número total estimado de issues abertas: {total_issues_count}")
        else:
            print("Não foi possível coletar issues da primeira página.")
            return []

        if total_issues_count > len(all_issues):
            pages_to_fetch = (total_issues_count // issues_per_page) + (1 if total_issues_count % issues_per_page > 0 else 0)
            print(f"Coletando issues restantes das páginas 2 até {pages_to_fetch}...")
            for page in range(2, pages_to_fetch + 1):
                page_url = f"{self.base_url}{GITHUB_ISSUES_PATH}?page={page}"
                page_data = self._fetch_page_data(page_url, description=f"issues da página {page}")
                if page_data:
                    all_issues.extend(interpretar_issues(page_data).get('issues', []))
                else:
                    print(f"Atenção: Falha ao coletar issues da página {page}.")

        print(f"Número total de issues coletadas: {len(all_issues)}")

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
        
        return issues_with_details

    def collect_pull_requests(self):
        """
        Coleta todas as pull requests abertas.
        Retorna uma lista de dicionários de pull requests.
        """
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
            print(f"Coletando pull requests restantes das páginas 2 até {pages_to_fetch}...")
            for page in range(2, pages_to_fetch + 1):
                page_url = f"{self.base_url}{GITHUB_PULLS_PATH}?page={page}"
                page_data = self._fetch_page_data(page_url, description=f"pull requests da página {page}")
                if page_data:
                    all_pull_requests.extend(interpretar_pull_requests(page_data).get('pull_requests', []))
                else:
                    print(f"Atenção: Falha ao coletar pull requests da página {page}.")

        print(f"Número total de pull requests coletadas: {len(all_pull_requests)}")
        return all_pull_requests
