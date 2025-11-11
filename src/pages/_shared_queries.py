from collections import defaultdict

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
    authors_rows = neo4j_service.query(AUTHORS_QUERY)
    if not authors_rows:
        return {}, []
    id_to_index: dict[int, int] = {}
    idx_to_name: dict[int, str] = {}
    for idx, row in enumerate(authors_rows):
        neo4j_id = row["id"]
        name = row.get("name") or str(neo4j_id)
        id_to_index[neo4j_id] = idx
        idx_to_name[idx] = name
    weighted_edges_map: defaultdict[tuple[int, int], float] = defaultdict(float)

    comment_on_issue_pr_rows = neo4j_service.query(COMMENT_ON_ISSUE_PR_QUERY)
    for row in comment_on_issue_pr_rows:
        if row["srcId"] in id_to_index and row["dstId"] in id_to_index:
            weighted_edges_map[(row["srcId"], row["dstId"])] += WEIGHTS["COMMENT"]

    issue_commented_rows = neo4j_service.query(ISSUE_COMMENTED_BY_OTHER_QUERY)
    for row in issue_commented_rows:
        if row["srcId"] in id_to_index and row["dstId"] in id_to_index:
            weighted_edges_map[(row["srcId"], row["dstId"])] += WEIGHTS["ISSUE_COMMENTED"]

    pr_review_approval_rows = neo4j_service.query(PR_REVIEW_APPROVAL_QUERY)
    for row in pr_review_approval_rows:
        if row["srcId"] in id_to_index and row["dstId"] in id_to_index:
            weighted_edges_map[(row["srcId"], row["dstId"])] += WEIGHTS["REVIEW"]

    pr_merge_rows = neo4j_service.query(PR_MERGE_QUERY)
    for row in pr_merge_rows:
        if row["srcId"] in id_to_index and row["dstId"] in id_to_index:
            weighted_edges_map[(row["srcId"], row["dstId"])] += WEIGHTS["MERGE"]

    edges: list[tuple[int, int, float]] = []
    for (src_neo4j_id, dst_neo4j_id), total_weight in weighted_edges_map.items():
        u = id_to_index[src_neo4j_id]
        v = id_to_index[dst_neo4j_id]
        if u != v:
            edges.append((u, v, total_weight))
    return idx_to_name, edges
