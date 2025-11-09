from neo4j import GraphDatabase

class Neo4jService:
    def __init__(self, uri, user, password):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        try: 
            self.driver.verify_connectivity()
            print("Conectado ao Neo4j.")
        except Exception as e:
            print(f"Erro ao conectar ao Neo4j: {e}")
            raise
            
    def close(self):
        if self.driver:
            self.driver.close()
            print("Desconectado do Neo4j.")

    # --- MÉTODOS DE ISSUE ---

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

        # Para cada comentário...
        for comment_data in issue_data.get('comments', []):
            if comment_data.get('author') is None:
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

        author_login = issue_data.get('author')
        closed_by_login = issue_data.get('closedBy')

        if closed_by_login and closed_by_login != author_login:
            tx.run("""
                MATCH (i:Issue {number: $issue_number})
                MATCH (c:Author {login: $closed_by_login})
                MERGE (c)-[:CLOSED]->(i)
            """, issue_number=issue_data.get('number'), closed_by_login=closed_by_login)

    def insert_issue_data(self, issue_data):
        """
        Insere os dados de uma única issue e seus comentários no Neo4j.
        """
        if not self.driver:
            print("Driver Neo4j não inicializado.")
            return

        if issue_data.get('author') is None:
            print(f"Skipping issue #{issue_data.get('number')} due to missing author.")
            return

        with self.driver.session() as session:
            session.execute_write(self._create_issue_and_comments_transaction, issue_data)

    def _create_pull_request_transaction(self, tx, pr_data):
        """
        Transação interna para criar/atualizar o PR, seu autor,
        comentários, revisões e merges.
        """
        pr_number = pr_data.get('number')
        author_login = pr_data.get('author')

        # 1. Criar/Atualizar o nó do Author do PR (se não for None)
        if author_login:
            tx.run("MERGE (a:Author {login: $login})", login=author_login)
        else:
            print(f"Autor do PR #{pr_number} é None, pulando criação de autor.")

        # 2. Criar/Atualizar o nó do PullRequest (com todos os novos campos)
        tx.run("""
            MERGE (pr:PullRequest {number: $pr_number})
            ON CREATE SET 
                pr.id = $id, 
                pr.title = $title,
                pr.body = $body,
                pr.createdAt = $createdAt,
                pr.closedAt = $closedAt,
                pr.mergedAt = $mergedAt,
                pr.status = $status
            ON MATCH SET
                pr.title = $title,
                pr.body = $body,
                pr.closedAt = $closedAt,
                pr.mergedAt = $mergedAt,
                pr.status = $status
            """, 
            id=pr_data.get('id'),
            pr_number=pr_number,
            title=pr_data.get('title'),
            body=pr_data.get('body'),
            createdAt=pr_data.get('createdAt'),
            closedAt=pr_data.get('closedAt'), 
            mergedAt=pr_data.get('mergedAt'),
            status=pr_data.get('status')
        )
        
        # 3. Ligar o PR ao seu Autor (se o autor existir)
        if author_login:
            tx.run("""
                MATCH (pr:PullRequest {number: $pr_number})
                MATCH (a:Author {login: $author_login})
                MERGE (a)-[:CREATED]->(pr)
                """, 
                pr_number=pr_number, 
                author_login=author_login
            )

        # 4. Ligar o PR a quem fez o MERGE (se houver)
        merged_by_login = pr_data.get('mergedBy')
        if merged_by_login:
            tx.run("MERGE (m:Author {login: $login})", login=merged_by_login)
            tx.run("""
                MATCH (pr:PullRequest {number: $pr_number})
                MATCH (m:Author {login: $merged_by_login})
                MERGE (m)-[:MERGED]->(pr)
                """,
                pr_number=pr_number,
                merged_by_login=merged_by_login
            )

        for comment_data in pr_data.get('comments', []):
            comment_author_login = comment_data.get('user', {}).get('login')
            if not comment_author_login:
                continue
            
            tx.run("MERGE (ca:Author {login: $login})", login=comment_author_login)
            tx.run("""
                MATCH (pr:PullRequest {number: $pr_number})
                MATCH (ca:Author {login: $comment_author_login})
                MERGE (c:Comment {id: $comment_id})
                ON CREATE SET c.body = $body, c.createdAt = $createdAt
                ON MATCH SET c.body = $body, c.createdAt = $createdAt
                
                MERGE (pr)-[:HAS_COMMENT]->(c)
                MERGE (ca)-[:AUTHORED]->(c)
                """,
                pr_number=pr_number,
                comment_author_login=comment_author_login,
                comment_id=comment_data.get('id'),
                body=comment_data.get('body'),
                createdAt=comment_data.get('created_at')
            )

        # 6. Loop: Comentários de Revisão (Linhas de Código)
        for review_comment_data in pr_data.get('review_comments', []):
            comment_author_login = review_comment_data.get('user', {}).get('login')
            if not comment_author_login:
                continue
            
            tx.run("MERGE (ca:Author {login: $login})", login=comment_author_login)
            tx.run("""
                MATCH (pr:PullRequest {number: $pr_number})
                MATCH (ca:Author {login: $comment_author_login})
                MERGE (c:Comment {id: $comment_id})
                ON CREATE SET c.body = $body, c.createdAt = $createdAt
                ON MATCH SET c.body = $body, c.createdAt = $createdAt
                
                MERGE (pr)-[:HAS_REVIEW_COMMENT]->(c)
                MERGE (ca)-[:AUTHORED]->(c)
                """,
                pr_number=pr_number,
                comment_author_login=comment_author_login,
                comment_id=review_comment_data.get('id'),
                body=review_comment_data.get('body'),
                createdAt=review_comment_data.get('created_at')
            )
        
        # 7. Loop: Eventos de Revisão (Aprovações, etc.)
        for review_data in pr_data.get('reviews', []):
            review_author_login = review_data.get('user', {}).get('login')
            if not review_author_login:
                continue
                
            tx.run("MERGE (ra:Author {login: $login})", login=review_author_login)
            tx.run("""
                MATCH (pr:PullRequest {number: $pr_number})
                MATCH (ra:Author {login: $review_author_login})
                MERGE (r:Review {id: $review_id})
                ON CREATE SET 
                    r.state = $state, 
                    r.submittedAt = $submittedAt,
                    r.body = $body
                ON MATCH SET 
                    r.state = $state, 
                    r.submittedAt = $submittedAt,
                    r.body = $body
                
                MERGE (pr)-[:HAS_REVIEW]->(r)
                MERGE (ra)-[:PERFORMED_REVIEW]->(r)
                """,
                pr_number=pr_number,
                review_author_login=review_author_login,
                review_id=review_data.get('id'),
                state=review_data.get('state'), 
                body=review_data.get('body'),
                submittedAt=review_data.get('submitted_at')
            )
        

    def insert_pull_request_data(self, pr_data):
        """
        Insere os dados de um único Pull Request e todos os seus
        detalhes (comentários, revisões) no Neo4j.
        """
        if not self.driver:
            print("Driver Neo4j não inicializado.")
            return

        with self.driver.session() as session:
            session.execute_write(self._create_pull_request_transaction, pr_data)
    