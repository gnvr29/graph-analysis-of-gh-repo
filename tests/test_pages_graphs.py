import importlib.util
import os
import sys

# helper to load module from path (pages have filenames starting with digits)

def load_module_from_path(path, module_name):
    spec = importlib.util.spec_from_file_location(module_name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeNeo4j:
    def __init__(self, authors_rows, other_rows):
        self._calls = 0
        self.authors_rows = authors_rows
        self.other_rows = other_rows

    def query(self, cypher):
        self._calls += 1
        if self._calls == 1:
            return self.authors_rows
        return self.other_rows


def test_page2_fetch_authors_and_edges(tmp_path):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    page2_path = os.path.join(repo_root, 'src', 'pages', '2_Grafo_Comentarios_PR_Issue.py')
    mod = load_module_from_path(page2_path, 'page2')

    # prepare fake rows: authors then comment interactions
    authors_rows = [
        {'id': 10, 'name': 'alice'},
        {'id': 20, 'name': 'bob'},
    ]
    comment_rows = [
        {'srcId': 10, 'dstId': 20},
    ]
    fake = FakeNeo4j(authors_rows, comment_rows)

    idx_to_name, edges = mod.fetch_authors_and_edges(fake)
    # idx_to_name should map 0->alice, 1->bob (order defined by enumerate of authors_rows)
    assert len(idx_to_name) == 2
    assert idx_to_name[0] == 'alice'
    assert idx_to_name[1] == 'bob'

    # edges should be in index space (u,v,weight)
    assert len(edges) == 1
    u, v, w = edges[0]
    assert (u, v) == (0, 1)
    assert w == mod.WEIGHTS['COMMENT']


def test_page3_fetch_review_edges(tmp_path):
    repo_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    page3_path = os.path.join(repo_root, 'src', 'pages', '3_Grafo_Reviews.py')
    mod = load_module_from_path(page3_path, 'page3')

    # create fake rows similar to the PR_REVIEW_APPROVAL_QUERY return
    rows = [
        {'srcId': 100, 'dstId': 200, 'srcName': 'carol', 'dstName': 'dave'},
        {'srcId': 100, 'dstId': 300, 'srcName': 'carol', 'dstName': 'eve'},
    ]

    class SimpleFake:
        def __init__(self, rows):
            self.rows = rows
        def query(self, cypher):
            return self.rows

    fake = SimpleFake(rows)
    idx_to_name, edges = mod.fetch_review_edges(fake)

    # idx_to_name should contain names for the involved neo4j ids
    assert 0 in idx_to_name and 1 in idx_to_name
    # edges should use internal indices assigned by the function and weights equal to WEIGHT_REVIEW
    assert all(w == mod.WEIGHT_REVIEW for (_, _, w) in edges)
    # there should be two edges produced
    assert len(edges) == 2
