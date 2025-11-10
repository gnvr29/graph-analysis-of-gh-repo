import sys
import os
from collections import defaultdict
import streamlit as st
import streamlit.components.v1 as components

# Tenta importar a biblioteca de desenho SVG
try:
    import svgwrite
except ImportError:
    st.error("Biblioteca 'svgwrite' não encontrada. Por favor, instale com: pip install svgwrite")
    st.stop()


# ============== IMPORTS DO PROJETO ==============

try:
    from src.core.AdjacencyListGraph import AdjacencyListGraph
except ImportError as e:
    raise ImportError(
        "Não foi possível importar AdjacencyListGraph. "
        "Verifique a estrutura de pastas."
    ) from e

# Importa a FUNÇÃO que obtém a conexão
try:
    from src.utils.neo4j_connector import get_neo4j_service
except ImportError:
    st.error("Não foi possível encontrar 'src.utils.neo4j_connector'. Verifique o arquivo.")
    st.stop()
        

# ============== CONFIGURAÇÕES E QUERIES (Sem alterações) ==============
LABEL_AUTHOR = "Author"
LABEL_ISSUE = "Issue"
LABEL_PR = "PullRequest"
LABEL_COMMENT = "Comment"
LABEL_REVIEW = "Review"
REL_AUTHORED_COMMENT = "AUTHORED"
REL_COMMENT_ON = "HAS_COMMENT"
REL_CREATED = "CREATED"
REL_PERFORMED_REVIEW = "PERFORMED_REVIEW"
REL_HAS_REVIEW = "HAS_REVIEW"

WEIGHTS = {
    "COMMENT": 2,
    "ISSUE_COMMENTED": 3,
    "REVIEW": 4,
    "MERGE": 5,
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
ISSUE_COMMENTED_BY_OTHER_QUERY = f"""
MATCH (dst:{LABEL_AUTHOR})-[:{REL_CREATED}|OPENED]->(i:{LABEL_ISSUE})
MATCH (src:{LABEL_AUTHOR})-[:{REL_AUTHORED_COMMENT}|COMMENTED]->(c:{LABEL_COMMENT})
MATCH (i)-[:{REL_COMMENT_ON}|ON]->(c)
WHERE src <> dst
RETURN id(src) AS srcId, id(dst) AS dstId
"""
PR_REVIEW_APPROVAL_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_PERFORMED_REVIEW}|REVIEWED|APPROVED]->(r:{LABEL_REVIEW})
MATCH (pr:{LABEL_PR})-[:{REL_HAS_REVIEW}|REVIEWS|FOR]->(r)
MATCH (pr)<-[:{REL_CREATED}|OPENED]-(dst:{LABEL_AUTHOR})
WHERE src <> dst
RETURN id(src) AS srcId, id(dst) AS dstId
"""
PR_MERGE_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_PERFORMED_REVIEW}|REVIEWED|APPROVED]->(r:{LABEL_REVIEW})
MATCH (pr:{LABEL_PR})-[:{REL_HAS_REVIEW}|REVIEWS|FOR]->(r)
MATCH (pr)<-[:{REL_CREATED}|OPENED]-(dst:{LABEL_AUTHOR})
WHERE src <> dst AND pr.mergedAt IS NOT NULL
RETURN id(src) AS srcId, id(dst) AS dstId
"""

# ============== FUNÇÕES AUXILIARES (Sem alterações) ==============

def fetch_authors_and_edges(neo4j_service) -> tuple[dict[int, str], list[tuple[int, int, float]]]:
    print("Buscando todos os autores...")
    authors_rows = neo4j_service.query(AUTHORS_QUERY)
    if not authors_rows:
        print("Nenhum autor encontrado no Neo4j.")
        return {}, []
    print(f"  Encontrados {len(authors_rows)} autores.")
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
    print(f"  Encontradas {len(comment_on_issue_pr_rows)} interações de comentário.")
    print("Buscando interações de 'Abertura de issue comentada por outro usuário' (Peso 3)...")
    issue_commented_rows = neo4j_service.query(ISSUE_COMMENTED_BY_OTHER_QUERY)
    for row in issue_commented_rows:
        if row["srcId"] in id_to_index and row["dstId"] in id_to_index:
            weighted_edges_map[(row["srcId"], row["dstId"])] += WEIGHTS["ISSUE_COMMENTED"]
    print(f"  Encontradas {len(issue_commented_rows)} interações de issue comentada.")
    print("Buscando interações de 'Revisão/aprovação de pull request' (Peso 4)...")
    pr_review_approval_rows = neo4j_service.query(PR_REVIEW_APPROVAL_QUERY)
    for row in pr_review_approval_rows:
        if row["srcId"] in id_to_index and row["dstId"] in id_to_index:
            weighted_edges_map[(row["srcId"], row["dstId"])] += WEIGHTS["REVIEW"]
    print(f"  Encontradas {len(pr_review_approval_rows)} interações de revisão/aprovação.")
    print("Buscando interações de 'Merge de pull request' (Peso 5)...")
    pr_merge_rows = neo4j_service.query(PR_MERGE_QUERY)
    for row in pr_merge_rows:
        if row["srcId"] in id_to_index and row["dstId"] in id_to_index:
            weighted_edges_map[(row["srcId"], row["dstId"])] += WEIGHTS["MERGE"]
    print(f"  Encontradas {len(pr_merge_rows)} interações de merge.")
    edges: list[tuple[int, int, float]] = []
    for (src_neo4j_id, dst_neo4j_id), total_weight in weighted_edges_map.items():
        u = id_to_index[src_neo4j_id]
        v = id_to_index[dst_neo4j_id]
        if u != v:
            edges.append((u, v, total_weight))
    print(f"Total de {len(edges)} arestas ponderadas únicas formadas após agregação.")
    return idx_to_name, edges


def build_graph(vertex_count: int, edges: list[tuple[int, int, float]]) -> "AdjacencyListGraph":
    st.info(f"Construindo grafo com {vertex_count} vértices e {len(edges)} arestas...")
    graph = AdjacencyListGraph(vertex_count)
    for u, v, w in edges:
        try:
            graph.addEdge(u, v, w)
        except Exception as e:
            st.warning(f"Falha ao adicionar aresta ({u}->{v}) peso {w}: {e}")
    st.success("Grafo construído com sucesso.")
    return graph

def truncate_name(name: str, max_len: int = 12) -> str:
    return name if len(name) <= max_len else name[:max_len - 3] + "..."

# ============== FUNÇÃO DE DISPLAY (MODIFICADA) ==============

def display_graph_svg_streamlit(
    graph: "AdjacencyListGraph", 
    idx_to_name: dict[int, str], 
    indices_to_render: list[int]  
) -> None:
    """
    Exibe a lista de adjacência do grafo como um SVG,
    renderizando APENAS os índices fornecidos em 'indices_to_render'.
    """
    
    n = len(indices_to_render) 
    if n == 0:
        return

    NODE_BOX_WIDTH = 120
    NODE_BOX_HEIGHT = 36
    TEXT_SIZE = 13
    PADDING_TEXT_X = NODE_BOX_WIDTH / 2
    PADDING_TEXT_Y = NODE_BOX_HEIGHT / 2 + 4
    ARROW_LENGTH = 40
    VERTICAL_NODE_SPACING = 24
    HORIZONTAL_ADJ_NODE_SPACING = 16
    MARGIN_LEFT = 40
    MARGIN_TOP = 36
    ARROW_HEAD_SIZE = 8
    STROKE_COLOR = "#00BFFF"
    NODE_FILL = "#E6E6E6"
    FONT_FAMILY = "Inter, Segoe UI, Roboto, Arial, sans-serif"

    # Comprimento máximo da lista de adjacência (baseado APENAS nos nós renderizados)
    max_adj_list_len = 0
    for u in indices_to_render: 
        if u < len(getattr(graph, "adj_out", [])):
            max_adj_list_len = max(max_adj_list_len, len(graph.adj_out[u]))

    total_width = (
        MARGIN_LEFT
        + NODE_BOX_WIDTH
        + (ARROW_LENGTH if max_adj_list_len > 0 else 0)
        + (max_adj_list_len * (NODE_BOX_WIDTH + HORIZONTAL_ADJ_NODE_SPACING)) 
        + MARGIN_LEFT
    )
    total_height = (
        MARGIN_TOP
        + (n * (NODE_BOX_HEIGHT + VERTICAL_NODE_SPACING)) 
        - (VERTICAL_NODE_SPACING if n > 0 else 0)
        + MARGIN_TOP
    )

    dwg = svgwrite.Drawing(size=("100%", "100%"))
    dwg.viewbox(0, 0, total_width, total_height)
    dwg.attribs["preserveAspectRatio"] = "xMinYMin meet"

    dwg.defs.add(dwg.style(f"""
        text {{ font-family: '{FONT_FAMILY}'; }}
        .fullname {{ visibility: hidden; fill: #FFF; pointer-events: none; }}
        g:hover .fullname {{ visibility: visible; }}
        g:hover rect {{ stroke: #FFD700; stroke-width: 2px; }}
    """))

    for row_index in range(n):
        y_mid = MARGIN_TOP + row_index * (NODE_BOX_HEIGHT + VERTICAL_NODE_SPACING) + NODE_BOX_HEIGHT / 2
        dwg.add(dwg.line(
            start=(MARGIN_LEFT - 10, y_mid),
            end=(total_width - (MARGIN_LEFT - 10), y_mid),
            stroke="#1a1a1a",
            stroke_width=1
        ))

    for row_index, u in enumerate(indices_to_render):
        u_box_x = MARGIN_LEFT
        u_box_y = MARGIN_TOP + row_index * (NODE_BOX_HEIGHT + VERTICAL_NODE_SPACING) 
        author_name = idx_to_name.get(u, f"Nó {u}") 

        g_src = dwg.g(id=f"node-{u}")
        g_src.add(dwg.rect(
            insert=(u_box_x, u_box_y),
            size=(NODE_BOX_WIDTH, NODE_BOX_HEIGHT),
            fill=NODE_FILL,
            stroke=STROKE_COLOR,
            rx=6, ry=6
        ))
        author_display = truncate_name(author_name, max_len=14)
        t_src = dwg.text(
            author_display,
            insert=(u_box_x + PADDING_TEXT_X, u_box_y + PADDING_TEXT_Y),
            text_anchor="middle",
            font_size=TEXT_SIZE,
            fill="#111"
        )
        g_src.add(t_src)
        t_full_src = dwg.text(
            author_name,
            insert=(u_box_x + PADDING_TEXT_X, u_box_y + NODE_BOX_HEIGHT + 12),
            text_anchor="middle",
            font_size=TEXT_SIZE - 2,
        )
        t_full_src.attribs["class"] = "fullname"
        g_src.add(t_full_src)
        dwg.add(g_src)
                
        neighbors = []
        adj_out = getattr(graph, "adj_out", {})
        if isinstance(adj_out, dict):
            neighbors = adj_out.get(u, {}).items()
        elif isinstance(adj_out, list) and u < len(adj_out):
            neighbors = adj_out[u].items()
        neighbors = sorted(neighbors, key=lambda it: it[1], reverse=True)

        if neighbors:
            current_adj_x = u_box_x + NODE_BOX_WIDTH + ARROW_LENGTH
            current_adj_y = u_box_y 

            # Desenha conexão para cada vizinho
            for v, w in neighbors:
                adj_name = idx_to_name.get(v, f"Nó {v}")
                adj_display = truncate_name(adj_name)

                # Posição Y da linha é baseada na 'linha' (row_index)
                line_y = u_box_y + NODE_BOX_HEIGHT / 2
                arrow_tip_x = current_adj_x
                line_start_x = u_box_x + NODE_BOX_WIDTH
                line_end_x = current_adj_x  

                # Linha
                dwg.add(dwg.line(
                    start=(line_start_x, line_y),
                    end=(line_end_x, line_y),
                    stroke=STROKE_COLOR,
                    stroke_width=2
                ))
                # Seta
                dwg.add(dwg.polygon(
                    points=[
                        (arrow_tip_x, line_y), 
                        (arrow_tip_x - ARROW_HEAD_SIZE, line_y - ARROW_HEAD_SIZE / 2),
                        (arrow_tip_x - ARROW_HEAD_SIZE, line_y + ARROW_HEAD_SIZE / 2),
                    ],
                    fill=STROKE_COLOR
                ))
                # Peso
                dwg.add(dwg.text(
                    str(w),
                    insert=((line_start_x + arrow_tip_x) / 2, line_y - 8),
                    text_anchor="middle",
                    font_size=TEXT_SIZE - 2,
                    fill="#00BFFF"
                ))
                # Caixa do vizinho
                g_adj = dwg.g(id=f"node-{u}-to-{v}")
                g_adj.add(dwg.rect(
                    insert=(current_adj_x, current_adj_y),
                    size=(NODE_BOX_WIDTH, NODE_BOX_HEIGHT),
                    fill=NODE_FILL,
                    stroke=STROKE_COLOR,
                    rx=4, ry=4
                ))
                # Texto do vizinho
                t_adj = dwg.text(
                    adj_display,
                    insert=(current_adj_x + PADDING_TEXT_X, current_adj_y + PADDING_TEXT_Y),
                    text_anchor="middle",
                    font_size=TEXT_SIZE,
                    fill="#111"
                )
                g_adj.add(t_adj)
                # Tooltip do vizinho
                t_full_adj = dwg.text(
                    f"{adj_name} (peso: {w})",
                    insert=(current_adj_x + PADDING_TEXT_X, current_adj_y + NODE_BOX_HEIGHT + 12),
                    text_anchor="middle",
                    font_size=TEXT_SIZE - 2
                )
                t_full_adj.attribs["class"] = "fullname"
                g_adj.add(t_full_adj)
                dwg.add(g_adj)  

                # Atualiza o X para o próximo vizinho
                current_adj_x += NODE_BOX_WIDTH + HORIZONTAL_ADJ_NODE_SPACING # Correção aqui

    # --- Fim do Loop Principal ---

    svg_string = dwg.tostring()

    # Wrapper HTML (idêntico, usa total_width/height calculados)
    visible_h_px = 600
    html_container = f"""
    <div style="width:100%; height:{visible_h_px}px; overflow:auto; border:1px solid #444; background:#0d0d1a;">
      <div style="width:{int(total_width)}px; height:{int(total_height)}px;">
        {svg_string}
      </div>
    </div>
    """
    components.html(html_container, height=visible_h_px + 24, scrolling=True)

    # Legenda
    st.markdown("---")
    st.subheader(f"Legenda dos Pesos (Mostrando {n} autores)")
    st.write(f"- Comentário em Issue/PR: {WEIGHTS.get('COMMENT', 'N/A')}")
    st.write(f"- Abertura de Issue comentada: {WEIGHTS.get('ISSUE_COMMENTED', 'N/A')}")
    st.write(f"- Revisão/Aprovação de PR: {WEIGHTS.get('REVIEW', 'N/A')}")
    st.write(f"- Merge de PR: {WEIGHTS.get('MERGE', 'N/A')}")
    st.info("Passe o mouse sobre as caixas para ver o nome completo e o peso agregado.")

    # Download
    st.download_button(
        "Baixar visualização (SVG)",
        data=svg_string.encode("utf-8"),
        file_name="lista_adjacencia_filtrada.svg",
        mime="image/svg+xml"
    )

# ============== FUNÇÃO APP  ==============

def app():
    st.title("Visualização da Lista de Adjacência (SVG)")
    st.markdown(
        """
        Esta página busca interações entre autores no Neo4j...
        Use os filtros na barra lateral para refinar a visualização.
        """
    )

    # --- FILTROS NA SIDEBAR ---
    st.sidebar.header("Opções de Filtro")
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
                idx_to_name, edges = fetch_authors_and_edges(neo4j_service)
                if not idx_to_name:
                    st.warning("Nenhum nó (:Author) encontrado no Neo4j.")
                    return 

                vertex_count = len(idx_to_name)
                graph = build_graph(vertex_count, edges)

                # --- 2. LÓGICA DE FILTRO ---
                
                # Calcula a atividade (peso total de saída) para todos os autores
                author_activity = []
                all_indices = list(range(len(idx_to_name)))
                for u in all_indices:
                    total_weight = 0
                    if u < len(graph.adj_out) and graph.adj_out[u]:
                        total_weight = sum(graph.adj_out[u].values())
                    author_activity.append((u, total_weight)) # (índice, peso_total)
                
                # Aplica o filtro da checkbox
                if filter_with_edges:
                    author_activity = [item for item in author_activity if item[1] > 0]
                    
                # Ordena pela atividade (do maior para o menor)
                author_activity.sort(key=lambda item: item[1], reverse=True)
                
                # Aplica o limite (se definido)
                if limit > 0:
                    author_activity = author_activity[:limit]
                    
                # Cria a lista final de ÍNDICES para renderizar
                indices_to_render = [u for u, weight in author_activity]
                # --- FIM DA LÓGICA DE FILTRO ---

                if not indices_to_render:
                    st.warning("Nenhum autor corresponde aos filtros selecionados.")
                    return

                # 3. Passa a lista filtrada para a função de display
                display_graph_svg_streamlit(graph, idx_to_name, indices_to_render)

            except Exception as e:
                st.error(f"Ocorreu um erro ao gerar o grafo: {e}")
                st.exception(e)


if __name__ == "__main__":
    app()