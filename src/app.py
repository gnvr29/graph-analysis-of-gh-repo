# src/app.py

import streamlit as st
import sys
import os

current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

try:
    from src.utils.neo4j_connector import get_neo4j_service
except ImportError as e:
    st.error(f"Erro crítico ao importar o conector: {e}")
    st.stop()


st.set_page_config(
    page_title="Análise de Grafos",
    layout="wide"
)

st.title("Análise de Grafos de Repositórios 🚀")
st.markdown(
    """
    Bem-vindo à ferramenta de análise de grafos.
    
    Use o menu na barra lateral à esquerda para navegar entre as
    diferentes visualizações.
    """
)

st.sidebar.header("Status da Conexão")
try:
    get_neo4j_service() 
    st.sidebar.success("Conectado ao Neo4j.")
except Exception as e:
    st.sidebar.error(f"Falha ao conectar ao Neo4j.")
    st.error(f"Erro de conexão: {e}")
    st.info("Verifique suas credenciais no 'config/settings.py' e se o Neo4j está rodando.")
    st.stop() 

st.sidebar.info("Selecione uma análise no menu.")