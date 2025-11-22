# src/analysis/community_ui.py
import streamlit as st
import pandas as pd
from typing import List, Tuple, Dict, Any

# Presumimos que community_metrics está disponível
# from src.analysis import community_metrics 

def display_community_metrics(out_adj: List[List[Tuple[int, float]]], names_map: Dict[int, str], graph_choice_name: str):
    """
    Desenha o formulário de Comunidade, calcula a métrica escolhida 
    e exibe os resultados.
    """
    st.header("Cálculo de Comunidade (Girvan-Newman & Bridging Ties)")

    with st.form("community_metrics_form_page"):
        col_split, col_metric = st.columns(2)
        max_splits = col_split.number_input("Max Divisões (G-N)", min_value=1, value=5, step=1, key="page_comm_max_splits")

        comm_metric_choice = col_metric.selectbox(
            "Escolha a métrica:",
            ("Community Detection (Girvan-Newman)", "Bridging Ties"),
            key="page_comm_choice"
        )
        
        submitted_community = st.form_submit_button("Calcular Comunidade")
        
    if submitted_community:
        with st.spinner(f"Calculando {comm_metric_choice} para {graph_choice_name}..."):
            try:
                # O módulo community_metrics deve estar no scope global do script principal
                
                # O cálculo G-N é necessário para ambas as métricas
                communities = st.session_state.community_metrics.girvan_newman_community_detection(out_adj, max_splits=int(max_splits))
                
                if comm_metric_choice == "Community Detection (Girvan-Newman)":
                    expl = f"Comunidades encontradas após {len(communities)} partições (máximo {max_splits} remoções de arestas)."
                    
                    data = []
                    for i, community in enumerate(communities):
                        community_members = ", ".join([names_map.get(node_idx, str(node_idx)) for node_idx in community])
                        data.append({
                            'Comunidade': i + 1,
                            'Tamanho': len(community),
                            'Membros': community_members
                        })
                    
                    df = pd.DataFrame(data)
                    
                    st.session_state.community_results = {
                        'metric': comm_metric_choice,
                        'expl': expl,
                        'df': df,
                        'is_bridge': False,
                        'num_comm': len(communities)
                    }

                elif comm_metric_choice == "Bridging Ties":
                    bridging_ties = st.session_state.community_metrics.find_bridging_ties(out_adj, communities)
                    expl = f"Arestas de ponte que conectam as {len(communities)} comunidades encontradas."
                    
                    data = []
                    for u, v, w in bridging_ties:
                        data.append({
                            'Origem': names_map.get(u, str(u)),
                            'Destino': names_map.get(v, str(v)),
                            'Peso': float(w)
                        })
                    
                    df = pd.DataFrame(data).sort_values(by='Peso', ascending=False)
                    
                    st.session_state.community_results = {
                        'metric': comm_metric_choice,
                        'expl': expl,
                        'df': df,
                        'is_bridge': True,
                        'num_comm': len(communities)
                    }
                
                st.toast('Cálculo de comunidade finalizado!', icon='✅')

            except Exception as e:
                st.error(f"Falha ao calcular métrica de comunidade: {e}")
                st.exception(e)
                st.session_state.community_results = None

    # Exibição dos resultados (fora do formulário)
    if 'community_results' in st.session_state and st.session_state.community_results:
        res = st.session_state.community_results
        st.subheader("Resultados")
        st.write(res['expl'])
        
        df_display = res['df']
        
        if res['is_bridge']:
            st.markdown(f"**{res['metric']}** (Total: {len(df_display)})")
            top_n_bridge = st.number_input("Top N Arestas de Ponte", min_value=0, value=10, step=1, key="bridge_top_n_display_page")
            if top_n_bridge > 0 and len(df_display) > 0:
                df_display = df_display.head(top_n_bridge)
            st.table(df_display)
        else:
            st.markdown(f"**{res['metric']}** ({res['num_comm']} Comunidade(s) Encontrada(s))")
            st.table(df_display)