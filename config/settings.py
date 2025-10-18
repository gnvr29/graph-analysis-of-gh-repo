import os

# Configurações do Neo4j
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD") 

# Configurações do GitHub
GITHUB_BASE_URL = "https://github.com/streamlit/streamlit/"
GITHUB_ISSUES_PATH = "issues"
GITHUB_PULLS_PATH = "pulls"

# Outras configurações
REQUEST_DELAY_SECONDS = 1