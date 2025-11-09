from src.core.AbstractGraph import Graph

class AdjacencyListGraph(Graph):
    """
    Implementação da API de Grafo usando Lista de Adjacência.
    Usa uma lista de dicionários, onde self.adj[u] = {v: peso, ...}
    """

    def __init__(self, num_vertices: int):
        """Construtor da Lista de Adjacência."""
        super().__init__(num_vertices)
        self.adj_out = [{} for _ in range(num_vertices)]
        self.adj_in = [{} for _ in range(num_vertices)]

    def hasEdge(self, u: int, v: int) -> bool:
        """Verifica se existe uma aresta (u, v)."""
        self._validate_edge_vertices(u, v)
        return v in self.adj_out[u]

    def addEdge(self, u: int, v: int, weight: float = 1.0) -> None:
        """Adiciona uma aresta (u, v) com um peso."""
        self._validate_edge_vertices(u, v)
        
        if u == v:
            print(f"Aviso: Tentativa de adicionar laço (loop) em {u}, operação ignorada.")
            return

        if not self.hasEdge(u, v):
            self._edge_count += 1
            
        self.adj_out[u][v] = weight
        self.adj_in[v][u] = weight 

    def removeEdge(self, u: int, v: int) -> None:
        """Remove a aresta (u, v)."""
        self._validate_edge_vertices(u, v)
        if self.hasEdge(u, v):
            del self.adj_out[u][v]
            del self.adj_in[v][u]
            self._edge_count -= 1

    def getVertexInDegree(self, v: int) -> int:
        """Retorna o grau de entrada do vértice v."""
        self._validate_vertex(v)
        return len(self.adj_in[v])

    def getVertexOutDegree(self, v: int) -> int:
        """Retorna o grau de saída do vértice v."""
        self._validate_vertex(v)
        return len(self.adj_out[v])

    def setEdgeWeight(self, u: int, v: int, weight: float) -> None:
        """Define o peso da aresta (u, v)."""
        self._validate_edge_vertices(u, v)
        if not self.hasEdge(u, v):
            self.addEdge(u, v, weight)
        else:
            self.adj_out[u][v] = weight
            self.adj_in[v][u] = weight

    def getEdgeWeight(self, u: int, v: int) -> float:
        """Retorna o peso da aresta (u, v). """
        self._validate_edge_vertices(u, v)
        if not self.hasEdge(u, v):
            raise ValueError(f"Aresta ({u}, {v}) não existe.")
        return self.adj_out[u][v]

    def isConnected(self) -> bool:
        """
        Verifica se o grafo é fracamente conexo (usando Busca em Largura/Profundidade). """
        if self.getVertexCount() == 0:
            return True
            
        visited = [False] * self.getVertexCount()
        queue = [0] 
        visited[0] = True
        count = 0

        while queue:
            u = queue.pop(0)
            count += 1
            
            for v in self.adj_out[u]:
                if not visited[v]:
                    visited[v] = True
                    queue.append(v)
            
            for v in self.adj_in[u]:
                if not visited[v]:
                    visited[v] = True
                    queue.append(v)
        
        return count == self.getVertexCount()

    def isCompleteGraph(self) -> bool:
        """Verifica se o grafo é completo."""
        n = self.getVertexCount()
        return self.getEdgeCount() == n * (n - 1)