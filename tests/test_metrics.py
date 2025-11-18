import pytest
from src.analysis import metrics


def test_build_relation_edge_lists():
    edges_by_relation = {'COMMENT': [(0, 1), (1, 2)]}
    res = metrics.build_relation_edge_lists(edges_by_relation)
    assert 'COMMENT' in res
    assert res['COMMENT'] == [(0, 1, 1.0), (1, 2, 1.0)]


def test_build_integrated_edges_defaults():
    edges_by_relation = {
        'COMMENT': [(0, 1), (0, 1)],  # duplicated to test aggregation
        'REVIEW': [(1, 2)],
    }
    res = metrics.build_integrated_edges(edges_by_relation)
    # convert to dict for easy assertions
    d = {(u, v): w for u, v, w in res}
    assert d[(0, 1)] == pytest.approx(metrics.DEFAULT_RELATION_WEIGHTS['COMMENT'] * 2)
    assert d[(1, 2)] == pytest.approx(metrics.DEFAULT_RELATION_WEIGHTS['REVIEW'])


def test_build_relation_graphs_adjlists_and_integrated_adjlists():
    n = 4
    edges_by_relation = {
        'COMMENT': [(0, 1), (2, 3)],
        'REVIEW': [(1, 2)],
    }

    rel_graphs = metrics.build_relation_graphs_adjlists(n, edges_by_relation)
    assert 'COMMENT' in rel_graphs and 'REVIEW' in rel_graphs

    out_comment, in_comment = rel_graphs['COMMENT']
    # check sizes
    assert len(out_comment) == n
    assert len(in_comment) == n
    # check expected edges present with weight 1.0
    assert any(v == 1 and w == 1.0 for v, w in out_comment[0])
    assert any(v == 3 and w == 1.0 for v, w in out_comment[2])

    # integrated
    out_int, in_int = metrics.build_integrated_graph_adjlists(n, edges_by_relation)
    # (0,1) weight should be COMMENT weight (2), (1,2) weight REVIEW (4), (2,3) COMMENT (2)
    assert any(v == 1 and w == pytest.approx(metrics.DEFAULT_RELATION_WEIGHTS['COMMENT']) for v, w in out_int[0])
    assert any(v == 2 and w == pytest.approx(metrics.DEFAULT_RELATION_WEIGHTS['REVIEW']) for v, w in out_int[1])
    assert any(v == 3 and w == pytest.approx(metrics.DEFAULT_RELATION_WEIGHTS['COMMENT']) for v, w in out_int[2])
