import streamlit as st
from collections import defaultdict
import streamlit.components.v1 as components
from typing import List, Tuple, Optional 
import math
import pandas as pd
import matplotlib.pyplot as plt

from pages._shared_queries import (WEIGHTS, AUTHORS_QUERY, COMMENT_ON_ISSUE_PR_QUERY)
from src.services.adjacency_list_service import display_adjacency_list_svg_streamlit
from src.services.adjacency_matrix_service import df_to_svg

import random                   

try:
    from src.core.AdjacencyListGraph import AdjacencyListGraph
    from src.core.AdjacencyMatrixGraph import AdjacencyMatrixGraph
    from src.core.AbstractGraph import AbstractGraph 
except ImportError as e:
    st.error(f"Erro crítico ao importar classes de Grafo: {e}")
    st.stop()

try:
    from src.utils.neo4j_connector import get_neo4j_service
except ImportError:
    st.error("Não foi possível encontrar 'src.utils.neo4j_connector'. Verifique o arquivo.")
    st.stop()

try:
    from src.utils.streamlit_helpers import draw_graph_api_sidebar
except ImportError:
    st.error("Não foi possível encontrar 'src.utils.streamlit_helpers'. Crie o arquivo.")
    st.stop()

import src.services.graph_service as graph_service

# ============== FUNÇÕES DE DADOS E GRAFO ==============

def fetch_authors_and_edges(neo4j_service) -> tuple[dict[int, str], list[tuple[int, int, float]]]:
    print("Buscando todos os autores...")
    authors_rows = neo4j_service.query(AUTHORS_QUERY)
    if not authors_rows:
        print("Nenhum autor encontrado no Neo4j.")
        return {}, []
    print(f"   Encontrados {len(authors_rows)} autores.")
    id_to_index: dict[int, int] = {}
    idx_to_name: dict[int, str] = {}
    for idx, row in enumerate(authors_rows):
        neo4j_id = row["id"]
        name = row.get("name") or str(neo4j_id)
        id_to_index[neo4j_id] = idx
        idx_to_name[idx] = name
    weighted_edges_map: defaultdict[tuple[int, int], float] = defaultdict(float)
    print("Buscando interações de 'Comentário em issue ou pull request' (Peso 2)...")
    comment_on_issue_pr_rows = neo4j_service.query(COMMENT_ON_ISSUE_PR_QUERY)
    for row in comment_on_issue_pr_rows:
        if row["srcId"] in id_to_index and row["dstId"] in id_to_index:
            weighted_edges_map[(row["srcId"], row["dstId"])] += WEIGHTS["COMMENT"]
    print(f"   Encontradas {len(comment_on_issue_pr_rows)} interações de comentário.")
    edges: list[tuple[int, int, float]] = []
    for (src_neo4j_id, dst_neo4j_id), total_weight in weighted_edges_map.items():
        u = id_to_index[src_neo4j_id]
        v = id_to_index[dst_neo4j_id]
        if u != v:
            edges.append((u, v, total_weight))
    print(f"Total de {len(edges)} arestas ponderadas únicas formadas após agregação.")
    return idx_to_name, edges    

def build_graph(impl_class: type[AbstractGraph], vertex_count: int, edges: list[tuple[int, int, float]]) -> AbstractGraph:
    """Constrói um grafo usando a classe de implementação fornecida."""
    print(f"Construindo grafo com implementação: {impl_class.__name__}")
    graph = impl_class(vertex_count)
    for u_idx, v_idx, weight in edges:
        graph.addEdge(u_idx, v_idx, weight)
    return graph

# ============== NOVA FUNÇÃO DE VISUALIZAÇÃO ==============

def draw_graph(graph: AbstractGraph, idx_to_name: dict, indices_to_render: list):
    """
    Desenha o grafo usando a API Abstrata,
    independente da implementação.
    """
    st.subheader("Visualização Gráfica")

    if not indices_to_render:
        st.warning("Nenhum autor corresponde aos filtros selecionados.")
        return

    n = len(indices_to_render)

    # ================= PARÂMETROS DE REPULSÃO =================
    area = 2000000               
    k = math.sqrt(area / n) * 2 
    iterations = 800            
    cooling = 0.95              
    max_step = k * 8            
    repulsion_factor = 20000        
    attraction_factor = 0.4     

    # ================= INICIALIZAÇÃO =================
    positions = {i: [random.uniform(-k, k), random.uniform(-k, k)] for i in indices_to_render}

    # ================= SIMULAÇÃO =================
    progress_bar = st.progress(0, text="Calculando...")
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

        # Atração 
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

    # Nós
    for i in indices_to_render:
        x, y = positions[i]
        plt.scatter(x, y, s=120, color="#5DADE2", edgecolors="black", zorder=3)
        plt.text(x, y, idx_to_name[i], fontsize=8, ha="center", va="center", color="black")

    st.pyplot(plt)
    plt.clf()


# ============== FUNÇÃO APP ==============

def app():
    st.title("Grafo de Interações entre Autores (Comentários)")
    st.markdown("Use esta página para carregar dados e analisar as interações.")

    PAGE_ID = "comentarios" 
    
    if 'current_graph_id' not in st.session_state:
        st.session_state.current_graph_id = PAGE_ID

    if st.session_state.current_graph_id != PAGE_ID:
        print(f"Mudando de página, limpando grafo antigo ({st.session_state.current_graph_id})...")
        st.session_state.graph_obj = None
        st.session_state.vertex_names_list = []
        st.session_state.name_to_idx_map = {}
        st.session_state.idx_to_name_map = {}
        st.session_state.current_graph_id = PAGE_ID

    # --- ESCOLHA DA IMPLEMENTAÇÃO ---
    st.sidebar.header("Configuração da Geração")
    impl_choice = st.sidebar.selectbox(
        "Escolha a implementação do Grafo:",
        ("Lista de Adjacência", "Matriz de Adjacência"),
        key=f"{PAGE_ID}_impl_choice" 
    )
    
    # --- FILTROS DE VISUALIZAÇÃO ---
    st.sidebar.header("Opções de Filtro (Visualização)")
    filter_with_edges = st.sidebar.checkbox("Mostrar apenas autores com interações", value=True, key=f"{PAGE_ID}_filter_edges")
    limit = st.sidebar.number_input("Limitar autores (0 = sem limite)", min_value=0, value=0, step=10, key=f"{PAGE_ID}_limit")

    # --- LÓGICA DE CONEXÃO ---
    try:
        neo4j_service = get_neo4j_service()
    except Exception as e:
        st.error(f"Erro ao obter conexão com Neo4j: {e}")
        st.stop()

    if st.button("Gerar e Analisar Grafo"):
        with st.spinner("Buscando dados e construindo grafo..."):
            try:
                idx_to_name, edges = fetch_authors_and_edges(neo4j_service)
                if not idx_to_name:
                    st.warning("Nenhum nó (:Author) encontrado no Neo4j.")
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

            except Exception as e:
                st.error(f"Ocorreu um erro ao gerar o grafo: {e}")
                st.exception(e)
                st.session_state.graph_obj = None 

    
    # --- RENDERIZAÇÃO ---
    
    if st.session_state.get("graph_obj") is not None:
        graph = st.session_state.graph_obj
        idx_to_name = st.session_state.idx_to_name_map
        
        st.success(f"Grafo gerado com sucesso usando: **{type(graph).__name__}**")

        # --- LÓGICA DE FILTRO ---
        author_activity = []
        for i in range(graph.getVertexCount()):
            out_degree = graph.getVertexOutDegree(i)
            author_activity.append((i, out_degree))

        if filter_with_edges:
            author_activity = [item for item in author_activity if item[1] > 0]
        author_activity.sort(key=lambda item: item[1], reverse=True)
        if limit > 0:
            author_activity = author_activity[:limit]
        indices_to_render_internal = [i for i, degree in author_activity]
        
        # --- RENDERIZAÇÃO EM ABAS ---
        st.divider()
        st.header("Representações do Grafo")
        
        tab1, tab2, tab3 = st.tabs(["Visualização (Força)", "Lista de Adjacência", "Matriz de Adjacência"])

        with tab1:
            st.info("Visualização do grafo filtrado:")
            if not indices_to_render_internal:
                st.warning("Nenhum autor corresponde aos filtros selecionados.")
            else:
                draw_graph(graph, idx_to_name, indices_to_render_internal)

        with tab2:
            st.info("Representação do grafo completo como Lista de Adjacência.")
            adj_list_data = graph_service.get_adjacency_list()
            
            display_adjacency_list_svg_streamlit(graph=graph, idx_to_name=idx_to_name, indices_to_render=indices_to_render_internal)

        with tab3:
            st.info("Representação do grafo completo como Matriz de Adjacência.")
            matrix_data = graph_service.get_adjacency_matrix()
            matrix_labels = [idx_to_name.get(i, str(i)) for i in range(len(matrix_data))]
            df = pd.DataFrame(matrix_data, columns=matrix_labels, index=matrix_labels)
            
            if indices_to_render_internal:
                selected = [idx_to_name[i] for i in indices_to_render_internal]
                df = df.loc[selected, selected]

            # Mostra dataframe
            st.dataframe(df)

            # Converte para SVG
            svg = df_to_svg(df)
            
            # Botão para baixar
            st.download_button(
                "Baixar matriz (SVG)",
                data=svg.encode("utf-8"),
                file_name="matriz_adjacencia.svg",
                mime="image/svg+xml",
            )

            st.markdown("---")
            st.subheader("Legenda dos Pesos")
            st.write(f"- Comentário em Issue/PR: {WEIGHTS.get('COMMENT', 'N/A')}")
            st.write(f"- Abertura de Issue comentada: {WEIGHTS.get('ISSUE_COMMENTED', 'N/A')}")
            st.write(f"- Revisão/Aprovação de PR: {WEIGHTS.get('REVIEW', 'N/A')}")
            st.write(f"- Merge de PR: {WEIGHTS.get('MERGE', 'N/A')}")

    else:
        st.info("Escolha uma implementação e clique em 'Gerar e Analisar Grafo' para carregar os dados.")

    
    # --- CHAMA O HELPER DA SIDEBAR ---
    draw_graph_api_sidebar()


if __name__ == "__main__":
    app()