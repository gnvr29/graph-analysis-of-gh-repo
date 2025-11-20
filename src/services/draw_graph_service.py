import matplotlib.pyplot as plt
import math
import streamlit as st
import random 

try:
    from src.core.AdjacencyListGraph import AdjacencyListGraph
    from src.core.AdjacencyMatrixGraph import AdjacencyMatrixGraph
    from src.core.AbstractGraph import AbstractGraph 
except ImportError as e:
    st.error(f"Erro crítico ao importar classes de Grafo: {e}")
    st.stop()


def draw_graph(graph: AbstractGraph, idx_to_name: dict, indices_to_render: list, highlight_vertex=None, highlight_edges=None):

    if highlight_edges is None:
        highlight_edges = set()
    """
    Desenha o grafo usando a API Abstrata,
    independente da implementação.
    """
    st.subheader("Visualização Gráfica")

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

# Arestas com destaque opcional
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
    for i in indices_to_render:
        x, y = positions[i]
        
        if highlight_vertex is not None and i == highlight_vertex:
            node_color = "orange"      # Cor diferente para destaque
            node_size = 250            # Maior tamanho para destacar
            edge_color = "red"
        else:
            node_color = "#5DADE2"
            node_size = 120
            edge_color = "black"
        
        plt.scatter(x, y, s=node_size, color=node_color, edgecolors=edge_color, zorder=3)
        plt.text(x, y, idx_to_name[i], fontsize=8, ha="center", va="center", color="black")


    st.pyplot(plt)
    plt.clf()