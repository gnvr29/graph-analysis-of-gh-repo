import json
from bs4 import BeautifulSoup

def html_to_json(response):
    """
    Extrai o JSON embutido de uma resposta HTML do GitHub.
    """
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
        else:
            return None
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON: {e} na URL: {response.url}")
        return None
    except AttributeError:
        return None
    except Exception as e:
        print(f"Um erro inesperado ocorreu em html_to_json: {e}")
        return None


def interpretar_issues(data):
    """
    Interpreta os dados JSON brutos de uma página de lista de issues do GitHub
    e retorna uma lista de issues e a contagem total.
    """
    issues = []
    issues_count = 0
    try:
        preloaded_queries = data.get('payload', {}).get('preloadedQueries', [])
        if preloaded_queries:
            result = preloaded_queries[0].get('result', {})
            repository_data = result.get('data', {}).get('repository', {})
            search_data = repository_data.get('search', {})

            issues_count = search_data.get('issueCount', 0)
            issues_data_edges = search_data.get('edges', [])

            for issue_edge in issues_data_edges:
                try:
                    issue_node = issue_edge.get('node', {})
                    if issue_node.get('__typename') == 'Issue':
                        issue_info = {
                            'id': issue_node.get('id'),
                            'title': issue_node.get('title'),
                            'number': issue_node.get('number'),
                            'createdAt': issue_node.get('createdAt'),
                            'author': (issue_node.get('author') or {}).get('login'),
                            'state': issue_node.get('state'),
                            'closed': issue_node.get('closed'),
                            'body': None, 
                            'comments': [] 
                        }
                        issues.append(issue_info)
                except Exception as e:
                    print(f"Erro ao interpretar uma issue individual da lista: {e}")
                    continue
    except Exception as e:
        print(f"Erro ao interpretar os dados gerais das issues: {e}")
    return {'issues': issues, 'count': issues_count}


def interpretar_comentarios(data_completa_issue_page):
    """
    Interpreta o JSON COMPLETO de uma página de issue individual,
    extraindo o corpo da issue e os comentários.
    """
    issue_body_content = None
    all_comments = []

    try:
        issue_obj = data_completa_issue_page.get('payload', {}).get('preloadedQueries', [{}])[0].get('result', {}).get('data', {}).get('repository', {}).get('issue', {})

        issue_body_content = issue_obj.get('body')

        timeline_items_edges = issue_obj.get('frontTimelineItems', {}).get('edges', [])

        for item_edge in timeline_items_edges:
            node = item_edge.get('node', {})
            if node.get('__typename') == 'IssueComment':
                comment_info = {
                    'id': node.get('id'),
                    'body': node.get('body'),
                    'createdAt': node.get('createdAt'),
                    'author': (node.get('author') or {}).get('login'),
                }
                all_comments.append(comment_info)

    except Exception as e:
        print(f"Erro ao interpretar o JSON da issue ou comentários: {e}")
        return {'issue_body': None, 'comments': []}
    
    return {'issue_body': issue_body_content, 'comments': all_comments}

def interpretar_pull_requests(data):
    """
    Interpreta os dados JSON brutos de uma página de lista de pull requests do GitHub
    e retorna uma lista de pull requests e a contagem total.
    """
    pull_requests = []
    open_pull_requests_count = 0
    closed_pull_requests_count = 0
    try:
        soup = BeautifulSoup(data, 'html.parser')
        pr_count = soup.select_one('div.table-list-header-toggle').text.strip().split()
        open_pull_requests_count = int(pr_count[0].replace(',', ''))
        closed_pull_requests_count = int(pr_count[2].replace(',', ''))

    except Exception as e:
        print(f"Erro ao interpretar os dados gerais das pull requests: {e}")
    return {'pull_requests': pull_requests, 'count': open_pull_requests_count + closed_pull_requests_count}