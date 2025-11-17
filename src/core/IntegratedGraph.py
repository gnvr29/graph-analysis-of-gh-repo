from src.core import AdjacencyMatrixGraph
from src.core.AbstractGraph import AbstractGraph
from src.core.AdjacencyListGraph import AdjacencyListGraph

class IntegratedGraph(AbstractGraph):
    """
    Grafo Integrado que pondera arestas baseado em:

    - Comentários em issue/PR: peso 2
    - Abertura de issue comentada por outro usuário: peso 3
    - Revisão/aprovação de PR: peso 4
    - Merge de PR: peso 5
    
    O grafo integrado agrega todas as interações ponderando-as apropriadamente.
    """

    def __init__(self, 
                 num_vertices: int,
                 graph_comments: AbstractGraph = None,
                 graph_issue_closures: AbstractGraph = None,
                 graph_pr_reviews: AbstractGraph = None
                 ):
        """
        Construtor do grafo integrado.
        
        Args:
            num_vertices: Número de vértices (usuários)
            graph_comments: Grafo de comentários (peso 2)
            graph_issue_closures: Grafo de fechamento de issues (peso 3)
            graph_pr_reviews: Grafo de reviews/merges de PRs (pesos 4 e 5)
        """
        super().__init__(num_vertices)
        
        self.graph_comments = graph_comments
        self.graph_issue_closures = graph_issue_closures
        self.graph_pr_reviews = graph_pr_reviews
        
        self._integrated_graph = AdjacencyListGraph(num_vertices)
        
        # Checa se os grafos foram fornecidos e chama a função de integração caso sim
        if all([graph_comments, graph_issue_closures, graph_pr_reviews]):
            self._integrate_graphs()

    def _integrate_graphs(self) -> None:
        """Integra os três grafos separados em um grafo único ponderado."""
        self._integrated_graph = AdjacencyListGraph(self._num_vertices)
        
        # Peso 2: Comentários em issue/PR
        if self.graph_comments:
            self._add_weighted_edges(self.graph_comments, weight_multiplier=2.0)
        
        # Peso 3: Abertura de issue comentada
        if self.graph_issue_closures:
            self._add_weighted_edges(self.graph_issue_closures, weight_multiplier=3.0)
        
        # Peso 4 e 5: Reviews/Merges de PRs
        if self.graph_pr_reviews:
            self._add_weighted_edges(self.graph_pr_reviews, weight_multiplier=4.0)

    def _add_weighted_edges(self, source_graph: AbstractGraph, weight_multiplier: float) -> None:
        """
        Adiciona as arestas de um grafo fonte ao grafo integrado,
        multiplicando seus pesos pelo multiplicador fornecido.
        
        Args:
            source_graph: Grafo fonte
            weight_multiplier: Multiplicador de peso (2, 3, 4 ou 5)
        """
        adj_list = source_graph.getAsAdjacencyList()
        
        for u in range(source_graph.getVertexCount()):
            for v, edge_weight in adj_list[u].items():
                new_weight = edge_weight * weight_multiplier
                
                if self._integrated_graph.hasEdge(u, v):
                    # Se a aresta já existe, adicionar o peso
                    current_weight = self._integrated_graph.getEdgeWeight(u, v)
                    self._integrated_graph.setEdgeWeight(u, v, current_weight + new_weight)
                else:
                    # Criar nova aresta com o peso ponderado
                    self._integrated_graph.addEdge(u, v, new_weight)

    def hasEdge(self, u: int, v: int) -> bool:
        """Verifica se existe uma aresta (u, v)."""
        return self._integrated_graph.hasEdge(u, v)

    def addEdge(self, u: int, v: int, weight: float = 1.0) -> bool:
        """Adiciona uma aresta (u, v) com um peso."""
        result = self._integrated_graph.addEdge(u, v, weight)
        if result:
            self._edge_count = self._integrated_graph.getEdgeCount()
        return result

    def removeEdge(self, u: int, v: int) -> None:
        """Remove a aresta (u, v)."""
        self._integrated_graph.removeEdge(u, v)
        self._edge_count = self._integrated_graph.getEdgeCount()

    def getVertexInDegree(self, v: int) -> int:
        """Retorna o grau de entrada do vértice v."""
        return self._integrated_graph.getVertexInDegree(v)

    def getVertexOutDegree(self, v: int) -> int:
        """Retorna o grau de saída do vértice v."""
        return self._integrated_graph.getVertexOutDegree(v)

    def setEdgeWeight(self, u: int, v: int, weight: float) -> None:
        """Define o peso da aresta (u, v)."""
        self._integrated_graph.setEdgeWeight(u, v, weight)

    def getEdgeWeight(self, u: int, v: int) -> float:
        """Retorna o peso da aresta (u, v)."""
        return self._integrated_graph.getEdgeWeight(u, v)

    def isConnected(self) -> bool:
        """Verifica se o grafo é conexo."""
        return self._integrated_graph.isConnected()

    def isCompleteGraph(self) -> bool:
        """Verifica se o grafo é completo."""
        return self._integrated_graph.isCompleteGraph()

    def exportToGEPHI(self, path: str) -> None:
        """Exporta o grafo integrado para um arquivo GEPHI."""
        self._integrated_graph.exportToGEPHI(path)

    def getAsAdjacencyList(self) -> list[dict[int, float]]:
        """Retorna a representação como lista de adjacência."""
        return self._integrated_graph.getAsAdjacencyList()

    def getAsAdjacencyMatrix(self) -> list[list[float]]:
        """Retorna a representação como matriz de adjacência."""
        return self._integrated_graph.getAsAdjacencyMatrix()

    def get_edge_count(self) -> int:
        """Retorna o número de arestas no grafo integrado."""
        return self._integrated_graph.getEdgeCount()

    def update_integrated_graph(self,
                                graph_comments: AbstractGraph = None,
                                graph_issue_closures: AbstractGraph = None,
                                graph_pr_reviews: AbstractGraph = None) -> None:
        """
        Atualiza o grafo integrado com novos grafos componentes.
        
        Args:
            graph_comments: Novo grafo de comentários
            graph_issue_closures: Novo grafo de fechamento de issues
            graph_pr_reviews: Novo grafo de reviews/merges
        """
        if graph_comments:
            self.graph_comments = graph_comments
        if graph_issue_closures:
            self.graph_issue_closures = graph_issue_closures
        if graph_pr_reviews:
            self.graph_pr_reviews = graph_pr_reviews
        
        # Re-integrar os grafos
        if all([self.graph_comments, self.graph_issue_closures, self.graph_pr_reviews]):
            self._integrate_graphs()