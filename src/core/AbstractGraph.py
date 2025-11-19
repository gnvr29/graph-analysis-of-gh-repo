from abc import ABC, abstractmethod

class AbstractGraph(ABC):
    """
    Classe base ABSTRATA para implementações de grafos.
    Define o "contrato" (API) que todas as implementações concretas
    (como AdjacencyListGraph e AdjacencyMatrixGraph) devem seguir,
    conforme especificado no trabalho prático.
    
    Os métodos estão na ordem exata da "API obrigatória" do PDF.
    """

    def __init__(self, num_vertices: int):
        if num_vertices < 0:
            raise ValueError("O número de vértices não pode ser negativo.")
        self._num_vertices = num_vertices
        self._edge_count = 0
        self._vertex_weights = [1.0] * num_vertices

    def _validate_vertex(self, v: int):
        """Helper para lançar exceção de índice inválido."""
        if not (0 <= v < self._num_vertices):
            raise IndexError(f"Índice de vértice inválido: {v}. Deve estar entre 0 e {self._num_vertices - 1}.")
            
    def _validate_edge_vertices(self, u: int, v: int):
        """Valida ambos os vértices de uma aresta."""
        self._validate_vertex(u)
        self._validate_vertex(v)

    def getVertexCount(self) -> int:
        """Retorna o número de vértices no grafo."""
        return self._num_vertices

    def getEdgeCount(self) -> int:
        """Retorna o número de arestas no grafo."""
        return self._edge_count

    @abstractmethod
    def hasEdge(self, u: int, v: int) -> bool:
        """Verifica se existe uma aresta (u, v)."""
        pass

    @abstractmethod
    def addEdge(self, u: int, v: int, weight: float = 1.0) -> bool:
        """Adiciona uma aresta (u, v) com um peso."""
        pass

    @abstractmethod
    def removeEdge(self, u: int, v: int) -> None:
        """Remove a aresta (u, v)."""
        pass

    def isSucessor(self, u: int, v: int) -> bool:
        """Verifica se v é sucessor de u (existe aresta u -> v)."""
        self._validate_edge_vertices(u, v)
        return self.hasEdge(u, v) 

    def isPredecessor(self, u: int, v: int) -> bool:
        """Verifica se v é predecessor de u (existe aresta v -> u)."""
        self._validate_edge_vertices(u, v)
        return self.hasEdge(v, u) 

    def isDivergent(self, u1: int, v1: int, u2: int, v2: int) -> bool:
        """Verifica se as arestas (u1, v1) e (u2, v2) são divergentes."""
        self._validate_edge_vertices(u1, v1)
        self._validate_edge_vertices(u2, v2)
        return (u1 == u2) and (v1 != v2) and self.hasEdge(u1, v1) and self.hasEdge(u2, v2)

    def isConvergent(self, u1: int, v1: int, u2: int, v2: int) -> bool:
        """Verifica se as arestas (u1, v1) e (u2, v2) são convergentes."""
        self._validate_edge_vertices(u1, v1)
        self._validate_edge_vertices(u2, v2)
        return (v1 == v2) and (u1 != u2) and self.hasEdge(u1, v1) and self.hasEdge(u2, v2)

    def isIncident(self, u: int, v: int, x: int) -> bool:
        """Verifica se o vértice x é incidente à aresta (u, v)."""
        self._validate_edge_vertices(u, v)
        self._validate_vertex(x)
        return x == u or x == v

    @abstractmethod
    def getVertexInDegree(self, v: int) -> int:
        """Retorna o grau de entrada do vértice v."""
        pass

    @abstractmethod
    def getVertexOutDegree(self, v: int) -> int:
        """Retorna o grau de saída do vértice v."""
        pass

    def setVertexWeight(self, v: int, w: float) -> None:
        """Define o peso do vértice v."""
        self._validate_vertex(v)
        self._vertex_weights[v] = w

    def getVertexWeight(self, v: int) -> float:
        """Retorna o peso do vértice v."""
        self._validate_vertex(v)
        return self._vertex_weights[v]

    @abstractmethod
    def setEdgeWeight(self, u: int, v: int, weight: float) -> None:
        """Define o peso da aresta (u, v)."""
        pass

    @abstractmethod
    def getEdgeWeight(self, u: int, v: int) -> float:
        """Retorna o peso da aresta (u, v)."""
        pass

    @abstractmethod
    def isConnected(self) -> bool:
        """Verifica se o grafo é conexo."""
        pass

    def isEmptyGraph(self) -> bool:
        """Verifica se o grafo está vazio (não tem arestas)."""
        return self.getEdgeCount() == 0

    @abstractmethod
    def isCompleteGraph(self) -> bool:
        """Verifica se o grafo é completo."""
        pass

    @abstractmethod
    def exportToGEPHI(self, path: str) -> None:
        """Exporta o grafo para um arquivo no formato GEPHI."""
        pass

    @abstractmethod
    def getAsAdjacencyList(self) -> list[dict[int, float]]:
        """
        Retorna a representação do grafo como uma lista de adjacência.
        """
        pass

    @abstractmethod
    def getAsAdjacencyMatrix(self) -> list[list[float]]:
        """
        Retorna a representação do grafo como uma matriz de adjacência.
        """
        pass
        
    def addVertex(self) -> int:
        """Adiciona um novo vértice ao grafo e retorna o índice criado.

        Implementação padrão: atualiza contadores e pesos de vértice,
        e delega a expansão das estruturas internas para o hook
        abstrato `_on_add_vertex(new_index)` que cada implementação
        concreta deve fornecer.
        """
        new_index = self._num_vertices
        # provisiona peso do novo vértice e incrementa contagem
        self._vertex_weights.append(0.0)
        self._num_vertices += 1

        try:
            # delega a responsabilidade de expandir estruturas (listas, matriz, etc.)
            self._on_add_vertex(new_index)
        except Exception as e:
            # rollback em caso de falha na expansão da subclasse
            self._num_vertices -= 1
            self._vertex_weights.pop()
            raise

        return new_index

    @abstractmethod
    def _on_add_vertex(self, new_index: int) -> None:
        """Hook abstrato chamado por `addVertex` para que a subclasse
        expanda suas estruturas internas (ex.: adicionar nova linha/coluna
        na matriz ou novos dicionários na lista de adjacência).

        `new_index` é o índice atribuído ao novo vértice.
        """
        pass
