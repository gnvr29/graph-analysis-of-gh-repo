import streamlit as st
import pandas as pd

from src.core.AdjacencyListGraph import AdjacencyListGraph
from src.core.AdjacencyMatrixGraph import AdjacencyMatrixGraph
from src.core.AbstractGraph import AbstractGraph 
import src.services.graph_service as graph_service

# Importamos a função compartilhada que agora sabe buscar ISSUE_CLOSED
from src.services.shared_queries import (WEIGHTS, fetch_authors_and_edges)

from src.services.adjacency_list_service import display_adjacency_lists_streamlit
from src.services.adjacency_matrix_service import df_to_svg
from src.utils.neo4j_connector import get_neo4j_service
from src.utils.streamlit_helpers import draw_graph_api_sidebar
from src.utils.streamlit_filters import visualization_filters

def app():
    st.title("Grafo: Fechamento de Issues")
    st.markdown("""
    **Descrição:** Este grafo representa a relação onde um usuário fecha a issue criada por outro.
    
    * **Origem (Source):** Usuário que fechou a issue.
    * **Destino (Target):** Usuário que criou a issue.
    * **Peso:** Quantidade de issues fechadas.
    """)

    PAGE_ID = "fechamento_issues" 
    
    if 'current_graph_id' not in st.session_state:
        st.session_state.current_graph_id = PAGE_ID

    if st.session_state.current_graph_id != PAGE_ID:
        st.session_state.graph_obj = None
        st.session_state.current_graph_id = PAGE_ID

    # --- ESCOLHA DA IMPLEMENTAÇÃO ---
    st.sidebar.header("Configuração da Geração")
    impl_choice = st.sidebar.selectbox(
        "Escolha a implementação do Grafo:",
        ("Lista de Adjacência", "Matriz de Adjacência"),
        key=f"{PAGE_ID}_impl_choice" 
    )
    
    # --- FILTROS DE VISUALIZAÇÃO ---
    st.sidebar.header("Opções de Filtro")
    filter_with_edges = st.sidebar.checkbox("Mostrar apenas autores com interações", value=True, key=f"{PAGE_ID}_filter_edges")
    limit = st.sidebar.number_input("Limitar autores (0 = sem limite)", min_value=0, value=0, step=10, key=f"{PAGE_ID}_limit")
    
    # --- LÓGICA DE CONEXÃO ---
    try:
        neo4j_service = get_neo4j_service()
    except Exception as e:
        st.error(f"Erro ao obter conexão com Neo4j: {e}")
        st.stop()

    if st.button("Gerar e Analisar Grafo"):
        with st.spinner("Buscando dados de fechamento de issues..."):
            try:
                # AQUI ESTÁ A MÁGICA: Solicitamos apenas o tipo ISSUE_CLOSED
                idx_to_name, edges = fetch_authors_and_edges(neo4j_service, enabled_interaction_types={"ISSUE_CLOSED"})
                
                if not idx_to_name:
                    st.warning("Nenhum autor encontrado.")
                    return

                vertex_count = len(idx_to_name)
                
                if impl_choice == "Lista de Adjacência":
                    impl_class = AdjacencyListGraph
                else:
                    impl_class = AdjacencyMatrixGraph
                
                graph = graph_service.build_graph(impl_class, vertex_count, edges)

                # Armazenar no Session State
                st.session_state.graph_obj = graph
                st.session_state.name_to_idx_map = {name: idx for idx, name in idx_to_name.items()}
                st.session_state.vertex_names_list = sorted(list(idx_to_name.values()))
                st.session_state.idx_to_name_map = idx_to_name 

            except Exception as e:
                st.error(f"Ocorreu um erro ao gerar o grafo: {e}")
                st.session_state.graph_obj = None 

    
    # --- RENDERIZAÇÃO --- 
    if st.session_state.get("graph_obj") is not None:
        graph = st.session_state.graph_obj
        idx_to_name = st.session_state.idx_to_name_map
        
        st.success(f"Grafo gerado com sucesso: {graph.getVertexCount()} vértices e {graph.getEdgeCount()} arestas.")

        visualization_filters(graph=graph, filter_with_edges=filter_with_edges, limit=limit)

        indices_to_render_internal = st.session_state.get("indices_to_render_internal")
        
        st.divider()
        st.header("Representações do Grafo")

        tab1, tab2, tab3 = st.tabs(["Visualização", "Lista de Adjacência", "Matriz de Adjacência"])

        with tab1:
            if not indices_to_render_internal:
                st.warning("Nenhum dado para exibir com os filtros atuais.")
            else:
                graph_service.draw_graph(idx_to_name, indices_to_render_internal)

        with tab2:
            display_adjacency_lists_streamlit(graph=graph, idx_to_name=idx_to_name, indices_to_render=indices_to_render_internal)

        with tab3:
            matrix_data = graph_service.get_adjacency_matrix()
            matrix_labels = [idx_to_name.get(i, str(i)) for i in range(len(matrix_data))]
            df = pd.DataFrame(matrix_data, columns=matrix_labels, index=matrix_labels)
            
            if indices_to_render_internal:
                selected = [idx_to_name[i] for i in indices_to_render_internal]
                df = df.loc[selected, selected]

            st.dataframe(df)
            
            # Botão de Download SVG
            svg = df_to_svg(df)
            st.download_button("Baixar matriz (SVG)", data=svg.encode("utf-8"), file_name="matriz_fechamento.svg", mime="image/svg+xml")
     
    else:
        st.info("Escolha uma implementação e clique em 'Gerar e Analisar Grafo' para carregar os dados.")

    # Ferramentas laterais (Métricas, etc)
    draw_graph_api_sidebar()

if __name__ == "__main__":
    app()