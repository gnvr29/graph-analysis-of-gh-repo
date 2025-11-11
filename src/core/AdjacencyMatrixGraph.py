from src.core.AbstractGraph import Graph

class AdjacencyMatrixGraph(Graph):
    """
    Implementação de grafo usando matriz de adjacência.

    Restrições implementadas:
    - Grafos simples: não permite laços (u == v) nem múltiplas arestas.
    - addEdge é idempotente: não duplica arestas.
    - Lança exceções para índices inválidos.
    """

    def __init__(self, num_vertices: int):
        super().__init__(num_vertices)
        # matriz n x n com 0.0 significando "sem aresta"
        self.matrix = [[0.0 for _ in range(num_vertices)] for _ in range(num_vertices)]

    def hasEdge(self, u: int, v: int) -> bool:
        self._validate_edge_vertices(u, v)
        return self.matrix[u][v] != 0.0

    def addEdge(self, u: int, v: int, weight: float = 1.0) -> None:
        self._validate_edge_vertices(u, v)
        if u == v:
            # Não permitimos laços em grafos simples
            raise ValueError(f"Laços não são permitidos: ({u},{v})")
        if weight is None:
            raise ValueError("Peso de aresta inválido: None")
        if self.matrix[u][v] == 0.0:
            # aresta nova
            self._edge_count += 1
        # idempotente: sobrescreve o mesmo peso sem duplicar
        self.matrix[u][v] = float(weight)

    def removeEdge(self, u: int, v: int) -> None:
        self._validate_edge_vertices(u, v)
        if self.matrix[u][v] != 0.0:
            self.matrix[u][v] = 0.0
            self._edge_count -= 1

    def getVertexInDegree(self, v: int) -> int:
        self._validate_vertex(v)
        count = 0
        for u in range(self._num_vertices):
            if self.matrix[u][v] != 0.0:
                count += 1
        return count

    def getVertexOutDegree(self, v: int) -> int:
        self._validate_vertex(v)
        count = 0
        for x in range(self._num_vertices):
            if self.matrix[v][x] != 0.0:
                count += 1
        return count

    def setEdgeWeight(self, u: int, v: int, weight: float) -> None:
        self._validate_edge_vertices(u, v)
        if weight is None:
            raise ValueError("Peso inválido: None")
        if self.matrix[u][v] == 0.0:
            # se não existe, cria (seguindo regras de addEdge)
            self.addEdge(u, v, weight)
        else:
            self.matrix[u][v] = float(weight)

    def getEdgeWeight(self, u: int, v: int) -> float:
        self._validate_edge_vertices(u, v)
        if self.matrix[u][v] == 0.0:
            raise ValueError(f"Aresta ({u}, {v}) não existe.")
        return self.matrix[u][v]

    def isConnected(self) -> bool:
        """
        Verifica se o grafo é fracamente conexo (ignora direção).
        Implementado via BFS em versão não-direcionada usando a matriz.
        """
        n = self.getVertexCount()
        if n == 0:
            return True
        visited = [False] * n
        queue = [0]
        visited[0] = True
        count = 0
        while queue:
            u = queue.pop(0)
            count += 1
            for v in range(n):
                if not visited[v] and (self.matrix[u][v] != 0.0 or self.matrix[v][u] != 0.0):
                    visited[v] = True
                    queue.append(v)
        return count == n

    def isCompleteGraph(self) -> bool:
        n = self.getVertexCount()
        # Para grafo dirigido simples completo: n*(n-1) arestas
        return self.getEdgeCount() == n * (n - 1)

    # Utilitário para construir a partir de uma lista de arestas (u,v,w)
    @classmethod
    def from_edge_list(cls, vertex_count: int, edges: list[tuple[int, int, float]]):
        g = cls(vertex_count)
        for u, v, w in edges:
            g.addEdge(u, v, w)
        return g
