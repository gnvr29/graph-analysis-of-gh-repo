# src/analysis/centrality_ui.py
import streamlit as st
import pandas as pd
import altair as alt
import io, csv
from typing import List, Tuple, Dict, Any

# Presumimos que centrality_metrics está disponível via import no script principal
# from src.analysis import centrality_metrics 

def display_centrality_metrics(out_adj: List[List[Tuple[int, float]]], in_adj: List[List[Tuple[int, float]]], names_map: Dict[int, str], graph_choice_name: str):
    """
    Desenha o formulário de Centralidade, calcula a métrica escolhida 
    e exibe os resultados.
    """
    st.header("Cálculo de Centralidade")

    with st.form("centrality_metrics_form"):
        metric_choice = st.selectbox(
            "Escolha a métrica:",
            ("Degree (weighted)", "Betweenness (weighted)", "PageRank", "Eigenvector Centrality"),
            key="centrality_choice"
        )

        col_top, col_mode = st.columns([1, 2])
        top_n = col_top.number_input("Top N (0 = todos)", min_value=0, value=10, step=1)
        degree_mode = col_mode.selectbox("Modo (Degree)", ("total", "out", "in"))

        st.markdown("---")
        st.subheader("Configurações Avançadas:")
        col_pr, col_eig = st.columns(2)
        damping = col_pr.slider("Damping (PageRank)", min_value=0.0, max_value=1.0, value=0.85)
        pr_iters = col_pr.number_input("Iterações (PageRank)", min_value=10, value=100, step=10)
        eig_iters = col_eig.number_input("Iterações (Eigenvector)", min_value=10, value=100, step=10)

        submitted_centrality = st.form_submit_button("Calcular Centralidade")

    if submitted_centrality:
        with st.spinner(f"Calculando {metric_choice} para {graph_choice_name}..."):
            try:
                # O módulo centrality_metrics deve estar no scope global do script principal
                # e é acessado indiretamente via st.session_state, ou importado no arquivo principal.
                
                scores: Dict[int, float] = {}
                expl: str = ""

                if metric_choice == "Degree (weighted)":
                    scores = st.session_state.centrality_metrics.degree_centrality(out_adj, in_adj, weighted=True, mode=degree_mode)
                    expl = "Degree: soma dos pesos das arestas (modo selecionado)."
                elif metric_choice == "Betweenness (weighted)":
                    scores = st.session_state.centrality_metrics.betweenness_centrality_weighted(out_adj)
                    expl = "Betweenness: contribuição em caminhos mínimos ponderados."
                elif metric_choice == "PageRank":
                    scores = st.session_state.centrality_metrics.pagerank(out_adj, damping=damping, max_iter=pr_iters)
                    expl = "PageRank: importância distribuída via arestas ponderadas (iteração de potência)."
                elif metric_choice == "Eigenvector Centrality":
                    scores = st.session_state.centrality_metrics.eigenvector_centrality(out_adj, in_adj, max_iter=int(eig_iters))
                    expl = "Eigenvector: influência considerando a importância dos vizinhos (autovetor)."

                items = sorted(scores.items(), key=lambda it: it[1], reverse=True)
                if top_n > 0:
                    items = items[:top_n]

                df = pd.DataFrame([{'Rank': i+1, 'Author': names_map.get(idx, str(idx)), 'Score': float(score)} for i, (idx, score) in enumerate(items)])

                st.session_state.centrality_results_df = df
                st.session_state.centrality_results_metric = metric_choice
                st.session_state.centrality_results_expl = expl
                
            except Exception as e:
                st.error(f"Falha ao calcular métrica de centralidade: {e}")
                st.exception(e)

    # Exibe resultados se existirem
    if 'centrality_results_df' in st.session_state and not st.session_state.centrality_results_df.empty:
        df_display = st.session_state.centrality_results_df
        metric_name = st.session_state.centrality_results_metric
        expl = st.session_state.centrality_results_expl
        
        st.subheader(f"Resultados — {metric_name}")
        st.write(expl)
        st.table(df_display)

        # Gráfico
        chart = alt.Chart(df_display).mark_bar().encode(
            x=alt.X('Score:Q'),
            y=alt.Y('Author:N', sort='-x'),
            tooltip=['Author', 'Score']
        ).properties(height=40 * len(df_display))
        st.altair_chart(chart, use_container_width=True)

        # Download CSV
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(['rank', 'author', 'score'])
        for _, row in df_display.iterrows():
            writer.writerow([int(row['Rank']), row['Author'], float(row['Score'])])
        st.download_button(
            'Baixar CSV', 
            data=buf.getvalue().encode('utf-8'), 
            file_name=f'{metric_name.lower().replace(" ", "_")}_{graph_choice_name.lower().replace(" ", "_")}_results.csv', 
            mime='text/csv'
        )