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
    graph_service para executar a lógica da API, traduzindo NOME -> ÍNDICE ATIVO.
    """
    if 'new_vertices' not in st.session_state:
        st.session_state.new_vertices = set()

    try:
        if 'graph_obj' not in st.session_state or st.session_state.graph_obj is None:
            st.sidebar.info("Gere um grafo na página principal para habilitar as ferramentas de análise.")
            return
        
        graph = st.session_state.graph_obj
    except Exception:
        st.sidebar.info("Gere um grafo na página principal para habilitar as ferramentas de análise.")
        return

    # Recupera os dados de MAPEAMENTO DO GRAFO ATIVO
    try:
        vertex_names = st.session_state.get('vertex_names_list', [])
        idx_to_name_active = st.session_state.get('idx_to_name_map', {}) 

        name_to_idx_active = {name: idx for idx, name in idx_to_name_active.items()} 

        if not vertex_names or not name_to_idx_active:
            if graph.getVertexCount() > 0:
                st.sidebar.warning("Mapeamento de nomes não encontrado. Usando índices padrões.")
                vertex_count = graph.getVertexCount() 
                vertex_names = [str(i) for i in range(vertex_count)]
                name_to_idx_active = {str(i): i for i in range(vertex_count)}
                idx_to_name_active = {i: str(i) for i in range(vertex_count)}
            else:
                st.sidebar.warning("O grafo ativo não contém vértices.")
                return

    except Exception as e:
        st.sidebar.error(f"Erro ao carregar mapeamento de nomes: {e}")
        return

    st.sidebar.divider()
    st.sidebar.header("Ferramentas de Análise")
    st.sidebar.caption(f"Analisando: {type(graph).__name__} (Filtrado)")

    # --- Expander 1: Propriedades Gerais ---
    propriedades_gerais()

    # --- Expander 2: Análise de Vértice ---
    analise_vertices(vertex_names, name_to_idx_active) 
    
    # --- Expander 3: Análise de Aresta (u, v) ---
    analise_arestas(vertex_names, name_to_idx_active) 

    # --- Expander 4: Convergência / Divergência (2 Arestas) ---
    convergencia_divergencia(vertex_names, name_to_idx_active) 

    # --- Expander 5: Modificar Grafo ---
    modificar_grafo(vertex_names, name_to_idx_active, idx_to_name_active) 

    # --- Expander 6: Exportar Grafo ---
    exportar_grafo()


def propriedades_gerais():
    """ Exibe métricas gerais do grafo ATIVO (filtrado). """
    with st.sidebar.expander("Propriedades Gerais", expanded=True):
        try:
            # Todas estas funções operam no grafo ATIVO (graph_obj)
            v_count = graph_service.get_vertex_count()
            e_count = graph_service.get_edge_count()
            
            # Recupera a contagem total de vértices do grafo COMPLETO para contexto
            total_v_count = st.session_state.get("total_vertex_count", v_count)

            st.metric("Vértices (Ativo)", f"{v_count}")
            st.metric("Arestas (Ativo)", e_count)
            
            col1, col2 = st.columns(2)
            col1.metric("É Conexo?", "Sim" if graph_service.is_connected() else "Não")
            col2.metric("É Vazio?", "Sim" if graph_service.is_empty() else "Não")
            col1.metric("É Completo?", "Sim" if graph_service.is_complete() else "Não")
        except Exception as e:
            st.error(f"Erro na API: {e}")

def analise_vertices(vertex_names, name_to_idx):
    """ Analisa um vértice individualmente no grafo ATIVO. """
    with st.sidebar.expander("Análise de Vértice"):
        selected_v_name = st.selectbox(
            "Selecione um Vértice (v):",
            vertex_names,
            key="sidebar_v_analysis"
        )
        if selected_v_name:
            try:
                # O índice é o ATIVO (0..N-1), obtido do mapa name_to_idx_active
                v_idx = name_to_idx[selected_v_name]
                st.metric("Grau de Entrada (In)", graph_service.get_vertex_in_degree(v_idx))
                st.metric("Grau de Saída (Out)", graph_service.get_vertex_out_degree(v_idx))
                st.metric("Peso do Vértice", f"{graph_service.get_vertex_weight(v_idx):.2f}")
            except Exception as e:
                st.error(f"Erro ao obter dados para {selected_v_name}: {e}")

def analise_arestas(vertex_names, name_to_idx):
    """ Analisa a relação (u, v) no grafo ATIVO. """
    with st.sidebar.expander("Análise de Aresta (u, v)"):
        u_name = st.selectbox("Vértice de Origem (u):", vertex_names, key="sidebar_u_edge")
        v_name = st.selectbox("Vértice de Destino (v):", vertex_names, key="sidebar_v_edge")
        
        if st.button("Analisar Relação (u, v)", key="sidebar_check_edge"):
            try:
                # Os índices são os ATIVOS (0..N-1)
                u_idx = name_to_idx[u_name]
                v_idx = name_to_idx[v_name]

                if graph_service.has_edge(u_idx, v_idx):
                    weight = graph_service.get_edge_weight(u_idx, v_idx)
                    st.success(f"Sim, ({u_name}, {v_name}) existe (Peso: {weight:.1f}).")
                else:
                    st.error(f"Não, ({u_name}, {v_name}) não existe.")

                # Verifica aresta inversa
                if graph_service.has_edge(v_idx, u_idx):
                    weight_inv = graph_service.get_edge_weight(v_idx, u_idx)
                    st.info(f"Sim, ({v_name}, {u_name}) existe (Peso: {weight_inv:.1f}).")
                else:
                    st.info(f"Não, ({v_name}, {u_name}) não existe.")

            except Exception as e:
                st.error(f"Erro: {e}")

def convergencia_divergencia(vertex_names, name_to_idx):
    """ 
    Verifica se as arestas (u1, v1) e (u2, v2) são convergentes ou divergentes,
    seguindo a definição formal da API (AbstractGraph) de 4 vértices.
    """
    with st.sidebar.expander("Convergência / Divergência"):
        st.markdown("--- Aresta 1 (u1, v1) ---")
        u1_name = st.selectbox("Vértice Origem (u1):", vertex_names, key="sidebar_u1")
        v1_name = st.selectbox("Vértice Destino (v1):", vertex_names, key="sidebar_v1")
        
        st.markdown("--- Aresta 2 (u2, v2) ---")
        u2_name = st.selectbox("Vértice Origem (u2):", vertex_names, key="sidebar_u2")
        v2_name = st.selectbox("Vértice Destino (v2):", vertex_names, key="sidebar_v2")

        if st.button("Verificar Relações", key="sidebar_check_cd"):
            if not all([u1_name, v1_name, u2_name, v2_name]):
                st.warning("Selecione os 4 vértices para definir as duas arestas.")
                return
            
            try:
                # Obter índices ativos
                u1 = name_to_idx[u1_name]
                v1 = name_to_idx[v1_name]
                u2 = name_to_idx[u2_name]
                v2 = name_to_idx[v2_name]
                
                # Checar se as arestas existem primeiro para dar feedback claro
                edge1_exists = graph_service.has_edge(u1, v1)
                edge2_exists = graph_service.has_edge(u2, v2)
                
                if not edge1_exists or not edge2_exists:
                    msg = "Relação inválida: "
                    if not edge1_exists:
                        msg += f"A aresta ({u1_name}, {v1_name}) não existe. "
                    if not edge2_exists:
                        msg += f"A aresta ({u2_name}, {v2_name}) não existe."
                    st.error(msg)
                    return

                # --- Chamada à API de 4 vértices ---
                
                # 1. Divergência: Verifica se as arestas saem do mesmo nó (u1 = u2)
                if graph_service.is_divergent(u1, v1, u2, v2):
                    st.info(f"**Divergente:** Ambas as arestas saem do nó **{u1_name}**.")
                else:
                    st.info("As arestas NÃO são divergentes (não compartilham origem ou são idênticas).")

                # 2. Convergência: Verifica se as arestas chegam no mesmo nó (v1 = v2)
                if graph_service.is_convergent(u1, v1, u2, v2):
                    st.success(f"**Convergente:** Ambas as arestas chegam no nó **{v1_name}**.")
                else:
                    st.success("As arestas NÃO são convergentes (não compartilham destino ou são idênticas).")

            except Exception as e:
                st.error(f"Erro: {e}")
                
def modificar_grafo(vertex_names, name_to_idx, idx_to_name):
    """ Controles para modificar o grafo ATIVO (Adicionar/Remover Arestas/Vértices). """
    with st.sidebar.expander("Modificar Grafo"):
        st.warning("Modificações afetam o grafo em memória.")

        _add_edge(vertex_names, name_to_idx)

        _remove_edge(vertex_names, name_to_idx)

        _add_vertex(idx_to_name)

def exportar_grafo():
    """ Exporta o grafo ATIVO para GEXF. """
    with st.sidebar.expander("Exportar Grafo"):
        export_dir = "exports"
        if not os.path.exists(export_dir):
            try:
                os.makedirs(export_dir)
            except OSError as e:
                st.error(f"Não foi possível criar diretório 'exports': {e}")
                return

        filename = st.text_input("Nome do Arquivo:", "meu_grafo_ativo.gexf")
        
        if st.button("Exportar para GEXF (Gephi)"):
            try:
                full_path = os.path.join(export_dir, filename)
                # Exporta o grafo ATIVO
                graph_service.export_to_gephi(full_path) 
                st.success(f"Grafo salvo em: {full_path}")
            except Exception as e:
                st.error(f"Erro ao exportar: {e}")

def _add_edge(vertex_names, name_to_idx):
    """ Adiciona ou atualiza uma aresta usando índices ATIVOS. """
    with st.form("form_add_edge"):
        st.subheader("Adicionar / Atualizar Aresta")
        # Usa vertex_names (nomes dos vértices ativos)
        u_name_add = st.selectbox("Origem (u):", vertex_names, key="sb_u_add")
        v_name_add = st.selectbox("Destino (v):", vertex_names, key="sb_v_add")
        weight_add = st.number_input("Peso:", min_value=0.1, value=1.0, step=0.1)
        
        submitted_add = st.form_submit_button("Adicionar/Atualizar Aresta")
        if submitted_add:
            try:
                # Converte Nome para Índice ATIVO
                u = name_to_idx[u_name_add]
                v = name_to_idx[v_name_add]
                
                # A função graph_service.add_edge opera no grafo ATIVO (índices 0..N-1)
                graph_service.add_edge(u, v, weight_add)

                # Atualiza highlight (usa índices ATIVOS)
                st.session_state["last_added_edge"] = (u, v)
                st.session_state["last_added_vertex"] = None

                st.success(f"Aresta ({u_name_add}, {v_name_add}) adicionada/atualizada com peso {weight_add}.")
                st.rerun() 
            except Exception as e:
                st.error(f"Erro ao adicionar aresta: {e}")

def _remove_edge(vertex_names, name_to_idx):
    """ Remove uma aresta usando índices ATIVOS. """
    with st.form("form_remove_edge"):
        st.subheader("Remover Aresta")
        # Usa vertex_names (nomes dos vértices ativos)
        u_name_rem = st.selectbox("Origem (u):", vertex_names, key="sb_u_rem")
        v_name_rem = st.selectbox("Destino (v):", vertex_names, key="sb_v_rem")
        
        submitted_rem = st.form_submit_button("Remover Aresta")
        if submitted_rem:
            try:
                # Converte Nome para Índice ATIVO
                u = name_to_idx[u_name_rem]
                v = name_to_idx[v_name_rem]
                
                # A função graph_service.remove_edge opera no grafo ATIVO
                if not graph_service.has_edge(u, v):
                    st.warning(f"Aresta ({u_name_rem}, {v_name_rem}) já não existe no grafo ativo.")
                else:
                    graph_service.remove_edge(u, v)
                    st.success(f"Aresta ({u_name_rem}, {v_name_rem}) removida.")
                    st.rerun()
            except Exception as e:
                st.error(f"Erro ao remover aresta: {e}")

def _add_vertex(idx_to_name):
    """ Adiciona um vértice ao grafo ATIVO. """
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
                # 1. Adiciona o vértice no grafo ATIVO. Ele retorna o NOVO índice ATIVO.
                new_active_index = graph_service.add_vertex()

                # 2. Nome do vértice
                vertex_name = vertex_name_input.strip() or f"Novo_{new_active_index}"
                
                # 3. Atualiza os mapeamentos do grafo ATIVO
                # name_to_idx_map: Nome -> Índice ATIVO (necessário para os selects)
                st.session_state.name_to_idx_map[vertex_name] = new_active_index
                # idx_to_name_map: Índice ATIVO -> Nome (passado como argumento)
                idx_to_name[new_active_index] = vertex_name
                
                # Adiciona o nome à lista de nomes (vertex_names_list)
                st.session_state.vertex_names_list.append(vertex_name)

                # 4. Adiciona ao conjunto de 'new_vertices' (índice ATIVO) para destaque
                st.session_state.new_vertices.add(new_active_index)
                st.session_state.last_added_vertex = new_active_index

                st.success(f"Vértice '{vertex_name}' adicionado com sucesso! (Índice Ativo: {new_active_index})")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao adicionar vértice: {e}")