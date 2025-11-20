import os
from dotenv import load_dotenv

# Carrega o arquivo .env. Tentamos localizar em lugares comuns porque em
# alguns fluxos (ex: execução via Streamlit) o cwd pode ser o diretório
# raiz do projeto, enquanto o .env foi colocado dentro de `src/`.
def _load_project_dotenv():
	here = os.path.abspath(os.path.dirname(__file__))  # config/
	candidates = [
		os.path.join(here, '..', '.env'),           # <project_root>/.env
		os.path.join(here, '..', 'src', '.env'),    # <project_root>/src/.env
		os.path.join(here, '.env'),                 # <project_root>/config/.env (unlikely)
	]

	for p in candidates:
		p = os.path.abspath(p)
		if os.path.exists(p):
			load_dotenv(p)
			return

	# fallback para comportamento padrão (procura no cwd e parents)
	load_dotenv()


# Executa o carregamento do .env
_load_project_dotenv()

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