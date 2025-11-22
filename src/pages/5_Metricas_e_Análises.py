from typing import List, Tuple, Dict, Any
import streamlit as st
import sys
import os
import importlib
import pandas as pd
import plotly.express as px

try:    
    current_dir = os.path.dirname(os.path.abspath(__file__))
    project_root = os.path.abspath(os.path.join(current_dir, '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
except Exception:
    pass
    
import src.services.graph_service as graph_service 
from src.core.AbstractGraph import AbstractGraph
from src.core.AdjacencyListGraph import AdjacencyListGraph
from src.utils.neo4j_connector import get_neo4j_service

import src.ui.centrality_ui as centrality_ui
import src.ui.community_ui as community_ui
import src.ui.structure_ui as structure_ui
import src.ui.sidebar_metrics as sidebar_metrics_ui

# Imports dos Módulos de Cálculo e Query
if 'centrality_metrics' not in st.session_state:
    st.session_state.centrality_metrics = importlib.import_module('src.analysis.centrality_metrics')
if 'community_metrics' not in st.session_state:
    st.session_state.community_metrics = importlib.import_module('src.analysis.community_metrics')
if 'structure_metrics' not in st.session_state:
    st.session_state.structure_metrics = importlib.import_module('src.analysis.structure_metrics')
if 'shared_queries' not in st.session_state:
    st.session_state.shared_queries = importlib.import_module('src.services.shared_queries')

def app():
    st.title("Métricas de Análise (Centralidade, Comunidade e Estrutura)")

    # --------------------------------------------------------
    # === EXECUÇÃO PRINCIPAL DA PÁGINA ===
    # --------------------------------------------------------

    # 1. Encontrar todos os grafos carregados na sessão
    loaded_graphs: Dict[str, AbstractGraph] = {}
    loaded_names_maps: Dict[str, Dict[int, str]] = {}

    for key, value in st.session_state.items():

       # -----------------------------------------------------
        # 1) GRAFOS CARREGADOS VIA SIDEBAR (graph_obj_*)
        # -----------------------------------------------------
        if key.startswith("graph_obj_") and value is not None:

            graph_obj_full_key = key                          # ex: graph_obj_custom_comments
            graph_id_suffix = key.replace("graph_obj_", "")   # ex: custom_comments

            # Tenta obter o nome de exibição armazenado na sessão
            display_name_key = f"display_name_for_{graph_obj_full_key}"

            if display_name_key in st.session_state:
                display_name = st.session_state[display_name_key]
            else:
                # fallback genérico para grafos sem nome explícito salvo
                display_name = graph_id_suffix.replace("_", " ").title()

            # Adiciona o grafo somente se ainda não estiver na lista
            if display_name not in loaded_graphs:
                loaded_graphs[display_name] = value

                names_map_key = f"names_map_{graph_id_suffix}"
                names_map = st.session_state.get(names_map_key, {})
                loaded_names_maps[display_name] = names_map


        # -----------------------------------------------------
        # 2) GRAFOS COMPLETOS DE OUTRAS PÁGINAS (full_*_obj)
        # -----------------------------------------------------
        # elif key.startswith("full_") and key.endswith("_obj") and value is not None:

        #     # Extrai o page_id: full_comments_obj → comments
        #     page_id = key.replace("full_", "").replace("_obj", "")

        #     # Nome de exibição padronizado
        #     display_name = f"Grafo Completo - {page_id.capitalize()}"

        #     if display_name not in loaded_graphs:
        #         loaded_graphs[display_name] = value

        #         # Primeiro tenta names_map_page, depois fallback para names_map global
        #         names_map_key = f"names_map_{page_id}"
        #         names_map = st.session_state.get(names_map_key, st.session_state.get("names_map", {}))

        #         loaded_names_maps[display_name] = names_map

    # --------------------------------------------------------
    # === SIDEBAR: CONTROLE DE ANÁLISE ESTRUTURAL (Geração) ===
    # --------------------------------------------------------

    st.sidebar.header("Configuração da Análise Estrutural")

    st.markdown("""
    <style>
    div[role=radiogroup] > label {
        margin-bottom: 8px; /* aumenta o espaçamento entre opções */
    }
    </style>
    """, unsafe_allow_html=True)

    analysis_mode = st.sidebar.radio(
        "Qual rede analisar? (Busca Neo4j)",
        (
            "Grafo Integrado (Todas as interações)",
            "Apenas Comentários",
            "Apenas Reviews, Aprovações e Merge",
            "Apenas Fechamentos de Issue"
        ),
        key="sidebar_structure_analysis_mode"
    )

    if st.sidebar.button("Calcular", key="sidebar_calculate_structure"):
        sidebar_metrics_ui.sidebar_metrics(analysis_mode=analysis_mode, get_neo4j_service=get_neo4j_service)

    # --------------------------------------------------------
    # === VERIFICAÇÃO DE PRÉ-REQUISITOS (BLOQUEIO) ===
    # --------------------------------------------------------

    if not loaded_graphs:
        st.error("Nenhum grafo foi carregado.")
        st.info("Use a **Configuração da Análise Estrutural** na barra lateral para começar a análise.")

        # Exibe os resultados da Estrutura se o usuário acabou de calcular
        # (Ainda usa a lógica antiga aqui para compatibilidade caso o 'all_graphs_structure_results' ainda não tenha sido populado)
        if st.session_state.get('structure_results'): # Mantido para compatibilidade com estado antigo
            st.header("Resultados de Estrutura")
            structure_ui.display_structure_results(st.session_state.structure_results) # Se os resultados foram armazenados na chave antiga

        st.stop()


    # --------------------------------------------------------
    # === CORPO DA PÁGINA (Grafo Carregado) ===
    # --------------------------------------------------------

    # 2. Seletor de Grafo (Para Centralidade e Comunidade)
    st.header("Selecione o Grafo de Origem")

    default_index = 0
    if 'last_calculated_graph_name' in st.session_state and st.session_state['last_calculated_graph_name'] in loaded_graphs:
        try:
            default_index = list(loaded_graphs.keys()).index(st.session_state['last_calculated_graph_name'])
        except ValueError:
            pass

    graph_choice_name = st.selectbox(
        "Escolha qual grafo analisar:",
        list(loaded_graphs.keys()),
        index=default_index,
        key="analysis_graph_selector"
    )

    # 3. Preparar dados do grafo SELECIONADO (para Centralidade e Comunidade)
    try:
        graph = loaded_graphs[graph_choice_name]
        names_map = loaded_names_maps.get(graph_choice_name, {})

        if hasattr(graph, 'getAsAdjacencyList'):
            adj_list = graph.getAsAdjacencyList()
        else:
            st.warning(f"Objeto {type(graph).__name__} não possui getAsAdjacencyList(). Tentando usar graph_service.get_adjacency_list().")
            # Se 'graph_service.get_adjacency_list()' espera o objeto graph como argumento:
            if hasattr(graph_service, 'get_adjacency_list') and callable(getattr(graph_service, 'get_adjacency_list')):
                 adj_list = graph_service.get_adjacency_list(graph)
            else:
                st.error("graph_service.get_adjacency_list() não encontrado ou não pode ser chamado.")
                st.stop() # Interrompe para evitar erro maior

        n = graph.getVertexCount()

        out_adj: List[List[Tuple[int, float]]] = [ [(v, float(w)) for v, w in nbrs.items()] for nbrs in adj_list ]
        in_adj: List[List[Tuple[int, float]]] = [[] for _ in range(n)]
        for u, nbrs in enumerate(out_adj):
            for v, w in nbrs:
                in_adj[v].append((u, w))

        st.success(f"Grafo selecionado: **{graph_choice_name}** | Vértices: **{n}** | Arestas: **{graph.getEdgeCount()}**")

    except Exception as e:
        st.error(f"Erro ao carregar dados do grafo selecionado: {e}")
        st.exception(e)
        st.stop()


    # --- Abas para Centralidade, Comunidade e Estrutura ---
    tab_structure, tab_centrality, tab_community = st.tabs(
        ["Estrutura e Coesão", "Centralidade", "Comunidade"]
    )

    # ====================================================================
    # === Aba 1: Métricas de Estrutura (APENAS EXIBE O RESULTADO SALVO) ===
    # ====================================================================
    with tab_structure:
        st.title("Análise de Estrutura e Coesão")
        st.markdown("Esta análise calcula a macroscopia da rede. O cálculo é iniciado na **barra lateral**.")

        # *** ALTERAÇÃO AQUI: Exibe resultados do grafo SELECIONADO ***
        if 'all_graphs_structure_results' in st.session_state and graph_choice_name in st.session_state.all_graphs_structure_results:
            structure_ui.display_structure_results(st.session_state.all_graphs_structure_results[graph_choice_name])
        else:
            st.info(f"Nenhum resultado de Análise Estrutural encontrado para o grafo '{graph_choice_name}'. Use o botão **Calcular** na barra lateral para gerar os resultados da estrutura para o tipo de rede desejado.")

    # ====================================================================
    # === Aba 2: Métricas de Centralidade ===
    # ====================================================================
    with tab_centrality:
        centrality_ui.display_centrality_metrics(out_adj, in_adj, names_map, graph_choice_name)

    # ====================================================================
    # === Aba 3: Métricas de Comunidade ===
    # ====================================================================
    with tab_community:
        community_ui.display_community_metrics(out_adj, names_map, graph_choice_name)

if __name__ == "__main__":
    app()