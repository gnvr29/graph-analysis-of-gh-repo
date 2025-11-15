import sys
import os
import math
import random
import matplotlib.pyplot as plt
import streamlit as st
import pandas as pd
from collections import defaultdict

# ============== AJUSTE DE PATH ==============
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# ============== IMPORTS DO PROJETO ==============
try:
    # Importa AMBAS as implementações
    from src.core.AdjacencyListGraph import AdjacencyListGraph
    from src.core.AdjacencyMatrixGraph import AdjacencyMatrixGraph 
    from src.core.AbstractGraph import AbstractGraph # Importa o "Pai"
except ImportError as e:
    st.error(f"Erro crítico ao importar classes de Grafo: {e}")
    st.stop()

try:
    # Usa o conector padrão
    from src.utils.neo4j_connector import get_neo4j_service
except ImportError:
    st.error("Não foi possível encontrar 'src.utils.neo4j_connector'. Verifique o arquivo.")
    st.stop()
    
try:
    # Importa o helper da sidebar
    from src.utils.streamlit_helpers import draw_graph_api_sidebar
except ImportError:
    st.error("Não foi possível encontrar 'src.utils.streamlit_helpers'. Crie o arquivo.")
    st.stop()

# Importa o service para as abas
import src.services.graph_service as graph_service


# ============== CONSTANTES (Sem alterações) ==============
LABEL_AUTHOR = "Author"
LABEL_PR = "PullRequest"
LABEL_REVIEW = "Review"
REL_PERFORMED_REVIEW = "PERFORMED_REVIEW"
REL_HAS_REVIEW = "HAS_REVIEW"
REL_CREATED = "CREATED"
WEIGHT_REVIEW = 4

# ============== QUERY (Sem alterações) ==============
PR_REVIEW_APPROVAL_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_PERFORMED_REVIEW}|REVIEWED|APPROVED]->(r:{LABEL_REVIEW})
MATCH (pr:{LABEL_PR})-[:{REL_HAS_REVIEW}|REVIEWS|FOR]->(r)
MATCH (pr)<-[:{REL_CREATED}|OPENED]-(dst:{LABEL_AUTHOR})
WHERE src <> dst
RETURN id(src) AS srcId, id(dst) AS dstId,
       coalesce(src.login, toString(id(src))) AS srcName,
       coalesce(dst.login, toString(id(dst))) AS dstName
"""

# ============== FUNÇÕES (Modificadas) ==============
def fetch_review_edges(neo4j_service):
    # ... (Sua função está correta, sem alterações) ...
    st.info("Buscando interações de review/aprovação no Neo4j...")
    rows = neo4j_service.query(PR_REVIEW_APPROVAL_QUERY)
    if not rows:
        st.warning("Nenhuma interação de review encontrada.")
        return {}, [], {}

    authors_id_to_name = {}
    name_to_id = {}
    edges_data = []
    
    id_map = {}
    current_idx = 0
    
    authors_neo4j_id_to_idx = {}
    idx_to_name_map = {}
    
    edges = []

    for row in rows:
        src_id = row["srcId"]
        dst_id = row["dstId"]
        src_name = row["srcName"]
        dst_name = row["dstName"]

        if src_id not in authors_neo4j_id_to_idx:
            authors_neo4j_id_to_idx[src_id] = current_idx
            idx_to_name_map[current_idx] = src_name
            current_idx += 1
            
        if dst_id not in authors_neo4j_id_to_idx:
            authors_neo4j_id_to_idx[dst_id] = current_idx
            idx_to_name_map[current_idx] = dst_name
            current_idx += 1

        u = authors_neo4j_id_to_idx[src_id]
        v = authors_neo4j_id_to_idx[dst_id]
        
        edges.append((u, v, WEIGHT_REVIEW))

    return idx_to_name_map, edges


def build_graph(impl_class: type[AbstractGraph], vertex_count: int, edges: list[tuple[int, int, float]]) -> AbstractGraph:
    """Constrói um grafo usando a classe de implementação fornecida."""
    st.info(f"Construindo grafo ({impl_class.__name__}) com {vertex_count} vértices e {len(edges)} arestas...")
    graph = impl_class(vertex_count)
    for u, v, w in edges:
        try:
            graph.addEdge(u, v, w)
        except Exception as e:
            st.warning(f"Falha ao adicionar aresta ({u}->{v}) peso {w}: {e}")
    st.success("Grafo construído com sucesso.")
    return graph


def draw_graph(graph: AbstractGraph, idx_to_name: dict, indices_to_render: list):
    """
    Desenha o grafo (layout de força) usando a API Abstrata,
    independente da implementação.
    """
    st.subheader("Visualização Gráfica (Layout de Força)")

    if not indices_to_render:
        st.warning("Nenhum autor corresponde aos filtros selecionados.")
        return

    n = len(indices_to_render)

    # ================= PARÂMETROS DE REPULSÃO (Sem alterações) =================
    area = 2000000               
    k = math.sqrt(area / n) * 2 
    iterations = 800            
    cooling = 0.95              
    max_step = k * 8            
    repulsion_factor = 20000        
    attraction_factor = 0.4     

    # ================= INICIALIZAÇÃO  =================
    positions = {i: [random.uniform(-k, k), random.uniform(-k, k)] for i in indices_to_render}

    # ================= SIMULAÇÃO =================
    
    # --- CORREÇÃO DA BARRA DE PROGRESSO ---
    progress_bar = st.progress(0, text="Calculando layout de força...")
    
    for iter_num in range(iterations):
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

        for u in indices_to_render:
            for v in indices_to_render: 
                if graph.hasEdge(u, v): 
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
        if (iter_num + 1) % (iterations // 20) == 0:
             progress_bar.progress((iter_num + 1) / iterations, text=f"Calculando layout: {iter_num+1}/{iterations} iterações")

    progress_bar.empty()
    # --- FIM DA CORREÇÃO ---

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
    st.success("Layout calculado. Desenhando gráfico...")
    plt.figure(figsize=(16, 12))
    plt.axis("off")

    # Arestas
    for u in indices_to_render:
        for v in indices_to_render:
            if graph.hasEdge(u, v): 
                x1, y1 = positions[u]
                x2, y2 = positions[v]
                plt.arrow(
                    x1, y1, x2 - x1, y2 - y1,
                    head_width=10000, head_length=10000,
                    fc="gray", ec="gray", alpha=0.5, length_includes_head=True
                )

    # Nós (Sem alterações)
    for i in indices_to_render:
        x, y = positions[i]
        plt.scatter(x, y, s=120, color="#5DADE2", edgecolors="black", zorder=3)
        plt.text(x, y, idx_to_name[i], fontsize=8, ha="center", va="center", color="black")

    st.pyplot(plt)
    plt.clf()


# ============== STREAMLIT APP (Modificado) ==============
def app():
    st.title("🔎 Grafo de Interações de Review entre Autores")

    # --- NOVO: GERENCIAMENTO DE ESTADO POR PÁGINA ---
    PAGE_ID = "reviews" # ID Único para esta página
    
    if 'current_graph_id' not in st.session_state:
        st.session_state.current_graph_id = PAGE_ID

    # Se o ID na sessão não for o ID desta página, limpe o grafo antigo
    if st.session_state.current_graph_id != PAGE_ID:
        print(f"Mudando de página, limpando grafo antigo ({st.session_state.current_graph_id})...")
        st.session_state.graph_obj = None
        st.session_state.vertex_names_list = []
        st.session_state.name_to_idx_map = {}
        st.session_state.idx_to_name_map = {}
        st.session_state.current_graph_id = PAGE_ID
    # --- FIM DO GERENCIAMENTO DE ESTADO ---

    # --- ESCOLHA DA IMPLEMENTAÇÃO ---
    st.sidebar.header("Configuração da Geração")
    impl_choice = st.sidebar.selectbox(
        "Escolha a implementação do Grafo:",
        ("Lista de Adjacência", "Matriz de Adjacência"),
        key=f"{PAGE_ID}_impl_choice" # Chave única
    )

    # --- FILTROS (Sem alterações) ---
    st.sidebar.header("Filtros")
    filter_with_edges = st.sidebar.checkbox(
        "Mostrar apenas autores com interações de saída", value=True, key=f"{PAGE_ID}_filter_edges"
    )
    limit = st.sidebar.number_input(
        "Limitar autores (0 = sem limite, Top N por atividade)", min_value=0, value=0, step=10, key=f"{PAGE_ID}_limit"
    )

    st.markdown(
        """
        Este aplicativo busca no Neo4j as interações de revisão e aprovação de Pull Requests.
        O peso da aresta representa a força da interação (padrão = 4 pontos por review).
        """
    )

    # --- Conexão ---
    try:
        neo4j_service = get_neo4j_service()
    except Exception as e:
        st.error(f"Falha ao conectar ao Neo4j: {e}")
        st.stop()

    if st.button("Gerar Grafo de Reviews"):
        with st.spinner("Carregando dados e construindo grafo..."):
            
            idx_to_name, edges = fetch_review_edges(neo4j_service)
            if not idx_to_name:
                st.warning("Nenhum dado para exibir.")
                st.session_state.graph_obj = None 
                st.session_state.vertex_names_list = []
                st.session_state.name_to_idx_map = {}
                st.session_state.idx_to_name_map = {}
                return
            
            vertex_count = len(idx_to_name)

            if impl_choice == "Lista de Adjacência":
                impl_class = AdjacencyListGraph
            else:
                impl_class = AdjacencyMatrixGraph

            graph = build_graph(impl_class, vertex_count, edges)
            
            # --- Armazenar no Session State ---
            st.session_state.graph_obj = graph
            st.session_state.name_to_idx_map = {name: idx for idx, name in idx_to_name.items()}
            st.session_state.vertex_names_list = sorted(list(idx_to_name.values()))
            st.session_state.idx_to_name_map = idx_to_name 
            st.session_state.current_graph_id = PAGE_ID 
            

    # --- RENDERIZAÇÃO ---
    if st.session_state.get("graph_obj") is not None:
        graph = st.session_state.graph_obj
        idx_to_name = st.session_state.idx_to_name_map
        
        st.success(f"Grafo gerado com sucesso usando: **{type(graph).__name__}**")

        # --- FILTRO ---
        author_activity = []
        for u in range(graph.getVertexCount()):
            total_weight = 0
            for v in range(graph.getVertexCount()):
                if graph.hasEdge(u, v):
                    total_weight += graph.getEdgeWeight(u, v)
            author_activity.append((u, total_weight))

        if filter_with_edges:
            author_activity = [item for item in author_activity if item[1] > 0]
        author_activity.sort(key=lambda item: item[1], reverse=True)
        if limit > 0:
            author_activity = author_activity[:limit]
        indices_to_render = [u for u, _ in author_activity]
        
        # --- RENDERIZAÇÃO EM ABAS ---
        st.divider()
        st.header("Representações do Grafo")
        
        tab1, tab2, tab3 = st.tabs(["Visualização (Força)", "Lista de Adjacência", "Matriz de Adjacência"])

        with tab1:
            if not indices_to_render:
                st.warning("Nenhum autor corresponde aos filtros selecionados.")
            else:
                draw_graph(graph, idx_to_name, indices_to_render)

        with tab2:
            st.info("Representação do grafo completo como Lista de Adjacência.")
            adj_list_data = graph_service.get_adjacency_list()
            readable_list = {idx_to_name.get(i, str(i)): {idx_to_name.get(v, str(v)): w for v, w in neighbors.items()} 
                             for i, neighbors in enumerate(adj_list_data) if neighbors}
            st.json(readable_list)

        with tab3:
            st.info("Representação do grafo completo como Matriz de Adjacência.")
            matrix_data = graph_service.get_adjacency_matrix()
            matrix_labels = [idx_to_name.get(i, str(i)) for i in range(len(matrix_data))]
            df = pd.DataFrame(matrix_data, columns=matrix_labels, index=matrix_labels)
            st.dataframe(df, height=600)
    
    else:
        st.info("Escolha uma implementação e clique em 'Gerar Grafo de Reviews' para carregar os dados.")


    # --- CHAMA O HELPER DA SIDEBAR ---
    draw_graph_api_sidebar()


if __name__ == "__main__":
    app()