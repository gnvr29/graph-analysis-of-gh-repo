import streamlit as st
import streamlit.components.v1 as components
import re
from pages._shared_queries import (WEIGHTS)

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


# ============== FUNÇÃO DE DISPLAY ==============

def display_adjacency_list_svg_streamlit(
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
    dwg.viewbox(0, 0, total_width, total_height) # vai ser sobrescrito depois 
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
            end=(total_width + (MARGIN_LEFT - 10), y_mid),
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

        current_cursor_x = u_box_x + NODE_BOX_WIDTH
                
        neighbors = []
        adj_out = getattr(graph, "adj_out", {})
        if isinstance(adj_out, dict):
            neighbors = adj_out.get(u, {}).items()
        elif isinstance(adj_out, list) and u < len(adj_out):
            neighbors = adj_out[u].items()
        neighbors = sorted(neighbors, key=lambda it: it[1], reverse=True)
        neighbors = [(v, w) for (v, w) in neighbors if v in indices_to_render]

        if neighbors:
            current_element_end_x = u_box_x + NODE_BOX_WIDTH 

            # Desenha conexão para cada vizinho
            for i, (v, w) in enumerate(neighbors):
                adj_name = idx_to_name.get(v, f"Nó {v}")
                adj_display = truncate_name(adj_name)

                line_y = u_box_y + NODE_BOX_HEIGHT / 2
    
                if i > 0:
                    current_cursor_x += HORIZONTAL_ADJ_NODE_SPACING
                
                line_start_x = current_cursor_x

                if i > 0: # Se não for o primeiro vizinho, retire o espaçamento entre eles
                    line_start_x -= HORIZONTAL_ADJ_NODE_SPACING
                
                # A ponta da seta está a ARROW_LENGTH de onde a linha começou
                arrow_tip_x = line_start_x + ARROW_LENGTH
                
                # A caixa do vizinho começa exatamente onde a seta termina
                v_box_x = arrow_tip_x 
                v_box_y = u_box_y # Vizinhos na mesma linha Y que o nó fonte

                # Linha
                dwg.add(dwg.line(
                    start=(line_start_x, line_y),
                    end=(arrow_tip_x, line_y),
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
                    insert=(v_box_x, v_box_y),
                    size=(NODE_BOX_WIDTH, NODE_BOX_HEIGHT),
                    fill=NODE_FILL,
                    stroke=STROKE_COLOR,
                    rx=4, ry=4
                ))
                # Texto do vizinho
                t_adj = dwg.text(
                    adj_display,
                    insert=(v_box_x + PADDING_TEXT_X, v_box_y + PADDING_TEXT_Y),
                    text_anchor="middle",
                    font_size=TEXT_SIZE,
                    fill="#111"
                )
                g_adj.add(t_adj)
                # Tooltip do vizinho
                t_full_adj = dwg.text(
                    f"{adj_name} (peso: {w})",
                    insert=(v_box_x + PADDING_TEXT_X, v_box_y + NODE_BOX_HEIGHT + 12),
                    text_anchor="middle",
                    font_size=TEXT_SIZE - 2
                )
                t_full_adj.attribs["class"] = "fullname"
                g_adj.add(t_full_adj)
                dwg.add(g_adj)  

                # Atualiza o X para o próximo vizinho
                current_element_end_x = v_box_x + NODE_BOX_WIDTH + HORIZONTAL_ADJ_NODE_SPACING
                current_cursor_x = v_box_x + NODE_BOX_WIDTH

        max_rendered_content_x = max(max_rendered_content_x, current_cursor_x)

    # --- Fim do Loop Principal ---

    total_width = max_rendered_content_x + MARGIN_LEFT
    dwg.viewbox(0, 0, total_width, total_height) 

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

    st.info("Passe o mouse sobre as caixas para ver o nome completo e o peso agregado.")

    modified_svg_for_download = _prepare_svg_for_download(svg_string, int(total_width), int(total_height))

    # Download
    st.download_button(
        "Baixar visualização (SVG)",
        data=modified_svg_for_download.encode("utf-8"),
        file_name="lista_adjacencia_filtrada.svg",
        mime="image/svg+xml"
    )

    # Legenda
    st.markdown("---")
    st.subheader(f"Legenda dos Pesos (Mostrando {n} autores)")
    st.write(f"- Comentário em Issue/PR: {WEIGHTS.get('COMMENT', 'N/A')}")
    st.write(f"- Abertura de Issue comentada: {WEIGHTS.get('ISSUE_COMMENTED', 'N/A')}")
    st.write(f"- Revisão/Aprovação de PR: {WEIGHTS.get('REVIEW', 'N/A')}")
    st.write(f"- Merge de PR: {WEIGHTS.get('MERGE', 'N/A')}")

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
