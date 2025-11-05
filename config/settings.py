import os
from dotenv import load_dotenv

load_dotenv()

# Configurações do Neo4j
NEO4J_URI = os.getenv("NEO4J_URI")
NEO4J_USERNAME = os.getenv("NEO4J_USERNAME")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD") 

# Configurações do GitHub
GITHUB_BASE_URL = "https://github.com/streamlit/streamlit/"
GITHUB_ISSUES_PATH = "issues"
GITHUB_CLOSED_ISSUES_PATH = "issues?q=is%3Aissue state%3Aclosed"
GITHUB_PULLS_PATH = "pulls"
GITHUB_CLOSED_PULLS_PATH = "pulls?q=is%3Apr+is%3Aclosed"

GITHUB_API_TOKEN = os.getenv("GITHUB_API_TOKEN", None)
REPO_OWNER = "streamlit"
REPO_NAME = "streamlit"

# Outras configurações
REQUEST_DELAY_SECONDS = 1