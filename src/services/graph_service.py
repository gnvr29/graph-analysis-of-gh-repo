import streamlit as st
# Corrigindo o import para corresponder ao nome do arquivo que criamos
from src.core.AbstractGraph import Graph
from typing import cast

def _get_graph_from_session() -> Graph:
    """
    Helper interno para buscar, validar e retornar o objeto de grafo
    armazenado no session_state.
    """
    if 'graph_obj' not in st.session_state or st.session_state.graph_obj is None:
        raise ValueError("Grafo não foi gerado ou carregado no state.")
    
    graph = cast(Graph, st.session_state.graph_obj)
    
    if not isinstance(graph, Graph):
        raise TypeError("O objeto em 'graph_obj' não é uma instância de Graph.")
        
    return graph

def get_vertex_count() -> int:
    """Retorna o número de vértices no grafo."""
    graph = _get_graph_from_session()
    return graph.getVertexCount()

def get_edge_count() -> int:
    """Retorna o número de arestas no grafo."""
    graph = _get_graph_from_session()
    return graph.getEdgeCount()

# --- Métodos de Manipulação de Arestas ---

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

# --- Métodos de Relação (Sucessor, Predecessor) ---

def is_successor(u: int, v: int) -> bool:
    """Verifica se v é sucessor de u (aresta u -> v)."""
    graph = _get_graph_from_session()
    return graph.isSucessor(u, v)

def is_predecessor(u: int, v: int) -> bool:
    """Verifica se v é predecessor de u (aresta v -> u)."""
    graph = _get_graph_from_session()
    return graph.isPredecessor(u, v)

# --- Métodos de Relação (Divergente, Convergente, Incidente) ---

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

# --- Métodos de Peso (Vértice) ---

def set_vertex_weight(v: int, weight: float) -> None:
    """Define o peso do vértice v."""
    graph = _get_graph_from_session()
    graph.setVertexWeight(v, weight)

def get_vertex_weight(v: int) -> float:
    """Retorna o peso do vértice v."""
    graph = _get_graph_from_session()
    return graph.getVertexWeight(v)

# --- Métodos de Peso (Aresta) ---

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
    return graph.isEmpty()

def is_complete() -> bool:
    """Verifica se o grafo é completo."""
    graph = _get_graph_from_session()
    return graph.isCompleteGraph()

# --- Métodos de Exportação ---

def export_to_gephi(path: str) -> None:
    """Exporta o grafo para um arquivo no formato GEPHI."""
    graph = _get_graph_from_session()
    graph.exportToGEPHI(path)