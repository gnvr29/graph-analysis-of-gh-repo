# main.py
from src.collectors.github_collector import GithubCollector
from src.services.neo4j_service import Neo4jService
from config.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

def run_github_data_pipeline():
    """
    Orquestra a coleta de dados do GitHub (issues abertas e fechadas) 
    e sua persistência no Neo4j.
    """
    neo4j_service = None
    try:
        print("Iniciando o pipeline de coleta e persistência de dados do GitHub...")

        # 1. Inicializar o coletor do GitHub
        github_collector = GithubCollector()

        # 2. Coletar issues ABERTAS do GitHub
        print("\n--- Coletando Issues ABERTAS do GitHub ---")
        open_issues_details = github_collector.collect_issues()
        print(f"Coleta de issues ABERTAS concluída. Total: {len(open_issues_details)}")

        # 3. Coletar issues FECHADAS do GitHub 
        print("\n--- Coletando Issues FECHADAS do GitHub ---")
        closed_issues_details = github_collector.collect_closed_issues()
        print(f"Coleta de issues FECHADAS concluída. Total: {len(closed_issues_details)}")
        
        # 4. Combinar as listas e verificar se há dados
        all_issues_details = open_issues_details + closed_issues_details

        if not all_issues_details:
            print("\nNenhuma issue (aberta ou fechada) foi coletada. Encerrando.")
            return

        print(f"\nColeta total de issues concluída. Total de issues detalhadas: {len(all_issues_details)}")

        # 5. Inicializar o serviço Neo4j
        print("\n--- Conectando ao Neo4j ---")
        neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

        # 6. Inserir TODAS as issues no Neo4j
        print("\n--- Inserindo Issues (Abertas e Fechadas) no Neo4j ---")
        for issue in all_issues_details: # Agora itera sobre a lista combinada
            try:
                neo4j_service.insert_issue_data(issue)
                # Log aprimorado para sabermos qual issue e status
                status = issue.get('status', 'Status Desconhecido').upper()
                print(f"Issue #{issue.get('number')} ({status}) e seus comentários inseridos/atualizados no Neo4j.")
            except Exception as e:
                print(f"Erro ao inserir issue #{issue.get('number')} no Neo4j: {e}")
        print("Inserção de issues no Neo4j concluída.")

        # 7. Coletar Pull Requests (Lógica inalterada)
        print("\n--- Coletando Pull Requests ABERTAS do GitHub ---")
        pull_requests_coletadas = github_collector.collect_pull_requests()

        if pull_requests_coletadas:
            print(f"\nColeta de Pull Requests concluída. Total de PRs: {len(pull_requests_coletadas)}")
            # TODO: Adicionar lógica para inserir Pull Requests no Neo4j,
            #       modelando PRs como um novo tipo de nó e seus relacionamentos.
            #       Por enquanto, apenas exibimos a contagem.
            print("Atenção: A inserção de Pull Requests no Neo4j ainda não está implementada neste script.")
        else:
            print("Nenhuma Pull Request foi coletada.")


        print("\nPipeline de dados concluído com sucesso!")

    except Exception as e:
        print(f"\nUm erro crítico ocorreu durante a execução do pipeline: {e}")
    finally:
        if neo4j_service:
            print("\n--- Fechando conexão com o Neo4j ---")
            neo4j_service.close()

if __name__ == "__main__":
    run_github_data_pipeline()