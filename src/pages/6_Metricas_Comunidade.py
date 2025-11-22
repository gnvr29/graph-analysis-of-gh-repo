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
# === FUNÇÕES AUXILIARES DE ESTRUTURA (Integradas aqui) ===
# --------------------------------------------------------

def build_simple_graph(AdjacencyListGraph, vertex_count: int, edges: List[Tuple[int, int, float]]):
    """Helper simples para montar a estrutura de lista de adjacência."""
    graph = AdjacencyListGraph(vertex_count)
    for u, v, w in edges:
        graph.addEdge(u, v, w)
    return graph

def display_structure_results(res: Dict[str, Any]):
    """Desenha os resultados da análise estrutural."""
    st.divider()
    st.subheader(f"Resultados para: {res['analysis_mode']}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Densidade da Rede", value=f"{res['density']:.5f}", help="Proporção de conexões existentes vs. possíveis.")
    with col2:
        st.metric(label="Coef. de Aglomeração (Médio)", value=f"{res['clustering']:.4f}", help="Probabilidade de dois vizinhos de um nó serem vizinhos entre si.")
    with col3:
        st.metric(label="Assortatividade", value=f"{res['assortativity']:.4f}", help="Correlação de grau.")

    st.subheader("Interpretação")
    # ... (Lógica de interpretação omitida para brevidade, mas deve ser mantida) ...
    density = res['density']
    clustering = res['clustering']
    assortativity = res['assortativity']

    dens_interp = "muito esparsa" if density < 0.01 else "esparsa" if density < 0.1 else "moderada" if density < 0.5 else "densa"
    st.markdown(f"- **Densidade:** A rede é **{dens_interp}**.")
    
    clust_interp = "baixa coesão local" if clustering < 0.1 else "alta tendência a comunidades"
    st.markdown(f"- **Clusterização:** O valor indica **{clust_interp}**.")
    
    if assortativity > 0.1:
        assort_interp = "rede elitista (Hubs conectam-se a Hubs)"
    elif assortativity < -0.1:
        assort_interp = "rede hierárquica (Hubs conectam-se a periféricos/novatos)"
    else:
        assort_interp = "rede neutra (sem preferência clara de conexão)"
    st.markdown(f"- **Assortatividade:** Indica uma **{assort_interp}**.")

    # --- GRÁFICO EXTRA: DISPERSÃO DE GRAUS ---
    st.subheader("Visualizando a Assortatividade")
    scatter_data = res['scatter_data']
    max_degree = res['max_degree']

    if len(scatter_data) > 0:
        df_scatter = pd.DataFrame(scatter_data)
        if len(df_scatter) > 5000:
                df_scatter = df_scatter.sample(n=5000, random_state=42).copy()
                st.caption("Nota: Exibindo amostra de 5000 conexões aleatórias para performance.")

        fig = px.scatter(
            df_scatter, 
            x="Grau Origem", 
            y="Grau Destino",
            hover_data=["Autor Origem", "Autor Destino"],
            opacity=0.3,
            title=f"Correlação de Graus ({len(df_scatter)} amostras)"
        )
        fig.add_shape(type="line", x0=0, y0=0, x1=max_degree, y1=max_degree,
                    line=dict(color="Red", width=1, dash="dash"))
        st.plotly_chart(fig, use_container_width=True)

# --------------------------------------------------------
# === EXECUÇÃO PRINCIPAL DA PÁGINA ===
# --------------------------------------------------------

# 1. Encontrar todos os grafos carregados na sessão
loaded_graphs: Dict[str, AbstractGraph] = {}
loaded_names_maps: Dict[str, Dict[int, str]] = {}
processed_graph_display_names = set() # Para evitar duplicatas de nomes de exibição

for key, value in st.session_state.items():
    if key.startswith("graph_obj_") and value is not None:
        
        current_graph_display_name = None
        graph_id_suffix = key.replace("graph_obj_", "") # e.g., "my_custom_graph" or "dynamic_structure_Grafo_Integrado"

        # Tenta obter o nome de exibição explicitamente armazenado para grafos dinâmicos/calculados
        display_name_key_in_session = f"display_name_for_{key}"
        if display_name_key_in_session in st.session_state:
            current_graph_display_name = st.session_state[display_name_key_in_session]
        else:
            current_graph_display_name = graph_id_suffix.replace("_", " ").title() 
        if current_graph_display_name and current_graph_display_name not in processed_graph_display_names:
            loaded_graphs[current_graph_display_name] = value
            # A chave para o names_map usa o mesmo sufixo do graph_obj
            loaded_names_maps[current_graph_display_name] = st.session_state.get(f"names_map_{graph_id_suffix}", {})
            processed_graph_display_names.add(current_graph_display_name)

# --------------------------------------------------------
# === SIDEBAR: CONTROLE DE ANÁLISE ESTRUTURAL (Geração) ===
# --------------------------------------------------------

st.sidebar.header("Configuração da Análise Estrutural")

analysis_mode = st.sidebar.selectbox(
    "Qual rede analisar? (Busca Neo4j)",
    (
        "Grafo Integrado (Todas as interações)",
        "Apenas Comentários",
        "Apenas Reviews/Aprovações/Merge",
        "Apenas Fechamentos de Issue"
    ),
    key="sidebar_structure_analysis_mode"
)

# --------------------------------------------------------
# === LÓGICA DE CÁLCULO DE ESTRUTURA (Ação na sidebar) ===
# --------------------------------------------------------

if st.sidebar.button("Calcular Estrutura", key="sidebar_calculate_structure"):
    
    # Mapeia a escolha da sidebar para os tipos de interação
    interaction_types = set()
    if analysis_mode == "Grafo Integrado (Todas as interações)":
        interaction_types = set(st.session_state.shared_queries.WEIGHTS.keys())
    elif analysis_mode == "Apenas Comentários":
        interaction_types = {"COMMENT_PR_ISSUE", "OPENED_ISSUE_COMMENTED"}
    elif analysis_mode == "Apenas Reviews/Aprovações/Merge":
        interaction_types = {"REVIEW", "APPROVED", "MERGE"}
    elif analysis_mode == "Apenas Fechamentos de Issue":
        interaction_types = {"ISSUE_CLOSED"}
        
    try:
        neo4j_service = get_neo4j_service()
        with st.spinner(f"Calculando métricas estruturais para {analysis_mode}..."):
            
            # Buscar Dados e construir o grafo temporário
            idx_to_name, edges = st.session_state.shared_queries.fetch_authors_and_edges(neo4j_service, interaction_types)
            
            if not idx_to_name:
                st.warning("Nenhum dado encontrado para esta seleção.")
                st.session_state.structure_results = None
                if 'last_calculated_graph_name' in st.session_state:
                    del st.session_state['last_calculated_graph_name']
                # Limpa também as entries específicas do grafo dinâmico
                dynamic_graph_key_temp = f"dynamic_structure_graph_{analysis_mode.replace(' ', '_').replace('(', '').replace(')', '')}"
                if f"graph_obj_{dynamic_graph_key_temp}" in st.session_state:
                    del st.session_state[f"graph_obj_{dynamic_graph_key_temp}"]
                if f"names_map_{dynamic_graph_key_temp}" in st.session_state:
                    del st.session_state[f"names_map_{dynamic_graph_key_temp}"]
            else:
                vertex_count = len(idx_to_name)
                edge_count = len(edges)
                
                graph = build_simple_graph(AdjacencyListGraph, vertex_count, edges)
                adj_list = graph.getAsAdjacencyList()
                
                # Calcular Métricas
                density = st.session_state.structure_metrics.calculate_density(vertex_count, edge_count)
                clustering = st.session_state.structure_metrics.calculate_average_clustering_coefficient(adj_list)
                assortativity = st.session_state.structure_metrics.calculate_assortativity(adj_list)
                
                # Preparar dados do scatter plot (lógica interna da função)
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
                
                st.session_state.structure_results = {
                    'analysis_mode': analysis_mode,
                    'density': density,
                    'clustering': clustering,
                    'assortativity': assortativity,
                    'scatter_data': scatter_data,
                    'max_degree': max(degrees) if degrees else 0,
                    'idx_to_name': idx_to_name
                }
                dynamic_graph_key_suffix = analysis_mode.replace(' ', '_').replace('(', '').replace(')', '')
                dynamic_graph_obj_key = f"graph_obj_dynamic_structure_graph_{dynamic_graph_key_suffix}"
                dynamic_names_map_key = f"names_map_dynamic_structure_graph_{dynamic_graph_key_suffix}"
                dynamic_graph_display_name = f"Estrutura Calculada: {analysis_mode}"
                
                st.session_state[dynamic_graph_obj_key] = graph
                st.session_state[dynamic_names_map_key] = idx_to_name
                
                # Define o grafo recém-calculado como o padrão para seleção nas abas
                st.session_state['last_calculated_graph_name'] = dynamic_graph_display_name

                st.success("Cálculos Estruturais concluídos e grafo preparado para outras análises!")

    except Exception as e:
        st.error(f"Erro ao calcular Estrutura: {e}")
        st.session_state.structure_results = None
        if 'last_calculated_graph_name' in st.session_state:
            del st.session_state['last_calculated_graph_name']
        dynamic_graph_key_suffix = analysis_mode.replace(' ', '_').replace('(', '').replace(')', '')
        dynamic_graph_obj_key = f"graph_obj_dynamic_structure_graph_{dynamic_graph_key_suffix}"
        dynamic_names_map_key = f"names_map_dynamic_structure_graph_{dynamic_graph_key_suffix}"
        if dynamic_graph_obj_key in st.session_state:
            del st.session_state[dynamic_graph_obj_key]
        if dynamic_names_map_key in st.session_state:
            del st.session_state[dynamic_names_map_key]

# Isso é feito APÓS a lógica do botão, para garantir que o grafo recém-calculado seja incluído.
if 'last_calculated_graph_name' in st.session_state:
    dynamic_graph_display_name = st.session_state['last_calculated_graph_name']
    dynamic_graph_key_suffix = dynamic_graph_display_name.replace('Estrutura Calculada: ', '').replace(' ', '_').replace('(', '').replace(')', '')
    dynamic_graph_obj_key = f"graph_obj_dynamic_structure_graph_{dynamic_graph_key_suffix}"
    dynamic_names_map_key = f"names_map_dynamic_structure_graph_{dynamic_graph_key_suffix}"

    if dynamic_graph_obj_key in st.session_state and st.session_state[dynamic_graph_obj_key] is not None:
        loaded_graphs[dynamic_graph_display_name] = st.session_state[dynamic_graph_obj_key]
        loaded_names_maps[dynamic_graph_display_name] = st.session_state[dynamic_names_map_key] 

# --------------------------------------------------------
# === VERIFICAÇÃO DE PRÉ-REQUISITOS (BLOQUEIO) ===
# --------------------------------------------------------

if not loaded_graphs:
    # Se não houver grafos, só exibe a mensagem de instrução e os resultados de Estrutura (se calculados)
    st.error("Nenhum grafo foi carregado.")
    st.info("Use a **Configuração da Análise Estrutural** na barra lateral para começar a análise, ou gere um grafo na página principal.")
    
    # Exibe os resultados da Estrutura se o usuário acabou de calcular
    if st.session_state.get('structure_results'):
        st.header("Resultados de Estrutura")
        display_structure_results(st.session_state.structure_results)
    
    st.stop()


# --------------------------------------------------------
# === CORPO DA PÁGINA (Grafo Carregado) ===
# --------------------------------------------------------

# 2. Seletor de Grafo (Para Centralidade e Comunidade)
st.header("Selecione o Grafo de Origem")
if 'last_calculated_graph_name' in st.session_state and st.session_state['last_calculated_graph_name'] in loaded_graphs:
    try:
        default_index = list(loaded_graphs.keys()).index(st.session_state['last_calculated_graph_name'])
    except ValueError:
        pass # Caso o nome não seja encontrado (improvável se o check acima estiver correto)

graph_choice_name = st.selectbox(
    "Escolha qual grafo analisar:",
    list(loaded_graphs.keys()),
    index=default_index, # <--- Usa o índice padrão
    key="analysis_graph_selector"
)

# 3. Preparar dados do grafo SELECIONADO (para Centralidade e Comunidade)
try:
    graph = loaded_graphs[graph_choice_name]
    names_map = loaded_names_maps.get(graph_choice_name, {})

    if hasattr(graph, 'getAsAdjacencyList'):
        adj_list = graph.getAsAdjacencyList()
    else:
        # Fallback (Deve ser testado para garantir que a matriz ou a lista genérica funcionem)
        st.warning(f"Objeto {type(graph).__name__} não possui getAsAdjacencyList(). Usando fallback.")
        adj_list = graph_service.get_adjacency_list() 
        
    n = graph.getVertexCount()
    
    # Conversão para o formato List[List[Tuple[int, float]]] exigido
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
    
    if st.session_state.get('structure_results'):
        display_structure_results(st.session_state.structure_results)
    else:
        st.info("Nenhum resultado de Análise Estrutural encontrado. Use o botão **Calcular Estrutura** na barra lateral.")
        
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