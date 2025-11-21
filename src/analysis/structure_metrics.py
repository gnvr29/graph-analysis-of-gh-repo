import math
from collections import defaultdict

def calculate_density(num_vertices: int, num_edges: int) -> float:
    """
    Calcula a densidade do grafo.
    Para grafo direcionado: D = m / (n * (n - 1))
    """
    if num_vertices <= 1:
        return 0.0
    possible_edges = num_vertices * (num_vertices - 1)
    return num_edges / possible_edges

def calculate_average_clustering_coefficient(adj_list: list[dict]) -> float:
    """
    Calcula o coeficiente de aglomeração médio.
    Trata o grafo como NÃO-DIRECIONADO para analisar a 'coesão social' (colaboração).
    
    Lógica:
    Para cada nó u:
      1. Identifica seus vizinhos (entrada e saída combinados).
      2. Conta quantas ligações existem entre esses vizinhos.
      3. Divide pelo total de ligações possíveis entre eles.
    """
    n = len(adj_list)
    if n == 0:
        return 0.0

    # Converter para lista de adjacência não-direcionada
    undirected_adj = defaultdict(set)
    for u, neighbors in enumerate(adj_list):
        for v in neighbors:
            if u != v:
                undirected_adj[u].add(v)
                undirected_adj[v].add(u)

    total_coefficient = 0.0
    
    for u in range(n):
        neighbors = list(undirected_adj[u])
        k = len(neighbors)
        
        if k < 2:
            continue
            
        actual_links = 0
        for i in range(k):
            for j in range(i + 1, k):
                neighbor_a = neighbors[i]
                neighbor_b = neighbors[j]
                
                if neighbor_b in undirected_adj[neighbor_a]:
                    actual_links += 1
        
        # Total possível de conexões entre os vizinhos: k * (k-1) / 2
        possible_links = (k * (k - 1)) / 2
        
        local_coefficient = actual_links / possible_links
        total_coefficient += local_coefficient

    return total_coefficient / n

def calculate_assortativity(adj_list: list[dict]) -> float:
    """
    Calcula a assortatividade de grau (Correlação de Pearson entre graus dos nós conectados).
    Analisa se nós muito conectados tendem a se conectar com outros nós muito conectados.
    
    Retorna:
       1.0: Perfeitamente assortativa (famosos com famosos).
       0.0: Não correlacionada.
      -1.0: Disassortativa (famosos com novatos).
    """
    # Calcular graus totais de cada nó
    n = len(adj_list)
    degrees = [0] * n
    
    edges = []
    
    for u, neighbors in enumerate(adj_list):
        degrees[u] += len(neighbors)
        for v in neighbors:
            degrees[v] += 1
            edges.append((u, v))
            
    if not edges:
        return 0.0

    # Preparar as listas X e Y para correlação
    # X = grau do nó de origem, Y = grau do nó de destino
    x_vals = []
    y_vals = []
    
    for u, v in edges:
        x_vals.append(degrees[u])
        y_vals.append(degrees[v])
        
    sum_x = sum(x_vals)
    sum_y = sum(y_vals)
    sum_xy = sum(i * j for i, j in zip(x_vals, y_vals))
    sum_x2 = sum(i ** 2 for i in x_vals)
    sum_y2 = sum(i ** 2 for i in y_vals)
    
    num_items = len(x_vals)
    
    numerator = (num_items * sum_xy) - (sum_x * sum_y)
    denominator = math.sqrt((num_items * sum_x2 - sum_x ** 2) * (num_items * sum_y2 - sum_y ** 2))
    
    if denominator == 0:
        return 0.0
        
    return numerator / denominator