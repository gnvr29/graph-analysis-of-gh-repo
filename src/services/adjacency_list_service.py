import streamlit as st
import streamlit.components.v1 as components
import re
from src.core.AdjacencyMatrixGraph import AdjacencyMatrixGraph
from src.services.shared_queries import (WEIGHTS)

try:
    import svgwrite
except ImportError:
    st.error("Biblioteca 'svgwrite' não encontrada. Por favor, instale com: pip install svgwrite")
    st.stop()

try:
    from src.core.AdjacencyListGraph import AdjacencyListGraph
except ImportError as e:
    raise ImportError(
        "Não foi possível importar AdjacencyListGraph. "
        "Verifique a estrutura de pastas."
    ) from e

def truncate_name(name: str, max_len: int = 12) -> str:
    return name if len(name) <= max_len else name[:max_len - 3] + "..."

def _prepare_svg_for_download(svg_content: str, width: int, height: int) -> str:
    """
    Modifica a string SVG para incluir ou ajustar os atributos width e height
    na tag <svg> raiz, visando melhorar a visualização ao ser baixada.
    Esta modificação é aplicada *apenas* à string SVG que será baixada,
    não afetando a renderização no Streamlit ou a geração original do SVG.
    """
    match = re.search(r'<svg(?P<attributes>.*?)(?<!/)>', svg_content, re.DOTALL)
    
    if match:
        attributes = match.group('attributes')
        
        attributes = re.sub(r'\s+width="[^"]*"', '', attributes)
        attributes = re.sub(r'\s+height="[^"]*"', '', attributes)
        
        new_svg_tag = f'<svg width="{width}px" height="{height}px" {attributes.strip()}>'
        
        return new_svg_tag + svg_content[match.end():]
    
    return svg_content

def _get_neighbors_from_graph(graph_obj, node_idx: int, is_predecessor_view: bool):
    """
    Função auxiliar para obter os vizinhos (sucessores ou predecessores) de um nó,
    independentemente da implementação do grafo (lista ou matriz de adjacência).
    Retorna um dicionário {vizinho_idx: peso}.
    """
    neighbors = {}

    # Caso 1: Grafo é uma Lista de Adjacência
    if isinstance(graph_obj, AdjacencyListGraph):
        if not is_predecessor_view: 
            neighbors = graph_obj.adj_out[node_idx]
        else:
            neighbors = graph_obj.adj_in[node_idx]

    # Caso 2: Grafo é uma Matriz de Adjacência (Assumindo que tenha um método get_adjacency_matrix)
    elif isinstance(graph_obj, AdjacencyMatrixGraph):
        matrix = graph_obj.getAsAdjacencyMatrix()
        num_nodes = len(matrix)

        if not (0 <= node_idx < num_nodes):
            return {}

        if not is_predecessor_view: 
            for v_idx in range(num_nodes):
                weight = matrix[node_idx][v_idx]
                if weight != 0: 
                    neighbors[v_idx] = weight
        else: 
            for u_idx in range(num_nodes):
                if 0 <= u_idx < num_nodes:
                    weight = matrix[u_idx][node_idx]
                    if weight != 0:
                        neighbors[u_idx] = weight
    else:
        st.error(f"Erro: Tipo de grafo não suportado para renderização de lista de adjacência: {type(graph_obj).__name__}")
        return {} 

    return neighbors

# ============== FUNÇÃO DE DISPLAY ==============

def _render_adjacency_list_svg(
    graph, 
    idx_to_name: dict[int, str], 
    indices_to_render: list[int],
    title: str,
    download_filename_prefix: str,
    is_predecessor_view: bool = False
) -> None:
    """
    Gera e exibe a lista de adjacência do grafo como um SVG no Streamlit,
    com suporte para sucessores ou antecessores.
    """
    
    n = len(indices_to_render) 
    if n == 0:
        st.info(f"Nenhum autor selecionado para exibir a {title.lower()}.")
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

    max_rendered_content_x = MARGIN_LEFT + NODE_BOX_WIDTH 
    total_width = max_rendered_content_x + MARGIN_LEFT 

    total_height = (
        MARGIN_TOP
        + (n * (NODE_BOX_HEIGHT + VERTICAL_NODE_SPACING)) 
        - (VERTICAL_NODE_SPACING if n > 0 else 0)
        + MARGIN_TOP
    )

    dwg = svgwrite.Drawing(size=("100%", "100%"))
    dwg.attribs["preserveAspectRatio"] = "xMinYMin meet"
    dwg.viewbox(0, 0, total_width, total_height) 
    dwg.defs.add(dwg.style(f"""
        text {{ font-family: '{FONT_FAMILY}'; }}
        .fullname {{ visibility: hidden; fill: #FFF; pointer-events: none; }}
        g:hover .fullname {{ visibility: visible; }}
        g:hover rect {{ stroke: #FFD700; stroke-width: 2px; }}
    """))

    for row_index, u in enumerate(indices_to_render):
        u_box_x = MARGIN_LEFT
        u_box_y = MARGIN_TOP + row_index * (NODE_BOX_HEIGHT + VERTICAL_NODE_SPACING) 
        author_name = idx_to_name.get(u, f"Nó {u}") 

        # Node principal
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

        # Tooltip para o node principal
        t_full_src = dwg.text(
            author_name,
            insert=(u_box_x + PADDING_TEXT_X, u_box_y + NODE_BOX_HEIGHT + 12),
            text_anchor="middle",
            font_size=TEXT_SIZE - 2,
        )
        t_full_src.attribs["class"] = "fullname"
        g_src.add(t_full_src)
        dwg.add(g_src)

        current_cursor_x = u_box_x + NODE_BOX_WIDTH
                
        # neighbors_map = getattr(graph, graph_data_attribute, {})
        # neighbors_for_u = {}
        # if isinstance(neighbors_map, dict):
        #     neighbors_for_u = neighbors_map.get(u, {})
        # elif isinstance(neighbors_map, list) and u < len(neighbors_map) and isinstance(neighbors_map[u], dict):
        #     neighbors_for_u = neighbors_map[u]
        
        # neighbors = sorted(neighbors_for_u.items(), key=lambda it: it[1], reverse=True)
        # # Filtra os vizinhos por aqueles foram definidos no filtro
        # neighbors = [(v, w) for (v, w) in neighbors if v in indices_to_render]

        neighbors_for_u = _get_neighbors_from_graph(graph, u, is_predecessor_view)

        neighbors_sorted = sorted(neighbors_for_u.items(), key=lambda it: it[1], reverse=True)
        neighbors = [(v, w) for (v, w) in neighbors_sorted if v in indices_to_render]

        if neighbors:
            # Conexoes para cada vizinho
            for i, (v, w) in enumerate(neighbors):
                adj_name = idx_to_name.get(v, f"Nó {v}")
                adj_display = truncate_name(adj_name)

                line_y = u_box_y + NODE_BOX_HEIGHT / 2
    
                if i > 0:
                    current_cursor_x += HORIZONTAL_ADJ_NODE_SPACING
                
                v_box_y = u_box_y 
                line_start_x = current_cursor_x

                if i > 0: 
                    line_start_x -= HORIZONTAL_ADJ_NODE_SPACING

                arrow_tip_x = line_start_x + ARROW_LENGTH
                v_box_x = arrow_tip_x

                arrow_points = [
                    (arrow_tip_x, line_y),
                    (arrow_tip_x - ARROW_HEAD_SIZE, line_y - ARROW_HEAD_SIZE / 2),
                    (arrow_tip_x - ARROW_HEAD_SIZE, line_y + ARROW_HEAD_SIZE / 2),
                ]
                
                # Linha da Seta
                dwg.add(dwg.line(
                    start=(line_start_x, line_y),
                    end=(arrow_tip_x, line_y),
                    stroke=STROKE_COLOR,
                    stroke_width=2
                ))
                # Seta
                dwg.add(dwg.polygon(points=arrow_points, fill=STROKE_COLOR))
                
                # Peso
                weight_text_x = (line_start_x + arrow_tip_x) / 2
                dwg.add(dwg.text(
                    str(w),
                    insert=(weight_text_x, line_y - 8),
                    text_anchor="middle",
                    font_size=TEXT_SIZE - 2,
                    fill="#00BFFF"
                ))

                # Node para o vizinho
                g_adj = dwg.g(id=f"node-{u}-to-{v}")
                g_adj.add(dwg.rect(
                    insert=(v_box_x, v_box_y),
                    size=(NODE_BOX_WIDTH, NODE_BOX_HEIGHT),
                    fill=NODE_FILL,
                    stroke=STROKE_COLOR,
                    rx=4, ry=4
                ))
                # Texto para vizinho
                t_adj = dwg.text(
                    adj_display,
                    insert=(v_box_x + PADDING_TEXT_X, v_box_y + PADDING_TEXT_Y),
                    text_anchor="middle",
                    font_size=TEXT_SIZE,
                    fill="#111"
                )
                g_adj.add(t_adj)

                if not is_predecessor_view:
                    tooltip_text = f"{adj_name} (peso de {author_name} para {adj_name}: {w})"
                else:
                    tooltip_text = f"{adj_name} (peso de {adj_name} para {author_name}: {w})"

                t_full_adj = dwg.text(
                    tooltip_text,
                    insert=(v_box_x + PADDING_TEXT_X, v_box_y + NODE_BOX_HEIGHT + 12),
                    text_anchor="middle",
                    font_size=TEXT_SIZE - 2
                )
                t_full_adj.attribs["class"] = "fullname"
                g_adj.add(t_full_adj)
                dwg.add(g_adj)  

                current_cursor_x = v_box_x + NODE_BOX_WIDTH

        max_rendered_content_x = max(max_rendered_content_x, current_cursor_x)

    # --- fim do loop principal ---

    total_width = max_rendered_content_x + MARGIN_LEFT

    dwg.viewbox(0, 0, total_width, total_height) 

    svg_string = dwg.tostring()

    visible_h_px = 600
    html_container = f"""
    <div style="width:100%; height:{visible_h_px}px; overflow:auto; border:1px solid #444; background:#0d0d1a;">
      <div style="width:{int(total_width)}px; height:{int(total_height)}px;">
        {svg_string}
      </div>
    </div>
    """
    
    st.subheader(title) 
    components.html(html_container, height=visible_h_px + 24, scrolling=True)

    st.info("Passe o mouse sobre as caixas para ver o nome completo e os detalhes da conexão.")

    modified_svg_for_download = _prepare_svg_for_download(svg_string, int(total_width), int(total_height))

    # Botao de download
    st.download_button(
        f"Baixar {download_filename_prefix.replace('_', ' ')}.svg",
        data=modified_svg_for_download.encode("utf-8"),
        file_name=f"{download_filename_prefix}.svg",
        mime="image/svg+xml"
    )

# ============== FUNÇÃO PRINCIPAL DE DISPLAY NO STREAMLIT ==============

def display_adjacency_lists_streamlit(
    graph, 
    idx_to_name: dict[int, str], 
    indices_to_render: list[int]  
) -> None:
    """
    Exibe as listas de adjacência para sucessores e antecessores em dois SVGs separados.
    """
    
    # Exibir lista de sucessores
    _render_adjacency_list_svg(
        graph=graph,
        idx_to_name=idx_to_name,
        indices_to_render=indices_to_render,
        title="Lista de Adjacência: Sucessores",
        download_filename_prefix="lista_adjacencia_sucessores",
        is_predecessor_view=False
    )
    
    st.markdown("---") 
    
    # Exibir lista de antecessores
    _render_adjacency_list_svg(
        graph=graph,
        idx_to_name=idx_to_name,
        indices_to_render=indices_to_render,
        title="Lista de Adjacência: Predecessores",
        download_filename_prefix="lista_adjacencia_predecessores",
        is_predecessor_view=True
    )