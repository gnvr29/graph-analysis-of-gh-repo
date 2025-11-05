class Graph:

    def getVertexCount(self):
        pass

    def getEdgeCount(self):
        pass

    def hasEdge(self, v: int, w: int) -> bool:
        pass

    def addEdge(self, v: int, w: int) -> None:
        pass

    def removeEdge(self, v: int, w: int) -> None:
        pass

    def isSucessor(self, v: int, w: int) -> bool:
        pass
    
    def isPredecessor(self, v: int, w: int) -> bool:
        pass

    def isDivergent(self, u1: int, v1: int, u2: int, v2: int) -> bool:
        pass

    def isConvergent(self, u1: int, v1: int, u2: int, v2: int) -> bool:
        pass

    def isIncident(self, u: int, v: int, x: int) -> bool:
        pass

    def getVertexInDegree(self, v: int) -> int:
        pass

    def getVertexOutDegree(self, v: int) -> int:
        pass

    def setVertexWeight(self, v: int, weight: float) -> None:
        pass

    def getVertexWeight(self, v: int) -> float:
        pass

    def setEdgeWeight(self, v: int, w: int, weight: float) -> None:
        pass

    def getEdgeWeight(self, v: int, w: int) -> float:
        pass

    def isConnected(self) -> bool:
        pass

    def isEmpty(self) -> bool:
        pass

    def isCompleteGraph(self) -> bool:
        pass



class AdjacencyMatrixGraph(Graph):
    
    def __init__(self, num_vertices: int):
        super().__init__()

class AdjacencyListGraph(Graph):
   
    def __init__(self, num_vertices: int):
        super().__init__()


class Node:
    
    def __init__(self, id: int):
        self.id = id
        self.adjacents = []
        self.weight = 0.0
        self.in_degree = 0 
        self.out_degree = 0

    def add_adjacent(self, node: 'Node') -> None:
        if node not in self.adjacents:
            self.adjacents.append(node)
            self.out_degree += 1
            node.in_degree += 1

    def remove_adjacent(self, node: 'Node') -> None:
        if node in self.adjacents:
            self.adjacents.remove(node)
            self.out_degree -= 1
            node.in_degree -= 1

    def set_weight(self, weight: float) -> None:
        self.weight = weight

    def get_weight(self) -> float:
        return self.weight

    def get_in_degree(self) -> int:
        return self.in_degree

    def get_out_degree(self) -> int:
        return self.out_degree


class Edge:    
    def __init__(self, v1: Node, v2: Node):
        self.v1 = v1
        self.v2 = v2
        self.weight = 0.0

    def set_weight(self, weight: float) -> None:
        self.weight = weight

    def get_weight(self) -> float:
        return self.weight