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


def build_adjlists(n: int, edges: List[Tuple[int, int, float]]):
    """Retorna (out_adj, in_adj) onde cada um é uma lista de listas de (vizinho, peso)."""
    out_adj = [[] for _ in range(n)]
    in_adj = [[] for _ in range(n)]
    for u, v, w in edges:
        out_adj[u].append((v, w))
        in_adj[v].append((u, w))
    return out_adj, in_adj


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

    # Converter para listas simples de vizinhos (não-ponderado) para BFS
    neighbors = [ [v for v,_ in out_adj[u]] for u in range(n) ]

    for s in range(n):
        # caminhos mais curtos a partir da fonte s
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

        # acumulação de dependências
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
            # normaliza por reachable para ser comparável entre nós
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
                # nó sem saída: distribui uniformemente (dangling)
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
        # normalizar
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
    "degree_centrality",
    "betweenness_centrality",
    "closeness_centrality",
    "pagerank",
    "eigenvector_centrality",
]
