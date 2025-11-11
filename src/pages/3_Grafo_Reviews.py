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

# ============== QUERY ==============
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


def draw_graph(graph, idx_to_name, indices_to_render):
    """Desenha o grafo aplicando o filtro de índices"""
    st.subheader("Visualização Gráfica das Interações de Review")

    if not indices_to_render:
        st.warning("Nenhum autor corresponde aos filtros selecionados.")
        return

    n = len(indices_to_render)

    # ================= PARÂMETROS DE REPULSÃO =================
    area = 2000000               # Aumente a "área lógica" — mais espaço para nós se repelirem
    k = math.sqrt(area / n) * 2 # Dobra o raio de repulsão base
    iterations = 800            # Mais iterações para estabilizar
    cooling = 0.95              # Menos resfriamento por iteração (movimento mais longo)
    max_step = k * 8            # Limite maior de deslocamento
    repulsion_factor = 20000        # Força de repulsão multiplicada
    attraction_factor = 0.4     # Força de atração reduzida

    # ================= INICIALIZAÇÃO =================
    positions = {i: [random.uniform(-k, k), random.uniform(-k, k)] for i in indices_to_render}

    # ================= SIMULAÇÃO =================
    for _ in range(iterations):
        disp = {i: [0.0, 0.0] for i in indices_to_render}

        # Repulsão
        for i, v in enumerate(indices_to_render):
            for j in range(i + 1, n):
                u = indices_to_render[j]
                dx = positions[v][0] - positions[u][0]
                dy = positions[v][1] - positions[u][1]
                dist = math.sqrt(dx * dx + dy * dy) + 0.01
                force = repulsion_factor * (k * k) / dist
                disp[v][0] += (dx / dist) * force
                disp[v][1] += (dy / dist) * force
                disp[u][0] -= (dx / dist) * force
                disp[u][1] -= (dy / dist) * force

        # Atração
        for u in indices_to_render:
            for v, w in graph.adj_out[u].items():
                if v in indices_to_render:
                    dx = positions[u][0] - positions[v][0]
                    dy = positions[u][1] - positions[v][1]
                    dist = math.sqrt(dx * dx + dy * dy) + 0.01
                    force = attraction_factor * (dist * dist) / k
                    disp[u][0] -= (dx / dist) * force
                    disp[u][1] -= (dy / dist) * force
                    disp[v][0] += (dx / dist) * force
                    disp[v][1] += (dy / dist) * force

        # Atualiza posições
        for v in indices_to_render:
            dx, dy = disp[v]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                step = min(max_step, dist)
                positions[v][0] += (dx / dist) * step
                positions[v][1] += (dy / dist) * step

        max_step *= cooling

    # Normalização
    xs = [positions[i][0] for i in indices_to_render]
    ys = [positions[i][1] for i in indices_to_render]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    scale = 10
    for i in indices_to_render:
        positions[i][0] = (positions[i][0] - (min_x + max_x) / 2) * scale
        positions[i][1] = (positions[i][1] - (min_y + max_y) / 2) * scale

    # Desenho
    plt.figure(figsize=(16, 12))
    plt.axis("off")

    # Arestas
    for u in indices_to_render:
        for v, w in graph.adj_out[u].items():
            if v in indices_to_render:
                x1, y1 = positions[u]
                x2, y2 = positions[v]
                plt.arrow(
                    x1, y1, x2 - x1, y2 - y1,
                    head_width=10000, head_length=10000,
                    fc="gray", ec="gray", alpha=0.5, length_includes_head=True
                )

    # Nós
    for i in indices_to_render:
        x, y = positions[i]
        plt.scatter(x, y, s=120, color="#5DADE2", edgecolors="black", zorder=3)
        plt.text(x, y, idx_to_name[i], fontsize=8, ha="center", va="center", color="black")

    st.pyplot(plt)
    plt.clf()


# ============== STREAMLIT APP ==============
def app():
    st.set_page_config(layout="wide")
    st.title("🔎 Grafo de Interações de Review entre Autores")

    st.sidebar.header("Filtros")
    filter_with_edges = st.sidebar.checkbox(
        "Mostrar apenas autores com interações de saída", value=True
    )
    limit = st.sidebar.number_input(
        "Limitar autores (0 = sem limite, Top N por atividade)", min_value=0, value=0, step=10
    )

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

            # --- FILTRO ---
            author_activity = []
            for u in range(len(idx_to_name)):
                total_weight = sum(graph.adj_out[u].values()) if u < len(graph.adj_out) and graph.adj_out[u] else 0
                author_activity.append((u, total_weight))

            if filter_with_edges:
                author_activity = [item for item in author_activity if item[1] > 0]

            author_activity.sort(key=lambda item: item[1], reverse=True)

            if limit > 0:
                author_activity = author_activity[:limit]

            indices_to_render = [u for u, _ in author_activity]

            # --- Desenho do grafo filtrado ---
            draw_graph(graph, idx_to_name, indices_to_render)

            # --- Lista de adjacência filtrada ---
            st.markdown("---")
            st.subheader("Lista de Adjacência (Mesma Ordem do SVG)")
            for u in indices_to_render:
                nome_u = idx_to_name.get(u, f"Nó {u}")
                vizinhos = graph.adj_out[u]
                if vizinhos:
                    vizinhos_ordenados = sorted(vizinhos.items(), key=lambda item: item[1], reverse=True)
                    linha = ", ".join(f"{idx_to_name[v]} (peso {w})" for v, w in vizinhos_ordenados)
                    st.write(f"**{nome_u} →** {linha}")
                else:
                    st.write(f"**{nome_u}**: sem saídas.")

    try:
        neo4j_service.close()
    except:
        pass


if __name__ == "__main__":
    app()
