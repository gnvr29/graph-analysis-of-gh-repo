import streamlit as st
# NOVO: Importa o service layer
import src.services.graph_service as graph_service

def draw_graph_api_sidebar():
    """
    Desenha o painel de ferramentas de análise do grafo na sidebar.
    
    Lê os nomes dos vértices do st.session_state e chama o 
    graph_service para executar a lógica da API.
    """

    try:
        # Tenta chamar a função mais leve. Se falhar, o grafo não está no state.
        graph_service.get_vertex_count()
    except Exception:
        st.sidebar.info("Gere um grafo na página principal para habilitar as ferramentas de análise.")
        return

    # 2. Recupera os dados de MAPEAMENTO 
    try:
        vertex_names = st.session_state.get('vertex_names_list', [])
        name_to_idx = st.session_state.get('name_to_idx_map', {})

        if not vertex_names or not name_to_idx:
            st.sidebar.warning("Mapeamento de nomes não encontrado. Usando índices.")
            vertex_count = graph_service.get_vertex_count() 
            vertex_names = [str(i) for i in range(vertex_count)]
            name_to_idx = {str(i): i for i in range(vertex_count)}
            st.session_state.vertex_names_list = vertex_names
            st.session_state.name_to_idx_map = name_to_idx

    except Exception as e:
        st.sidebar.error(f"Erro ao carregar mapeamento de nomes: {e}")
        return

    st.sidebar.divider()
    st.sidebar.header("🔬 Ferramentas de Análise")

    # --- Expander 1: Propriedades Gerais ---
    with st.sidebar.expander("Propriedades Gerais"):
        try:
            # MODIFICADO: Chama as funções do graph_service
            st.metric("Vértices", graph_service.get_vertex_count())
            st.metric("Arestas", graph_service.get_edge_count())
            
            col1, col2 = st.columns(2)
            col1.metric("É Conexo?", "Sim" if graph_service.is_connected() else "Não")
            col2.metric("É Vazio?", "Sim" if graph_service.is_empty() else "Não")
            col1.metric("É Completo?", "Sim" if graph_service.is_complete() else "Não")
        except (ValueError, NotImplementedError) as e:
            st.error(f"Erro na API: {e}")
        except Exception as e:
            st.error(f"Erro inesperado: {e}")

    # --- Expander 2: Análise de Vértice ---
    with st.sidebar.expander("Análise de Vértice"):
        selected_v_name = st.selectbox(
            "Selecione um Vértice (v):",
            vertex_names,
            key="sidebar_v_analysis"
        )
        if selected_v_name:
            try:
                v_idx = name_to_idx[selected_v_name]
                st.metric("Grau de Entrada (In)", graph_service.get_vertex_in_degree(v_idx))
                st.metric("Grau de Saída (Out)", graph_service.get_vertex_out_degree(v_idx))
                st.metric("Peso do Vértice", f"{graph_service.get_vertex_weight(v_idx):.2f}")
            except (ValueError, NotImplementedError) as e:
                st.error(f"Erro na API: {e}")
            except Exception as e:
                st.error(f"Erro: {e}")
    
    # --- Expander 3: Análise de Aresta (u, v) ---
    with st.sidebar.expander("Análise de Aresta (u, v)"):
        u_name = st.selectbox("Vértice de Origem (u):", vertex_names, key="sidebar_u_edge")
        v_name = st.selectbox("Vértice de Destino (v):", vertex_names, key="sidebar_v_edge")
        
        if st.button("Analisar Relação (u, v)", key="sidebar_check_edge"):
            try:
                u_idx = name_to_idx[u_name]
                v_idx = name_to_idx[v_name]

                # MODIFICADO: Chama as funções do graph_service
                if graph_service.is_successor(u_idx, v_idx):
                    weight = graph_service.get_edge_weight(u_idx, v_idx)
                    st.success(f"Sim, (u, v) existe (Peso: {weight:.1f}).")
                else:
                    st.error("Não, (u, v) não existe.")

                # MODIFICADO: Chama as funções do graph_service
                if graph_service.is_predecessor(u_idx, v_idx):
                    st.info(f"Sim, (v, u) existe (v é predecessor).")
                else:
                    st.info("Não, (v, u) não existe.")
            except (ValueError, NotImplementedError) as e:
                st.error(f"Erro na API: {e}")
            except Exception as e:
                    st.error(f"Erro: {e}")

    # --- Expander 4: Convergência / Divergência ---
    with st.sidebar.expander("Convergência / Divergência"):
        st.markdown("Aresta 1: (u1, v1)")
        u1_name = st.selectbox("Vértice (u1):", vertex_names, key="sidebar_u1")
        v1_name = st.selectbox("Vértice (v1):", vertex_names, key="sidebar_v1")
        
        st.markdown("Aresta 2: (u2, v2)")
        u2_name = st.selectbox("Vértice (u2):", vertex_names, key="sidebar_u2")
        v2_name = st.selectbox("Vértice (v2):", vertex_names, key="sidebar_v2")

        if st.button("Verificar", key="sidebar_check_conv_div"):
            if not (u1_name and v1_name and u2_name and v2_name):
                st.warning("Selecione os 4 vértices.")
            else:
                try:
                    u1 = name_to_idx[u1_name]
                    v1 = name_to_idx[v1_name]
                    u2 = name_to_idx[u2_name]
                    v2 = name_to_idx[v2_name]

                    if graph_service.is_divergent(u1, v1, u2, v2):
                        st.info(f"**Divergente**: Saem de '{u1_name}'.")
                    else:
                        st.info("Não são divergentes.")
                        
                    # MODIFICADO: Chama as funções do graph_service
                    if graph_service.is_convergent(u1, v1, u2, v2):
                        st.success(f"**Convergente**: Chegam em '{v1_name}'.")
                    else:
                        st.info("Não são convergentes.")
                except (ValueError, NotImplementedError) as e:
                    st.error(f"Erro na API: {e}")
                except Exception as e:
                        st.error(f"Erro: {e}")