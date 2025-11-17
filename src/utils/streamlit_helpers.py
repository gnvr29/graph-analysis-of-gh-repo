import streamlit as st
import src.services.graph_service as graph_service
import os
import pandas as pd
import altair as alt
from src.analysis import metrics
from typing import List, Tuple

def draw_graph_api_sidebar():
    """
    Desenha o painel de ferramentas de análise do grafo na sidebar.
    
    Lê os nomes dos vértices do st.session_state e chama o 
    graph_service para executar a lógica da API.
    """

    try:
        if 'graph_obj' not in st.session_state or st.session_state.graph_obj is None:
             st.sidebar.info("Gere um grafo na página principal para habilitar as ferramentas de análise.")
             return
    except Exception:
        st.sidebar.info("Gere um grafo na página principal para habilitar as ferramentas de análise.")
        return

    # Recupera os dados de MAPEAMENTO
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
    st.sidebar.header("Ferramentas de Análise")
    st.sidebar.caption(f"Analisando: {type(st.session_state.graph_obj).__name__}")


    # --- Expander 1: Propriedades Gerais ---
    with st.sidebar.expander("Propriedades Gerais", expanded=True):
        try:
            st.metric("Vértices", graph_service.get_vertex_count())
            st.metric("Arestas", graph_service.get_edge_count())
            
            col1, col2 = st.columns(2)
            col1.metric("É Conexo?", "Sim" if graph_service.is_connected() else "Não")
            col2.metric("É Vazio?", "Sim" if graph_service.is_empty() else "Não")
            col1.metric("É Completo?", "Sim" if graph_service.is_complete() else "Não")
        except Exception as e:
            st.error(f"Erro na API: {e}")

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

                if graph_service.is_successor(u_idx, v_idx):
                    weight = graph_service.get_edge_weight(u_idx, v_idx)
                    st.success(f"Sim, (u, v) existe (Peso: {weight:.1f}).")
                else:
                    st.error("Não, (u, v) não existe.")

                if graph_service.is_predecessor(u_idx, v_idx):
                    st.info(f"Sim, (v, u) existe (v é predecessor).")
                else:
                    st.info("Não, (v, u) não existe.")
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
                        
                    if graph_service.is_convergent(u1, v1, u2, v2):
                        st.success(f"**Convergente**: Chegam em '{v1_name}'.")
                    else:
                        st.info("Não são convergentes.")
                except Exception as e:
                        st.error(f"Erro: {e}")

    with st.sidebar.expander("Modificar Grafo"):
        st.warning("Modificações afetam o grafo em memória.")

        with st.form("form_add_edge"):
            st.subheader("Adicionar / Atualizar Aresta")
            u_name_add = st.selectbox("Origem (u):", vertex_names, key="sb_u_add")
            v_name_add = st.selectbox("Destino (v):", vertex_names, key="sb_v_add")
            weight_add = st.number_input("Peso:", min_value=0.1, value=1.0, step=0.1)
            
            submitted_add = st.form_submit_button("Adicionar/Atualizar Aresta")
            if submitted_add:
                try:
                    u = name_to_idx[u_name_add]
                    v = name_to_idx[v_name_add]
                    result = graph_service.add_edge(u, v, weight_add)
                    if result:
                        st.success(f"Aresta ({u_name_add}, {v_name_add}) adicionada com peso {weight_add}.")
                    else:
                        st.info(f"Aresta ({u_name_add}, {v_name_add}) foi ignorada. (Grafo simples não permite laços e arestas duplicadas.)")
                    st.rerun()
                except Exception as e:
                    st.error(f"Erro ao adicionar aresta: {e}")

        with st.form("form_remove_edge"):
            st.subheader("Remover Aresta")
            u_name_rem = st.selectbox("Origem (u):", vertex_names, key="sb_u_rem")
            v_name_rem = st.selectbox("Destino (v):", vertex_names, key="sb_v_rem")
            
            submitted_rem = st.form_submit_button("Remover Aresta")
            if submitted_rem:
                try:
                    u = name_to_idx[u_name_rem]
                    v = name_to_idx[v_name_rem]
                    if not graph_service.has_edge(u, v):
                        st.warning("Aresta já não existe.")
                    else:
                        graph_service.remove_edge(u, v)
                        st.success(f"Aresta ({u_name_rem}, {v_name_rem}) removida.")
                        st.rerun()
                except Exception as e:
                    st.error(f"Erro ao remover aresta: {e}")

    with st.sidebar.expander("Exportar Grafo"):
        export_dir = "exports"
        if not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir)
            except OSError as e:
                st.error(f"Não foi possível criar diretório 'exports': {e}")
                return

        filename = st.text_input("Nome do Arquivo:", "meu_grafo.gexf")
        
        if st.button("Exportar para GEXF (Gephi)"):
            try:
                full_path = os.path.join(export_dir, filename)
                graph_service.export_to_gephi(full_path)
                st.success(f"Grafo salvo em: {full_path}")
            except Exception as e:
                st.error(f"Erro ao exportar: {e}")

    # --- Expander 6: Métricas de Rede (apenas ponderadas, visual melhorada) ---
    with st.sidebar.expander("Métricas de Rede"):
        try:
            metric_choice = st.selectbox(
                "Escolha a métrica ponderada:",
                (
                    "Degree (weighted)",
                    "Betweenness (weighted)",
                    "PageRank",
                    "Eigenvector Centrality",
                ),
            )

            top_n = st.number_input("Top N (0 = todos)", min_value=0, value=10, step=1)

            # Degree options (weighted only)
            degree_mode = st.selectbox("Modo (Degree)", ("total", "out", "in"))

            # PageRank / Eigen params
            damping = st.slider("Damping (PageRank)", min_value=0.0, max_value=1.0, value=0.85)
            pr_iters = st.number_input("Iterações (PageRank)", min_value=10, value=100, step=10)
            eig_iters = st.number_input("Iterações (Eigenvector)", min_value=10, value=100, step=10)

            st.markdown("---")
            st.markdown("**Interpretação rápida:** métricas ponderadas usam os pesos definidos no projeto (COMMENT=2, ISSUE_COMMENTED=3, REVIEW=4, MERGE=5). Use Top N para limitar a visualização.")

            if st.button("Calcular Métrica"):
                try:
                    adj_list = graph_service.get_adjacency_list()
                    n = len(adj_list)
                    out_adj: List[List[Tuple[int, float]]] = [ [(v, float(w)) for v, w in nbrs.items()] for nbrs in adj_list ]
                    in_adj: List[List[Tuple[int, float]]] = [[] for _ in range(n)]
                    for u, nbrs in enumerate(out_adj):
                        for v, w in nbrs:
                            in_adj[v].append((u, w))

                    if metric_choice == "Degree (weighted)":
                        scores = metrics.degree_centrality(out_adj, in_adj, weighted=True, mode=degree_mode)
                        expl = "Degree ponderado: soma dos pesos das arestas (modo selecionado)."
                    elif metric_choice == "Betweenness (weighted)":
                        scores = metrics.betweenness_centrality_weighted(out_adj)
                        expl = "Betweenness ponderado: contribuição em caminhos mínimos ponderados."
                    elif metric_choice == "PageRank":
                        scores = metrics.pagerank(out_adj, damping=damping, max_iter=pr_iters)
                        expl = "PageRank: importância distribuída via arestas ponderadas (iteração de potência)."
                    elif metric_choice == "Eigenvector Centrality":
                        scores = metrics.eigenvector_centrality(out_adj, in_adj, max_iter=int(eig_iters))
                        expl = "Eigenvector: influência considerando a importância dos vizinhos (autovetor)."
                    else:
                        st.error("Métrica desconhecida")
                        scores = {}
                        expl = ""

                    items = sorted(scores.items(), key=lambda it: it[1], reverse=True)
                    if top_n > 0:
                        items = items[:top_n]

                    names_map = st.session_state.get('idx_to_name_map') or st.session_state.get('idx_to_name', {})
                    df = pd.DataFrame([{'Rank': i+1, 'Author': names_map.get(idx, str(idx)), 'Score': float(score)} for i, (idx, score) in enumerate(items)])

                    st.subheader(f"Resultados — {metric_choice}")
                    st.write(expl)
                    st.table(df)

                    if not df.empty:
                        chart = alt.Chart(df).mark_bar().encode(
                            x=alt.X('Score:Q'),
                            y=alt.Y('Author:N', sort='-x'),
                            tooltip=['Author', 'Score']
                        ).properties(height=40 * len(df))
                        st.altair_chart(chart, use_container_width=True)

                    # CSV download
                    import io, csv
                    buf = io.StringIO()
                    writer = csv.writer(buf)
                    writer.writerow(['rank', 'author', 'score'])
                    for _, row in df.iterrows():
                        writer.writerow([int(row['Rank']), row['Author'], float(row['Score'])])
                    st.download_button('Baixar CSV', data=buf.getvalue().encode('utf-8'), file_name='metric_results.csv', mime='text/csv')

                except Exception as e:
                    st.error(f"Falha ao calcular métrica: {e}")
        except Exception as e:
            st.error(f"Erro preparando a UI de métricas: {e}")