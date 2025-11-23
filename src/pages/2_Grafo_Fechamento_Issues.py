import streamlit as st
import pandas as pd

from src.core.AdjacencyListGraph import AdjacencyListGraph
from src.core.AdjacencyMatrixGraph import AdjacencyMatrixGraph
from src.core.AbstractGraph import AbstractGraph 
import src.services.graph_service as graph_service

# Importamos a função compartilhada que agora sabe buscar ISSUE_CLOSED
from src.services.shared_queries import fetch_authors_and_edges

from src.services.adjacency_list_service import display_adjacency_lists_streamlit
from src.services.adjacency_matrix_service import df_to_svg
from src.utils.neo4j_connector import get_neo4j_service
from src.utils.streamlit_helpers import draw_graph_api_sidebar
from src.utils.streamlit_filters import visualization_filters

# ============== FUNÇÃO APP ==============
def app():
    st.title("Grafo: Fechamento de Issues")
    st.markdown("""
    **Descrição:** Este grafo representa a relação onde um usuário fecha a issue criada por outro.
    
    * **Origem (Source):** Usuário que fechou a issue.
    * **Destino (Target):** Usuário que criou a issue.
    * **Peso:** Quantidade de issues fechadas.
    """)

    PAGE_ID = "fechamento_issues" 
    ACTIVE_GRAPH_KEY = "graph_obj" 
    FULL_GRAPH_KEY = f"full_{PAGE_ID}_obj"
    FILTER_STATE_KEY = f"{PAGE_ID}_current_filter_state"
    
    if 'current_graph_id' not in st.session_state:
        st.session_state.current_graph_id = PAGE_ID

    if st.session_state.current_graph_id != PAGE_ID:
        print(
            f"Mudando de página, limpando grafo antigo ({st.session_state.current_graph_id})...")
        st.session_state[ACTIVE_GRAPH_KEY] = None
        st.session_state[FULL_GRAPH_KEY] = None
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
    st.session_state[f"{PAGE_ID}_current_author_limit"] = limit
    
    current_filter_state = (filter_with_edges, limit)
    
    # --- LÓGICA DE CONEXÃO ---
    try:
        neo4j_service = get_neo4j_service()
    except Exception as e:
        st.error(f"Erro ao obter conexão com Neo4j: {e}")
        st.stop()

    if st.button("Gerar e Analisar Grafo"):
        with st.spinner("Buscando dados de fechamento de issues e construindo grafo..."):
            try:
                # 1. Busca dados
                idx_to_name_full, edges = fetch_authors_and_edges(
                    neo4j_service, enabled_interaction_types={"ISSUE_CLOSED"})
                
                if not idx_to_name_full:
                    st.warning("Nenhum autor encontrado.")
                    # Limpa estados
                    for key in [ACTIVE_GRAPH_KEY, FULL_GRAPH_KEY, 'vertex_names_list', 'name_to_idx_map', 'full_idx_to_name_map']:
                        st.session_state[key] = None if key.endswith('obj') or key.endswith('map') else []
                    return

                vertex_count_full = len(idx_to_name_full)
                
                # 2. Constrói o Grafo COMPLETO
                if impl_choice == "Lista de Adjacência":
                    impl_class = AdjacencyListGraph
                else:
                    impl_class = AdjacencyMatrixGraph
                
                full_graph = graph_service.build_graph(
                    impl_class, vertex_count_full, edges)

                # 3. Armazena o Grafo Completo e o mapeamento completo no Session State
                st.session_state[FULL_GRAPH_KEY] = full_graph
                st.session_state.full_idx_to_name_map = idx_to_name_full 
                st.session_state.total_vertex_count = vertex_count_full 
                st.session_state.current_graph_id = PAGE_ID
                
                # Força reconstrução do ativo na próxima iteração
                st.session_state[ACTIVE_GRAPH_KEY] = None
                st.session_state[FILTER_STATE_KEY] = None 

            except Exception as e:
                st.error(f"Ocorreu um erro ao gerar o grafo: {e}")
                st.exception(e)
                st.session_state[ACTIVE_GRAPH_KEY] = None 

    
    # --- RENDERIZAÇÃO E FILTRAGEM --- 
    full_graph = st.session_state.get(FULL_GRAPH_KEY)
    idx_to_name_full = st.session_state.get("full_idx_to_name_map")

    if full_graph is not None and st.session_state.current_graph_id == PAGE_ID:
        
        if st.session_state.get(ACTIVE_GRAPH_KEY) is None or st.session_state.get(FILTER_STATE_KEY) != current_filter_state:

            # 1. Lógica de Filtro: Obtém a lista de índices ORIGINAIS a serem incluídos
            indices_to_render_original = visualization_filters(
                graph=full_graph, 
                filter_with_edges=filter_with_edges, 
                limit=limit, 
                idx_to_name_full=idx_to_name_full
            )
            
            # 2. Constrói o Grafo ATIVO/FILTRADO (apenas se houver vértices para renderizar)
            if indices_to_render_original:
                active_graph = graph_service.build_filtered_graph(
                    full_graph=full_graph, 
                    indices_to_include=indices_to_render_original
                )
                st.session_state[ACTIVE_GRAPH_KEY] = active_graph
                
                # 3. Cria o novo mapeamento (Novo Índice -> Nome)
                new_idx_to_name_map = {
                    new_idx: idx_to_name_full[original_idx] 
                    for new_idx, original_idx in enumerate(indices_to_render_original)
                }
                st.session_state.idx_to_name_map = new_idx_to_name_map
                st.session_state.indices_to_render_internal = list(new_idx_to_name_map.keys())
            else:
                # Caso não haja vértices após a filtragem
                st.session_state[ACTIVE_GRAPH_KEY] = None
                st.session_state.idx_to_name_map = {}
                st.session_state.indices_to_render_internal = []
                
            st.session_state[FILTER_STATE_KEY] = current_filter_state

        # Pega o grafo ATIVO para renderização e análise
        graph = st.session_state.get(ACTIVE_GRAPH_KEY)
        idx_to_name = st.session_state.get("idx_to_name_map", {})
        indices_to_render_internal = st.session_state.get("indices_to_render_internal", [])
        total_vertex_count = st.session_state.get("total_vertex_count", 0)

        # Se o grafo ativo não for None
        if graph:
            st.success(
                f"Grafo ativo (filtrado) gerado com sucesso usando: **{type(graph).__name__}**")

            # A contagem de vértices é do grafo ATIVO/FILTRADO
            current_vertex_count = graph.getVertexCount()

            # --- RENDERIZAÇÃO EM ABAS ---
            st.divider()
            st.header("Representações do Grafo")

            tab1, tab2, tab3 = st.tabs(
                ["Visualização", "Lista de Adjacência", "Matriz de Adjacência"])

            with tab1:
                st.info(f"Visualização do grafo filtrado ({current_vertex_count} de {total_vertex_count} vértices):")
                
                highlight_vertex = st.session_state.get("new_vertices", set())
                
                graph_service.draw_graph(
                    graph, 
                    idx_to_name, 
                    indices_to_render_internal, 
                    highlight_edges=st.session_state.get("new_edges", set()),
                    highlight_vertex=highlight_vertex
                )
            
            with tab2:
                st.info(f"Representação (Lista de Adjacência) - {current_vertex_count} vértices no grafo ativo.")

                display_adjacency_lists_streamlit(
                    graph=graph, 
                    idx_to_name=idx_to_name, 
                    indices_to_render=indices_to_render_internal 
                )

            with tab3:
                # O get_adjacency_matrix e o get_vertex_count agora operam no grafo ATIVO/FILTRADO
                st.info(f"Representação (Matriz de Adjacência) - Matriz de {current_vertex_count}x{current_vertex_count}.")

                matrix_data = graph_service.get_adjacency_matrix()
                
                matrix_labels = [idx_to_name.get(i, str(i))
                                 for i in indices_to_render_internal]
                                 
                df = pd.DataFrame(
                    matrix_data, columns=matrix_labels, index=matrix_labels)
                
                st.dataframe(df)
                
                svg = df_to_svg(df)
                st.download_button("Baixar matriz (SVG)", data=svg.encode("utf-8"), file_name="matriz_fechamento.svg", mime="image/svg+xml")
        
        else:
             st.warning("Nenhum autor corresponde aos filtros selecionados. Ajuste os filtros.")


    else:
        st.info("Escolha uma implementação e clique em 'Gerar e Analisar Grafo' para carregar os dados.")

    draw_graph_api_sidebar()

if __name__ == "__main__":
    app()