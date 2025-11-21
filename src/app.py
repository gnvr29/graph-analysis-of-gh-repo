# src/app.py

import streamlit as st
import sys
import os
import time 

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


MAX_RETRIES = 3  
RETRY_DELAY = 5  

st.sidebar.header("Status da Conexão")

connection_successful = False
for attempt in range(MAX_RETRIES):
    try:
        st.sidebar.info(f"Tentando conectar ao Neo4j... (Tentativa {attempt + 1}/{MAX_RETRIES})")
        get_neo4j_service() 
        st.sidebar.success("Conectado ao Neo4j.")
        connection_successful = True
        break  
    except Exception as e:
        if attempt < MAX_RETRIES - 1:
            st.sidebar.warning(f"Falha na conexão. Tentando novamente em {RETRY_DELAY} segundos...")
            time.sleep(RETRY_DELAY)
        else:
            st.sidebar.error(f"Falha ao conectar ao Neo4j após {MAX_RETRIES} tentativas.")
            st.error(f"Erro de conexão final: {e}")
            st.info("Verifique suas credenciais no 'config/settings.py' e se o Neo4j está rodando.")
            st.stop()

if connection_successful:
    st.sidebar.info("Selecione uma análise no menu.")
