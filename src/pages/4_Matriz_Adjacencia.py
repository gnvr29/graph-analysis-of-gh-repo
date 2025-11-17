import streamlit as st
import pandas as pd
from typing import List, Tuple
import html
import streamlit.components.v1 as components

from src.core.AdjacencyMatrixGraph import AdjacencyMatrixGraph
from src.utils.neo4j_connector import get_neo4j_service
from src.pages._shared_queries import (
    fetch_authors,
    fetch_edges_by_relation,
    build_integrated_edges,
    fetch_authors_and_edges,
    WEIGHTS,
)


def build_matrix(vertex_count: int, edges: List[Tuple[int, int, float]]) -> AdjacencyMatrixGraph:
    st.info(f"Construindo matriz com {vertex_count} vértices e {len(edges)} arestas...")
    graph = AdjacencyMatrixGraph(vertex_count)
    for u, v, w in edges:
        try:
            graph.addEdge(u, v, w)
        except Exception as exc:
            st.warning(f"Falha ao adicionar aresta {u}->{v} (peso={w}): {exc}")
    st.success("Matriz construída com sucesso.")
    return graph


def df_to_svg(df: pd.DataFrame, cell_w: int = 120, cell_h: int = 26) -> str:
    """Render a small, readable SVG table from a square DataFrame."""
    cols = list(df.columns)
    rows = list(df.index)
    ncols = len(cols)
    nrows = len(rows)
    width = cell_w * (ncols + 1)
    height = cell_h * (nrows + 1)
    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">']
    parts.append('<style>text{font-family: Arial, Helvetica, sans-serif; font-size:12px}</style>')

    for j, header in enumerate([""] + cols):
        x = j * cell_w
        parts.append(f'<rect x="{x}" y="0" width="{cell_w}" height="{cell_h}" fill="#f3f4f6" stroke="#d1d5db"/>')
        label = html.escape(str(header)) if header else ""
        parts.append(f'<text x="{x + cell_w/2}" y="{cell_h/2 + 5}" text-anchor="middle">{label}</text>')

    for i, row_name in enumerate(rows):
        y = (i + 1) * cell_h
        parts.append(f'<rect x="0" y="{y}" width="{cell_w}" height="{cell_h}" fill="#fbfbfb" stroke="#eee"/>')
        parts.append(f'<text x="{cell_w/2}" y="{y + cell_h/2 + 5}" text-anchor="middle">{html.escape(str(row_name))}</text>')
        for j, col in enumerate(cols):
            x = (j + 1) * cell_w
            val = df.iat[i, j]
            txt = "" if (pd.isna(val) or val == 0) else str(val)
            parts.append(f'<rect x="{x}" y="{y}" width="{cell_w}" height="{cell_h}" fill="#ffffff" stroke="#eee"/>')
            parts.append(f'<text x="{x + cell_w/2}" y="{y + cell_h/2 + 5}" text-anchor="middle">{html.escape(txt)}</text>')

    parts.append('</svg>')
    return "".join(parts)


def app():
    st.title("Matriz de Adjacência")
    st.markdown(
        """
        Visualização da matriz de adjacência (autores x autores) com pesos agregados.
        Esta página mostra a matriz como tabela e permite baixar a matriz como SVG.
        """
    )

    st.sidebar.header("Opções de Filtro")
    filter_with_edges = st.sidebar.checkbox("Mostrar apenas autores com interações de saída", value=True)
    limit = st.sidebar.number_input("Limitar autores (0 = sem limite, Top N por atividade)", min_value=0, value=0, step=10)
    weight_threshold = st.sidebar.slider("Mostrar apenas arestas com peso >=", min_value=0, max_value=WEIGHTS.get('MERGE', 5), value=0)
    graph_mode = st.sidebar.selectbox(
        "Tipo de grafo",
        (
            "Integrado (todas as interações, ponderadas)",
            "Comentários (apenas comentários em issues/PR)",
            "Issue comentada (abertura de issue comentada por outro)",
            "Revisões/Merges (reviews, aprovações e merges)",
        ),
        index=0,
    )

    try:
        neo4j_service = get_neo4j_service()
    except Exception as e:
        st.error(f"Erro ao obter conexão com Neo4j: {e}")
        st.stop()

    if st.button("Gerar Matriz"):
        with st.spinner("Buscando dados e construindo matriz..."):
            id_to_index, idx_to_name = fetch_authors(neo4j_service)
            if not id_to_index:
                st.warning("Nenhum autor encontrado no Neo4j.")
                return

            edges_by_relation = fetch_edges_by_relation(neo4j_service, id_to_index)

            if graph_mode.startswith("Integrado"):
                edges = build_integrated_edges(edges_by_relation, WEIGHTS)
            elif graph_mode.startswith("Comentários"):
                edges = [(u, v, WEIGHTS.get('COMMENT', 2)) for (u, v) in edges_by_relation.get('COMMENT', [])]
            elif graph_mode.startswith("Issue comentada"):
                edges = [(u, v, WEIGHTS.get('ISSUE_COMMENTED', 3)) for (u, v) in edges_by_relation.get('ISSUE_COMMENTED', [])]
            elif graph_mode.startswith("Revisões/Merges"):
                subset = {
                    'REVIEW': edges_by_relation.get('REVIEW', []),
                    'MERGE': edges_by_relation.get('MERGE', []),
                }
                subset_weights = {
                    'REVIEW': WEIGHTS.get('REVIEW', 4),
                    'MERGE': WEIGHTS.get('MERGE', 5),
                }
                edges = build_integrated_edges(subset, subset_weights)
            else:
                edges = []

            vertex_count = len(idx_to_name)

            if weight_threshold > 0:
                edges = [(u, v, w) for (u, v, w) in edges if w >= weight_threshold]

            graph = build_matrix(vertex_count, edges)

            names = [idx_to_name[i] for i in range(vertex_count)]
            mat = [[graph.matrix[i][j] for j in range(vertex_count)] for i in range(vertex_count)]
            df = pd.DataFrame(mat, index=names, columns=names)

            author_activity = [(i, sum(row)) for i, row in enumerate(mat)]
            if filter_with_edges:
                author_activity = [item for item in author_activity if item[1] > 0]
            author_activity.sort(key=lambda item: item[1], reverse=True)
            if limit > 0:
                author_activity = author_activity[:limit]
            indices_to_render = [i for i, _ in author_activity]

            if indices_to_render:
                sel_names = [names[i] for i in indices_to_render]
                df_sub = df.loc[sel_names, sel_names]
            else:
                df_sub = df

            st.subheader("Matriz (DataFrame)")
            st.dataframe(df_sub)

            svg = df_to_svg(df_sub)
            st.markdown("**Exportar matriz como SVG**")
            st.download_button("Baixar matriz (SVG)", data=svg.encode("utf-8"), file_name="matriz_adjacencia.svg", mime="image/svg+xml")

            st.markdown("---")
            st.subheader("Legenda dos Pesos")
            st.write(f"- Comentário em Issue/PR: {WEIGHTS.get('COMMENT', 'N/A')}")
            st.write(f"- Abertura de Issue comentada: {WEIGHTS.get('ISSUE_COMMENTED', 'N/A')}")
            st.write(f"- Revisão/Aprovação de PR: {WEIGHTS.get('REVIEW', 'N/A')}")
            st.write(f"- Merge de PR: {WEIGHTS.get('MERGE', 'N/A')}")


if __name__ == "__main__":
    app()