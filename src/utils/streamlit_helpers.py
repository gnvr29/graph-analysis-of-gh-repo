import streamlit as st
import src.services.graph_service as graph_service
import os
import pandas as pd
import altair as alt
from src.analysis import centrality_metrics
from typing import List, Tuple
from src.analysis import community_metrics 

def draw_graph_api_sidebar():
    """
    Desenha o painel de ferramentas de análise do grafo na sidebar.
    
    Lê os nomes dos vértices do st.session_state e chama o 
    graph_service para executar a lógica da API.
    """

    if 'community_results' not in st.session_state:
        st.session_state.community_results = None
    if 'centrality_results' not in st.session_state:
        st.session_state.centrality_results = None

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
    propriedades_gerais(vertex_names)

    # --- Expander 2: Análise de Vértice ---
    analise_vertices(vertex_names,name_to_idx)
    
    # --- Expander 3: Análise de Aresta (u, v) ---
    analise_arestas(vertex_names, name_to_idx)

    # --- Expander 4: Convergência / Divergência ---
    convergencia_divergencia(vertex_names,name_to_idx)

    # --- Expander 5: Modificar Grafo ---
    modificar_grafo(vertex_names, name_to_idx)

    # --- Expander 6: Exportar Grafo ---
    exportar_grafo()

    # --- Expander 6: Métricas de Centralidade ---
    metricas_centralidade()

    # --- Expander 7: Métricas de Comunidade ---
    metricas_comunidade()


def propriedades_gerais(vertex_names):
    with st.sidebar.expander("Propriedades Gerais", expanded=True):
        try:
            st.metric("Vértices", len(vertex_names))
            st.metric("Arestas", graph_service.get_edge_count())
            
            col1, col2 = st.columns(2)
            col1.metric("É Conexo?", "Sim" if graph_service.is_connected() else "Não")
            col2.metric("É Vazio?", "Sim" if graph_service.is_empty() else "Não")
            col1.metric("É Completo?", "Sim" if graph_service.is_complete() else "Não")
        except Exception as e:
            st.error(f"Erro na API: {e}")

def analise_vertices(vertex_names, name_to_idx):
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

def analise_arestas(vertex_names, name_to_idx):
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

def convergencia_divergencia(vertex_names, name_to_idx):
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
                
def modificar_grafo(vertex_names, name_to_idx):
     with st.sidebar.expander("Modificar Grafo"):
        st.warning("Modificações afetam o grafo em memória.")

        _add_edge(vertex_names, name_to_idx)

        _remove_edge(vertex_names, name_to_idx)

        _add_vertex(vertex_names)

def exportar_grafo():
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

def metricas_centralidade():
    with st.sidebar.expander("Métricas de Centralidade"):
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

            degree_mode = st.selectbox("Modo (Degree)", ("total", "out", "in"))

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
                        scores = centrality_metrics.degree_centrality(out_adj, in_adj, weighted=True, mode=degree_mode)
                        expl = "Degree: soma dos pesos das arestas (modo selecionado)."
                    elif metric_choice == "Betweenness (weighted)":
                        scores = centrality_metrics.betweenness_centrality_weighted(out_adj)
                        expl = "Betweenness: contribuição em caminhos mínimos ponderados."
                    elif metric_choice == "PageRank":
                        scores = centrality_metrics.pagerank(out_adj, damping=damping, max_iter=pr_iters)
                        expl = "PageRank: importância distribuída via arestas ponderadas (iteração de potência)."
                    elif metric_choice == "Eigenvector Centrality":
                        scores = centrality_metrics.eigenvector_centrality(out_adj, in_adj, max_iter=int(eig_iters))
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

def metricas_comunidade():
    with st.sidebar.expander("Métricas de Comunidade"):
        with st.form("community_metrics_form"):
            max_splits = st.number_input("Max Divisões (G-N)", min_value=1, value=5, step=1, key="form_comm_max_splits")

            comm_metric_choice = st.selectbox(
                "Escolha a métrica:",
                ("Community Detection (Girvan-Newman)", "Bridging Ties"),
                key="form_comm_choice"
            )

            st.markdown("---")
            st.markdown("**Interpretação rápida:** O **Girvan-Newman** (baseado em Betweenness Centrality) é não-ponderado e remove as arestas de maior intermediação para encontrar comunidades. O número de divisões afeta a granularidade.")

            submitted = st.form_submit_button("Calcular Comunidade")
            
            if submitted:
                # O cálculo só ocorre quando o botão do formulário é clicado
                try:
                    # 1. Pré-cálculo das Listas de Adjacência
                    adj_list = graph_service.get_adjacency_list()
                    n = len(adj_list)
                    out_adj: List[List[Tuple[int, float]]] = [ [(v, float(w)) for v, w in nbrs.items()] for nbrs in adj_list ]

                    names_map = st.session_state.get('idx_to_name_map') or st.session_state.get('idx_to_name', {})
                    
                    # 2. Lógica de Cálculo
                    if comm_metric_choice == "Community Detection (Girvan-Newman)":
                        communities = community_metrics.girvan_newman_community_detection(out_adj, max_splits=int(max_splits))
                        expl = f"Comunidades encontradas após divisões (máximo {max_splits} remoções de arestas)."
                        
                        data = []
                        for i, community in enumerate(communities):
                            community_members = ", ".join([names_map.get(node_idx, str(node_idx)) for node_idx in community])
                            data.append({
                                'Comunidade': i + 1,
                                'Tamanho': len(community),
                                'Membros': community_members
                            })
                        
                        df = pd.DataFrame(data)
                        
                        # 3. Armazena os resultados no estado da sessão
                        st.session_state.community_results = {
                            'metric': comm_metric_choice,
                            'expl': expl,
                            'df': df,
                            'is_bridge': False
                        }

                    elif comm_metric_choice == "Bridging Ties":
                        communities = community_metrics.girvan_newman_community_detection(out_adj, max_splits=int(max_splits))
                        bridging_ties = community_metrics.find_bridging_ties(out_adj, communities)
                        expl = f"Arestas de ponte que conectam as {len(communities)} comunidades encontradas."
                        
                        data = []
                        for u, v, w in bridging_ties:
                            data.append({
                                'Origem': names_map.get(u, str(u)),
                                'Destino': names_map.get(v, str(v)),
                                'Peso': float(w)
                            })
                        
                        df = pd.DataFrame(data).sort_values(by='Peso', ascending=False)
                        
                        # 3. Armazena os resultados no estado da sessão
                        st.session_state.community_results = {
                            'metric': comm_metric_choice,
                            'expl': expl,
                            'df': df,
                            'is_bridge': True
                        }
                    
                    st.toast('Cálculo de comunidade finalizado!', icon='✅')

                except Exception as e:
                    st.error(f"Falha ao calcular métrica de comunidade: {e}")
                    st.exception(e)
                    st.session_state.community_results = None

        # 4. Exibição dos resultados (fora do formulário)
        if st.session_state.community_results:
            res = st.session_state.community_results
            st.markdown("### Resultados (Último Cálculo)")
            st.write(res['expl'])
            
            if res['is_bridge']:
                st.subheader(f"{res['metric']} (Total: {len(res['df'])})")
                top_n_bridge = st.number_input("Top N Arestas de Ponte", min_value=0, value=10, step=1, key="bridge_top_n_display")
                if top_n_bridge > 0:
                    df_display = res['df'].head(top_n_bridge)
                else:
                    df_display = res['df']
                st.table(df_display)
            else:
                st.subheader(f"{res['metric']} (Total: {len(res['df'])})")
                st.table(res['df'])

def _add_edge(vertex_names, name_to_idx):
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
                graph_service.add_edge(u, v, weight_add)

                # Atualiza highlight
                st.session_state["last_added_edge"] = (u, v)
                st.session_state["last_added_vertex"] = None  # ou destaque algum vértice se quiser

                st.success(f"Aresta ({u_name_add}, {v_name_add}) adicionada com peso {weight_add}.")
                st.rerun() 
            except Exception as e:
                st.error(f"Erro ao adicionar aresta: {e}")

def _remove_edge(vertex_names, name_to_idx):
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

def _add_vertex(vertex_names):
    with st.form("form_add_vertex"):
        st.subheader("Adicionar Vértice")
        vertex_name_input = st.text_input(
            "Nome do novo vértice:",
            value="",
            placeholder="Digite um nome opcional"
        )
        submitted_add_vertex = st.form_submit_button("Adicionar Vértice")
        
        if submitted_add_vertex:
            try:
                graph = st.session_state.graph_obj
                new_index = graph.addVertex()  # índice único

                # Nome do vértice
                vertex_name = vertex_name_input.strip() or f"Novo_{new_index}"
                st.session_state.idx_to_name_map[new_index] = vertex_name
                st.session_state.vertex_names_list.append(vertex_name)

                # ===== Mantém todos os novos vértices =====
               # Adiciona para destaque
                if "new_vertices" not in st.session_state:
                    st.session_state.new_vertices = set()
                st.session_state.new_vertices.add(new_index)

                # Ainda pode manter last_added_vertex para foco imediato
                st.session_state.last_added_vertex = new_index

                st.success(f"Vértice '{vertex_name}' adicionado com sucesso! (Índice: {new_index})")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao adicionar vértice: {e}")

