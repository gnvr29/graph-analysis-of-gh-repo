import streamlit as st
import pandas as pd

from src.core.AdjacencyListGraph import AdjacencyListGraph
from src.core.AdjacencyMatrixGraph import AdjacencyMatrixGraph
from src.core.AbstractGraph import AbstractGraph
import src.services.graph_service as graph_service

from src.services.shared_queries import (WEIGHTS, fetch_authors_and_edges)

from src.services.adjacency_list_service import display_adjacency_lists_streamlit
from src.services.adjacency_matrix_service import df_to_svg
from src.utils.neo4j_connector import get_neo4j_service
from src.utils.streamlit_helpers import draw_graph_api_sidebar


# ============== FUNÇÃO APP ==============
def app():
    st.title("Grafo de Comentários em PR's e Issues")
    st.markdown("""
    **Descrição:** Este grafo representa a relação onde um usuário possui um comentário em uma issue ou pull request de outro usuário.
    
    * **Origem (Source):** Usuário que comentou.
    * **Destino (Target):** Usuário que criou a issue ou pull request.
    * **Peso:** Comentário em Issue/PR (valor: 2).
    """)

    PAGE_ID = "comentarios"

    if 'current_graph_id' not in st.session_state:
        st.session_state.current_graph_id = PAGE_ID

    if st.session_state.current_graph_id != PAGE_ID:
        print(
            f"Mudando de página, limpando grafo antigo ({st.session_state.current_graph_id})...")
        st.session_state.graph_obj = None
        st.session_state.vertex_names_list = []
        st.session_state.name_to_idx_map = {}
        st.session_state.idx_to_name_map = {}
        st.session_state.current_graph_id = PAGE_ID

    # --- ESCOLHA DA IMPLEMENTAÇÃO ---
    st.sidebar.header("Configuração da Geração")
    impl_choice = st.sidebar.selectbox(
        "Escolha a implementação do Grafo:",
        ("Lista de Adjacência", "Matriz de Adjacência"),
        key=f"{PAGE_ID}_impl_choice"
    )

    # --- FILTROS DE VISUALIZAÇÃO ---
    st.sidebar.header("Opções de Filtro (Visualização)")
    filter_with_edges = st.sidebar.checkbox(
        "Mostrar apenas autores com interações", value=True, key=f"{PAGE_ID}_filter_edges")
    limit = st.sidebar.number_input(
        "Limitar autores (0 = sem limite)", min_value=0, value=0, step=10, key=f"{PAGE_ID}_limit")
    st.session_state[f"{PAGE_ID}_current_author_limit"] = limit

    # --- LÓGICA DE CONEXÃO ---
    try:
        neo4j_service = get_neo4j_service()
    except Exception as e:
        st.error(f"Erro ao obter conexão com Neo4j: {e}")
        st.stop()

    if st.button("Gerar e Analisar Grafo"):
        with st.spinner("Buscando dados e construindo grafo..."):
            try:
                idx_to_name, edges = fetch_authors_and_edges(
                    neo4j_service, enabled_interaction_types={"COMMENT"})
                if not idx_to_name:
                    st.warning("Nenhum nó (:Author) encontrado no Neo4j.")
                    st.session_state.graph_obj = None
                    st.session_state.vertex_names_list = []
                    st.session_state.name_to_idx_map = {}
                    st.session_state.idx_to_name_map = {}
                    return

                vertex_count = len(idx_to_name)

                if impl_choice == "Lista de Adjacência":
                    impl_class = AdjacencyListGraph
                else:
                    impl_class = AdjacencyMatrixGraph

                graph = graph_service.build_graph(
                    impl_class, vertex_count, edges)

                # --- Armazenar no Session State ---
                st.session_state.graph_obj = graph
                st.session_state.name_to_idx_map = {
                    name: idx for idx, name in idx_to_name.items()}
                st.session_state.vertex_names_list = sorted(
                    list(idx_to_name.values()))
                st.session_state.idx_to_name_map = idx_to_name
                st.session_state.current_graph_id = PAGE_ID

            except Exception as e:
                st.error(f"Ocorreu um erro ao gerar o grafo: {e}")
                st.exception(e)
                st.session_state.graph_obj = None

    # --- RENDERIZAÇÃO ---
    if st.session_state.get("graph_obj") is not None:
        graph = st.session_state.graph_obj
        idx_to_name = st.session_state.idx_to_name_map

        st.success(
            f"Grafo gerado com sucesso usando: **{type(graph).__name__}**")

        # --- LÓGICA DE FILTRO ---
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

        # --- RENDERIZAÇÃO EM ABAS ---
        st.divider()
        st.header("Representações do Grafo")

        tab1, tab2, tab3 = st.tabs(
            ["Visualização (Força)", "Lista de Adjacência", "Matriz de Adjacência"])

        with tab1:
            st.info("Visualização do grafo filtrado:")
            if not indices_to_render_internal:
                st.warning(
                    "Nenhum autor corresponde aos filtros selecionados.")
            else:
                graph_service.draw_graph(
                    idx_to_name, indices_to_render_internal)

        with tab2:
            st.info("Representação do grafo completo como Lista de Adjacência.")
            adj_list_data = graph_service.get_adjacency_list()

            display_adjacency_lists_streamlit(
                graph=graph, idx_to_name=idx_to_name, indices_to_render=indices_to_render_internal)

        with tab3:
            st.info("Representação do grafo completo como Matriz de Adjacência.")
            matrix_data = graph_service.get_adjacency_matrix()
            matrix_labels = [idx_to_name.get(i, str(i))
                             for i in range(len(matrix_data))]
            df = pd.DataFrame(
                matrix_data, columns=matrix_labels, index=matrix_labels)

            if indices_to_render_internal:
                selected = [idx_to_name[i] for i in indices_to_render_internal]
                df = df.loc[selected, selected]

            # Mostra dataframe
            st.dataframe(df)

            # Converte para SVG
            svg = df_to_svg(df)

            # Botão para baixar
            st.download_button(
                "Baixar matriz (SVG)",
                data=svg.encode("utf-8"),
                file_name="matriz_adjacencia.svg",
                mime="image/svg+xml",
            )

            st.markdown("---")
            st.subheader("Legenda dos Pesos")
            st.write(
                f"- Comentário em Issue/PR: {WEIGHTS.get('COMMENT', 'N/A')}")
            st.write(
                f"- Abertura de Issue comentada: {WEIGHTS.get('ISSUE_COMMENTED', 'N/A')}")
            st.write(
                f"- Revisão/Aprovação de PR: {WEIGHTS.get('REVIEW', 'N/A')}")
            st.write(f"- Merge de PR: {WEIGHTS.get('MERGE', 'N/A')}")

    else:
        st.info(
            "Escolha uma implementação e clique em 'Gerar e Analisar Grafo' para carregar os dados.")

    # --- CHAMA O HELPER DA SIDEBAR ---
    draw_graph_api_sidebar()


if __name__ == "__main__":
    app()
