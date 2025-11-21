import streamlit as st
from src.core.AbstractGraph import AbstractGraph

def visualization_filters (graph, filter_with_edges, limit): 
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

    filtered_vertex_names_list = []
    filtered_name_to_idx_map = {}

    for original_idx in indices_to_render_internal:
        author_name = st.session_state.idx_to_name_map[original_idx]
        filtered_vertex_names_list.append(author_name)
        # Mapeia o nome do autor filtrado para o seu índice ORIGINAL no grafo.
        filtered_name_to_idx_map[author_name] = original_idx

    # Atualiza os estados da sessão que serão usados pela sidebar
    st.session_state.vertex_names_list = sorted(filtered_vertex_names_list)
    st.session_state.name_to_idx_map = filtered_name_to_idx_map
    st.session_state.indices_to_render_internal = indices_to_render_internal
