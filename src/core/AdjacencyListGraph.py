from src.core.AbstractGraph import AbstractGraph
from collections import deque

class AdjacencyListGraph(AbstractGraph):
    """
    Implementação concreta de um Grafo (direcionado e ponderado) 
    usando Listas de Adjacência.
    
    Esta classe herda de 'AbstractGraph' e implementa todos os 
    métodos abstratos definidos lá.
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

    def addEdge(self, u: int, v: int, weight: float = 1.0) -> bool:
        """Adiciona uma aresta (u, v) com um peso."""
        self._validate_edge_vertices(u, v)
        
        if u == v:
            print(f"Aviso: Laço (aresta {u} -> {u}) ignorado. Grafos simples não permitem laços.")
            return False
        if weight <= 0:
            raise ValueError("O peso da aresta deve ser positivo.")
            
        if not self.hasEdge(u, v):
            self.adj_out[u][v] = weight
            self.adj_in[v][u] = weight
            self._edge_count += 1
            return True
        else:
            return False

    def removeEdge(self, u: int, v: int) -> None:
        """Remove a aresta (u, v)."""
        self._validate_edge_vertices(u, v)
        if self.hasEdge(u, v):
            weight_to_subtract = self.adj_out[u][v]
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
            raise LookupError(f"Aresta (u, v) não encontrada: ({u}, {v})")
        return self.adj_out[u][v]

    def isConnected(self) -> bool:
        """
        Verifica se o grafo é fracamente conexo (usando Busca em Largura/Profundidade). """
        if self._num_vertices == 0:
            return True
        visited = [False] * self._num_vertices
        queue = deque()
        queue.append(0)
        visited[0] = True
        nodes_visited_count = 0
        
        while queue:
            u = queue.popleft()
            nodes_visited_count += 1
            for v in self.adj_out[u]:
                if not visited[v]:
                    visited[v] = True
                    queue.append(v)
            for v in self.adj_in[u]:
                if not visited[v]:
                    visited[v] = True
                    queue.append(v)
        return nodes_visited_count == self._num_vertices

    def isCompleteGraph(self) -> bool:
        return self.getEdgeCount() == (self._num_vertices * (self._num_vertices - 1))

    def exportToGEPHI(self, path: str) -> None:
        try:
            with open(path, 'w', encoding='utf-8') as f:
                f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
                f.write('<gexf xmlns="http://www.gexf.net/1.2draft" version="1.2">\n')
                f.write('  <graph defaultedgetype="directed">\n')
                f.write('    <nodes>\n')
                for i in range(self._num_vertices):
                    f.write(f'      <node id="{i}" label="Vértice {i}" />\n')
                f.write('    </nodes>\n')
                f.write('    <edges>\n')
                edge_id = 0
                for u in range(self._num_vertices):
                    for v, weight in self.adj_out[u].items():
                        f.write(f'      <edge id="{edge_id}" source="{u}" target="{v}" weight="{weight}" />\n')
                        edge_id += 1
                f.write('    </edges>\n')
                f.write('  </graph>\n')
                f.write('</gexf>\n')
        except IOError as e:
            raise IOError(f"Erro ao exportar GEXF: {e}")

    # --- Métodos de Representação ---

    def getAsAdjacencyList(self) -> list[dict[int, float]]:
        """Retorna a estrutura interna de lista de adjacência."""
        return self.adj_out

    def getAsAdjacencyMatrix(self) -> list[list[float]]:
        """CONSTRÓI e retorna uma matriz de adjacência."""
        matrix = [[0.0] * self._num_vertices for _ in range(self._num_vertices)]
        for u in range(self._num_vertices):
            for v, weight in self.adj_out[u].items():
                matrix[u][v] = weight
        return matrix


    def _on_add_vertex(self, new_index: int) -> None:
        """Hook chamado por AbstractGraph.addVertex para expandir estruturas."""
        # Adiciona novas entradas vazias nas listas de adjacência
        self.adj_out.append({})
        self.adj_in.append({})