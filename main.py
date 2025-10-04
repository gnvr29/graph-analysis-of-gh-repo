import requests
from bs4 import BeautifulSoup
import json
import time

def busca_dados_github():

    issues = []
    totalIssues = 0
    pull_requests = []
    comments = []

    try:
        # PEGAR AS ISSUES
        data = coleta_issues()
        issues = data.get('issues', [])
        totalIssues = data.get('count', 0)

        issues.extend(coleta_issues(totalIssues).get('issues', []))

        print(f"Número total de issues coletadas: {len(issues)}")

        # PEGAR AS PULL REQUESTS
    except requests.exceptions.RequestException as e:
        print(f"Erro ao fazer a requisição: {e}")
        return issues, pull_requests, comments


def coleta_issues(total_issues=0, issues_per_page=25):
    url = "https://github.com/streamlit/streamlit/issues"
    if total_issues == 0:
        print(f"Coletando issues ABERTAS da página 1")
        response = requests.get(f"{url}?page=1")

        response.raise_for_status()

        data = html_to_json(response)
        return interpretar_issues(data)
    else:
        pages = total_issues // issues_per_page + 1
        issues = []
        for page in range(2, pages + 1):
            print(f"Coletando issues ABERTAS da página {page}")
            response = requests.get(f"{url}?page={page}")
            response.raise_for_status()
            data = html_to_json(response)
            issues.extend(interpretar_issues(data).get('issues', []))
            time.sleep(3) 
        return {'issues': issues, 'count': total_issues}

        


def html_to_json(response):
    if not response:
        return None
    
    try:
        soup = BeautifulSoup(response.text, 'html.parser')
        script_tag = soup.find('script', {
            'type': 'application/json',
            'data-target': 'react-app.embeddedData'
        })
        json_text = script_tag.string
        if json_text:
            data = json.loads(json_text)
            return data
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON: {e}")
        return None

def interpretar_issues(data):
    issues = []
    try:
        issues_data = data.get('payload').get('preloadedQueries', {})[0].get('result', {}).get('data', {}).get('repository', {}).get('search')

        issues_count = issues_data.get('issueCount')
        # print(f"Número total de issues: {issues_count}")
        issues_data = issues_data.get('edges', [])

        for issue in issues_data:
            try:
                issue_node = issue.get('node', {})
                issue_info = {
                    'id': issue_node.get('id'),
                    'title': issue_node.get('title'),
                    'number': issue_node.get('number'),
                    'createdAt': issue_node.get('createdAt'),
                    'author': (issue_node.get('author') or {}).get('login'),
                    'state': issue_node.get('state'),
                    'closed': issue_node.get('closed'),
                }
                issues.append(issue_info)
            except Exception as e:
                print(f"Erro ao interpretar uma issue: {e}")
                continue
    except Exception as e:
        print(f"Erro ao interpretar os dados das issues: {e}")
    return {'issues': issues, 'count': issues_count}


busca_dados_github()
