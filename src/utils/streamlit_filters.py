import streamlit as st
from src.core.AbstractGraph import AbstractGraph

def visualization_filters (graph: AbstractGraph): 
    # A lógica de filtragem de limite (`limit`) e autores ativos (`filter_with_edges`)
    # foi completamente delegada à consulta Neo4j (fetch_authors).
    # Esta função agora atua apenas como um finalizador de estado para o Streamlit.
    
    indices_to_render_internal = list(range(graph.getVertexCount()))
    
    # Prepara listas e mapeamentos para o Streamlit (Sidebar e Visualização)
    filtered_vertex_names_list = []
    filtered_name_to_idx_map = {}

    for original_idx in indices_to_render_internal:
        # Pega o nome do autor do mapa original
        author_name = st.session_state.idx_to_name_map[original_idx]
        filtered_vertex_names_list.append(author_name)
        # Mapeia o nome do autor filtrado para o seu índice ORIGINAL no grafo.
        filtered_name_to_idx_map[author_name] = original_idx

    # Atualiza os estados da sessão que serão usados pela sidebar e renderização
    st.session_state.vertex_names_list = sorted(filtered_vertex_names_list)
    st.session_state.name_to_idx_map = filtered_name_to_idx_map
    st.session_state.indices_to_render_internal = indices_to_render_internal
