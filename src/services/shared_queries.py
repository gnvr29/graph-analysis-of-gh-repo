from collections import defaultdict
from typing import Dict, List, Tuple, Set

LABEL_AUTHOR = "Author"
LABEL_ISSUE = "Issue"
LABEL_PR = "PullRequest"
LABEL_COMMENT = "Comment"
LABEL_REVIEW = "Review"
REL_AUTHORED_COMMENT = "AUTHORED"
REL_COMMENT_ON = "HAS_COMMENT"
REL_CREATED = "CREATED"
REL_PERFORMED_REVIEW = "PERFORMED_REVIEW"
REL_HAS_REVIEW = "HAS_REVIEW"
REL_CLOSED = "CLOSED"
REL_MERGED = "MERGED" 
REL_APPROVED = "APPROVED" 

WEIGHTS = {
    "COMMENT": 2,
    "ISSUE_COMMENTED": 3,
    "REVIEW": 4,
    "APPROVED": 4,
    "MERGE": 5,
    "ISSUE_CLOSED": 1,
}

AUTHORS_QUERY = f"""
MATCH (a:{LABEL_AUTHOR})
RETURN id(a) AS id, coalesce(a.login, toString(id(a))) AS name
"""

AUTHORS_WITH_ACTIVITY_QUERY = f"""
MATCH (a:{LABEL_AUTHOR})
WHERE (a)--()
RETURN id(a) AS id, coalesce(a.login, toString(id(a))) AS name
"""

COMMENT_ON_ISSUE_PR_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_AUTHORED_COMMENT}]->(comment:{LABEL_COMMENT})
MATCH (target: {LABEL_ISSUE}|{LABEL_PR})-[:{REL_COMMENT_ON}]->(comment)
MATCH (target)<-[:{REL_CREATED}]-(dst:{LABEL_AUTHOR})
WHERE src <> dst AND (target:{LABEL_ISSUE} OR target:{LABEL_PR})
RETURN id(src) AS srcId, id(dst) AS dstId
"""

ISSUE_COMMENTED_BY_OTHER_QUERY = f"""
MATCH (dst:{LABEL_AUTHOR})-[:{REL_CREATED}|OPENED]->(i:{LABEL_ISSUE})
MATCH (src:{LABEL_AUTHOR})-[:{REL_AUTHORED_COMMENT}|COMMENTED]->(c:{LABEL_COMMENT})
MATCH (i)-[:{REL_COMMENT_ON}|ON]->(c)
WHERE src <> dst
RETURN id(src) AS srcId, id(dst) AS dstId
"""

PR_REVIEW_APPROVAL_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_PERFORMED_REVIEW}|REVIEWED|APPROVED]->(r:{LABEL_REVIEW})
MATCH (pr:{LABEL_PR})-[:{REL_HAS_REVIEW}|REVIEWS|FOR]->(r)
MATCH (pr)<-[:{REL_CREATED}|OPENED]-(dst:{LABEL_AUTHOR})
WHERE src <> dst
RETURN id(src) AS srcId, id(dst) AS dstId
"""

PR_MERGE_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_PERFORMED_REVIEW}|REVIEWED|APPROVED]->(r:{LABEL_REVIEW})
MATCH (pr:{LABEL_PR})-[:{REL_HAS_REVIEW}|REVIEWS|FOR]->(r)
MATCH (pr)<-[:{REL_CREATED}|OPENED]-(dst:{LABEL_AUTHOR})
WHERE src <> dst AND pr.mergedAt IS NOT NULL
RETURN id(src) AS srcId, id(dst) AS dstId
"""

ISSUE_CLOSED_BY_OTHER_QUERY = f"""
MATCH (src:{LABEL_AUTHOR})-[:{REL_CLOSED}]->(i:{LABEL_ISSUE})
MATCH (i)<-[:{REL_CREATED}]-(dst:{LABEL_AUTHOR})
WHERE src <> dst
RETURN id(src) AS srcId, id(dst) AS dstId
"""


def fetch_authors_and_edges(neo4j_service, enabled_interaction_types: Set[str], limit: int = 0, only_active_authors: bool = False) -> tuple[dict[int, str], list[tuple[int, int, float]]]:
    """
    Função principal para buscar autores e arestas, aplicando a filtragem e o limite
    somente aos autores que participaram dos tipos de interação habilitados.
    """
    print("Buscando todos os autores...")
    # 1. Busca todos os autores (ativos ou não, sem limite no Cypher)
    id_to_index_full, idx_to_name_full = fetch_authors(neo4j_service, limit, only_active_authors=only_active_authors)
    
    if not id_to_index_full:
        print("Nenhum autor encontrado no Neo4j.")
        return {}, []
    
    print(f"Encontrados {len(idx_to_name_full)} autores no total.") 

    # 2. Busca as arestas, considerando APENAS os tipos de interação habilitados
    # Usamos o id_to_index_full para mapear os IDs Neo4j para os índices temporários
    edges_by_relation = fetch_edges_by_relation(neo4j_service, id_to_index_full, enabled_interaction_types)

    filtered_weights = {k: v for k, v in WEIGHTS.items() if k in enabled_interaction_types}

    # 3. Constrói as arestas integradas com os pesos filtrados
    edges = build_integrated_edges(edges_by_relation, filtered_weights)

    if not edges:
        print(f"Nenhuma aresta formada com os tipos de interação habilitados: {', '.join(enabled_interaction_types)}")
        return {}, []
    
    # -----------------------------------------------------------
    # 4. PASSO FINAL: FILTRAGEM E APLICAÇÃO DO LIMIT NO PYTHON
    # -----------------------------------------------------------
    
    if only_active_authors or limit > 0:
        
        # Encontra todos os índices (u ou v) que aparecem nas arestas habilitadas
        active_indices = set()
        for u, v, _ in edges:
            active_indices.add(u)
            active_indices.add(v)

        idx_to_name_filtered = {}
        old_to_new_index = {}
        new_index = 0
        
        # Cria a lista final de autores, aplicando o LIMIT e o filtro de atividade
        for old_index, name in idx_to_name_full.items():
            if old_index in active_indices:
                
                # Aplica o LIMIT aqui: se o novo índice já atingiu o limite, para.
                if limit > 0 and new_index >= limit:
                    break
                
                idx_to_name_filtered[new_index] = name
                old_to_new_index[old_index] = new_index
                new_index += 1

        # Atualiza as arestas para usar os novos índices (re-indexação)
        edges_final = []
        for u_old, v_old, weight in edges:
            # Só inclui a aresta se ambos os nós foram mantidos na lista filtrada (após filtro e limite)
            if u_old in old_to_new_index and v_old in old_to_new_index:
                u_new = old_to_new_index[u_old]
                v_new = old_to_new_index[v_old]
                edges_final.append((u_new, v_new, weight))
            
        idx_to_name = idx_to_name_filtered
        edges = edges_final
        
        print(f"Total de {len(idx_to_name)} autores filtrados (após filtro de interações e limite).")
    
    else:
        # Se não há filtro de ativos nem limite, usa os dados completos
        idx_to_name = idx_to_name_full
        
    # -----------------------------------------------------------
    
    if enabled_interaction_types:
        print(f"Tipos de interações incluídos: {', '.join(enabled_interaction_types)}")
    
    print(f"Total de {len(edges)} arestas ponderadas únicas formadas após agregação.")
    
    return idx_to_name, edges


def fetch_authors(neo4j_service, limit, only_active_authors: bool = False) -> Tuple[Dict[int, int], Dict[int, str]]:
    """Retorna (id_to_index, idx_to_name) a partir dos autores no Neo4j, buscando todos primeiro."""

    if only_active_authors:
        cypher_query = AUTHORS_WITH_ACTIVITY_QUERY
        print("Filtrando para buscar APENAS autores ATIVOS.")
    else:
        cypher_query = AUTHORS_QUERY
        print("Buscando todos os autores (ativos e inativos).")

    # A ordenação é mantida para garantir consistência, mas o LIMIT é aplicado depois no Python.
    cypher_query += " ORDER BY name"
    print("Buscando todos os autores do Neo4j (sem limite inicial)...")

    authors_rows = neo4j_service.query(cypher_query)
    if not authors_rows:
        return {}, {}
    
    id_to_index: Dict[int, int] = {}
    idx_to_name: Dict[int, str] = {}
    
    for idx, row in enumerate(authors_rows):
        neo4j_id = row["id"]
        name = row.get("name") or str(neo4j_id)
        
        # Mapeamento do Neo4j ID para o índice sequencial
        id_to_index[neo4j_id] = idx
        idx_to_name[idx] = name
        
    return id_to_index, idx_to_name


def fetch_edges_by_relation(neo4j_service, id_to_index: Dict[int, int],  enabled_interaction_types: Set[str]) -> Dict[str, List[Tuple[int, int]]]:
    """
    Busca no Neo4j e retorna arestas separadas por tipo de relação,
    incluindo apenas os tipos especificados.

    Chaves: 'COMMENT', 'ISSUE_COMMENTED', 'REVIEW', 'MERGE'.

    Valores: listas de pares (u_index, v_index).
    """
    edges: Dict[str, List[Tuple[int, int]]] = defaultdict(list)

    if "COMMENT" in enabled_interaction_types:
        # Comentários em issues/PRs
        rows = neo4j_service.query(COMMENT_ON_ISSUE_PR_QUERY)
        for row in rows:
            src, dst = row["srcId"], row["dstId"]
            if src in id_to_index and dst in id_to_index:
                edges["COMMENT"].append((id_to_index[src], id_to_index[dst]))

    if "ISSUE_COMMENTED" in enabled_interaction_types:
        # Issues comentadas por outro usuário
        rows = neo4j_service.query(ISSUE_COMMENTED_BY_OTHER_QUERY)
        for row in rows:
            src, dst = row["srcId"], row["dstId"]
            if src in id_to_index and dst in id_to_index:
                edges["ISSUE_COMMENTED"].append((id_to_index[src], id_to_index[dst]))

    if "REVIEW" in enabled_interaction_types:
        # Reviews / approvals
        rows = neo4j_service.query(PR_REVIEW_APPROVAL_QUERY)
        for row in rows:
            src, dst = row["srcId"], row["dstId"]
            if src in id_to_index and dst in id_to_index:
                edges["REVIEW"].append((id_to_index[src], id_to_index[dst]))

    if "MERGE" in enabled_interaction_types:
        # Merges
        rows = neo4j_service.query(PR_MERGE_QUERY)
        for row in rows:
            src, dst = row["srcId"], row["dstId"]
            if src in id_to_index and dst in id_to_index:
                edges["MERGE"].append((id_to_index[src], id_to_index[dst]))
    
    if "ISSUE_CLOSED" in enabled_interaction_types:
        # Fechamento de issues por terceiros
        rows = neo4j_service.query(ISSUE_CLOSED_BY_OTHER_QUERY)
        for row in rows:
            src, dst = row["srcId"], row["dstId"]
            if src in id_to_index and dst in id_to_index:
                edges["ISSUE_CLOSED"].append((id_to_index[src], id_to_index[dst]))

    return edges


def build_integrated_edges(edges_by_relation: Dict[str, List[Tuple[int, int]]],
                           weights: Dict[str, float]) -> List[Tuple[int, int, float]]:
    """Agrega arestas por par (u,v) somando pesos conforme o mapeamento weights.

    Retorna lista de (u_index, v_index, total_weight).
    """
    agg = defaultdict(float)
    for rel, pairs in edges_by_relation.items():
        w = float(weights.get(rel, 1))
        for u, v in pairs:
            if u == v:
                continue
            agg[(u, v)] += w
    return [(u, v, total) for (u, v), total in agg.items()]
