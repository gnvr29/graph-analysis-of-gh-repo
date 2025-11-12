import streamlit as st
import svgwrite
from collections import defaultdict
import streamlit.components.v1 as components
from typing import List, Tuple, Optional 
import math

try:
    from src.core.AdjacencyListGraph import AdjacencyListGraph
except ImportError as e:
    raise ImportError(
        "Não foi possível importar AdjacencyListGraph. "
        "Verifique a estrutura de pastas."
    ) from e

try:
    from src.utils.neo4j_connector import get_neo4j_service
except ImportError:
    st.error("Não foi possível encontrar 'src.utils.neo4j_connector'. Verifique o arquivo.")
    st.stop()

# NOVO: Importa o helper da sidebar
try:
    from src.utils.streamlit_helpers import draw_graph_api_sidebar
except ImportError:
    st.error("Não foi possível encontrar 'src.utils.streamlit_helpers'. Crie o arquivo.")
    st.stop()


# ============== CONFIGURAÇÕES E QUERIES (Sem alterações) ==============
LABEL_AUTHOR = "Author"
LABEL_ISSUE = "Issue"
LABEL_PR = "PullRequest"
# ... (resto das suas constantes)
LABEL_COMMENT = "Comment"
REL_AUTHORED_COMMENT = "AUTHORED"
REL_COMMENT_ON = "HAS_COMMENT"
REL_CREATED = "CREATED"

WEIGHTS = {
    "COMMENT": 2.0,
}

AUTHORS_QUERY = f"""
MATCH (a:{LABEL_AUTHOR})
RETURN id(a) AS id, coalesce(a.login, toString(id(a))) AS name
ORDER BY name
"""

COMMENT_ON_ISSUE_PR_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_AUTHORED_COMMENT}]->(comment:{LABEL_COMMENT})
MATCH (target: {LABEL_ISSUE}|{LABEL_PR})-[:{REL_COMMENT_ON}]->(comment)
MATCH (target)<-[:{REL_CREATED}]-(dst:{LABEL_AUTHOR})
WHERE src <> dst AND (target:{LABEL_ISSUE} OR target:{LABEL_PR})
RETURN id(src) AS srcId, id(dst) AS dstId
"""

# ============== FUNÇÕES DE DADOS E GRAFO (Sem alterações) ==============

def fetch_authors_and_edges(neo4j_service) -> tuple[dict[int, str], list[tuple[int, int, float]]]:
    print("Buscando todos os autores...")
    authors_rows = neo4j_service.query(AUTHORS_QUERY)
    if not authors_rows:
        print("Nenhum autor encontrado no Neo4j.")
        return {}, []
    print(f"   Encontrados {len(authors_rows)} autores.")
    id_to_index: dict[int, int] = {}
    idx_to_name: dict[int, str] = {}
    for idx, row in enumerate(authors_rows):
        neo4j_id = row["id"]
        name = row.get("name") or str(neo4j_id)
        id_to_index[neo4j_id] = idx
        idx_to_name[idx] = name
    weighted_edges_map: defaultdict[tuple[int, int], float] = defaultdict(float)
    print("Buscando interações de 'Comentário em issue ou pull request' (Peso 2)...")
    comment_on_issue_pr_rows = neo4j_service.query(COMMENT_ON_ISSUE_PR_QUERY)
    for row in comment_on_issue_pr_rows:
        if row["srcId"] in id_to_index and row["dstId"] in id_to_index:
            weighted_edges_map[(row["srcId"], row["dstId"])] += WEIGHTS["COMMENT"]
    print(f"   Encontradas {len(comment_on_issue_pr_rows)} interações de comentário.")
    edges: list[tuple[int, int, float]] = []
    for (src_neo4j_id, dst_neo4j_id), total_weight in weighted_edges_map.items():
        u = id_to_index[src_neo4j_id]
        v = id_to_index[dst_neo4j_id]
        if u != v:
            edges.append((u, v, total_weight))
    print(f"Total de {len(edges)} arestas ponderadas únicas formadas após agregação.")
    return idx_to_name, edges    

def build_graph(vertex_count: int, edges: list[tuple[int, int, float]]) -> AdjacencyListGraph:
    print("Construindo grafo de adjacência...")
    graph = AdjacencyListGraph(vertex_count)
    for u_idx, v_idx, weight in edges:
        graph.addEdge(u_idx, v_idx, weight)
    return graph

# ============== FUNÇÕES DE VISUALIZAÇÃO (Sem alterações) ==============
# ... (sua função display_graph_svg_streamlit) ...
def display_graph_svg_streamlit(
    graph: AdjacencyListGraph,
    idx_to_name: dict[int, str],
    indices_to_render: list[int]
): 
    # ... (Seu código de visualização SVG complexo)
    pass

def desenhar_grafo_svg(nos: List[str], arestas: List[Tuple[str, str]], destaque: Optional[List[str]] = None, width=600, height=600) -> str:
    # ... (Seu código da função desenhar_grafo_svg)
    n = len(nos)
    if n == 0:
        return "<svg width='{}' height='{}'></svg>".format(width, height)
    raio = min(width, height) // 2 - 50
    cx, cy = width // 2, height // 2
    pos = {}
    for i, no in enumerate(nos):
        ang = 2 * math.pi * i / n
        x = cx + raio * math.cos(ang)
        y = cy + raio * math.sin(ang)
        pos[no] = (x, y)
    svg = [f"<svg width='{width}' height='{height}' style='background:#f9f9f9'>"]
    for origem, destino in arestas:
        x1, y1 = pos[origem]
        x2, y2 = pos[destino]
        svg.append(f"<line x1='{x1}' y1='{y1}' x2='{x2}' y2='{y2}' stroke='#888' stroke-width='2' marker-end='url(#arrow)' />")
    svg.append("""
    <defs>
      <marker id='arrow' markerWidth='10' markerHeight='10' refX='10' refY='5' orient='auto' markerUnits='strokeWidth'>
        <path d='M0,0 L10,5 L0,10 L2,5 z' fill='#888' />
      </marker>
    </defs>
    """)
    for no in nos:
        x, y = pos[no]
        cor = '#ff4136' if destaque and no in destaque else '#0074d9'
        svg.append(f"<circle cx='{x}' cy='{y}' r='18' fill='{cor}' stroke='#333' stroke-width='2' />")
        svg.append(f"<text x='{x}' y='{y+5}' text-anchor='middle' font-size='13' fill='#fff'>{no}</text>")
    svg.append("</svg>")
    return ''.join(svg)


# ============== FUNÇÃO APP (MODIFICADA) ==============

def app():
    st.title("Grafo de Interações entre Autores (Comentários em PRs e Issues)")
    st.markdown(
        """
        Esta página exibe um grafo direcionado representando as interações entre autores
        de comentários em Pull Requests e Issues no repositório GitHub.
        """
    )

    # --- NOVO: Inicialização do Session State ---
    # Usamos nomes genéricos para o helper da sidebar funcionar
    if 'graph_obj' not in st.session_state:
        st.session_state.graph_obj = None
    if 'vertex_names_list' not in st.session_state:
        st.session_state.vertex_names_list = []
    if 'name_to_idx_map' not in st.session_state:
        st.session_state.name_to_idx_map = {}


    # --- FILTROS NA SIDEBAR ---
    # (Estes são os filtros específicos desta PÁGINA)
    st.sidebar.header("Opções de Filtro (Visualização)")
    filter_with_edges = st.sidebar.checkbox(
        "Mostrar apenas autores com interações de saída",
        value=True
    )
    limit = st.sidebar.number_input(
        "Limitar autores (0 = sem limite, Top N por atividade)",
        min_value=0,
        value=0,
        step=10
    )

    # --- LÓGICA DE CONEXÃO ---
    try:
        neo4j_service = get_neo4j_service()
    except Exception as e:
        st.error(f"Erro ao obter conexão com Neo4j: {e}")
        st.info("Verifique se o app.py foi executado e a conexão foi estabelecida.")
        st.stop()


    if st.button("Gerar e Exibir Grafo"):
        with st.spinner("Processando dados e construindo grafo..."):
            try:
                # 1. Busca e constrói o GRAFO COMPLETO
                idx_to_name, edges_with_weights = fetch_authors_and_edges(neo4j_service)
                
                if not idx_to_name:
                    st.warning("Nenhum nó (:Author) encontrado no Neo4j.")
                    # Limpa o state se não encontrar nada
                    st.session_state.graph_obj = None
                    st.session_state.vertex_names_list = []
                    st.session_state.name_to_idx_map = {}
                    return

                vertex_count = len(idx_to_name)
                graph = build_graph(vertex_count, edges_with_weights)

                # --- NOVO: Armazenar no Session State ---
                # Salvamos o grafo e os mapas com nomes genéricos
                st.session_state.graph_obj = graph
                st.session_state.name_to_idx_map = {name: idx for idx, name in idx_to_name.items()}
                st.session_state.vertex_names_list = sorted(list(idx_to_name.values()))
                
                
                # --- 2. LÓGICA DE FILTRO (Sem alterações) ---
                author_activity = []
                all_indices_from_map = list(idx_to_name.keys())
                for u_neo4j_id in all_indices_from_map:
                    u_internal_idx = list(idx_to_name.keys()).index(u_neo4j_id)
                    total_weight = 0
                    if u_internal_idx < len(graph.adj_out) and graph.adj_out[u_internal_idx]:
                        total_weight = sum(graph.adj_out[u_internal_idx].values())
                    author_activity.append((u_internal_idx, total_weight)) 

                if filter_with_edges:
                    author_activity = [item for item in author_activity if item[1] > 0]
                
                author_activity.sort(key=lambda item: item[1], reverse=True)

                if limit > 0:
                    author_activity = author_activity[:limit]

                indices_to_render_internal = [u_internal_idx for u_internal_idx, weight in author_activity]
                
                if not indices_to_render_internal:
                    st.warning("Nenhum autor corresponde aos filtros selecionados.")
                    return

                # --- 3. PREPARAR DADOS (Sem alterações) ---
                node_names_for_svg = [idx_to_name[list(idx_to_name.keys())[idx]] for idx in indices_to_render_internal]
                edges_for_svg = []
                for u_internal_idx in indices_to_render_internal:
                    if u_internal_idx < len(graph.adj_out):
                        for v_internal_idx, weight in graph.adj_out[u_internal_idx].items():
                            if v_internal_idx in indices_to_render_internal:
                                source_name = idx_to_name[list(idx_to_name.keys())[u_internal_idx]]
                                target_name = idx_to_name[list(idx_to_name.keys())[v_internal_idx]]
                                edges_for_svg.append((source_name, target_name))

                # --- 4. RENDERIZAÇÃO (Sem alterações) ---
                st.info("Visualização do grafo (layout circular):")

                svg_content = desenhar_grafo_svg(
                    nos=node_names_for_svg,
                    arestas=edges_for_svg,
                    width=800, 
                    height=800
                )
                html_container = f"""
                <div style="width:100%; height:820px; overflow:auto; border:1px solid #444; background:#0d0d1a;">
                  <div style="width:800px; height:800px;">
                    {svg_content}
                  </div>
                </div>
                """
                components.html(html_container, height=840, scrolling=True)

            except Exception as e:
                st.error(f"Ocorreu um erro ao gerar o grafo: {e}")
                st.exception(e)
                # Limpa o state em caso de erro
                st.session_state.graph_obj = None
                st.session_state.vertex_names_list = []
                st.session_state.name_to_idx_map = {}
                
    
    # --- NOVO: CHAMA O HELPER DA SIDEBAR ---
    # Esta função irá ler do st.session_state e desenhar o painel
    draw_graph_api_sidebar()


if __name__ == "__main__":
    app()