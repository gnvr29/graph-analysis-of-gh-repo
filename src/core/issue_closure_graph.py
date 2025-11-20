import sys
import os

project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if project_root not in sys.path:
    sys.path.append(project_root)

from src.services.neo4j_service import Neo4jService
from src.core.AdjacencyListGraph import AdjacencyListGraph
from config.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

def build_issue_closure_graph():
    """
    Constrói o Grafo 2: Fechamento de Issue por outro usuário.

    Neste grafo[cite: 24, 29]:
    - Nós: Usuários (Authors)
    - Arestas (u, v): O usuário 'u' (closer) fechou uma issue do usuário 'v' (author).
    
    Retorna:
        (AdjacencyListGraph, dict, dict): O grafo construído,
        o mapeamento 'login' -> ID do vértice,
        e o mapeamento ID do vértice -> 'login'.
    """
    print("Iniciando construção do Grafo 2: Fechamento de Issues por Outros Usuários...")
    
    neo4j_service = None
    try:
        # Conecta ao Neo4j
        neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        
        with neo4j_service.driver.session() as session:
            
            # Obter todos os usuários para mapear login -> ID
            # Os vértices do grafo são inteiros de 0 a N-1
            result = session.run("MATCH (a:Author) RETURN a.login AS login")
            user_logins = [record["login"] for record in result]
            
            user_to_id = {login: i for i, login in enumerate(user_logins)}
            id_to_user = {i: login for i, login in enumerate(user_logins)}
            
            num_vertices = len(user_to_id)
            if num_vertices == 0:
                print("Nenhum usuário (Author) encontrado no banco. Encerrando.")
                return AdjacencyListGraph(0), {}, {}
                
            print(f"Mapeados {num_vertices} usuários (vértices).")

            # Inicializa a implementação do grafo
            graph = AdjacencyListGraph(num_vertices)

            # Obter as relações de fechamento, onde closer é diferente de author
            query = """
            MATCH (closer:Author)-[:CLOSED]->(i:Issue)<-[:CREATED]-(author:Author)
            WHERE closer.login <> author.login
            RETURN closer.login AS closer_login, author.login AS author_login
            """
            closure_records = session.run(query)

            # Adicionar as arestas no grafo
            edge_count = 0
            for record in closure_records:
                closer_login = record["closer_login"]
                author_login = record["author_login"]
                
                u = user_to_id.get(closer_login)
                v = user_to_id.get(author_login)
                
                # Adiciona a aresta (Closer -> Author)
                if u is not None and v is not None:
                    graph.addEdge(u, v)
                    edge_count += 1
            
            print(f"Grafo de fechamento de issues construído. Total de arestas: {graph.getEdgeCount()}")
            
            return graph, user_to_id, id_to_user

    except Exception as e:
        print(f"Erro ao construir o grafo de fechamento de issues: {e}")
        return AdjacencyListGraph(0), {}, {}
    finally:
        if neo4j_service:
            neo4j_service.close()
# Teste básico da construção do grafo
# Você pode executar este arquivo diretamente para testar sua lógica
if __name__ == "__main__":
    
    # Constrói o grafo
    closure_graph, user_map, id_map = build_issue_closure_graph()
    
    if closure_graph.getVertexCount() > 0:
        print("\n--- Testando a API Obrigatória do Grafo ---")
        
        print(f"Total de Vértices (Usuários): {closure_graph.getVertexCount()}")
        print(f"Total de Arestas (Fechamentos): {closure_graph.getEdgeCount()}")
        
        print(f"Grafo está vazio (sem arestas)? {closure_graph.isEmptyGraph()}")
        print(f"Grafo é completo? {closure_graph.isCompleteGraph()}")
        print(f"Grafo é (fracamente) conexo? {closure_graph.isConnected()}")

        # Encontrar o usuário com mais fechamentos de issues de outros (maior OutDegree)
        max_out_degree = 0
        user_max_out_degree = -1
        
        for i in range(closure_graph.getVertexCount()):
            out_degree = closure_graph.getVertexOutDegree(i)
            if out_degree > max_out_degree:
                max_out_degree = out_degree
                user_max_out_degree = i
        
        if user_max_out_degree != -1:
            print(f"Usuário mais ativo (mais fechamentos): '{id_map[user_max_out_degree]}' com {max_out_degree} fechamentos.")
        
        # Encontrar o usuário que mais teve issues fechadas por outros (maior InDegree)
        max_in_degree = 0
        user_max_in_degree = -1
        
        for i in range(closure_graph.getVertexCount()):
            in_degree = closure_graph.getVertexInDegree(i)
            if in_degree > max_in_degree:
                max_in_degree = in_degree
                user_max_in_degree = i

        if user_max_in_degree != -1:
            print(f"Usuário com mais issues fechadas por outros: '{id_map[user_max_in_degree]}' com {max_in_degree} issues.")