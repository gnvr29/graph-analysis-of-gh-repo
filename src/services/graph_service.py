import streamlit as st
from src.core.AbstractGraph import AbstractGraph
from typing import cast

def _get_graph_from_session() -> AbstractGraph:
    """
    Helper interno para buscar, validar e retornar o objeto de grafo
    armazenado no session_state.
    """
    if 'graph_obj' not in st.session_state or st.session_state.graph_obj is None:
        raise ValueError("Grafo não foi gerado ou carregado no state.")
    graph = cast(AbstractGraph, st.session_state.graph_obj)
    if not isinstance(graph, AbstractGraph):
        raise TypeError("O objeto em 'graph_obj' não é uma instância de AbstractGraph.")
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

def add_edge(u: int, v: int, weight: float = 1.0) -> None:
    """Adiciona uma aresta (u, v) com um peso."""
    graph = _get_graph_from_session()
    graph.addEdge(u, v, weight)
    # Nota: Isso modifica o grafo no state. 
    # O Streamlit pode precisar ser re-executado para UI refletir.

def remove_edge(u: int, v: int) -> None:
    """Remove a aresta (u, v)."""
    graph = _get_graph_from_session()
    graph.removeEdge(u, v)
    # Nota: Isso modifica o grafo no state.


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