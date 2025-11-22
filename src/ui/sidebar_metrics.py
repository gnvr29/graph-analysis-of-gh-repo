import streamlit as st
from src.core.AdjacencyListGraph import AdjacencyListGraph
import src.ui.structure_ui as structure_ui
from typing import List, Tuple

def build_simple_graph(AdjacencyListGraph, vertex_count: int, edges: List[Tuple[int, int, float]]):
    """Helper simples para montar a estrutura de lista de adjacência."""
    graph = AdjacencyListGraph(vertex_count)
    for u, v, w in edges:
        graph.addEdge(u, v, w)
    return graph


def sidebar_metrics(analysis_mode, get_neo4j_service): 

# --------------------------------------------------------
# === LÓGICA DE CÁLCULO DE ESTRUTURA (Ação na sidebar) ===
# --------------------------------------------------------
    
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
                
                graph = build_simple_graph(AdjacencyListGraph, vertex_count, edges)
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
                st.rerun()

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