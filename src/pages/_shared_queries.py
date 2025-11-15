from collections import defaultdict
from typing import Dict, List, Tuple

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

WEIGHTS = {
    "COMMENT": 2,
    "ISSUE_COMMENTED": 3,
    "REVIEW": 4,
    "MERGE": 5,
}

AUTHORS_QUERY = f"""
MATCH (a:{LABEL_AUTHOR})
RETURN id(a) AS id, coalesce(a.login, toString(id(a))) AS name
ORDER BY name
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


def fetch_authors_and_edges(neo4j_service) -> tuple[dict[int, str], list[tuple[int, int, float]]]:
    # Backwards-compatible wrapper: usa as novas funções
    id_to_index, idx_to_name = fetch_authors(neo4j_service)
    if not id_to_index:
        return {}, []
    edges_by_relation = fetch_edges_by_relation(neo4j_service, id_to_index)
    edges = build_integrated_edges(edges_by_relation, WEIGHTS)
    return idx_to_name, edges


def fetch_authors(neo4j_service) -> Tuple[Dict[int, int], Dict[int, str]]:
    """Retorna (id_to_index, idx_to_name) a partir dos autores no Neo4j."""
    authors_rows = neo4j_service.query(AUTHORS_QUERY)
    if not authors_rows:
        return {}, {}
    id_to_index: Dict[int, int] = {}
    idx_to_name: Dict[int, str] = {}
    for idx, row in enumerate(authors_rows):
        neo4j_id = row["id"]
        name = row.get("name") or str(neo4j_id)
        id_to_index[neo4j_id] = idx
        idx_to_name[idx] = name
    return id_to_index, idx_to_name


def fetch_edges_by_relation(neo4j_service, id_to_index: Dict[int, int]) -> Dict[str, List[Tuple[int, int]]]:
    """Busca no Neo4j e retorna arestas separadas por tipo de relação.

    Chaves: 'COMMENT', 'ISSUE_COMMENTED', 'REVIEW', 'MERGE'.
    Valores: listas de pares (u_index, v_index).
    """
    edges: Dict[str, List[Tuple[int, int]]] = {
        "COMMENT": [],
        "ISSUE_COMMENTED": [],
        "REVIEW": [],
        "MERGE": [],
    }

    # Comentários em issues/PRs
    rows = neo4j_service.query(COMMENT_ON_ISSUE_PR_QUERY)
    for row in rows:
        src, dst = row["srcId"], row["dstId"]
        if src in id_to_index and dst in id_to_index:
            edges["COMMENT"].append((id_to_index[src], id_to_index[dst]))

    # Issues comentadas por outro usuário
    rows = neo4j_service.query(ISSUE_COMMENTED_BY_OTHER_QUERY)
    for row in rows:
        src, dst = row["srcId"], row["dstId"]
        if src in id_to_index and dst in id_to_index:
            edges["ISSUE_COMMENTED"].append((id_to_index[src], id_to_index[dst]))

    # Reviews / approvals
    rows = neo4j_service.query(PR_REVIEW_APPROVAL_QUERY)
    for row in rows:
        src, dst = row["srcId"], row["dstId"]
        if src in id_to_index and dst in id_to_index:
            edges["REVIEW"].append((id_to_index[src], id_to_index[dst]))

    # Merges
    rows = neo4j_service.query(PR_MERGE_QUERY)
    for row in rows:
        src, dst = row["srcId"], row["dstId"]
        if src in id_to_index and dst in id_to_index:
            edges["MERGE"].append((id_to_index[src], id_to_index[dst]))

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
