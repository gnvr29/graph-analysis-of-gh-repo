import streamlit as st
import pandas as pd
import plotly.express as px

from src.utils.neo4j_connector import get_neo4j_service
from src.core.AdjacencyListGraph import AdjacencyListGraph
from src.services.shared_queries import fetch_authors_and_edges, WEIGHTS

from src.analysis.structure_metrics import (
    calculate_density,
    calculate_average_clustering_coefficient,
    calculate_assortativity
)

def build_simple_graph(vertex_count, edges):
    """Helper simples para montar a estrutura de lista de adjacência"""
    graph = AdjacencyListGraph(vertex_count)
    for u, v, w in edges:
        graph.addEdge(u, v, w)
    return graph

def app():
    st.title("📊 Análise de Estrutura e Coesão")
    st.markdown("""
    Nesta página, analisamos a **macroscopia** da rede de colaboradores.
    
    Métricas analisadas:
    1. **Densidade:** O quão conectada a rede é (0 a 1).
    2. **Coeficiente de aglomeração:** A tendência de formar grupos fechados.
    3. **Assortatividade:** Se colaboradores "famosos" interagem apenas entre si.
    """)

    st.sidebar.header("Configuração da Análise")
    
    # Opção para escolher qual "camada" do grafo analisar
    analysis_mode = st.sidebar.selectbox(
        "Qual rede analisar?",
        (
            "Grafo Integrado (Todas as interações)",
            "Apenas Comentários",
            "Apenas Reviews/Aprovações/Merge",
            "Apenas Fechamentos de Issue"
        )
    )
    
    # Mapeia a escolha para os tipos de interação do _shared_queries
    interaction_types = set()
    if analysis_mode == "Grafo Integrado (Todas as interações)":
        interaction_types = set(WEIGHTS.keys())
    elif analysis_mode == "Apenas Comentários":
        interaction_types = {"COMMENT", "ISSUE_COMMENTED"}
    elif analysis_mode == "Apenas Reviews/Aprovações/Merge":
        interaction_types = {"REVIEW", "APPROVED", "MERGE"}
    elif analysis_mode == "Apenas Fechamentos de Issue":
        interaction_types = {"ISSUE_CLOSED"}

    # --- CONEXÃO E CARGA ---
    try:
        neo4j_service = get_neo4j_service()
    except Exception as e:
        st.error(f"Erro de conexão: {e}")
        st.stop()

    if st.button("Calcular Métricas"):
        with st.spinner("Calculando métricas estruturais..."):
            try:
                # Buscar Dados
                idx_to_name, edges = fetch_authors_and_edges(neo4j_service, interaction_types)
                
                if not idx_to_name:
                    st.warning("Nenhum dado encontrado para esta seleção.")
                    return
                
                vertex_count = len(idx_to_name)
                edge_count = len(edges)
                
                # Construir o Grafo
                graph = build_simple_graph(vertex_count, edges)
                adj_list = graph.getAsAdjacencyList()
                
                # Calcular Métricas
                density = calculate_density(vertex_count, edge_count)
                clustering = calculate_average_clustering_coefficient(adj_list)
                assortativity = calculate_assortativity(adj_list)
                
                # --- EXIBIÇÃO DOS RESULTADOS ---
                st.success("Cálculos concluídos!")
                st.divider()
                
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric(
                        label="Densidade da Rede",
                        value=f"{density:.5f}",
                        help="Proporção de conexões existentes vs. possíveis. Valor baixo indica rede esparsa."
                    )
                    
                with col2:
                    st.metric(
                        label="Coef. de Aglomeração (Médio)",
                        value=f"{clustering:.4f}",
                        help="Probabilidade de dois vizinhos de um nó serem vizinhos entre si (formar triângulos)."
                    )
                    
                with col3:
                    st.metric(
                        label="Assortatividade",
                        value=f"{assortativity:.4f}",
                        help="Correlação de grau. >0: Famosos falam com famosos. <0: Famosos falam com novatos."
                    )

                # --- INTERPRETAÇÃO AUTOMÁTICA ---
                st.subheader("📝 Interpretação")
                
                # Densidade
                dens_interp = "muito esparsa" if density < 0.1 else "moderada" if density < 0.5 else "densa"
                st.markdown(f"- **Densidade:** A rede é **{dens_interp}**. Isso é comum em projetos Open Source grandes, onde nem todos falam com todos.")
                
                # Clustering
                clust_interp = "baixa coesão local" if clustering < 0.1 else "alta tendência a comunidades"
                st.markdown(f"- **Clusterização:** O valor indica **{clust_interp}**. Isso reflete se existem grupos de trabalho fechados ou se a comunicação é dispersa.")
                
                # Assortatividade
                if assortativity > 0.1:
                    assort_interp = "rede elitista (Hubs conectam-se a Hubs)"
                elif assortativity < -0.1:
                    assort_interp = "rede hierárquica (Hubs conectam-se a periféricos/novatos)"
                else:
                    assort_interp = "rede neutra (sem preferência clara de conexão)"
                st.markdown(f"- **Assortatividade:** Indica uma **{assort_interp}**.")
                
                # --- GRÁFICO EXTRA: DISPERSÃO DE GRAUS ---
                st.subheader("🔎 Visualizando a Assortatividade")
                st.markdown("O gráfico abaixo mostra, para cada interação, o grau de quem iniciou vs. o grau de quem recebeu.")
                
                # Preparar dados para o gráfico
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
                            "Autor Origem": idx_to_name[u],
                            "Autor Destino": idx_to_name[v]
                        })
                
                if len(scatter_data) > 0:
                    # Limitação para performance
                    df_scatter = pd.DataFrame(scatter_data[:5000]) 
                    
                    fig = px.scatter(
                        df_scatter, 
                        x="Grau Origem", 
                        y="Grau Destino",
                        hover_data=["Autor Origem", "Autor Destino"],
                        opacity=0.3,
                        title=f"Correlação de Graus ({len(df_scatter)} amostras)"
                    )
                    fig.add_shape(type="line", x0=0, y0=0, x1=max(degrees), y1=max(degrees),
                                line=dict(color="Red", width=1, dash="dash"))
                    st.plotly_chart(fig, use_container_width=True)
                    if len(scatter_data) > 5000:
                        st.caption("Nota: Exibindo amostra das primeiras 5000 conexões para performance.")

            except Exception as e:
                st.error(f"Erro ao calcular: {e}")

if __name__ == "__main__":
    app()