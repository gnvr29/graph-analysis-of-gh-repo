from neo4j import GraphDatabase

class Neo4jService:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        try: 
            self.driver.verify_connectivity()
            print("Conectado ao Neo4j")
        except Exception as e:
            print(f"Erro ao conectar ao Neo4j: {e}")
            raise
    def close(self):
        if self.driver:
            self.driver.close()
            print("Desconectado do Neo4j")
    
    def _create_issue_and_comments_transaction(self, tx, issue_data):
        """
        Transação interna para criar/atualizar a issue, autor e comentários.
        """
        # Criar/Atualizar o nó do Author da Issue
        tx.run("""
            MERGE (a:Author {login: $author_login})
            RETURN a
        """, author_login=issue_data.get('author'))

        # Criar/Atualizar o nó da Issue e o relacionamento CREATED
        tx.run("""
            MERGE (i:Issue {number: $issue_number})
            ON CREATE SET 
                i.id = $id, 
                i.title = $title, 
                i.body = $body, 
                i.createdAt = $createdAt, 
                i.state = $state, 
                i.closed = $closed
            ON MATCH SET
                i.title = $title, 
                i.body = $body, 
                i.createdAt = $createdAt, 
                i.state = $state, 
                i.closed = $closed
            WITH i
            MATCH (a:Author {login: $author_login})
            MERGE (a)-[:CREATED]->(i)
            RETURN i
        """, 
        id=issue_data.get('id'),
        issue_number=issue_data.get('number'),
        title=issue_data.get('title'),
        body=issue_data.get('body'),
        createdAt=issue_data.get('createdAt'),
        state=issue_data.get('state'),
        closed=issue_data.get('closed'),
        author_login=issue_data.get('author')
        )

        # Para cada comentário, criar/atualizar o nó do Comment, o Author do comentário
        # e os relacionamentos HAS_COMMENT e AUTHORED
        for comment_data in issue_data.get('comments', []):
            if comment_data.get('author') is None:
                # Ignora comentários sem autor válido
                continue

            tx.run("""
                MERGE (ca:Author {login: $comment_author_login})
                RETURN ca
            """, comment_author_login=comment_data.get('author'))

            tx.run("""
                MATCH (i:Issue {number: $issue_number})
                MERGE (c:Comment {id: $comment_id})
                ON CREATE SET 
                    c.body = $comment_body, 
                    c.createdAt = $comment_createdAt
                ON MATCH SET
                    c.body = $comment_body, 
                    c.createdAt = $comment_createdAt
                WITH i, c
                MERGE (i)-[:HAS_COMMENT]->(c)
                WITH c
                MATCH (ca:Author {login: $comment_author_login})
                MERGE (ca)-[:AUTHORED]->(c)
                RETURN c
            """, 
            issue_number=issue_data.get('number'),
            comment_id=comment_data.get('id'),
            comment_body=comment_data.get('body'),
            comment_createdAt=comment_data.get('createdAt'),
            comment_author_login=comment_data.get('author')
            )

    def insert_issue_data(self, issue_data):
        """
        Insere os dados de uma única issue e seus comentários no Neo4j.
        """
        if not self.driver:
            print("Driver Neo4j não inicializado.")
            return

        # Verifica se o autor principal da issue é None antes de tentar inserir
        if issue_data.get('author') is None:
            print(f"Skipping issue #{issue_data.get('number')} due to missing author.")
            return

        with self.driver.session() as session:
            session.write_transaction(self._create_issue_and_comments_transaction, issue_data)

# Exemplo de uso (opcional, para testar a conexão deste arquivo individualmente)
if __name__ == "__main__":
    URI = "neo4j+s://72e8c7dd.databases.neo4j.io"
    AUTH_USER = "neo4j"
    AUTH_PASS = "T8QbYzRzt1HHShophpPNfPAJeDwJwlITFXHxMJV5Xsg" # Sua senha do Neo4j

    try:
        neo4j_service = Neo4jService(URI, AUTH_USER, AUTH_PASS)
        # Você pode adicionar um teste de inserção aqui se quiser
        # Por exemplo, um dado de teste estático para uma issue mínima
        test_issue = {
            'id': 'test-issue-id-123',
            'number': 99999,
            'title': 'Test Issue Title',
            'body': 'This is a test issue body.',
            'createdAt': '2023-01-01T10:00:00Z',
            'author': 'testuser',
            'state': 'OPEN',
            'closed': False,
            'comments': [
                {
                    'id': 'test-comment-id-456',
                    'body': 'First test comment.',
                    'createdAt': '2023-01-01T10:05:00Z',
                    'author': 'commenter1'
                },
                {
                    'id': 'test-comment-id-789',
                    'body': 'Second test comment by same author.',
                    'createdAt': '2023-01-01T10:10:00Z',
                    'author': 'commenter1'
                }
            ]
        }
        print("\nTentando inserir uma issue de teste...")
        neo4j_service.insert_issue_data(test_issue)
        print(f"Issue de teste #{test_issue['number']} inserida (verifique no Neo4j Browser).")

    except Exception as e:
        print(f"Um erro ocorreu durante o teste do Neo4jService: {e}")
    finally:
        if 'neo4j_service' in locals():
            neo4j_service.close()