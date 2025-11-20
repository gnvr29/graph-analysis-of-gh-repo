import streamlit as st
import pandas as pd
import tempfile
import os

from src.core.AdjacencyListGraph import AdjacencyListGraph
from src.core.AdjacencyMatrixGraph import AdjacencyMatrixGraph
from src.core.AbstractGraph import AbstractGraph
import src.services.graph_service as graph_service
from pages._shared_queries import WEIGHTS, fetch_authors_and_edges
from src.services.adjacency_list_service import display_adjacency_lists_streamlit
from src.services.adjacency_matrix_service import df_to_svg
from src.services.draw_graph_service import draw_graph
from src.utils.neo4j_connector import get_neo4j_service


def build_graph(impl_class: type[AbstractGraph], vertex_count: int, edges: list[tuple[int, int, float]]) -> AbstractGraph:
    graph = impl_class(vertex_count)
    for u, v, w in edges:
        graph.addEdge(u, v, w)
    return graph


def app():
    st.title("Teste: Grafo Integrado (Visualização Completa)")
    st.markdown("Gera um grafo integrado com todos os tipos de interação e mostra todas as visualizações de teste.")

    st.sidebar.header("Configuração")
    impl_choice = st.sidebar.selectbox("Implementação:", ("Lista de Adjacência", "Matriz de Adjacência"))

    # conexão
    try:
        neo4j_service = get_neo4j_service()
    except Exception as e:
        st.error(f"Erro ao conectar ao Neo4j: {e}")
        st.stop()

    if st.button("Gerar Grafo Integrado (todos os tipos)"):
        with st.spinner("Buscando dados e gerando grafo integrado..."):
            enabled = set(WEIGHTS.keys())
            try:
                idx_to_name, edges = fetch_authors_and_edges(neo4j_service, enabled_interaction_types=enabled)
            except Exception as e:
                st.error(f"Erro ao buscar arestas: {e}")
                return

            if not idx_to_name:
                st.warning("Nenhum autor encontrado no Neo4j.")
                return

            vertex_count = len(idx_to_name)
            impl_class = AdjacencyListGraph if impl_choice == "Lista de Adjacência" else AdjacencyMatrixGraph
            graph = build_graph(impl_class, vertex_count, edges)

            # manter também uma cópia em lista de adjacência para exibição da lista
            adj_display_graph = AdjacencyListGraph(vertex_count)
            for u, v, w in edges:
                adj_display_graph.addEdge(u, v, w)

            st.session_state['test_integrated_graph'] = graph
            st.session_state['test_integrated_display_graph'] = adj_display_graph
            st.session_state['test_idx_to_name'] = idx_to_name

    if st.session_state.get('test_integrated_graph') is None:
        st.info("Clique em 'Gerar Grafo Integrado' para iniciar.")
        return

    graph = st.session_state['test_integrated_graph']
    display_graph = st.session_state['test_integrated_display_graph']
    idx_to_name = st.session_state['test_idx_to_name']

    st.success(f"Grafo gerado: {type(graph).__name__} — {graph.getVertexCount()} vértices, {graph.getEdgeCount()} arestas")

    indices = list(range(graph.getVertexCount()))

    tab1, tab2, tab3 = st.tabs(["Visualização (Força)", "Lista de Adjacência", "Matriz de Adjacência"])

    with tab1:
        st.info("Visualização do grafo integrado (layout de força).")
        draw_graph(graph, idx_to_name, indices)

    with tab2:
        st.info("Lista de Adjacência (representação construída a partir das arestas integradas).")
        display_adjacency_lists_streamlit(display_graph, idx_to_name, indices)

    with tab3:
        st.info("Matriz de Adjacência (DataFrame)")
        matrix = graph.getAsAdjacencyMatrix()
        labels = [idx_to_name.get(i, str(i)) for i in range(len(matrix))]
        df = pd.DataFrame(matrix, columns=labels, index=labels)
        st.dataframe(df)

        svg = df_to_svg(df)
        st.download_button("Baixar matriz (SVG)", data=svg.encode('utf-8'), file_name='matriz_integrada.svg', mime='image/svg+xml')

        # tentativa de exportar GEXF para download
        try:
            tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.gexf')
            tmp.close()
            graph.exportToGEPHI(tmp.name)
            with open(tmp.name, 'rb') as f:
                gexf_bytes = f.read()
            st.download_button("Baixar GEXF (Gephi)", data=gexf_bytes, file_name='grafo_integrado.gexf', mime='application/gexf+xml')
            os.unlink(tmp.name)
        except Exception as e:
            st.warning(f"Export to GEXF falhou: {e}")


if __name__ == '__main__':
    app()
