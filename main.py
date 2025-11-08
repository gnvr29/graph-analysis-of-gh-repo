from src.collectors.github_collector import GithubCollector
from src.services.neo4j_service import Neo4jService
from config.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

def run_github_data_pipeline():
    """
    Orquestra a coleta de dados do GitHub e persiste no Neo4j incrementalmente.
    """
    neo4j_service = None
    try:
        print("Iniciando o pipeline de coleta e persistência INCREMENTAL...")

        # 1. Inicializar serviços (Conectamos ao banco PRIMEIRO agora)
        print("\n--- Conectando ao Neo4j ---")
        neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        
        print("\n--- Inicializando Coletor GitHub ---")
        github_collector = GithubCollector()

        # --- SEÇÃO DE ISSUES (Scraping) ---

        # 2. Coletar e Inserir Issues ABERTAS
        print("\n--- [FASE 1] Issues ABERTAS (Scraping + Inserção Imediata) ---")
        count_open = 0
        for issue in github_collector.collect_issues():
            try:
                neo4j_service.insert_issue_data(issue)
                count_open += 1
                print(f"✅ Issue ABERTA #{issue.get('number')} salva.")
            except Exception as e:
                print(f"❌ Erro ao salvar Issue ABERTA #{issue.get('number')}: {e}")
        print(f"Concluído: {count_open} issues ABERTAS processadas.")

        print("\n--- [FASE 2] Issues FECHADAS (Scraping + Inserção Imediata) ---")
        count_closed = 0
        for issue in github_collector.collect_closed_issues(start_page=41):
            try:
                neo4j_service.insert_issue_data(issue)
                count_closed += 1
                print(f"✅ Issue FECHADA #{issue.get('number')} salva.")
            except Exception as e:
                print(f"❌ Erro ao salvar Issue FECHADA #{issue.get('number')}: {e}")
        print(f"Concluído: {count_closed} issues FECHADAS processadas.")

        # --- SEÇÃO DE PULL REQUESTS (API) ---

        # 4. Coletar e Inserir Pull Requests
        print("\n--- [FASE 3] Pull Requests (API + Inserção Imediata) ---")
        count_prs = 0
        # Novamente: idealmente collect_all_pull_requests_api deve usar 'yield' internamente
        for pr in github_collector.collect_all_pull_requests_api():
            try:
                # Verificação de segurança caso o método ainda não exista
                if hasattr(neo4j_service, 'insert_pull_request_data'):
                    neo4j_service.insert_pull_request_data(pr)
                    count_prs += 1
                    print(f"✅ PR #{pr.get('number')} salvo.")
                else:
                    print("🚨 MÉTODO FALTANDO: 'insert_pull_request_data' não existe no Neo4jService. Pulando PR.")
            except Exception as e:
                print(f"❌ Erro ao salvar PR #{pr.get('number')}: {e}")
        print(f"Concluído: {count_prs} Pull Requests processados.")

        print("\n🎉 Pipeline concluído com sucesso!")
        print(f"Resumo Final: {count_open} Issues Abertas | {count_closed} Issues Fechadas | {count_prs} PRs")

    except KeyboardInterrupt:
        print("\n\n⚠️ Pipeline interrompido pelo usuário!")
        print("Os dados já processados até aqui foram salvos no Neo4j.")
    except Exception as e:
        print(f"\n🔥 Um erro crítico ocorreu e interrompeu o pipeline: {e}")
    finally:
        if neo4j_service:
            print("\n--- Fechando conexão com o Neo4j ---")
            neo4j_service.close()

if __name__ == "__main__":
    run_github_data_pipeline()