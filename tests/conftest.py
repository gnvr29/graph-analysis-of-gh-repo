import pytest
from src.services.neo4j_service import Neo4jService
from src.collectors.github_collector import GithubCollector
from config.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, GITHUB_BASE_URL, REQUEST_DELAY_SECONDS

# Fixture para o serviço Neo4j
@pytest.fixture(scope="module")
def neo4j_service():
    """
    Cria uma instância de Neo4jService para os testes.
    Assegura que a conexão seja fechada após todos os testes do módulo.
    """
    try:
        print("\nIniciando Neo4jService para testes...")
        print(NEO4J_URI)
        service = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        yield service 
    except Exception as e:
        pytest.fail(f"Falha ao inicializar Neo4jService para testes: {e}")
    finally:
        if 'service' in locals() and service:
            service.close()

# Fixture para o coletor GitHub
@pytest.fixture(scope="module")
def github_collector():
    """
    Cria uma instância de GithubCollector para os testes.
    """
    collector = GithubCollector(base_url=GITHUB_BASE_URL, delay_seconds=0.1) 
    yield collector