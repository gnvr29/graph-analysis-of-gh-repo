# main.py
from src.collectors.github_collector import GithubCollector
from src.services.neo4j_service import Neo4jService
from config.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

def run_github_data_pipeline():
    """
    Orquestra a coleta de dados do GitHub (issues e PRs, abertos e fechados) 
    e sua persistência no Neo4j.
    """
    neo4j_service = None
    try:
        print("Iniciando o pipeline de coleta e persistência de dados do GitHub...")

        # 1. Inicializar o coletor do GitHub
        github_collector = GithubCollector()

        # --- SEÇÃO DE ISSUES (Scraping) ---

        # 2. Coletar issues ABERTAS
        print("\n--- Coletando Issues ABERTAS do GitHub (Scraping) ---")
        open_issues_details = github_collector.collect_issues()
        print(f"Coleta de issues ABERTAS concluída. Total: {len(open_issues_details)}")

        # 3. Coletar issues FECHADAS
        print("\n--- Coletando Issues FECHADAS do GitHub (Scraping) ---")
        closed_issues_details = github_collector.collect_closed_issues()
        print(f"Coleta de issues FECHADAS concluída. Total: {len(closed_issues_details)}")
        
        # 4. Combinar issues
        all_issues_details = open_issues_details + closed_issues_details

        if not all_issues_details:
            print("\nNenhuma issue (aberta ou fechada) foi coletada.")
        else:
            print(f"\nColeta total de issues concluída. Total detalhado: {len(all_issues_details)}")

        # --- SEÇÃO DE PULL REQUESTS (API) ---
        
        # 5. Coletar TODOS os Pull Requests (Abertos e Fechados) via API
        # As etapas 5, 6 e 7 foram substituídas por esta única chamada:
        print("\n--- Coletando Pull Requests (Abertos e Fechados) via API ---")
        all_pull_requests = github_collector.collect_all_pull_requests_api()

        if not all_pull_requests:
            print("\nNenhum Pull Request (aberto ou fechado) foi coletado.")
        else:
            print(f"\nColeta total de Pull Requests (API) concluída. Total: {len(all_pull_requests)}")

        # --- SEÇÃO DE BANCO DE DADOS ---

        if not all_issues_details and not all_pull_requests:
            print("\nNenhum dado (Issue ou PR) foi coletado. Encerrando pipeline.")
            return

        # 8. Inicializar o serviço Neo4j
        print("\n--- Conectando ao Neo4j ---")
        neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

        # 9. Inserir TODAS as issues no Neo4j
        if all_issues_details:
            print("\n--- Inserindo Issues (Abertas e Fechadas) no Neo4j ---")
            for issue in all_issues_details:
                try:
                    neo4j_service.insert_issue_data(issue)
                    status = issue.get('status', 'Status Desconhecido').upper()
                    print(f"Issue #{issue.get('number')} ({status}) e comentários inseridos/atualizados no Neo4j.")
                except Exception as e:
                    print(f"Erro ao inserir issue #{issue.get('number')} no Neo4j: {e}")
            print("Inserção de issues no Neo4j concluída.")
        
        # 10. Inserir TODOS os Pull Requests no Neo4j 
        if all_pull_requests:
            print("\n--- Inserindo Pull Requests (Abertos e Fechados) no Neo4j ---")
            for pr in all_pull_requests:
                try:
                    # ** IMPORTANTE: Este método precisa ser criado no Neo4jService **
                    neo4j_service.insert_pull_request_data(pr)
                    
                    status = pr.get('status', 'Status Desconhecido').upper()
                    print(f"Pull Request #{pr.get('number')} ({status}) inserido/atualizado no Neo4j.")
                except AttributeError:
                    print(f"\nERRO FATAL: O método 'insert_pull_request_data' não foi encontrado em Neo4jService.")
                    print("Por favor, implemente este método para salvar PRs no banco.")
                    print("Interrompendo inserção de Pull Requests.")
                    break # Para o loop de PRs se o método não existir
                except Exception as e:
                    print(f"Erro ao inserir Pull Request #{pr.get('number')} no Neo4j: {e}")
            print("Inserção de Pull Requests no Neo4j concluída.")


        print("\nPipeline de dados concluído com sucesso!")

    except Exception as e:
        print(f"\nUm erro crítico ocorreu durante a execução do pipeline: {e}")
    finally:
        if neo4j_service:
            print("\n--- Fechando conexão com o Neo4j ---")
            neo4j_service.close()

if __name__ == "__main__":
    run_github_data_pipeline()