import sys
import os
import math
import random
import matplotlib.pyplot as plt
import streamlit as st

# ============== AJUSTE DE PATH ==============
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ============== IMPORTS DO PROJETO ==============
try:
    from src.core.AdjacencyListGraph import AdjacencyListGraph
except ImportError as e:
    raise ImportError("Não foi possível importar AdjacencyListGraph.") from e

from config.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

try:
    from src.services.neo4j_service import Neo4jService
except ImportError:
    from neo4j import GraphDatabase

    class Neo4jService:
        def __init__(self, uri, user, password):
            self.driver = GraphDatabase.driver(uri, auth=(user, password))
        def query(self, cypher):
            with self.driver.session() as s:
                return [dict(r) for r in s.run(cypher)]
        def close(self):
            self.driver.close()

# ============== CONSTANTES ==============
LABEL_AUTHOR = "Author"
LABEL_PR = "PullRequest"
LABEL_REVIEW = "Review"

REL_PERFORMED_REVIEW = "PERFORMED_REVIEW"
REL_HAS_REVIEW = "HAS_REVIEW"
REL_CREATED = "CREATED"

WEIGHT_REVIEW = 4

# Query principal
PR_REVIEW_APPROVAL_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_PERFORMED_REVIEW}|REVIEWED|APPROVED]->(r:{LABEL_REVIEW})
MATCH (pr:{LABEL_PR})-[:{REL_HAS_REVIEW}|REVIEWS|FOR]->(r)
MATCH (pr)<-[:{REL_CREATED}|OPENED]-(dst:{LABEL_AUTHOR})
WHERE src <> dst
RETURN id(src) AS srcId, id(dst) AS dstId,
       coalesce(src.login, toString(id(src))) AS srcName,
       coalesce(dst.login, toString(id(dst))) AS dstName
"""

# ============== FUNÇÕES ==============
def fetch_review_edges(neo4j_service):
    st.info("Buscando interações de review/aprovação no Neo4j...")
    rows = neo4j_service.query(PR_REVIEW_APPROVAL_QUERY)
    if not rows:
        st.warning("Nenhuma interação de review encontrada.")
        return {}, []

    authors = {}
    edges = []

    for row in rows:
        src_id = row["srcId"]
        dst_id = row["dstId"]
        src_name = row["srcName"]
        dst_name = row["dstName"]

        if src_id not in authors:
            authors[src_id] = src_name
        if dst_id not in authors:
            authors[dst_id] = dst_name

        edges.append((src_id, dst_id, WEIGHT_REVIEW))

    return authors, edges


def build_graph(authors, edges):
    id_to_index = {neo4j_id: idx for idx, neo4j_id in enumerate(authors.keys())}
    idx_to_name = {idx: name for idx, name in enumerate(authors.values())}
    g = AdjacencyListGraph(len(authors))
    for src_id, dst_id, w in edges:
        u, v = id_to_index[src_id], id_to_index[dst_id]
        g.addEdge(u, v, w)
    return g, idx_to_name


def draw_graph(graph, idx_to_name):
    """Desenha o grafo com layout de repulsão estilo teia de aranha (ajustado para grandes grafos)."""
    st.subheader("Visualização Gráfica das Interações de Review")

    n = len(idx_to_name)
    if n == 0:
        st.warning("Grafo vazio.")
        return

    # ================= PARÂMETROS MELHORADOS =================
    area = 2000000               # Aumente a "área lógica" — mais espaço para nós se repelirem
    k = math.sqrt(area / n) * 2 # Dobra o raio de repulsão base
    iterations = 800            # Mais iterações para estabilizar
    cooling = 0.95              # Menos resfriamento por iteração (movimento mais longo)
    max_step = k * 8            # Limite maior de deslocamento
    repulsion_factor = 5    # Força de repulsão multiplicada
    attraction_factor = 0.4     # Força de atração reduzida

    # ================= INICIALIZAÇÃO =================
    positions = {
        i: [random.uniform(-k, k), random.uniform(-k, k)]
        for i in range(n)
    }

    # ================= SIMULAÇÃO =================
    for _ in range(iterations):
        disp = {i: [0.0, 0.0] for i in range(n)}

        # --- Repulsão entre todos os pares ---
        for v in range(n):
            for u in range(v + 1, n):
                dx = positions[v][0] - positions[u][0]
                dy = positions[v][1] - positions[u][1]
                dist = math.sqrt(dx * dx + dy * dy) + 0.01
                force = repulsion_factor * (k * k) / dist
                disp[v][0] += (dx / dist) * force
                disp[v][1] += (dy / dist) * force
                disp[u][0] -= (dx / dist) * force
                disp[u][1] -= (dy / dist) * force

        # --- Atração nas arestas ---
        for u in range(n):
            for v, w in graph.adj_out[u].items():
                dx = positions[u][0] - positions[v][0]
                dy = positions[u][1] - positions[v][1]
                dist = math.sqrt(dx * dx + dy * dy) + 0.01
                force = attraction_factor * (dist * dist) / k
                disp[u][0] -= (dx / dist) * force
                disp[u][1] -= (dy / dist) * force
                disp[v][0] += (dx / dist) * force
                disp[v][1] += (dy / dist) * force

        # --- Atualiza posições ---
        for v in range(n):
            dx, dy = disp[v]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                step = min(max_step, dist)
                positions[v][0] += (dx / dist) * step
                positions[v][1] += (dy / dist) * step

        max_step *= cooling

    # ================= NORMALIZAÇÃO =================
    xs = [p[0] for p in positions.values()]
    ys = [p[1] for p in positions.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)

    scale = 10
    for i in positions:
        positions[i][0] = (positions[i][0] - (min_x + max_x) / 2) * scale
        positions[i][1] = (positions[i][1] - (min_y + max_y) / 2) * scale

    # ================= DESENHO =================
    plt.figure(figsize=(16, 12))
    plt.axis("off")

    # Arestas
    for u in range(n):
        for v, w in graph.adj_out[u].items():
            x1, y1 = positions[u]
            x2, y2 = positions[v]
            plt.arrow(
                x1, y1, x2 - x1, y2 - y1,
                head_width=0.4, head_length=0.6,
                fc="gray", ec="gray", alpha=0.5, length_includes_head=True
            )

    # Nós
    for i, (x, y) in positions.items():
        plt.scatter(x, y, s=250, color="#5DADE2", edgecolors="black", zorder=3)
        plt.text(x, y, idx_to_name[i], fontsize=8, ha="center", va="center", color="black")

    st.pyplot(plt)
    plt.clf()



# ============== STREAMLIT APP ==============
def app():
    st.set_page_config(layout="wide")
    st.title("🔎 Grafo de Interações de Review entre Autores")

    st.markdown(
        """
        Este aplicativo busca no **Neo4j** as interações de revisão e aprovação de Pull Requests.
        Cada nó representa um autor, e uma aresta direcionada (→) indica que o autor revisou
        uma PR criada por outro autor.  
        O peso da aresta representa a força da interação (padrão = 4 pontos por review).
        """
    )

    try:
        neo4j_service = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
    except Exception as e:
        st.error(f"Falha ao conectar ao Neo4j: {e}")
        return

    if st.button("Gerar Grafo de Reviews"):
        with st.spinner("Carregando dados e construindo grafo..."):
            authors, edges = fetch_review_edges(neo4j_service)
            if not authors:
                st.warning("Nenhum dado para exibir.")
                return

            graph, idx_to_name = build_graph(authors, edges)
            draw_graph(graph, idx_to_name)

            st.markdown("---")
            st.subheader("Lista de Adjacência (Resumo Textual)")
            for u in range(len(graph.adj_out)):
                nome_u = idx_to_name.get(u, f"Nó {u}")
                vizinhos = graph.adj_out[u]
                if vizinhos:
                    linha = ", ".join(f"{idx_to_name[v]} (peso {w})" for v, w in vizinhos.items())
                    st.write(f"**{nome_u} →** {linha}")
                else:
                    st.write(f"**{nome_u}**: sem saídas.")

    try:
        neo4j_service.close()
    except:
        pass


if __name__ == "__main__":
    app()
