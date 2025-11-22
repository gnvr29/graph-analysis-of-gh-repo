# src/analysis/structure_ui.py
import streamlit as st
import pandas as pd
import plotly.express as px
from typing import List, Tuple, Dict, Any

# Assumimos que os módulos/classes abaixo estão disponíveis no PATH:
# - structure_metrics (do st.session_state)
# - shared_queries (do st.session_state)
# - AdjacencyListGraph

def build_simple_graph(AdjacencyListGraph, vertex_count: int, edges: List[Tuple[int, int, float]]):
    """Helper simples para montar a estrutura de lista de adjacência."""
    graph = AdjacencyListGraph(vertex_count)
    for u, v, w in edges:
        graph.addEdge(u, v, w)
    return graph

def display_structure_metrics(neo4j_service, AdjacencyListGraph, structure_metrics_module, shared_queries_module):
    """
    Desenha a interface de seleção e calcula as métricas de estrutura, 
    buscando dados diretamente do Neo4j.
    """
    
    # --- CONFIGURAÇÃO (DENTRO DA ABA) ---
    st.subheader("Configuração da Rede de Análise")
    
    col_mode, col_button = st.columns([3, 1])

    with col_mode:
        analysis_mode = st.selectbox(
            "Qual rede analisar? (Dados buscados do Neo4j)",
            (
                "Grafo Integrado (Todas as interações)",
                "Apenas Comentários",
                "Apenas Reviews/Aprovações",
                "Apenas Fechamentos de Issue"
            ),
            key="structure_analysis_mode"
        )
    
    interaction_types = set()
    if analysis_mode == "Grafo Integrado (Todas as interações)":
        interaction_types = set(shared_queries_module.WEIGHTS.keys())
    elif analysis_mode == "Apenas Comentários":
        interaction_types = {"COMMENT", "ISSUE_COMMENTED"}
    elif analysis_mode == "Apenas Reviews/Aprovações":
        interaction_types = {"REVIEW", "MERGE"}
    elif analysis_mode == "Apenas Fechamentos de Issue":
        interaction_types = {"ISSUE_CLOSED"}

    with col_button:
        # Espaço vertical para alinhar o botão
        st.write("")
        if st.button("Calcular Métricas Estruturais", key="calculate_structure_final"):
            with st.spinner(f"Calculando métricas estruturais para {analysis_mode}..."):
                try:
                    # Buscar Dados
                    idx_to_name, edges = shared_queries_module.fetch_authors_and_edges(neo4j_service, interaction_types)
                    
                    if not idx_to_name:
                        st.warning("Nenhum dado encontrado para esta seleção.")
                        st.session_state.structure_results = None
                        return
                    
                    vertex_count = len(idx_to_name)
                    edge_count = len(edges)
                    
                    # Construir o Grafo
                    graph = build_simple_graph(AdjacencyListGraph, vertex_count, edges)
                    adj_list = graph.getAsAdjacencyList() # adj_list é List[Dict[int, float]]
                    
                    # Calcular Métricas
                    density = structure_metrics_module.calculate_density(vertex_count, edge_count)
                    clustering = structure_metrics_module.calculate_average_clustering_coefficient(adj_list)
                    assortativity = structure_metrics_module.calculate_assortativity(adj_list)
                    
                    # Preparar dados para o gráfico de dispersão de graus
                    degrees = [0] * vertex_count
                    for u, neighbors in enumerate(adj_list):
                        # Grau de saída é o número de vizinhos
                        degrees[u] += len(neighbors) 
                        # Grau de entrada é a contribuição do vizinho
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
                    st.success("Cálculos concluídos!")

                except Exception as e:
                    st.error(f"Erro ao calcular: {e}")
                    st.exception(e)
                    st.session_state.structure_results = None

    # --- EXIBIÇÃO DOS RESULTADOS (FORA DO FORMULÁRIO) ---
    if st.session_state.get('structure_results'):
        res = st.session_state.structure_results
        
        st.divider()
        st.subheader(f"Resultados para: {res['analysis_mode']}")
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric(label="Densidade da Rede", value=f"{res['density']:.5f}", help="Proporção de conexões existentes vs. possíveis.")
        with col2:
            st.metric(label="Coef. de Aglomeração (Médio)", value=f"{res['clustering']:.4f}", help="Probabilidade de dois vizinhos de um nó serem vizinhos entre si.")
        with col3:
            st.metric(label="Assortatividade", value=f"{res['assortativity']:.4f}", help="Correlação de grau.")

        # --- INTERPRETAÇÃO AUTOMÁTICA ---
        st.subheader("📝 Interpretação")
        
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
        st.subheader("🔎 Visualizando a Assortatividade")
        
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