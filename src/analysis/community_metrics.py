from collections import deque, defaultdict
from typing import List, Tuple, Dict
import math

def _get_undirected_adj(out_adj: List[List[Tuple[int, float]]]) -> List[List[Tuple[int, float]]]:
    """Cria uma lista de adjacência não-direcionada/simétrica a partir da dirigida."""
    n = len(out_adj)
    undirected_adj = [[] for _ in range(n)]
    processed_edges = set() 
    
    for u in range(n):
        for v, _ in out_adj[u]:
            edge = tuple(sorted((u, v)))
            if edge not in processed_edges:
                undirected_adj[u].append((v, 1.0))
                undirected_adj[v].append((u, 1.0))
                processed_edges.add(edge)
                
    return undirected_adj


def girvan_newman_community_detection(out_adj: List[List[Tuple[int, float]]], max_splits: int = 5):
    """
    Detecção de comunidades usando Girvan-Newman (G-N). Remove iterativamente a aresta 
    com a maior Betweenness Centrality (não-ponderada de aresta).
    """
    n = len(out_adj)
    current_out_adj = _get_undirected_adj(out_adj)
    
    if n == 0:
        return []

    def get_connected_components(adj: List[List[Tuple[int, float]]]):
        """Helper para encontrar componentes conexos (comunidades) via BFS."""
        visited = [False] * n
        components = []
        for i in range(n):
            if not visited[i]:
                component = set()
                q = deque([i])
                visited[i] = True
                while q:
                    u = q.popleft()
                    component.add(u)
                    for v, _ in adj[u]: 
                        if not visited[v]:
                            visited[v] = True
                            q.append(v)
                if component:
                    components.append(component)
        return components

    # O loop principal G-N: remove arestas até max_splits
    for split in range(max_splits):
        edge_scores = defaultdict(float)
        
        # 1. Calcular Betweenness Centrality da Aresta (usando Brandes/BFS modificado)
        for s in range(n):
            S = []
            P = [[] for _ in range(n)]
            sigma = [0.0] * n
            dist = [-1] * n
            sigma[s] = 1.0
            dist[s] = 0
            Q = deque([s])
            
            neighbors_current = [ [v for v,_ in current_out_adj[u]] for u in range(n) ]

            while Q:
                v = Q.popleft()
                S.append(v)
                for w in neighbors_current[v]:
                    if dist[w] < 0:
                        dist[w] = dist[v] + 1
                        Q.append(w)
                    if dist[w] == dist[v] + 1:
                        sigma[w] += sigma[v]
                        P[w].append(v)

            delta = [0.0] * n
            while S:
                w = S.pop()
                for v in P[w]:
                    if sigma[w] != 0:
                        contribution = (sigma[v] / sigma[w]) * (1.0 + delta[w])
                        edge = tuple(sorted((v, w)))
                        edge_scores[edge] += contribution
                        delta[v] += contribution
                        
        # 2. Encontrar e remover a aresta com a maior Betweenness
        if not edge_scores:
            break
            
        max_edge_val = -1.0
        edge_to_remove = None
        
        for edge, score in edge_scores.items():
            if score / 2.0 > max_edge_val:
                max_edge_val = score / 2.0
                edge_to_remove = edge

        if edge_to_remove is None:
            break
            
        u_rem, v_rem = edge_to_remove

        # 3. Remover a aresta (simétrica)
        # remove o vizinho V de U
        current_out_adj[u_rem] = [(v, w) for v, w in current_out_adj[u_rem] if v != v_rem]
        # remove o vizinho U de V
        current_out_adj[v_rem] = [(v, w) for v, w in current_out_adj[v_rem] if v != u_rem]

    # Retorna os Componentes Conexos resultantes
    communities = get_connected_components(current_out_adj)
    return [list(c) for c in communities] 


def find_bridging_ties(out_adj: List[List[Tuple[int, float]]], communities: List[List[int]]):
    """
    Identifica os 'Bridging Ties' (Laços de Ponte): arestas dirigidas e ponderadas
    que conectam dois nós pertencentes a comunidades diferentes.
    """
    if not communities:
        return []

    # Mapeamento nó -> índice da comunidade
    node_to_community = {}
    for i, community in enumerate(communities):
        for node in community:
            node_to_community[node] = i

    bridging_ties = []
    
    # Percorrer todas as arestas dirigidas e ponderadas no grafo original (out_adj)
    for u, nbrs in enumerate(out_adj):
        u_community = node_to_community.get(u)
        
        if u_community is None: 
            continue
            
        for v, w in nbrs:
            v_community = node_to_community.get(v)

            # Se os nós u e v estão em comunidades diferentes
            if v_community is not None and u_community != v_community:
                bridging_ties.append((u, v, w))

    return bridging_ties