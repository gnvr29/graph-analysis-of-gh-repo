# Documentação (src)

Este README dentro de `src/` explica, em detalhe, como o projeto monta a matriz de adjacência, quais métricas de redes foram implementadas do zero e como rodar as ferramentas.

Sumário rápido
- Fonte de dados: Neo4j (queries centralizadas em `src/pages/_shared_queries.py`).
- Matriz de adjacência: construída a partir de arestas agregadas por tipo de interação.
- Exportação: página Streamlit (`src/pages/2_Matriz_Adjacencia.py`) que exibe DataFrame e permite exportar SVG.
- Métricas: implementadas em `src/analysis/metrics.py` sem bibliotecas externas; runner em `src/analysis/run_metrics.py`.

1) Fluxo geral e responsabilidades dos módulos

- `src/services/neo4j_service.py`: fornece cliente Neo4j. Tem tentativa de conexão com `neo4j+s://...` e, em caso de erro de verificação TLS em ambiente de desenvolvimento, tenta `neo4j+ssc://...` (relaxa verificação). Use as mesmas variáveis `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` no `.env`.
- `src/pages/_shared_queries.py`: concentra as consultas Cypher e a lógica de agregação de arestas. Retorna um par `(idx_to_name, edges)`:
  - `idx_to_name`: lista/array onde o índice corresponde ao id interno usado na matriz e o valor é o login/nome do autor.
  - `edges`: lista de tuplas `(src_idx, dst_idx, weight)` já agregadas (uma aresta por par com peso total).
- `src/core/AdjacencyMatrixGraph.py`: classe simples para representar a matriz NxN e operar sobre ela (adicionar arestas, consultar, etc.). A página Streamlit usa essa classe para construir a matriz antes de montar o `pandas.DataFrame`.
- `src/pages/2_Matriz_Adjacencia.py`: página Streamlit que
  1. conecta ao Neo4j via `get_neo4j_service()`;
  2. chama `fetch_authors_and_edges` para obter `idx_to_name` e `edges`;
  3. aplica filtros (limite top-N, threshold por peso, mostrar apenas autores com saída);
  4. constrói o DataFrame e o exibe;
  5. gera um SVG (função `df_to_svg`) e fornece um botão para download do arquivo `matriz_adjacencia.svg`.

- `src/analysis/metrics.py`: implementações das métricas (descritas abaixo). Tudo foi implementado sem `networkx` ou similares — apenas listas e estruturas nativas.
- `src/analysis/run_metrics.py`: runner para terminal. Faz `fetch_authors_and_edges`, constrói listas de adjacência (out/in) e imprime os top-N de cada métrica. Útil para demonstração via terminal.

2) Construção da Matriz de Adjacência (detalhes para apresentar)

Dados de entrada: resultados das queries Cypher que retornam pares de autores envolvidos em interações (origem, destino).

Passos:
1. As queries em `_shared_queries.py` extraem relações relevantes (comentários, reviews, merges, etc.) e convertem autor->autor em pares (src, dst).
2. Cada tipo de interação recebe um peso fixo (decisão do projeto):
   - COMMENT = 2
   - ISSUE_COMMENTED = 3
   - REVIEW = 4
   - MERGE = 5
3. Ao agregar, somamos os pesos para cada par (src, dst). Resultado: lista `edges` com uma entrada por par (src, dst, peso_total).
4. Criamos uma matriz NxN onde N = número de autores (len(`idx_to_name`)). A célula M[i][j] armazena a soma dos pesos das interações de i para j.

Pontos a explicar em apresentação:
- Por que agregamos pesos? (reduz ruído e dá importância relativa a interações mais relevantes).
- Direcionalidade: a matriz é direcionada (i -> j diferente de j -> i).
- Como lidar com autores que não possuem interação (linhas/colunas zeradas) — mantemos a dimensão NxN para índices estáveis.

3) Mapeamento dos pesos e motivação

- COMMENT (2): comentário simples tem peso baixo.
- ISSUE_COMMENTED (3): comentar issue/PR é uma interação mais relevante que apenas um comentário isolado.
- REVIEW (4): revisão/aprovação é atividade com impacto no fluxo, recebe peso maior.
- MERGE (5): merge é ação crítica, recebe mais peso.

Explique que esses valores são escolhas de projeto e podem ser alterados. Em avaliação, destaque por que estes pesos refletem níveis diferentes de atuação.

4) Métricas implementadas — explicação técnica e como apresentar

Formato de entrada para as métricas: listas de adjacência `out_adj` e `in_adj` construídas a partir de `edges`:
- `out_adj[i]` = lista de pares `(j, w)` indicando arestas i->j com peso w.
- `in_adj[j]` = lista de pares `(i, w)` indicando arestas i->j com peso w.

- Degree Centrality (`degree_centrality`)
  - O que mede: soma (ou contagem) das conexões diretas de cada nó.
  - Parâmetros: `weighted=True|False`, `mode='in'|'out'|'total'`.
  - Saída: dicionário `{node: score}`.
  - Complexidade: O(n + m) para percorrer adjacências.

- Betweenness Centrality (`betweenness_centrality`) — algoritmo de Brandes (não-ponderado)
  - O que mede: quantas vezes um nó aparece em caminhos mais curtos entre outros nós (indica nós-ponte).
  - Implementação: Brandes puro usando BFS para grafos não-ponderados.
  - Observação: é não-ponderado; para considerar pesos seria necessário adaptar para Dijkstra (mais custoso).
  - Complexidade: O(n*m) em grafos não-ponderados.

- Closeness Centrality (`closeness_centrality`)
  - O que mede: quão “próximo” um nó está de todos os outros em termos de caminhos mínimos.
  - Implementação: BFS a partir de cada nó (não-ponderado). Retornamos `reachable_count / sum(distances)` para evitar divisão por (n-1) em grafos desconexos.
  - Atenção: nós isolados -> 0.

- PageRank (`pagerank`)
  - O que mede: influência considerando que ligações de nós influentes valem mais.
  - Implementação: power iteration com damping (0.85 por padrão). Pesos de arestas são usados para distribuir o PageRank proporcionalmente (out-strength).
  - Dangling nodes: distribuídos uniformemente.
  - Complexidade: O(k*(n+m)) onde k é número de iterações até convergência.

- Eigenvector Centrality (`eigenvector_centrality`)
  - O que mede: influência do nó considerando a importância dos vizinhos (autovetor principal de A).
  - Implementação: iteração de potência sobre A^T (usamos `in_adj` para eficiência). Normalizamos a cada iteração.
  - Observações: depende de convergência; para grafos grandes e esparsos é aceitável, mas exige atenção à normalização.

  6) Como as funções novas trabalham (resumo prático)

  - `DEFAULT_RELATION_WEIGHTS`:
    - Dicionário com os pesos padrão usados para agregar relações: `{'COMMENT':2, 'ISSUE_COMMENTED':3, 'REVIEW':4, 'MERGE':5}`.

  - `build_relation_edge_lists(edges_by_relation, *, default_weight=1.0)`:
    - Entrada: `edges_by_relation` é um dict onde cada chave é uma relação (ex: `'COMMENT'`) e o valor é uma lista de pares `(u, v)` com índices inteiros de nós.
    - Saída: dict relação -> lista de arestas `(u, v, w)` onde `w` é `default_weight` (útil para construir grafos separados por relação).

  - `build_integrated_edges(edges_by_relation, weights=None)`:
    - Agrega todas as listas de arestas em um grafo integrado ponderado.
    - Para cada par `(u, v)` soma os pesos associados a cada relação conforme o dicionário `weights` (se `None`, usa `DEFAULT_RELATION_WEIGHTS`).
    - Saída: lista de tuplas `(u, v, total_weight)` — uma entrada por par único com peso total.

  - `build_relation_graphs_adjlists(n, edges_by_relation)`:
    - Conveniência que transforma `edges_by_relation` em uma estrutura `relation -> (out_adj, in_adj)` onde cada adjlista usa peso 1.0 por aresta.
    - `n` é o número de vértices; as listas de adjacência têm tamanho `n`.

  - `build_integrated_graph_adjlists(n, edges_by_relation, weights=None)`:
    - Retorna `(out_adj, in_adj)` do grafo integrado ponderado, usando `build_integrated_edges` internamente.

  Observação prática: as páginas Streamlit do projeto (por exemplo `src/pages/4_Matriz_Adjacencia.py`) já chamam fluxos semelhantes: primeiro obtêm `idx_to_name` (mapa índice->nome) e `edges_by_relation` (ou arestas já agregadas), depois escolhem construir grafos separados ou o grafo integrado (com os pesos fornecidos) e finalmente convertem para `AdjacencyMatrixGraph` ou `AdjacencyListGraph` para exibir/exportar.

  7) Visualização das métricas na sidebar

  - Foi adicionada uma seção no helper de sidebar (`src/utils/streamlit_helpers.py`) chamada **Métricas de Rede** que calcula métricas ponderadas diretamente sobre o grafo atual em memória (via `src.services.graph_service.get_adjacency_list()`).
  - Métricas disponíveis na UI (apenas ponderadas):
    - `Degree (weighted)` — soma dos pesos das arestas (modo: `total`, `in` ou `out`).
    - `Betweenness (weighted)` — versão ponderada (Brandes adaptado) que considera custo inverso ao peso.
    - `PageRank` — iteração de potência usando distribuição ponderada por força de saída.
    - `Eigenvector Centrality` — iteração de potência sobre A^T usando pesos de entrada.
  - A UI mostra: uma breve interpretação da métrica, tabela Top-N com autores e score, gráfico de barras (Altair) e botão para baixar CSV com os resultados.

  8) Testes adicionados

  - Foram criados testes unitários em `tests/test_metrics.py` para validar:
    - construção de listas por relação (`build_relation_edge_lists`),
    - agregação integrada (`build_integrated_edges`) e
    - geração de adjlists (`build_relation_graphs_adjlists` / `build_integrated_graph_adjlists`).
  - Também foi criado `tests/test_pages_graphs.py` que carrega as páginas (`2_Grafo_Comentarios_PR_Issue.py` e `3_Grafo_Reviews.py`) e testa as funções de obtenção/transformação de autores e arestas com Neo4j mocks simples.

  Como rodar os testes:
  ```powershell
  pytest -q
  # ou apenas os novos testes
  pytest -q tests/test_metrics.py tests/test_pages_graphs.py
  ```

  9) Recomendações rápidas

  - Garanta que as páginas que constroem grafo populam `st.session_state['idx_to_name_map']` (mapa índice→nome). A sidebar usa essa chave para mostrar nomes legíveis nas tabelas de métricas.
  - Se alterar os pesos, passe explicitamente um dicionário `weights` para `build_integrated_edges`/`build_integrated_graph_adjlists` para reprodutibilidade.


5) Como rodar 

- Requisitos: Python 3.10+ (o projeto foi testado em Python 3.13). Instale bibliotecas do `requirements.txt` se necessário.

- Rodar a página Streamlit (visualmente mostrar a matriz):
```powershell
# a partir da raiz do repositório
& C:/Python313/python.exe -m pip install -r requirements.txt
& C:/Python313/python.exe -m streamlit run "src/app.py"
```

- Rodar o runner de métricas (terminal):
```powershell
& C:/Python313/python.exe "src/analysis/run_metrics.py"
```