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

# Imports dos Módulos de Cálculo e Query
if 'centrality_metrics' not in st.session_state:
    st.session_state.centrality_metrics = importlib.import_module('src.analysis.centrality_metrics')
if 'community_metrics' not in st.session_state:
    st.session_state.community_metrics = importlib.import_module('src.analysis.community_metrics')
if 'structure_metrics' not in st.session_state:
    st.session_state.structure_metrics = importlib.import_module('src.analysis.structure_metrics')
if 'shared_queries' not in st.session_state:
    st.session_state.shared_queries = importlib.import_module('src.services.shared_queries')


PAGE_TITLE = "Métricas de Análise (Centralidade, Comunidade e Estrutura)"
st.title(PAGE_TITLE)

# --------------------------------------------------------
# === EXECUÇÃO PRINCIPAL DA PÁGINA ===
# --------------------------------------------------------

# 1. Encontrar todos os grafos carregados na sessão
loaded_graphs: Dict[str, AbstractGraph] = {}
loaded_names_maps: Dict[str, Dict[int, str]] = {}
# Não precisamos mais de processed_graph_display_names se o check de unicidade for feito diretamente em loaded_graphs

for key, value in st.session_state.items():
    if key.startswith("graph_obj_") and value is not None:
        
        current_graph_display_name = None
        graph_obj_full_key = key # e.g., "graph_obj_my_custom_graph"
        graph_id_suffix = key.replace("graph_obj_", "") # e.g., "my_custom_graph"

        # Tenta obter o nome de exibição explicitamente armazenado
        display_name_key_in_session = f"display_name_for_{graph_obj_full_key}"
        if display_name_key_in_session in st.session_state:
            current_graph_display_name = st.session_state[display_name_key_in_session]
        else:
            # Fallback genérico para grafos que não têm um nome de exibição explícito salvo
            # (e.g., grafos de outras páginas ou sessões antigas)
            current_graph_display_name = graph_id_suffix.replace("_", " ").title()
        
        # Adiciona o grafo apenas se o nome de exibição ainda não estiver em loaded_graphs
        if current_graph_display_name not in loaded_graphs:
            loaded_graphs[current_graph_display_name] = value
            loaded_names_maps[current_graph_display_name] = st.session_state.get(f"names_map_{graph_id_suffix}", {})

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

# --------------------------------------------------------
# === LÓGICA DE CÁLCULO DE ESTRUTURA (Ação na sidebar) ===
# --------------------------------------------------------

if st.sidebar.button("Calcular", key="sidebar_calculate_structure"):
    
    # Mapeia a escolha da sidebar para os tipos de interação
    interaction_types = set()
    if analysis_mode == "Grafo Integrado (Todas as interações)":
        interaction_types = set(st.session_state.shared_queries.WEIGHTS.keys())
    elif analysis_mode == "Apenas Comentários":
        interaction_types = {"COMMENT_PR_ISSUE", "OPENED_ISSUE_COMMENTED"}
    elif analysis_mode == "Apenas Reviews, Aprovações e Merge":
        interaction_types = {"REVIEW", "APPROVED", "MERGE"}
    elif analysis_mode == "Apenas Fechamentos de Issue":
        interaction_types = {"ISSUE_CLOSED"}
        
    try:
        neo4j_service = get_neo4j_service()
        with st.spinner(f"Calculando métricas estruturais para {analysis_mode}..."):
            
            # Buscar Dados e construir o grafo temporário
            idx_to_name, edges = st.session_state.shared_queries.fetch_authors_and_edges(neo4j_service, interaction_types)
            
            # Gerar um sufixo de chave consistente e o nome de exibição desejado
            dynamic_graph_key_suffix = analysis_mode.replace(' ', '_').replace('(', '').replace(')', '')
            graph_obj_full_key = f"graph_obj_dynamic_structure_graph_{dynamic_graph_key_suffix}" # Chave para o objeto do grafo
            names_map_full_key = f"names_map_dynamic_structure_graph_{dynamic_graph_key_suffix}" # Chave para o names_map
            dynamic_graph_display_name = f"{analysis_mode}" # Nome de exibição em português
            
            if not idx_to_name:
                st.warning("Nenhum dado encontrado para esta seleção.")
                # Limpa as entries específicas do grafo dinâmico se existirem
                if graph_obj_full_key in st.session_state:
                    del st.session_state[graph_obj_full_key]
                if names_map_full_key in st.session_state:
                    del st.session_state[names_map_full_key]
                if f"display_name_for_{graph_obj_full_key}" in st.session_state:
                    del st.session_state[f"display_name_for_{graph_obj_full_key}"]
                # Remove os resultados de estrutura para este grafo específico
                if 'all_graphs_structure_results' in st.session_state and dynamic_graph_display_name in st.session_state.all_graphs_structure_results:
                    del st.session_state.all_graphs_structure_results[dynamic_graph_display_name]
                if 'last_calculated_graph_name' in st.session_state and st.session_state['last_calculated_graph_name'] == dynamic_graph_display_name:
                     del st.session_state['last_calculated_graph_name']
            else:
                vertex_count = len(idx_to_name)
                edge_count = len(edges)
                
                graph = structure_ui.build_simple_graph(AdjacencyListGraph, vertex_count, edges)
                adj_list = graph.getAsAdjacencyList()
                
                # Calcular Métricas
                density = st.session_state.structure_metrics.calculate_density(vertex_count, edge_count)
                clustering = st.session_state.structure_metrics.calculate_average_clustering_coefficient(adj_list)
                assortativity = st.session_state.structure_metrics.calculate_assortativity(adj_list)
                
                # Preparar dados do scatter plot
                degrees = [0] * vertex_count
                for u, neighbors in enumerate(adj_list):
                    degrees[u] += len(neighbors)
                    for v in neighbors:
                        degrees[v] += 1
                
                scatter_data = []
                for u, neighbors in enumerate(adj_list):
                    for v in neighbors:
                        scatter_data.append({
                            "Grau Origem": degrees[u],
                            "Grau Destino": degrees[v],
                            "Autor Origem": idx_to_name.get(u, str(u)),
                            "Autor Destino": idx_to_name.get(v, str(v))
                        })
                
                # *** ARMAZENA RESULTADOS DE ESTRUTURA POR NOME DE GRAFO ***
                if 'all_graphs_structure_results' not in st.session_state:
                    st.session_state.all_graphs_structure_results = {}
                
                st.session_state.all_graphs_structure_results[dynamic_graph_display_name] = {
                    'analysis_mode': analysis_mode,
                    'density': density,
                    'clustering': clustering,
                    'assortativity': assortativity,
                    'scatter_data': scatter_data,
                    'max_degree': max(degrees) if degrees else 0,
                    'idx_to_name': idx_to_name # Opcional, para usar na display_structure_results se necessário
                }
                
                st.session_state[graph_obj_full_key] = graph
                st.session_state[names_map_full_key] = idx_to_name
                
                # Armazena o nome de exibição explicitamente!
                st.session_state[f"display_name_for_{graph_obj_full_key}"] = dynamic_graph_display_name

                # Define o grafo recém-calculado como o padrão para seleção nas abas
                st.session_state['last_calculated_graph_name'] = dynamic_graph_display_name

                st.success("Cálculos Estruturais concluídos e grafo preparado para outras análises!")

    except Exception as e:
        st.error(f"Erro ao calcular Estrutura: {e}")
        # Garante que as chaves associadas ao grafo dinâmico sejam limpas em caso de erro
        dynamic_graph_key_suffix = analysis_mode.replace(' ', '_').replace('(', '').replace(')', '')
        graph_obj_full_key = f"graph_obj_dynamic_structure_graph_{dynamic_graph_key_suffix}"
        names_map_full_key = f"names_map_dynamic_structure_graph_{dynamic_graph_key_suffix}"

        if graph_obj_full_key in st.session_state:
            del st.session_state[graph_obj_full_key]
        if names_map_full_key in st.session_state:
            del st.session_state[names_map_full_key]
        if f"display_name_for_{graph_obj_full_key}" in st.session_state:
            del st.session_state[f"display_name_for_{graph_obj_full_key}"]
        # Remove os resultados de estrutura para este grafo específico
        dynamic_graph_display_name = f"{analysis_mode}" # Recria o nome de exibição para limpeza
        if 'all_graphs_structure_results' in st.session_state and dynamic_graph_display_name in st.session_state.all_graphs_structure_results:
            del st.session_state.all_graphs_structure_results[dynamic_graph_display_name]
        
        if 'last_calculated_graph_name' in st.session_state:
            del st.session_state['last_calculated_graph_name']


# --------------------------------------------------------
# === VERIFICAÇÃO DE PRÉ-REQUISITOS (BLOQUEIO) ===
# --------------------------------------------------------

if not loaded_graphs:
    st.error("Nenhum grafo foi carregado.")
    st.info("Use a **Configuração da Análise Estrutural** na barra lateral para começar a análise, ou gere um grafo na página principal.")
    
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
    ["Estrutura (Resultados)", "Centralidade", "Comunidade"]
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
