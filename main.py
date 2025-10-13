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
        data = coleta_issues()
        issues = data.get('issues', [])
        totalIssues = data.get('count', 0)

        issues_per_page = 25

        # if totalIssues > len(issues):
            # print(f"Coletando issues restantes das páginas 2 em diante...")
            # issues.extend(coleta_issues(total_issues=totalIssues, issues_per_page=issues_per_page).get('issues', []))
        
        print(f"Número total de issues coletadas: {len(issues)}")

        for issue_dict in issues:
            issue_number = issue_dict.get('number')
            print(f"Coletando corpo e comentários detalhados para a issue #{issue_number}...")
            
            detalhes_coletados = coleta_issues_coments(issue_number)

            issue_dict['body'] = detalhes_coletados.get('issue_body')
            issue_dict['comments'] = detalhes_coletados.get('comments')
            
            time.sleep(1)

    except requests.exceptions.RequestException as e:
        print(f"Erro ao fazer a requisição: {e}")
        return issues, pull_requests, comments
    except Exception as e:
        print(f"Um erro inesperado ocorreu: {e}")
        return issues, pull_requests, comments
    
    return issues, pull_requests, comments


def coleta_issues(total_issues=0, issues_per_page=25):
    url = "https://github.com/streamlit/streamlit/issues"
    todas_issues_paginadas = []
    issues_count = 0

    if total_issues == 0:
        print(f"Coletando issues ABERTAS da página 1 para contagem total...")
        response = requests.get(f"{url}?page=1")
        response.raise_for_status()
        data = html_to_json(response)
        
        if data:
            result = interpretar_issues(data)
            todas_issues_paginadas.extend(result.get('issues', []))
            issues_count = result.get('count', 0)
        return {'issues': todas_issues_paginadas, 'count': issues_count}
    else:
        pages_to_collect = (total_issues // issues_per_page) + (1 if total_issues % issues_per_page > 0 else 0)
        for page in range(2, pages_to_collect + 1):
            print(f"Coletando issues ABERTAS da página {page}/{pages_to_collect}...")
            response = requests.get(f"{url}?page={page}")
            response.raise_for_status()
            data = html_to_json(response)
            if data:
                todas_issues_paginadas.extend(interpretar_issues(data).get('issues', []))
            time.sleep(3)
        return {'issues': todas_issues_paginadas, 'count': total_issues}


def coleta_issues_coments(issue_number):
    url = "https://github.com/streamlit/streamlit/issues/" + str(issue_number) 

    print(f"Coletando comentários da issue {issue_number}")
    
    response = requests.get(url)
    response.raise_for_status()

    data_json_completa_da_issue = html_to_json(response)
    
    if data_json_completa_da_issue:
        return interpretar_comentarios(data_json_completa_da_issue)
    return {'issue_body': None, 'comments': []}


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
        else:
            print("Tag de script JSON encontrada, mas seu conteúdo está vazio.")
            return None
    except json.JSONDecodeError as e:
        print(f"Erro ao decodificar JSON: {e}")
        return None
    except AttributeError:
        print(f"Não foi possível encontrar a tag de script JSON 'react-app.embeddedData' na página.")
        return None


def interpretar_issues(data):
    issues = []
    try:
        issues_data = data.get('payload').get('preloadedQueries', [{}])[0].get('result', {}).get('data', {}).get('repository', {}).get('search', {})

        issues_count = issues_data.get('issueCount')
        issues_data_edges = issues_data.get('edges', [])

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
    MODIFICADO: Interpreta o JSON COMPLETO de uma página de issue individual
    (como o JSON que você forneceu), extraindo o corpo da issue e os comentários
    da seção 'frontTimelineItems'.

    Args:
        data_completa_issue_page (dict): O dicionário JSON completo da resposta
                                         HTTP de uma única página de issue.

    Returns:
        dict: Um dicionário contendo o corpo da issue ('issue_body') e uma lista
              de comentários ('comments'). Retorna None para 'issue_body' e uma
              lista vazia para 'comments' se os dados não forem encontrados ou houver erro.
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


if __name__ == "__main__":
    print("Iniciando coleta de dados...")
    issues_com_detalhes, _, _ = busca_dados_github()

    if issues_com_detalhes:
        print(f"\nColeta concluída. Total de issues detalhadas: {len(issues_com_detalhes)}")
        if issues_com_detalhes:
            primeira_issue = issues_com_detalhes[0]
            print(f"\n--- Detalhes da Primeira Issue (Número: {primeira_issue.get('number')}) ---")
            print(f"Título: {primeira_issue.get('title')}")
            print(f"Corpo Principal da Issue:\n{primeira_issue.get('body', 'N/A')}")
            
            if primeira_issue.get('comments'):
                print(f"\nNúmero de Comentários Adicionais: {len(primeira_issue['comments'])}")
                print("Exemplo do primeiro comentário:")
                primeiro_comentario = primeira_issue['comments'][0]
                print(f"  Autor: {primeiro_comentario.get('author')}")
                print(f"  Criado em: {primeiro_comentario.get('createdAt')}")
                print(f"  ID: {primeiro_comentario.get('id')}")
                print(f"  Corpo: {primeiro_comentario.get('body')}")
            else:
                print("\nNenhum comentário adicional encontrado para esta issue.")
        else:
            print("Nenhuma issue detalhada na lista.")
    else:
        print("Nenhuma issue foi coletada ou um erro ocorreu.")