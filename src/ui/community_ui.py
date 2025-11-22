# src/analysis/community_ui.py

import streamlit as st
import pandas as pd
from typing import List, Tuple, Dict, Any
import plotly.express as px # Importa Plotly para gráficos interativos

# Presumimos que community_metrics está disponível
# O módulo community_metrics deve estar no scope global do script principal
# (ou acessível via st.session_state como no seu código original)
from src.analysis import community_metrics 

def display_community_metrics(out_adj: List[List[Tuple[int, float]]], names_map: Dict[int, str], graph_choice_name: str):
    """
    Desenha o formulário de Comunidade, calcula a métrica escolhida 
    e exibe os resultados com visualizações aprimoradas.
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
                # O cálculo G-N é necessário para ambas as métricas
                # Mantendo o acesso via st.session_state.community_metrics conforme seu código original
                communities = st.session_state.community_metrics.girvan_newman_community_detection(out_adj, max_splits=int(max_splits))
                
                if comm_metric_choice == "Community Detection (Girvan-Newman)":
                    expl = f"Comunidades encontradas após {len(communities)} partições (máximo {max_splits} remoções de arestas)."
                    
                    data = []
                    for i, community in enumerate(communities):
                        community_members = [names_map.get(node_idx, str(node_idx)) for node_idx in community]
                        data.append({
                            'Comunidade ID': i + 1,
                            'Tamanho': len(community),
                            'Membros': "<br>".join(community_members), # <-- MODIFICADO: Usa <br> para quebras de linha no hover
                            'Membros_Lista': community_members # Lista para exibição detalhada no expander
                        })
                    
                    df = pd.DataFrame(data)
                    # <-- MODIFICADO: Ordena as comunidades por tamanho antes de armazenar
                    df = df.sort_values(by='Tamanho', ascending=False).reset_index(drop=True)
                    # Convert 'Comunidade ID' para string para garantir tratamento categórico no Plotly
                    df['Comunidade ID'] = df['Comunidade ID'].astype(str)

                    st.session_state.community_results = {
                        'metric': comm_metric_choice,
                        'expl': expl,
                        'df': df,
                        'is_bridge': False,
                        'num_comm': len(communities)
                    }

                elif comm_metric_choice == "Bridging Ties":
                    # Mantendo o acesso via st.session_state.community_metrics conforme seu código original
                    bridging_ties = st.session_state.community_metrics.find_bridging_ties(out_adj, communities)
                    expl = f"Arestas de ponte que conectam as {len(communities)} comunidades encontradas."
                    
                    data = []
                    for u, v, w in bridging_ties:
                        data.append({
                            'Origem': names_map.get(u, str(u)),
                            'Destino': names_map.get(v, str(v)),
                            'Peso': float(w)
                        })
                    
                    if data: # Se a lista 'data' não estiver vazia
                        df = pd.DataFrame(data).sort_values(by='Peso', ascending=False).reset_index(drop=True)
                    else: # Se a lista 'data' estiver vazia, cria um DataFrame vazio com as colunas esperadas
                        df = pd.DataFrame(columns=['Origem', 'Destino', 'Peso'])
                    
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
        
        if res['is_bridge']: # Visualização de Arestas de Ponte
            st.markdown(f"**{res['metric']}** (Total: {len(df_display)})")
            
            if not df_display.empty:
                # Gráfico para Arestas de Ponte
                st.markdown("### Top Arestas de Ponte por Peso")
                
                slider_max = min(20, len(df_display)) if len(df_display) > 0 else 1
                slider_value = min(10, len(df_display)) if len(df_display) > 0 else 1

                top_n_bridge_chart = st.slider("Número de arestas para o gráfico:", min_value=1, max_value=slider_max, value=slider_value, key="bridge_chart_slider")
                
                if top_n_bridge_chart > 0:
                    df_chart = df_display.head(top_n_bridge_chart).copy()
                    df_chart['Aresta'] = df_chart['Origem'] + " - " + df_chart['Destino']
                    
                    fig = px.bar(df_chart, 
                                 x='Peso', 
                                 y='Aresta', 
                                 orientation='h', 
                                 title='Arestas de Ponte por Peso (Top N)',
                                 labels={'Peso': 'Peso da Aresta', 'Aresta': 'Conexão'},
                                 height=max(300, top_n_bridge_chart * 40))
                    fig.update_layout(yaxis={'categoryorder':'total ascending'})
                    st.plotly_chart(fig, use_container_width=True)

                st.markdown("### Detalhes das Arestas de Ponte")
                
                num_input_max = len(df_display)
                num_input_value = min(10, len(df_display)) if len(df_display) > 0 else 0

                top_n_bridge_table = st.number_input("Número de Arestas de Ponte para Tabela (0 para todas)", min_value=0, max_value=num_input_max, value=num_input_value, step=1, key="bridge_top_n_display_page")
                
                if top_n_bridge_table > 0 and not df_display.empty:
                    st.dataframe(df_display.head(top_n_bridge_table), use_container_width=True)
                elif not df_display.empty:
                    st.dataframe(df_display, use_container_width=True)
                else:
                    st.info("Nenhuma aresta de ponte encontrada para exibição.")

            else:
                st.info("Nenhuma aresta de ponte encontrada.")

        else: # Visualização de Detecção de Comunidade
            st.markdown(f"**{res['metric']}** ({res['num_comm']} Comunidade(s) Encontrada(s))")
            
            if not df_display.empty:
                # Gráfico para Tamanho das Comunidades
                st.markdown("### Tamanho das Comunidades")
                fig = px.bar(df_display, 
                             x='Comunidade ID', # Já é string e ordenado por Tamanho
                             y='Tamanho', 
                             title='Tamanho de Cada Comunidade (Ordenado por Tamanho)',
                             labels={'Tamanho': 'Número de Membros', 'Comunidade ID': 'ID da Comunidade'},
                             hover_data={'Membros': True, 'Comunidade ID': False, 'Tamanho': False})
                # <-- MODIFICADO: Garante que as maiores comunidades apareçam primeiro no gráfico
                fig.update_xaxes(categoryorder='total descending') 
                st.plotly_chart(fig, use_container_width=True)

                st.markdown("### Detalhes das Comunidades")
                for index, row in df_display.iterrows():
                    with st.expander(f"Comunidade {row['Comunidade ID']} (Membros: {row['Tamanho']})"):
                        st.write(f"**Membros:**")
                        if row['Membros_Lista']:
                            for member in row['Membros_Lista']:
                                st.markdown(f"- {member}")
                        else:
                            st.markdown("Nenhum membro nesta comunidade.")
            else:
                st.info("Nenhuma comunidade encontrada.")