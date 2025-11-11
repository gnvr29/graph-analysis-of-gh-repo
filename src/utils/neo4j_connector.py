import streamlit as st
from config.settings import NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD

try:
    from src.services.neo4j_service import Neo4jService
except ImportError:
    st.error("Falha ao importar a classe Neo4jService.")
    Neo4jService = None 

@st.cache_resource(show_spinner="Conectando ao Neo4j...")
def get_neo4j_service():
    """
    Cria e armazena em cache a conexão do serviço Neo4j.
    Esta função será executada APENAS UMA VEZ.
    """
    if Neo4jService is None:
        raise ImportError("Neo4jService não pôde ser importado.")
        
    try:
        service = Neo4jService(NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD)
        service.query("MATCH (n) RETURN count(n) AS nodeCount LIMIT 1")
        print("Conexão com Neo4j estabelecida com sucesso.")
        return service
    except Exception as e:
        raise ConnectionError(f"Falha ao conectar ao Neo4j: {e}")