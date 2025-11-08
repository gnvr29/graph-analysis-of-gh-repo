# Arquivo: test_graph_adjancy_list.py
# Objetivo:
# - Buscar dados no Neo4j considerando apenas nós (:Author)
# - Transformar "outros nós" (Issue, PullRequest, etc.) em arestas direcionadas entre autores, com pesos específicos
# - Construir o grafo usando a classe AdjacencyListGraph (já existente no seu projeto — aqui apenas importada)
# - Gerar uma visualização nativa do Python usando tkinter (Canvas), exportando para PostScript (.ps) e também salvar a lista de adjacência em .txt
#
# Observações importantes:
# 1) Este script usa APENAS bibliotecas padrão do Python para visualização (tkinter). A exportação é em PostScript (.ps), que pode ser aberta em diversos visualizadores.
# 2) Ajuste os caminhos de import da AdjacencyListGraph e Neo4jService caso sua estrutura de pastas seja diferente.
# 3) Os pesos são somados quando ocorrem múltiplas interações entre o mesmo par de autores.
# 4) As consultas Cypher usam rótulos e relacionamentos comuns (COMMENTED/ON/OPENED/CREATED/REVIEWED/APPROVED/MERGED). Se seu schema tiver nomes diferentes, ajuste as constantes abaixo.
# 5) Execução:
#    python test_graph_adjancy_list.py
#
# Requisitos de execução:
# - Ter o Neo4j acessível via URI/usuário/senha definidos em config.settings
# - Ter a classe AdjacencyListGraph disponível no projeto (apenas importada aqui)
# - Ter o serviço Neo4jService disponível; caso não esteja, o código tenta um fallback simples usando o driver oficial 'neo4j' (que precisa estar instalado no ambiente).
#   Se você já possui o Neo4jService no seu projeto, esse fallback não será usado.


import sys
import os
from collections import defaultdict
import streamlit as st 

# ============== CÓDIGO PARA CORRIGIR O PATH ==============
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))

if project_root not in sys.path:
    sys.path.insert(0, project_root)



# ============== IMPORTS DO PROJETO ==============

try:
    from src.core.AdjacencyListGraph import AdjacencyListGraph 
except ImportError:
    try:
        from src.core.AdjacencyListGraph import AdjacencyListGraph 
    except ImportError as e:
        raise ImportError(
            "Não foi possível importar AdjacencyListGraph. "
            "Ajuste o caminho do import conforme a estrutura do seu projeto."
        ) from e

from config.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

Neo4jService = None
try:
    from src.services.neo4j_service import Neo4jService 
except Exception:
    try:
        from src.services.neo4j_service import Neo4jService 
    except Exception:
        print(
            "Não foi possível importar src.services.neo4j_service. "
            "Tentando usar o driver 'neo4j' diretamente. "
            "Certifique-se de que 'neo4j' está instalado (pip install neo4j)."
        )
        


# ============== CONFIGURAÇÕES DO MODELO DE DADOS ==============
LABEL_AUTHOR = "Author"
LABEL_ISSUE = "Issue"
LABEL_PR = "PullRequest"
LABEL_COMMENT = "Comment"
LABEL_REVIEW = "Review"

REL_AUTHORED_COMMENT = "AUTHORED"  # Author -> Comment
REL_COMMENT_ON = "HAS_COMMENT"            # Comment -> Issue/PR
REL_CREATED = "CREATED"               # Author -> Issue/PR
REL_PERFORMED_REVIEW = "PERFORMED_REVIEW"  # Author -> Review
REL_HAS_REVIEW = "HAS_REVIEW"

# Pesos definidos pelo enunciado
WEIGHTS = {
    "COMMENT": 2,          # Comentário em issue ou pull request
    "ISSUE_COMMENTED": 3,  # Abertura de issue comentada por outro usuário
    "REVIEW": 4,           # Revisão/aprovação de pull request
    "MERGE": 5,            # Merge de pull request
}

# ============== CONSULTAS CYPHER (agora mais focadas) ==============
AUTHORS_QUERY = f"""
MATCH (a:{LABEL_AUTHOR})
RETURN id(a) AS id, coalesce(a.login, toString(id(a))) AS name
ORDER BY name
"""

# Query para "Comentário em issue ou pull request" (Peso 2)
COMMENT_ON_ISSUE_PR_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_AUTHORED_COMMENT}]->(comment:{LABEL_COMMENT})
MATCH (target: {LABEL_ISSUE}|{LABEL_PR})-[:{REL_COMMENT_ON}]->(comment)
MATCH (target)<-[:{REL_CREATED}]-(dst:{LABEL_AUTHOR})
WHERE src <> dst AND (target:{LABEL_ISSUE} OR target:{LABEL_PR})
RETURN id(src) AS srcId, id(dst) AS dstId
"""

# Query para "Abertura de issue comentada por outro usuário" (Peso 3)
ISSUE_COMMENTED_BY_OTHER_QUERY = f"""
MATCH (dst:{LABEL_AUTHOR})-[:{REL_CREATED}|OPENED]->(i:{LABEL_ISSUE})
MATCH (src:{LABEL_AUTHOR})-[:{REL_AUTHORED_COMMENT}|COMMENTED]->(c:{LABEL_COMMENT})
MATCH (i)-[:{REL_COMMENT_ON}|ON]->(c)
WHERE src <> dst
RETURN id(src) AS srcId, id(dst) AS dstId
"""

# Query para "Revisão/aprovação de pull request" (Peso 4)
PR_REVIEW_APPROVAL_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_PERFORMED_REVIEW}|REVIEWED|APPROVED]->(r:{LABEL_REVIEW})
MATCH (pr:{LABEL_PR})-[:{REL_HAS_REVIEW}|REVIEWS|FOR]->(r)
MATCH (pr)<-[:{REL_CREATED}|OPENED]-(dst:{LABEL_AUTHOR})
WHERE src <> dst
RETURN id(src) AS srcId, id(dst) AS dstId
"""

# Query para "Merge de pull request" (Peso 5)
PR_MERGE_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_PERFORMED_REVIEW}|REVIEWED|APPROVED]->(r:{LABEL_REVIEW})
MATCH (pr:{LABEL_PR})-[:{REL_HAS_REVIEW}|REVIEWS|FOR]->(r)
MATCH (pr)<-[:{REL_CREATED}|OPENED]-(dst:{LABEL_AUTHOR})
WHERE src <> dst AND pr.mergedAt IS NOT NULL
RETURN id(src) AS srcId, id(dst) AS dstId
"""

# ============== FUNÇÕES AUXILIARES ==============

def fetch_authors_and_edges(neo4j_service) -> tuple[dict[int, str], list[tuple[int, int, float]]]:
    """
    Busca autores e interações no Neo4j, processando as arestas e pesos em Python.
    Retorna:
      - idx_to_name: dict {indice_local: nome_autor}
      - edges: lista de arestas (u, v, peso) com índices locais
    """
    print("Buscando todos os autores...")
    authors_rows = neo4j_service.query(AUTHORS_QUERY)
    if not authors_rows:
        print("Nenhum autor encontrado no Neo4j.")
        return {}, []
    print(f"  Encontrados {len(authors_rows)} autores.")

    # Mapear id(neo4j) -> índice local (0, 1, 2...)
    id_to_index: dict[int, int] = {}
    idx_to_name: dict[int, str] = {}
    for idx, row in enumerate(authors_rows):
        neo4j_id = row["id"]
        name = row.get("name") or str(neo4j_id)
        id_to_index[neo4j_id] = idx
        idx_to_name[idx] = name

    # Dicionário para acumular pesos das arestas, usando IDs do Neo4j como chaves
    # {(src_neo4j_id, dst_neo4j_id): total_weight}
    weighted_edges_map: defaultdict[tuple[int, int], float] = defaultdict(float)

    # 1. Comentário em issue ou pull request (Peso 2)
    print("Buscando interações de 'Comentário em issue ou pull request' (Peso 2)...")
    comment_on_issue_pr_rows = neo4j_service.query(COMMENT_ON_ISSUE_PR_QUERY)
    for row in comment_on_issue_pr_rows:
        src_id = row["srcId"]
        dst_id = row["dstId"]
        # Certifica-se de que os IDs existem no mapeamento de autores
        if src_id in id_to_index and dst_id in id_to_index:
            weighted_edges_map[(src_id, dst_id)] += WEIGHTS["COMMENT"]
    print(f"  Encontradas {len(comment_on_issue_pr_rows)} interações de comentário.")

    # 2. Abertura de issue comentada por outro usuário (Peso 3)
    print("Buscando interações de 'Abertura de issue comentada por outro usuário' (Peso 3)...")
    issue_commented_rows = neo4j_service.query(ISSUE_COMMENTED_BY_OTHER_QUERY)
    for row in issue_commented_rows:
        src_id = row["srcId"]
        dst_id = row["dstId"]
        if src_id in id_to_index and dst_id in id_to_index:
            weighted_edges_map[(src_id, dst_id)] += WEIGHTS["ISSUE_COMMENTED"]
    print(f"  Encontradas {len(issue_commented_rows)} interações de issue comentada.")

    # 3. Revisão/aprovação de pull request (Peso 4)
    print("Buscando interações de 'Revisão/aprovação de pull request' (Peso 4)...")
    pr_review_approval_rows = neo4j_service.query(PR_REVIEW_APPROVAL_QUERY)
    for row in pr_review_approval_rows:
        src_id = row["srcId"]
        dst_id = row["dstId"]
        if src_id in id_to_index and dst_id in id_to_index:
            weighted_edges_map[(src_id, dst_id)] += WEIGHTS["REVIEW"]
    print(f"  Encontradas {len(pr_review_approval_rows)} interações de revisão/aprovação.")

    # 4. Merge de pull request (Peso 5)
    print("Buscando interações de 'Merge de pull request' (Peso 5)...")
    pr_merge_rows = neo4j_service.query(PR_MERGE_QUERY)
    for row in pr_merge_rows:
        src_id = row["srcId"]
        dst_id = row["dstId"]
        if src_id in id_to_index and dst_id in id_to_index:
            weighted_edges_map[(src_id, dst_id)] += WEIGHTS["MERGE"]
    print(f"  Encontradas {len(pr_merge_rows)} interações de merge.")

    # Converter os IDs do Neo4j para índices locais e formar a lista final de arestas
    edges: list[tuple[int, int, float]] = []
    for (src_neo4j_id, dst_neo4j_id), total_weight in weighted_edges_map.items():
        # As queries já filtram src <> dst, mas mantemos a verificação para robustez
        u = id_to_index[src_neo4j_id]
        v = id_to_index[dst_neo4j_id]
        if u != v:
            edges.append((u, v, total_weight))
        # else: print(f"[Debug] Auto-laço detectado/ignorado: {src_neo4j_id}") # Para depuração

    print(f"Total de {len(edges)} arestas ponderadas únicas formadas após agregação.")
    return idx_to_name, edges


def build_graph(vertex_count: int, edges: list[tuple[int, int, float]]) -> "AdjacencyListGraph":
    """
    Constrói o grafo de lista de adjacência a partir do número de vértices e arestas ponderadas.
    """
    st.info(f"Construindo grafo com {vertex_count} vértices e {len(edges)} arestas...")
    graph = AdjacencyListGraph(vertex_count)
    for u, v, w in edges:
        try:
            graph.addEdge(u, v, w)
        except Exception as e:
            st.warning(
                f"Falha ao adicionar aresta ({u}->{v}) peso {w}: {e}")
    st.success("Grafo construído com sucesso.")
    return graph


def display_graph_textual_streamlit(graph: "AdjacencyListGraph", idx_to_name: dict[int, str]) -> None:
    """
    Exibe a lista de adjacência do grafo em formato textual no Streamlit.
    """

    n = len(idx_to_name)
    if n == 0:
        st.warning("Nenhum autor para exibir.")
        return

    adj_list_str = []
    for u in range(n):
        if u < len(graph.adj_out):
            neighbors = graph.adj_out[u]
            pares = []
            sorted_neighbors = sorted(neighbors.items(), key=lambda item: item[1], reverse=True)
            for v, w in sorted_neighbors:
                nome_v = idx_to_name.get(v, f"Nó desconhecido ({v})")
                pares.append(f"{nome_v} (peso: {w})")
            
            node_name = idx_to_name.get(u, f"Nó desconhecido ({u})")
            if pares:
                adj_list_str.append(f"**{node_name}** aponta para: " + ", ".join(pares))
            else:
                adj_list_str.append(f"**{node_name}**: Não possui saídas.")
        else:
            adj_list_str.append(f"**Nó desconhecido ({u})**: (Índice fora do limite de adj_out)")

    st.subheader("Representação Textual da Lista de Adjacência")
    st.info("Cada linha representa um autor (nó) e seus vizinhos de saída, com os pesos das arestas.")

      # Legenda para os pesos
    st.markdown("---")
    st.subheader("Legenda dos Pesos das Interações:")
    st.write(
        f"- **Comentário em Issue/PR**: {WEIGHTS['COMMENT']} pontos (quando src comenta em Issue/PR criada por dst)"
    )
    st.write(
        f"- **Abertura de Issue Comentada**: {WEIGHTS['ISSUE_COMMENTED']} pontos (quando src comenta em Issue criada por dst)"
    )
    st.write(
        f"- **Revisão/Aprovação de PR**: {WEIGHTS['REVIEW']} pontos (quando src revisa/aprova PR criada por dst)"
    )
    st.write(
        f"- **Merge de PR**: {WEIGHTS['MERGE']} pontos (quando src revisa/aprova PR *mesclada* criada por dst)"
    )
    st.info("O peso exibido em cada aresta é o valor agregado total das interações entre os autores.")

  
    # Opção para baixar a lista de adjacência em TXT
    txt_content = "\n".join(adj_list_str)
    st.download_button(
        label="Baixar Lista de Adjacência (TXT)",
        data=txt_content.encode("utf-8"),
        file_name="adjacency_list.txt",
        mime="text/plain"
    )

    # Exibe a lista de adjacência em um st.dataframe ou st.text_area
    st.markdown("\n".join(adj_list_str))




def app():
    st.set_page_config(layout="wide")
    st.title("Análise de Grafo de Interações de Autores (Representação Textual)")

    st.markdown(
        """
        Este aplicativo busca interações entre autores em um repositório (comentários, revisões, merges)
        e constrói um grafo de lista de adjacência. Os pesos das arestas representam a força da interação.
        Devido à restrição de usar **apenas Streamlit** e nenhuma outra biblioteca de visualização,
        o grafo será exibido em um formato textual, listando as adjacências.
        """
    )

    neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    if neo4j_service is None:
        st.error("Serviço Neo4j não inicializado. Verifique as configurações e instalações.")
        return

    st.sidebar.header("Status da Conexão")
    try:
        neo4j_service.query("MATCH (n) RETURN count(n) AS nodeCount LIMIT 1")
        st.sidebar.success("Conectado ao Neo4j.")
    except Exception as e:
        st.sidebar.error(f"Falha ao conectar ao Neo4j: {e}")
        st.error("Verifique suas credenciais e se o Neo4j está rodando.")
        return

    if st.button("Gerar e Exibir Grafo"):
        st.spinner("Processando dados e construindo grafo... Isso pode levar um tempo.")
        try:
            idx_to_name, edges = fetch_authors_and_edges(neo4j_service)
            if not idx_to_name:
                st.warning("Nenhum nó (:Author) encontrado no Neo4j. Não é possível construir o grafo.")
                return

            vertex_count = len(idx_to_name)
            graph = build_graph(vertex_count, edges)

            display_graph_textual_streamlit(graph, idx_to_name)

        except Exception as e:
            st.error(f"Ocorreu um erro ao gerar o grafo: {e}")
        finally:
            if hasattr(neo4j_service, "close"):
                try:
                    neo4j_service.close()
                    st.sidebar.info("Conexão com Neo4j fechada.")
                except Exception as e:
                    st.sidebar.error(f"Erro ao fechar conexão Neo4j: {e}")


if __name__ == "__main__":
    app()
    