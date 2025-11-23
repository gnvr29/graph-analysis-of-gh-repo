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
            full_graph = st.session_state.get(f"full_{st.session_state.get('current_graph_id', 'default')}_obj")

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

                is_sucessor_uv = graph_service.is_successor(u_idx, v_idx)

                if is_sucessor_uv:
                    weight = graph_service.get_edge_weight(u_idx, v_idx)
                    st.success(f"Sim, ({u_name}, {v_name}) existe (Sucessor). Peso: {weight:.1f}.")
                else:
                    st.error(f"Não, ({u_name}, {v_name}) não existe (Não é Sucessor).")

                is_predecessor_uv = graph_service.is_predecessor(u_idx, v_idx)
                
                if is_predecessor_uv:
                    weight_inv = graph_service.get_edge_weight(v_idx, u_idx)
                    st.info(f"Sim, ({v_name}, {u_name}) existe ({u_name} é Predecessor de {v_name}). Peso: {weight_inv:.1f}.")
                else:
                    st.info(f"Não, ({v_name}, {u_name}) não existe (Não é Predecessor).")

                is_u_incident = graph_service.is_incident(u_idx, v_idx, u_idx)
                is_v_incident = graph_service.is_incident(u_idx, v_idx, v_idx)
                
                st.markdown("---")
                st.caption(f"Incidência em ({u_name}, {v_name}):")
                st.markdown(f"**{u_name}** é incidente: {'Sim' if is_u_incident else 'Não'}")
                st.markdown(f"**{v_name}** é incidente: {'Sim' if is_v_incident else 'Não'}")


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

        _set_vertex_weight(vertex_names, name_to_idx)

        _add_edge(vertex_names, name_to_idx)

        _remove_edge(vertex_names, name_to_idx)

        _add_vertex(idx_to_name)

def _set_vertex_weight(vertex_names, name_to_idx):
    """ Define o peso de um vértice no grafo ATIVO. """
    
    st.subheader("Alterar Peso do Vértice")
    v_name = st.selectbox("Vértice:", vertex_names, key="sb_v_set_weight")
    
    current_weight = 1.0
    
    try:
        if v_name:
            v_idx = name_to_idx.get(v_name)
            if v_idx is not None:
                current_weight = graph_service.get_vertex_weight(v_idx)
                st.caption(f"Peso atual de {v_name}: **{current_weight:.2f}**")
            else:
                st.caption("Selecione um vértice válido.")
    except Exception:
        st.caption("Aguardando seleção ou erro de peso.")

    with st.form("form_set_vertex_weight"):
        new_weight = st.number_input("Novo Peso:", min_value=0.0, value=current_weight, step=0.1, key="num_v_new_weight")
        
        submitted = st.form_submit_button("Definir Novo Peso")
        
        if submitted:
            try:
                v_idx = name_to_idx[v_name]
                graph_service.set_vertex_weight(v_idx, new_weight)
                st.success(f"Peso do vértice '{v_name}' definido como {new_weight:.2f}.")
                st.rerun()
            except Exception as e:
                st.error(f"Erro ao definir peso do vértice: {e}")


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
    
    st.subheader("Adicionar / Atualizar Aresta")
    
    u_name_add = st.selectbox("Origem (u):", vertex_names, key="sb_u_add")
    v_name_add = st.selectbox("Destino (v):", vertex_names, key="sb_v_add")
    
    current_weight = 1.0
    
    try:
        u = name_to_idx.get(u_name_add)
        v = name_to_idx.get(v_name_add)
        
        if u is not None and v is not None:
            
            if graph_service.has_edge(u, v):
                current_weight = graph_service.get_edge_weight(u, v)
                st.caption(f"Peso atual de ({u_name_add} -> {v_name_add}): **{current_weight:.2f}** (Aresta Existente)")
            else:
                if graph_service.has_edge(v, u):
                    reverse_weight = graph_service.get_edge_weight(v, u)
                    st.caption(f"A aresta ({u_name_add} -> {v_name_add}) não existe. OBS: A inversa ({v_name_add} -> {u_name_add}) tem peso {reverse_weight:.2f}.")
                else:
                    st.caption(f"Aresta ({u_name_add} -> {v_name_add}) não existe. Nova com peso padrão (1.0).")

            
    except Exception:
        current_weight = 1.0
        st.caption("Selecione a Origem e Destino para verificar o peso atual.")
    
    with st.form("form_add_edge"):
        
        new_weight = st.number_input(
            "Novo Peso:", 
            min_value=0.1, 
            value=current_weight, 
            step=0.1, 
            key="num_e_new_weight"
        )
        
        submitted_add = st.form_submit_button("Adicionar/Atualizar Aresta")
        if submitted_add:
            try:
                # Converte Nome para Índice ATIVO
                u = name_to_idx[u_name_add]
                v = name_to_idx[v_name_add]
                
                if graph_service.has_edge(u, v):
                    graph_service.set_edge_weight(u, v, new_weight)
                    st.session_state["last_added_edge"] = (u, v) # Mantém o highlight
                    st.success(f"Peso da aresta ({u_name_add}, {v_name_add}) atualizado para {new_weight:.2f}.")
                    st.rerun() 
                else:
                    edge_added = graph_service.add_edge(u, v, new_weight) 

                    if edge_added:
                        st.session_state["last_added_edge"] = (u, v)
                        st.session_state["last_added_vertex"] = None

                        st.success(f"Aresta ({u_name_add}, {v_name_add}) adicionada com peso {new_weight:.2f}.")
                        st.rerun() 
                    else:
                        st.warning(f"Aresta ({u_name_add}, {v_name_add}) não foi adicionada. É possível que os vértices sejam os mesmos (laço) ou outra restrição.")

            except Exception as e:
                st.error(f"Erro ao adicionar/atualizar aresta: {e}")

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
                # OBS: Em addVertex o peso é inicializado em 0.0 na classe AbstractGraph
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