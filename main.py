# main.py
from src.collectors.github_collector import GithubCollector
from src.services.neo4j_service import Neo4jService
from config.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

def run_github_data_pipeline():
    """
    Orquestra a coleta de dados do GitHub e sua persistência no Neo4j.
    """
    neo4j_service = None
    try:
        print("Iniciando o pipeline de coleta e persistência de dados do GitHub...")

        # 1. Inicializar o coletor do GitHub
        github_collector = GithubCollector()

        # 2. Coletar issues do GitHub
        print("\n--- Coletando Issues do GitHub ---")
        issues_com_detalhes = github_collector.collect_issues()

        if not issues_com_detalhes:
            print("Nenhuma issue foi coletada. Encerrando.")
            return

        print(f"\nColeta de issues concluída. Total de issues detalhadas: {len(issues_com_detalhes)}")

        # 3. Inicializar o serviço Neo4j
        print("\n--- Conectando ao Neo4j ---")
        neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)

        # 4. Inserir issues no Neo4j
        print("\n--- Inserindo Issues no Neo4j ---")
        for issue in issues_com_detalhes:
            try:
                neo4j_service.insert_issue_data(issue)
                print(f"Issue #{issue.get('number')} e seus comentários inseridos/atualizados no Neo4j.")
            except Exception as e:
                print(f"Erro ao inserir issue #{issue.get('number')} no Neo4j: {e}")
        print("Inserção de issues no Neo4j concluída.")

        # 5. Coletar Pull Requests (Opcional, mas já implementado)
        print("\n--- Coletando Pull Requests do GitHub ---")
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
            neo4j_service.close()

if __name__ == "__main__":
    run_github_data_pipeline()