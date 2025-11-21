import streamlit as st
from src.core.AbstractGraph import AbstractGraph

def visualization_filters(graph, filter_with_edges, limit): 
    author_activity = []
    
    # monta lista de vértices com seu out_degree
    for i in range(graph.getVertexCount()):
        out_degree = graph.getVertexOutDegree(i)
        author_activity.append((i, out_degree))

    # ===== FILTRA APENAS QUEM TEM ARESTAS =====
    if filter_with_edges:
        author_activity_filtered = [item for item in author_activity if item[1] > 0]
    else:
        author_activity_filtered = author_activity.copy()

    # ===== INCLUI VÉRTICES NOVOS MESMO SEM ARESTAS =====
    new_vertices = st.session_state.get("new_vertices", set())
    for v in new_vertices:
        if v not in [i for i, _ in author_activity_filtered]:
            out_degree = graph.getVertexOutDegree(v)
            author_activity_filtered.append((v, out_degree))

    author_activity = author_activity_filtered

    # ===== ORDENAR PELO OUT DEGREE =====
    author_activity.sort(key=lambda item: item[1], reverse=True)

    # ===== LIMIT =====
    if limit > 0:
        author_activity = author_activity[:limit]

    # ===== CONSTRÓI LISTA FINAL =====
    indices_to_render_internal = [i for i, degree in author_activity]

    # ===== MAPEAR NOMES FILTRADOS =====
    filtered_vertex_names_list = []
    filtered_name_to_idx_map = {}

    for original_idx in indices_to_render_internal:
        author_name = st.session_state.idx_to_name_map[original_idx]
        filtered_vertex_names_list.append(author_name)
        filtered_name_to_idx_map[author_name] = original_idx

    # ===== ATUALIZA SESSION STATE =====
    st.session_state.vertex_names_list = sorted(filtered_vertex_names_list)
    st.session_state.name_to_idx_map = filtered_name_to_idx_map
    st.session_state.indices_to_render_internal = indices_to_render_internal
