"""Métricas de grafo implementadas do zero (sem bibliotecas de grafos).

As funções esperam nós como inteiros de 0..n-1 e arestas como uma lista de
tuplas (u, v, w) onde w é um peso positivo (float ou int). A implementação
usa listas de adjacência construídas a partir das arestas.

Métricas fornecidas:
- build_adjlists
- degree_centrality (in/out/total, ponderada/não-ponderada)
- betweenness_centrality (algoritmo de Brandes, não-ponderado)
- closeness_centrality (menores caminhos não-ponderados via BFS)
- pagerank (método iterativo de potência)
- eigenvector_centrality (iteração de potência usando pesos de entrada)

Todas as implementações evitam bibliotecas externas de grafo. Numpy não é
necessário.
"""
from collections import deque, defaultdict
from typing import List, Tuple, Dict
import heapq
import math


def build_adjlists(n: int, edges: List[Tuple[int, int, float]]):
    """Retorna (out_adj, in_adj) onde cada um é uma lista de listas de (vizinho, peso)."""
    out_adj = [[] for _ in range(n)]
    in_adj = [[] for _ in range(n)]
    for u, v, w in edges:
        out_adj[u].append((v, w))
        in_adj[v].append((u, w))
    return out_adj, in_adj


# Default weights for integrated graph (can be overridden by callers)
DEFAULT_RELATION_WEIGHTS = {
    'COMMENT': 2,
    'ISSUE_COMMENTED': 3,
    'REVIEW': 4,
    'MERGE': 5,
}


def build_relation_edge_lists(edges_by_relation: Dict[str, List[Tuple[int, int]]], *, default_weight: float = 1.0):
    """Constrói listas de arestas ponderadas por relação.

    Args:
        edges_by_relation: dict onde a chave é o nome da relação (ex: 'COMMENT')
            e o valor é uma lista de tuplas (u, v) com índices inteiros de nós.
        default_weight: peso atribuído a cada aresta nas listas separadas (padrão 1.0).

    Retorna:
        dict: mapeamento relação -> lista de arestas (u, v, w).
    """
    result = {}
    for rel, pairs in edges_by_relation.items():
        result[rel] = [(int(u), int(v), float(default_weight)) for (u, v) in pairs]
    return result


def build_integrated_edges(edges_by_relation: Dict[str, List[Tuple[int, int]]],
                           weights: Dict[str, float] = None):
    """Agrega arestas de várias relações em um grafo integrado ponderado.

    Cada aresta (u, v) presente em uma relação contribui com o peso definido
    em `weights` para a soma total daquela aresta no grafo integrado.

    Args:
        edges_by_relation: dict relação -> lista de (u, v)
        weights: dict relação -> peso (se None, usa DEFAULT_RELATION_WEIGHTS)

    Retorna:
        list de tuplas (u, v, total_weight) agregadas por par (u, v).
    """
    if weights is None:
        weights = DEFAULT_RELATION_WEIGHTS

    agg = {}
    for rel, pairs in edges_by_relation.items():
        w = float(weights.get(rel, 1.0))
        for (u, v) in pairs:
            key = (int(u), int(v))
            agg[key] = agg.get(key, 0.0) + w

    return [(u, v, wt) for (u, v), wt in agg.items()]


def build_relation_graphs_adjlists(n: int, edges_by_relation: Dict[str, List[Tuple[int, int]]]):
    """Retorna um dicionário relação -> (out_adj, in_adj) onde cada grafo usa peso 1.0."""
    rel_graphs = {}
    relation_edges = build_relation_edge_lists(edges_by_relation, default_weight=1.0)
    for rel, edges in relation_edges.items():
        out_adj, in_adj = build_adjlists(n, edges)
        rel_graphs[rel] = (out_adj, in_adj)
    return rel_graphs


def build_integrated_graph_adjlists(n: int, edges_by_relation: Dict[str, List[Tuple[int, int]]],
                                    weights: Dict[str, float] = None):
    """Retorna as listas de adjacência do grafo integrado ponderado."""
    edges = build_integrated_edges(edges_by_relation, weights=weights)
    return build_adjlists(n, edges)


def degree_centrality(out_adj: List[List[Tuple[int, float]]], in_adj: List[List[Tuple[int, float]]],
                      weighted: bool = True, mode: str = "total") -> Dict[int, float]:
    """Computa centralidade de grau.

    mode: 'out', 'in' ou 'total'.
    Se weighted=True soma os pesos das arestas; caso contrário conta as arestas.
    Retorna um mapeamento nó -> centralidade (não normalizado).
    """
    n = len(out_adj)
    deg = {i: 0.0 for i in range(n)}
    for i in range(n):
        if mode in ("out", "total"):
            if weighted:
                deg[i] += sum(w for _, w in out_adj[i])
            else:
                deg[i] += len(out_adj[i])
        if mode in ("in", "total"):
            if weighted:
                deg[i] += sum(w for _, w in in_adj[i])
            else:
                deg[i] += len(in_adj[i])
    return deg


def betweenness_centrality(out_adj: List[List[Tuple[int, float]]], directed: bool = True) -> Dict[int, float]:
    """Algoritmo de Brandes para centralidade de intermediação (não-ponderado).

    Complexidade O(n*m) para grafos não-ponderados.
    Retorna um dicionário nó->betweenness (não normalizado).
    """
    n = len(out_adj)
    CB = [0.0] * n

    neighbors = [ [v for v,_ in out_adj[u]] for u in range(n) ]

    for s in range(n):
        S = []
        P = [[] for _ in range(n)]
        sigma = [0.0] * n
        dist = [-1] * n
        sigma[s] = 1.0
        dist[s] = 0
        Q = deque([s])
        while Q:
            v = Q.popleft()
            S.append(v)
            for w in neighbors[v]:
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
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                CB[w] += delta[w]

    return {i: CB[i] for i in range(n)}


def betweenness_centrality_weighted(out_adj: List[List[Tuple[int, float]]]) -> Dict[int, float]:
    """Brandes algorithm adaptado para grafos ponderados (arestas com peso > 0).

    Implementação utiliza Dijkstra para caminhos mínimos ponderados (custo = 1/weight).
    Retorna dicionário nó -> betweenness (não normalizado).

    Observação sobre custo: como aqui os pesos representam força/importância
    (maior = mais forte), usamos custo = 1.0 / weight para que arestas mais
    pesadas correspondam a caminhos "mais curtos".
    """
    n = len(out_adj)
    CB = [0.0] * n

    for s in range(n):
        S = []
        P = [[] for _ in range(n)]
        sigma = [0.0] * n
        dist = [math.inf] * n
        sigma[s] = 1.0
        dist[s] = 0.0

        heap = [(0.0, s)]
        while heap:
            d_v, v = heapq.heappop(heap)
            if d_v > dist[v] + 1e-15:
                continue
            S.append(v)
            for w, weight in out_adj[v]:
                if weight <= 0:
                    continue
                cost = 1.0 / float(weight)
                alt = dist[v] + cost
                if alt + 1e-15 < dist[w]:
                    dist[w] = alt
                    heapq.heappush(heap, (alt, w))
                    sigma[w] = sigma[v]
                    P[w] = [v]
                elif abs(alt - dist[w]) <= 1e-15:
                    sigma[w] += sigma[v]
                    P[w].append(v)

        delta = [0.0] * n
        while S:
            w = S.pop()
            for v in P[w]:
                if sigma[w] != 0:
                    delta[v] += (sigma[v] / sigma[w]) * (1.0 + delta[w])
            if w != s:
                CB[w] += delta[w]

    return {i: CB[i] for i in range(n)}


def closeness_centrality(out_adj: List[List[Tuple[int, float]]], directed: bool = True) -> Dict[int, float]:
    """Centralidade de proximidade não-ponderada usando distâncias por BFS.

    closeness(v) = (número de nós alcançáveis) / soma(das distâncias para nós alcançáveis)
    Retorna 0 para nós isolados.
    """
    n = len(out_adj)
    neighbors = [ [v for v,_ in out_adj[u]] for u in range(n) ]
    C = {}
    for s in range(n):
        dist = [-1] * n
        Q = deque([s])
        dist[s] = 0
        while Q:
            v = Q.popleft()
            for w in neighbors[v]:
                if dist[w] < 0:
                    dist[w] = dist[v] + 1
                    Q.append(w)
        total = 0
        reachable = 0
        for d in dist:
            if d > 0:
                total += d
                reachable += 1
        if total > 0:
            C[s] = reachable / total
        else:
            C[s] = 0.0
    return C


def pagerank(out_adj: List[List[Tuple[int, float]]], damping: float = 0.85, max_iter: int = 100,
             tol: float = 1.0e-6) -> Dict[int, float]:
    """PageRank simples (os pesos das arestas são usados para distribuir o rank).

    Tratamos os pesos de saída como frações da força de saída para distribuir o rank proporcionalmente.
    """
    n = len(out_adj)
    if n == 0:
        return {}
    out_strength = [sum(w for _, w in out_adj[i]) for i in range(n)]
    pr = [1.0 / n] * n
    for it in range(max_iter):
        new_pr = [ (1.0 - damping) / n ] * n
        for i in range(n):
            if out_strength[i] == 0:
                add = damping * pr[i] / n
                for j in range(n):
                    new_pr[j] += add
            else:
                for j, w in out_adj[i]:
                    new_pr[j] += damping * pr[i] * (w / out_strength[i])
        err = sum(abs(new_pr[i] - pr[i]) for i in range(n))
        pr = new_pr
        if err < tol:
            break
    return {i: pr[i] for i in range(n)}


def eigenvector_centrality(out_adj: List[List[Tuple[int, float]]], in_adj: List[List[Tuple[int, float]]],
                           max_iter: int = 100, tol: float = 1.0e-6) -> Dict[int, float]:
    """Iteração de potência para centralidade de autovetor usando pesos de entrada.

    Calculamos v <- A^T v (ou seja, arestas de entrada contribuem) e normalizamos.
    """
    n = len(out_adj)
    if n == 0:
        return {}
    v = [1.0 / n] * n
    for _ in range(max_iter):
        new_v = [0.0] * n
        for i in range(n):
            s = 0.0
            for j, w in in_adj[i]:
                s += w * v[j]
            new_v[i] = s
        norm = sum(abs(x) for x in new_v)
        if norm == 0:
            break
        new_v = [x / norm for x in new_v]
        err = sum(abs(new_v[i] - v[i]) for i in range(n))
        v = new_v
        if err < tol:
            break
    return {i: v[i] for i in range(n)}


__all__ = [
    "build_adjlists",
    "DEFAULT_RELATION_WEIGHTS",
    "build_relation_edge_lists",
    "build_integrated_edges",
    "build_relation_graphs_adjlists",
    "build_integrated_graph_adjlists",
    "degree_centrality",
    "betweenness_centrality",
    "betweenness_centrality_weighted",
    "closeness_centrality",
    "pagerank",
    "eigenvector_centrality",
]
