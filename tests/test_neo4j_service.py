import pytest
from src.services.neo4j_service import Neo4jService # Importa apenas para type hinting e clareza

# O fixture neo4j_service será automaticamente injetado pelo pytest
# (definido em conftest.py)

def test_neo4j_connection(neo4j_service: Neo4jService):
    """
    Verifica se o serviço Neo4j pode se conectar.
    A falha na conexão já é tratada na fixture.
    """
    assert neo4j_service.driver is not None
    try:
        neo4j_service.driver.verify_connectivity()
        print("\nTeste de conexão Neo4j bem-sucedido.")
    except Exception as e:
        pytest.fail(f"Falha na verificação de conectividade do Neo4j: {e}")

def test_insert_issue_data(neo4j_service: Neo4jService):
    """
    Testa a inserção de dados de uma issue e seus comentários no Neo4j.
    Usa um número de issue e IDs de comentário únicos para evitar colisões
    e garantir a idempotência do MERGE.
    """
    # Dados de teste
    issue_number = 99999999 + hash("test_insert_issue_data") % 10000000 # Garante número único
    test_issue = {
        'id': f'test-issue-id-{issue_number}',
        'number': issue_number,
        'title': f'Pytest Test Issue {issue_number}',
        'body': 'This is a test issue body inserted by pytest.',
        'createdAt': '2024-01-01T12:00:00Z',
        'author': 'pytest-author',
        'state': 'OPEN',
        'closed': False,
        'comments': [
            {
                'id': f'test-comment-id-{issue_number}-1',
                'body': 'First comment from pytest.',
                'createdAt': '2024-01-01T12:05:00Z',
                'author': 'pytest-commenter1'
            },
            {
                'id': f'test-comment-id-{issue_number}-2',
                'body': 'Second comment from pytest.',
                'createdAt': '2024-01-01T12:10:00Z',
                'author': 'pytest-commenter2'
            }
        ]
    }

    # Insere os dados
    try:
        neo4j_service.insert_issue_data(test_issue)
        print(f"\nIssue de teste #{issue_number} inserida com sucesso.")
    except Exception as e:
        pytest.fail(f"Erro ao inserir issue de teste no Neo4j: {e}")

    # Verifica se os dados foram inseridos corretamente (opcional, mas boa prática)
    with neo4j_service.driver.session() as session:
        result = session.run("MATCH (i:Issue {number: $num}) RETURN i", num=issue_number).single()
        assert result is not None
        assert result["i"]["title"] == test_issue['title']

        comments_result = session.run("""
            MATCH (i:Issue {number: $num})-[:HAS_COMMENT]->(c:Comment)
            RETURN c.id ORDER BY c.id
        """, num=issue_number).value()
        
        expected_comment_ids = sorted([c['id'] for c in test_issue['comments']])
        assert sorted(comments_result) == expected_comment_ids

        # Limpeza (opcional, dependendo da estratégia de teste)
        session.run("MATCH (i:Issue {number: $num}) DETACH DELETE i", num=issue_number)
        print(f"Issue de teste #{issue_number} removida.")

def test_insert_issue_without_author(neo4j_service: Neo4jService):
    """
    Testa se o método ignora issues com autor nulo.
    """
    issue_number = 99999999 + hash("test_issue_no_author") % 10000000
    test_issue_no_author = {
        'id': f'test-issue-no-author-{issue_number}',
        'number': issue_number,
        'title': 'Issue without author',
        'body': 'Should be skipped.',
        'createdAt': '2024-01-02T00:00:00Z',
        'author': None, # Autor nulo
        'state': 'OPEN',
        'closed': False,
        'comments': []
    }
    # O método deve imprimir uma mensagem e não levantar erro
    neo4j_service.insert_issue_data(test_issue_no_author)
    
    # Verifica que a issue não foi inserida
    with neo4j_service.driver.session() as session:
        result = session.run("MATCH (i:Issue {number: $num}) RETURN i", num=issue_number).single()
        assert result is None
        print(f"\nIssue de teste #{issue_number} sem autor não foi inserida, conforme esperado.")
