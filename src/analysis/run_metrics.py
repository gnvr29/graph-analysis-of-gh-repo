"""Terminal runner to compute and print graph metrics using the DB as source.

Usage:
    python src/analysis/run_metrics.py

This script connects to Neo4j using the project's `get_neo4j_service` and the
shared `fetch_authors_and_edges` function. It builds adjacency lists and
computes the available metrics, printing the top contributors for each.
"""
import sys
from pathlib import Path
from pprint import pprint

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.utils.neo4j_connector import get_neo4j_service
from src.services.shared_queries import fetch_authors_and_edges
from src.analysis.centrality_metrics import (
    build_adjlists,
    degree_centrality,
    betweenness_centrality,
    closeness_centrality,
    pagerank,
    eigenvector_centrality,
)


def top_n(mapping, names, n=10, reverse=True):
    items = sorted(mapping.items(), key=lambda kv: kv[1], reverse=reverse)
    out = []
    for idx, score in items[:n]:
        out.append((names[idx], score))
    return out


def main():
    try:
        neo4j = get_neo4j_service()
    except Exception as e:
        print("Erro conectando ao Neo4j:", e, file=sys.stderr)
        sys.exit(1)

    idx_to_name, edges = fetch_authors_and_edges(neo4j)
    if not idx_to_name:
        print("Nenhum autor retornado pelo banco.")
        return

    n = len(idx_to_name)
    print(f"Autores: {n}, Arestas: {len(edges)}")

    out_adj, in_adj = build_adjlists(n, edges)

    print('\nDegree centrality (weighted, total) - top 10:')
    deg = degree_centrality(out_adj, in_adj, weighted=True, mode='total')
    pprint(top_n(deg, idx_to_name, n=10))

    print('\nDegree centrality (unweighted, out-degree) - top 10:')
    deg_un = degree_centrality(out_adj, in_adj, weighted=False, mode='out')
    pprint(top_n(deg_un, idx_to_name, n=10))

    print('\nBetweenness centrality (unweighted Brandes) - top 10:')
    bc = betweenness_centrality(out_adj)
    pprint(top_n(bc, idx_to_name, n=10))

    print('\nCloseness centrality (unweighted) - top 10:')
    cc = closeness_centrality(out_adj)
    pprint(top_n(cc, idx_to_name, n=10))

    print('\nPageRank (weighted) - top 10:')
    pr = pagerank(out_adj)
    pprint(top_n(pr, idx_to_name, n=10))

    print('\nEigenvector centrality (power iteration) - top 10:')
    ev = eigenvector_centrality(out_adj, in_adj)
    pprint(top_n(ev, idx_to_name, n=10))


if __name__ == '__main__':
    main()
