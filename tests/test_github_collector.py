# tests/test_github_collector.py
import pytest
from src.collectors.github_collector import GithubCollector # Importa apenas para type hinting e clareza

# O fixture github_collector será automaticamente injetado pelo pytest
# (definido em conftest.py)

def test_collect_issues_returns_data(github_collector: GithubCollector):
    """
    Verifica se o coletor de issues retorna uma lista não vazia de issues.
    Este é um teste de integração que faz requisições reais ao GitHub.
    """
    print("\nIniciando test_collect_issues_returns_data...")
    issues = github_collector.collect_issues()
    assert isinstance(issues, list)
    assert len(issues) > 0, "Deveria ter coletado algumas issues."
    
    # Verifica a estrutura básica de uma issue
    first_issue = issues[0]
    assert "number" in first_issue
    assert "title" in first_issue
    assert "body" in first_issue # Deve ter sido preenchido
    assert "comments" in first_issue # Deve ter sido preenchido
    assert isinstance(first_issue["comments"], list)
    print(f"Coletadas {len(issues)} issues. Primeira issue: #{first_issue['number']} - {first_issue['title']}")

def test_collect_pull_requests_returns_data(github_collector: GithubCollector):
    """
    Verifica se o coletor de pull requests retorna uma lista não vazia de PRs.
    Este é um teste de integração que faz requisições reais ao GitHub.
    """
    print("\nIniciando test_collect_pull_requests_returns_data...")
    pull_requests = github_collector.collect_pull_requests()
    assert isinstance(pull_requests, list)
    assert len(pull_requests) > 0, "Deveria ter coletado algumas pull requests."

    # Verifica a estrutura básica de uma pull request
    first_pr = pull_requests[0]
    assert "number" in first_pr
    assert "title" in first_pr
    assert "author" in first_pr
    print(f"Coletadas {len(pull_requests)} pull requests. Primeira PR: #{first_pr['number']} - {first_pr['title']}")
