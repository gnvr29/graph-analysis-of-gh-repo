import streamlit as st
from src.core.AbstractGraph import AbstractGraph
from typing import cast
import matplotlib.pyplot as plt
import math
import random 

def _get_graph_from_session() -> AbstractGraph:
    """
    Retorna o grafo atual do session_state.
    Garante que seja uma instância de AbstractGraph ou de uma subclasse.
    """
    graph = st.session_state.get("graph_obj")
    if graph is None:
        raise ValueError("Grafo não foi gerado ou carregado no state.")
    
    # Checa se é do tipo AbstractGraph ou qualquer subclasse
    if not isinstance(graph, AbstractGraph):
        # fallback: checa se o objeto tem os métodos esperados de AbstractGraph
        required_methods = [
            "getVertexCount", "getEdgeCount", "hasEdge",
            "addEdge", "removeEdge", "getAsAdjacencyList", "getAsAdjacencyMatrix"
        ]
        missing_methods = [m for m in required_methods if not callable(getattr(graph, m, None))]
        if missing_methods:
            raise TypeError(
                f"O objeto em 'graph_obj' não é compatível com AbstractGraph. "
                f"Faltam métodos: {missing_methods}. Tipo atual: {type(graph)}"
            )
    
    return graph

def get_vertex_count() -> int:
    """Retorna o número de vértices no grafo."""
    graph = _get_graph_from_session()
    return graph.getVertexCount()

def get_edge_count() -> int:
    """Retorna o número de arestas no grafo."""
    graph = _get_graph_from_session()
    return graph.getEdgeCount()

def has_edge(u: int, v: int) -> bool:
    """Verifica se existe uma aresta (u, v)."""
    graph = _get_graph_from_session()
    return graph.hasEdge(u, v)

def add_edge(u: int, v: int, weight: float = 1.0) -> bool:
    """
    Adiciona uma aresta (u, v) com peso no grafo atual.
    Retorna True se a aresta foi adicionada, False se ignorada (duplicada ou laço).
    """
    graph = _get_graph_from_session()

    # Verifica se a aresta já existe ou se é um laço (u == v)
    if u == v or graph.hasEdge(u, v):
        return False

    graph.addEdge(u, v, weight)

    # Marca a aresta como recém-adicionada
    if "new_edges" not in st.session_state:
        st.session_state.new_edges = set()
    st.session_state.new_edges.add((u, v))

    # Atualiza o session_state com o mesmo objeto
    st.session_state.graph_obj = graph
    st.session_state.last_added_edge = (u, v)  # Para destaque imediato
    return True

def remove_edge(u: int, v: int) -> None:
    """Remove a aresta (u, v)."""
    graph = _get_graph_from_session()
    graph.removeEdge(u, v)
    # Nota: Isso modifica o grafo no state.

def add_vertex() -> int:
    graph = _get_graph_from_session()

    # Chama o método real da classe do grafo
    new_index = graph.addVertex()

    # Atualiza o state com o grafo modificado
    st.session_state.graph_obj = graph

    # Guarda para highlight, igual ao comportamento usado para edges
    st.session_state.last_added_vertex = new_index

    return new_index


def is_successor(u: int, v: int) -> bool:
    """Verifica se v é sucessor de u (aresta u -> v)."""
    graph = _get_graph_from_session()
    return graph.isSucessor(u, v)

def is_predecessor(u: int, v: int) -> bool:
    """Verifica se v é predecessor de u (aresta v -> u)."""
    graph = _get_graph_from_session()
    return graph.isPredecessor(u, v)

def is_divergent(u1: int, v1: int, u2: int, v2: int) -> bool:
    """Verifica se as arestas (u1, v1) e (u2, v2) são divergentes."""
    graph = _get_graph_from_session()
    return graph.isDivergent(u1, v1, u2, v2)

def is_convergent(u1: int, v1: int, u2: int, v2: int) -> bool:
    """Verifica se as arestas (u1, v1) e (u2, v2) são convergentes."""
    graph = _get_graph_from_session()
    return graph.isConvergent(u1, v1, u2, v2)

def is_incident(u: int, v: int, x: int) -> bool:
    """Verifica se o vértice x é incidente à aresta (u, v)."""
    graph = _get_graph_from_session()
    return graph.isIncident(u, v, x)

def get_vertex_in_degree(v: int) -> int:
    """Retorna o grau de entrada do vértice v."""
    graph = _get_graph_from_session()
    return graph.getVertexInDegree(v)

def get_vertex_out_degree(v: int) -> int:
    """Retorna o grau de saída do vértice v."""
    graph = _get_graph_from_session()
    return graph.getVertexOutDegree(v)

def set_vertex_weight(v: int, weight: float) -> None:
    """Define o peso do vértice v."""
    graph = _get_graph_from_session()
    graph.setVertexWeight(v, weight)

def get_vertex_weight(v: int) -> float:
    """Retorna o peso do vértice v."""
    graph = _get_graph_from_session()
    return graph.getVertexWeight(v)

def set_edge_weight(u: int, v: int, weight: float) -> None:
    """Define o peso da aresta (u, v)."""
    graph = _get_graph_from_session()
    graph.setEdgeWeight(u, v, weight)

def get_edge_weight(u: int, v: int) -> float:
    """Retorna o peso da aresta (u, v)."""
    graph = _get_graph_from_session()
    return graph.getEdgeWeight(u, v)

def is_connected() -> bool:
    """Verifica se o grafo é (fracamente) conexo."""
    graph = _get_graph_from_session()
    return graph.isConnected()

def is_empty() -> bool:
    """Verifica se o grafo está vazio (sem arestas)."""
    graph = _get_graph_from_session()
    return graph.isEmptyGraph()

def is_complete() -> bool:
    """Verifica se o grafo é completo."""
    graph = _get_graph_from_session()
    return graph.isCompleteGraph()

def export_to_gephi(path: str) -> None:
    """Exporta o grafo para um arquivo no formato GEPHI."""
    graph = _get_graph_from_session()
    graph.exportToGEPHI(path)

def get_adjacency_list() -> list[dict[int, float]]:
    """Retorna a representação do grafo como lista de adjacência."""
    graph = _get_graph_from_session()
    return graph.getAsAdjacencyList()

def get_adjacency_matrix() -> list[list[float]]:
    """Retorna a representação do grafo como matriz de adjacência."""
    graph = _get_graph_from_session()
    return graph.getAsAdjacencyMatrix()

def draw_graph(graph: AbstractGraph, idx_to_name: dict, indices_to_render: list, highlight_vertex=None, highlight_edges=None):    

    if highlight_edges is None:
        highlight_edges = set()
 
    st.subheader("Visualização Gráfica")

    graph = _get_graph_from_session()

    if not indices_to_render:
        st.warning("Nenhum autor corresponde aos filtros selecionados.")
        return

    n = len(indices_to_render)

    # ================= PARÂMETROS DE REPULSÃO =================
    area = 2000000               
    k = math.sqrt(area / n) * 2 
    iterations = 800            
    cooling = 0.95              
    max_step = k * 8            
    repulsion_factor = 20000        
    attraction_factor = 0.4     

    # ================= INICIALIZAÇÃO =================
    positions = {i: [random.uniform(-k, k), random.uniform(-k, k)] for i in indices_to_render}

    # ================= SIMULAÇÃO =================
    progress_bar = st.progress(0, text="Calculando...")
    for iter_num in range(iterations):
        disp = {i: [0.0, 0.0] for i in indices_to_render}

        # Repulsão
        for i, v in enumerate(indices_to_render):
            for j in range(i + 1, n):
                u = indices_to_render[j]
                dx = positions[v][0] - positions[u][0]
                dy = positions[v][1] - positions[u][1]
                dist = math.sqrt(dx * dx + dy * dy) + 0.01
                force = repulsion_factor * (k * k) / dist
                disp[v][0] += (dx / dist) * force
                disp[v][1] += (dy / dist) * force
                disp[u][0] -= (dx / dist) * force
                disp[u][1] -= (dy / dist) * force

        # Atração 
        for u in indices_to_render:
            for v in indices_to_render:
                if graph.hasEdge(u, v):
                    dx = positions[u][0] - positions[v][0]
                    dy = positions[u][1] - positions[v][1]
                    dist = math.sqrt(dx * dx + dy * dy) + 0.01
                    force = attraction_factor * (dist * dist) / k
                    disp[u][0] -= (dx / dist) * force
                    disp[u][1] -= (dy / dist) * force
                    disp[v][0] += (dx / dist) * force
                    disp[v][1] += (dy / dist) * force

        # Atualiza posições
        for v in indices_to_render:
            dx, dy = disp[v]
            dist = math.sqrt(dx * dx + dy * dy)
            if dist > 0:
                step = min(max_step, dist)
                positions[v][0] += (dx / dist) * step
                positions[v][1] += (dy / dist) * step

        max_step *= cooling
        if (iter_num + 1) % (iterations // 20) == 0:
             progress_bar.progress((iter_num + 1) / iterations, text=f"Calculando layout: {iter_num+1}/{iterations} iterações")
    
    progress_bar.empty()

    # Normalização
    xs = [positions[i][0] for i in indices_to_render]
    ys = [positions[i][1] for i in indices_to_render]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    scale = 10
    for i in indices_to_render:
        positions[i][0] = (positions[i][0] - (min_x + max_x) / 2) * scale
        positions[i][1] = (positions[i][1] - (min_y + max_y) / 2) * scale

    # Desenho
    st.success("Layout calculado. Desenhando gráfico...")
    plt.figure(figsize=(16, 12))
    plt.axis("off")

    # Arestas
    
    for u in indices_to_render:
        for v in indices_to_render:
            if graph.hasEdge(u, v):

                x1, y1 = positions[u]
                x2, y2 = positions[v]

                # Destaque da aresta recém-adicionada
                if (u, v) in highlight_edges or (v, u) in highlight_edges:
                    color = "red"
                    alpha = 0.9
                    lw = 3
                    st.write(f"[LOG] Aresta destacada detectada: ({u}, {v})")
                else:
                    color = "gray"
                    alpha = 0.5
                    lw = 1.5

                dx = x2 - x1
                dy = y2 - y1
                dist = math.sqrt(dx*dx + dy*dy) + 1

                head_w = dist * 0.05
                head_l = dist * 0.08

                plt.arrow(
                    x1, y1, dx, dy,
                    head_width=head_w,
                    head_length=head_l,
                    fc=color,
                    ec=color,
                    alpha=alpha,
                    linewidth=lw,
                    length_includes_head=True
                )

    # Nós
    highlight_vertex = st.session_state.get("new_vertices", set())

    # Dentro do loop que desenha os nós
    for i in indices_to_render:
        x, y = positions[i]
        if i in highlight_vertex:
            node_color = "yellow"
            node_size = 260
            edge_color = "red"
        else:
            node_color = "#5DADE2"
            node_size = 120
            edge_color = "black"

        plt.scatter(
            x, y,
            s=node_size,
            color=node_color,
            edgecolors=edge_color,
            linewidths=2,
            zorder=3
        )

        plt.text(x, y, idx_to_name[i], fontsize=8, ha="center", va="center", color="black")

    st.pyplot(plt)
    plt.clf()

def build_graph(impl_class: type[AbstractGraph], vertex_count: int, edges: list[tuple[int, int, float]]) -> AbstractGraph:
    """Constrói um grafo usando a classe de implementação fornecida."""
    print(f"Construindo grafo com implementação: {impl_class.__name__}")
    graph = impl_class(vertex_count)
    for u_idx, v_idx, weight in edges:
        graph.addEdge(u_idx, v_idx, weight)
    return graph