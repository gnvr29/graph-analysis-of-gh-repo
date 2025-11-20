# GitHub Data Pipeline (Issues & PRs) para Neo4j

Este projeto é um pipeline de dados robusto projetado para extrair **Issues** (Abertas e Fechadas) e **Pull Requests** de um repositório GitHub (neste caso, focado no `streamlit/streamlit`) e ingeri-los em um banco de dados Neo4j.

O principal objetivo é construir um grafo de conhecimento das atividades do repositório, capturando não apenas os itens principais, mas também suas interações (comentários, revisões) e metadados (autores, datas, status).

O pipeline é construído para ser **resiliente** e **eficiente em termos de memória**, utilizando uma estratégia de *streaming* (com geradores Python) para processar um item de cada vez, permitindo a coleta de repositórios massivos sem estourar a memória RAM.

## 🏗️ Como Funciona (Arquitetura)

O pipeline é orquestrado pelo `main.py` e opera em um fluxo de *streaming* (item por item):

1.  **Inicialização:** O `main.py` é executado.
2.  **Conexão:** Ele primeiro estabelece uma conexão com o banco de dados Neo4j usando o `Neo4jService`.
3.  **Coleta de Issues:**
    * O `GithubCollector` é iniciado.
    * O `main.py` chama `github_collector.collect_issues()` (abertas) e `collect_closed_issues()` (fechadas).
    * Esses métodos são **geradores (`yield`)**. Eles não baixam tudo de uma vez.
    * Para cada issue retornada pelo gerador, o `main.py` imediatamente a envia para o `neo4j_service.insert_issue_data()`.
4.  **Coleta de Pull Requests:**
    * O `main.py` chama `github_collector.collect_all_pull_requests_api()`.
    * Este método também é um gerador que usa a **API do GitHub**.
    * Para cada PR retornado, o `main.py` o envia para `neo4j_service.insert_pull_request_data()`.
5.  **Finalização:** Após a conclusão de todos os fluxos (ou interrupção), a conexão com o Neo4j é fechada.

## ✨ Estratégias de Coleta e Recursos

Este coletor utiliza duas estratégias diferentes para maximizar a coleta de dados e contornar os limites da API.

### 1. Issues: Estratégia Híbrida (Scraping + API Fallback)

Para evitar o rápido esgotamento da cota da API do GitHub (que é limitada), a coleta de issues prioriza o *scraping* das páginas públicas.

* **Scraping (Primário):**
    * O `github_collector.py` usa `requests.Session` para baixar a página HTML das issues (ex: `/streamlit/streamlit/issues`).
    * O `github_parser.py` (`html_to_json`) extrai um bloco JSON gigante embutido na página (um `<script data-target="react-app.embeddedData">`).
    * As funções `interpretar_issues` e `interpretar_comentarios` navegam por esse JSON complexo para extrair os dados da issue, corpo e comentários.
* **API Fallback (Secundário):**
    * O scraping do GitHub pode falhar. O `_collect_paginated_issues` detecta essa falha, para o *loop* de scraping e aciona o `collect_issues_api`.
    * Este método de API (`collect_issues_api`) assume a coleta a partir da página onde o scraping parou, garantindo que nenhum dado seja perdido.

### 2. Pull Requests: Estratégia Pura (API)

A coleta de Pull Requests é feita **exclusivamente pela API v3 do GitHub**. Isso é necessário para obter dados detalhados que não estão facilmente disponíveis via scraping, como:

* Status (`merged`, `closed`, `open`)
* Datas (`createdAt`, `closedAt`, `mergedAt`)
* Revisões (`reviews`)
* Comentários de Revisão (em linhas de código)
* Comentários da Issue (na thread principal do PR)

### 3. Eficiência e Resiliência

* **Streaming (Geradores `yield`):** A memória permanece baixa, pois apenas um item (issue ou PR) é mantido em memória por vez.
* **Controle de Rate Limit:** O coletor monitora o cabeçalho `X-RateLimit-Remaining` da API. Se o limite estiver baixo (< 50), ele pausa automaticamente por 60 segundos.
* **Tolerância a Falhas:** O pipeline pode ser interrompido a qualquer momento com `Ctrl+C`. Como os dados são inseridos item por item, tudo o que foi coletado até aquele momento já está salvo no Neo4j.

## 🗂️ Estrutura do Projeto

* `main.py`: O orquestrador do pipeline. Ponto de entrada para iniciar a coleta.
* `src/collectors/github_collector.py`: O cérebro da operação. Contém a classe `GithubCollector` com toda a lógica de scraping, chamadas de API, paginação e o *fallback*.
* `src/parsers/github_parser.py`: Funções auxiliares responsáveis por "traduzir" o HTML/JSON bruto (obtido pelo scraper) em dicionários Python limpos.
* `src/services/neo4j_service.py`: **(Arquivo Faltante)** Este arquivo é essencial. Ele deve conter a classe `Neo4jService` com a lógica de conexão ao banco e os métodos:
    * `insert_issue_data(issue_dict)`
    * `insert_pull_request_data(pr_dict)`
* `config/settings.py`: **(Arquivo Faltante)** Arquivo que carrega as variáveis de ambiente do `.env`.
* `.env`: **(Arquivo Faltante)** Arquivo para armazenar credenciais e segredos.

---

## 🚀 Como Configurar e Rodar

### 1. Pré-requisitos

* Python 3.8+
* Uma instância do Neo4j (local ou em nuvem)
* Um **Token de Acesso Pessoal (Classic)** do GitHub.
    * É **essencial** para a coleta de PRs e para o fallback da API.
    * Crie um em: `GitHub > Settings > Developer settings > Personal access tokens (Classic)`.
    * Marque apenas o escopo `public_repo`.

### 2. Instalação

1.  Clone este repositório.
2.  Crie um ambiente virtual:
    ```bash
    python -m venv venv
    source venv/bin/activate 
    # ou "venv\Scripts\activate" no Windows
    ```
3.  Instale as dependências. Crie um arquivo `requirements.txt`:
    ```txt
    # requirements.txt
    requests
    beautifulsoup4
    neo4j
    python-dotenv
    ```
    E instale:
    ```bash
    pip install -r requirements.txt
    ```

### 3. Arquivos de Configuração (Essencial)

Você **precisa** criar os dois arquivos faltantes para o projeto funcionar.

**A. Crie o arquivo `.env`:**

Crie um arquivo chamado `.env` na raiz do projeto. Ele **nunca** deve ser enviado ao GitHub (adicione-o ao `.gitignore`).

```ini
# .env
# --- Credenciais Neo4j ---
NEO4J_URI="neo4j://localhost:7687"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="sua_senha_aqui"

# --- Token da API do GitHub ---
GITHUB_API_TOKEN="seu_token_aqui_ghp_..."# GitHub Data Pipeline (Issues & PRs) para Neo4j

Este projeto é um pipeline de dados robusto projetado para extrair **Issues** (Abertas e Fechadas) e **Pull Requests** de um repositório GitHub (neste caso, focado no `streamlit/streamlit`) e ingeri-los em um banco de dados Neo4j.

O principal objetivo é construir um grafo de conhecimento das atividades do repositório, capturando não apenas os itens principais, mas também suas interações (comentários, revisões) e metadados (autores, datas, status).

O pipeline é construído para ser **resiliente** e **eficiente em termos de memória**, utilizando uma estratégia de *streaming* (com geradores Python) para processar um item de cada vez, permitindo a coleta de repositórios massivos sem estourar a memória RAM.

## 🏗️ Como Funciona (Arquitetura)

O pipeline é orquestrado pelo `main.py` e opera em um fluxo de *streaming* (item por item):

1.  **Inicialização:** O `main.py` é executado.
2.  **Conexão:** Ele primeiro estabelece uma conexão com o banco de dados Neo4j usando o `Neo4jService`.
3.  **Coleta de Issues:**
    * O `GithubCollector` é iniciado.
    * O `main.py` chama `github_collector.collect_issues()` (abertas) e `collect_closed_issues()` (fechadas).
    * Esses métodos são **geradores (`yield`)**. Eles não baixam tudo de uma vez.
    * Para cada issue retornada pelo gerador, o `main.py` imediatamente a envia para o `neo4j_service.insert_issue_data()`.
4.  **Coleta de Pull Requests:**
    * O `main.py` chama `github_collector.collect_all_pull_requests_api()`.
    * Este método também é um gerador que usa a **API do GitHub**.
    * Para cada PR retornado, o `main.py` o envia para `neo4j_service.insert_pull_request_data()`.
5.  **Finalização:** Após a conclusão de todos os fluxos (ou interrupção), a conexão com o Neo4j é fechada.

## ✨ Estratégias de Coleta e Recursos

Este coletor utiliza duas estratégias diferentes para maximizar a coleta de dados e contornar os limites da API.

### 1. Issues: Estratégia Híbrida (Scraping + API Fallback)

Para evitar o rápido esgotamento da cota da API do GitHub (que é limitada), a coleta de issues prioriza o *scraping* das páginas públicas.

* **Scraping (Primário):**
    * O `github_collector.py` usa `requests.Session` para baixar a página HTML das issues (ex: `/streamlit/streamlit/issues`).
    * O `github_parser.py` (`html_to_json`) extrai um bloco JSON gigante embutido na página (um `<script data-target="react-app.embeddedData">`).
    * As funções `interpretar_issues` e `interpretar_comentarios` navegam por esse JSON complexo para extrair os dados da issue, corpo e comentários.
* **API Fallback (Secundário):**
    * O scraping do GitHub pode falhar. O `_collect_paginated_issues` detecta essa falha, para o *loop* de scraping e aciona o `collect_issues_api`.
    * Este método de API (`collect_issues_api`) assume a coleta a partir da página onde o scraping parou, garantindo que nenhum dado seja perdido.

### 2. Pull Requests: Estratégia Pura (API)

A coleta de Pull Requests é feita **exclusivamente pela API v3 do GitHub**. Isso é necessário para obter dados detalhados que não estão facilmente disponíveis via scraping, como:

* Status (`merged`, `closed`, `open`)
* Datas (`createdAt`, `closedAt`, `mergedAt`)
* Revisões (`reviews`)
* Comentários de Revisão (em linhas de código)
* Comentários da Issue (na thread principal do PR)

### 3. Eficiência e Resiliência

* **Streaming (Geradores `yield`):** A memória permanece baixa, pois apenas um item (issue ou PR) é mantido em memória por vez.
* **Controle de Rate Limit:** O coletor monitora o cabeçalho `X-RateLimit-Remaining` da API. Se o limite estiver baixo (< 50), ele pausa automaticamente por 60 segundos.
* **Tolerância a Falhas:** O pipeline pode ser interrompido a qualquer momento com `Ctrl+C`. Como os dados são inseridos item por item, tudo o que foi coletado até aquele momento já está salvo no Neo4j.

## 🗂️ Estrutura do Projeto

* `main.py`: O orquestrador do pipeline. Ponto de entrada para iniciar a coleta.
* `src/collectors/github_collector.py`: O cérebro da operação. Contém a classe `GithubCollector` com toda a lógica de scraping, chamadas de API, paginação e o *fallback*.
* `src/parsers/github_parser.py`: Funções auxiliares responsáveis por "traduzir" o HTML/JSON bruto (obtido pelo scraper) em dicionários Python limpos.
* `src/services/neo4j_service.py`: Este arquivo é essencial. Ele contÊM a classe `Neo4jService` com a lógica de conexão ao banco e os métodos:
    * `insert_issue_data(issue_dict)`
    * `insert_pull_request_data(pr_dict)`
* `config/settings.py`: Arquivo que carrega as variáveis de ambiente do `.env`.
* `.env`: Arquivo para armazenar credenciais e segredos.

---

## 🚀 Como Configurar e Rodar

### 1. Pré-requisitos

* Python 3.8+
* Uma instância do Neo4j (local ou em nuvem)
* Um **Token de Acesso Pessoal (Classic)** do GitHub.
    * É **essencial** para a coleta de PRs e para o fallback da API.
    * Crie um em: `GitHub > Settings > Developer settings > Personal access tokens (Classic)`.
    * Marque apenas o escopo `public_repo`.

### 2. Instalação

1.  Clone este repositório.
2.  Crie um ambiente virtual:
    ```bash
    python -m venv venv
    source venv/bin/activate 
    # ou "venv\Scripts\activate" no Windows
    ```
3.  Instale as dependências. Crie um arquivo `requirements.txt`:
    ```txt
    # requirements.txt
    requests
    beautifulsoup4
    neo4j
    python-dotenv
    ```
    E instale:
    ```bash
    pip install -r requirements.txt
    ```

### 3. Arquivos de Configuração (Essencial)

Você **precisa** criar o arquivo .env faltante para o projeto funcionar.

**A. Crie o arquivo `.env`:**

Crie um arquivo chamado `.env` na raiz do projeto. Ele **nunca** deve ser enviado ao GitHub (adicione-o ao `.gitignore`).

```ini
# .env
# --- Credenciais Neo4j ---
NEO4J_URI="neo4j://localhost:7687"
NEO4J_USERNAME="neo4j"
NEO4J_PASSWORD="sua_senha_aqui"

# --- Token da API do GitHub ---
GITHUB_API_TOKEN="seu_token_aqui_ghp_..."