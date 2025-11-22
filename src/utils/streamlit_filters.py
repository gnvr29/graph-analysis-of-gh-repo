import streamlit as st
from src.core.AbstractGraph import AbstractGraph

def visualization_filters(graph: AbstractGraph, filter_with_edges: bool, limit: int, idx_to_name_full: dict) -> list[int]: 
    """
    Aplica filtros de visualização ao grafo COMPLETO, limitando autores por out-degree
    e/ou removendo autores sem arestas (se solicitado).
    
    Retorna a lista de ÍNDICES ORIGINAIS (do grafo completo) que devem ser incluídos 
    no subgrafo ativo.
    
    :param graph: O grafo COMPLETO (AbstractGraph)
    :param filter_with_edges: Mostrar apenas autores com interações
    :param limit: Limite de autores
    :param idx_to_name_full: Mapeamento de índice original -> nome (completo)
    :return: Lista de índices ORIGINAIS que passaram pelos filtros
    """
    author_activity = []
    
    # 1. Monta lista de vértices com seu out_degree
    for i in range(graph.getVertexCount()):
        out_degree = graph.getVertexOutDegree(i)
        author_activity.append((i, out_degree))

    # 2. ===== FILTRA APENAS QUEM TEM ARESTAS =====
    if filter_with_edges:
        author_activity_filtered = [item for item in author_activity if item[1] > 0]
    else:
        author_activity_filtered = author_activity.copy()

    author_activity = author_activity_filtered

    # 3. ===== ORDENAR PELO OUT DEGREE =====
    author_activity.sort(key=lambda item: item[1], reverse=True)

    # 4. ===== LIMITAR  =====
    if limit > 0:
        author_activity = author_activity[:limit]

    # 5. ===== CONSTRÓI LISTA FINAL DE ÍNDICES ORIGINAIS PARA CONSTRUÇÃO DO SUBGRAFO =====
    indices_to_render_original = [i for i, degree in author_activity]

    # 6. ===== ATUALIZAÇÕES DO SESSION STATE PARA SIDEBARS =====
    filtered_vertex_names_list = []
    filtered_name_to_idx_map = {}

    for original_idx in indices_to_render_original:
        author_name = idx_to_name_full.get(original_idx, f"ID_{original_idx}")
        filtered_vertex_names_list.append(author_name)
        filtered_name_to_idx_map[author_name] = original_idx 

    st.session_state.vertex_names_list = sorted(filtered_vertex_names_list)
    st.session_state.name_to_idx_map = filtered_name_to_idx_map
    
    return indices_to_render_original