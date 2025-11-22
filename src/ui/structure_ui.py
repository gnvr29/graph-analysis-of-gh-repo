import streamlit as st
import pandas as pd
import plotly.express as px
from typing import Dict, Any

def display_structure_results(res: Dict[str, Any]):
    """Desenha os resultados da análise estrutural."""
    st.divider()
    st.subheader(f"Resultados para: {res['analysis_mode']}")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric(label="Densidade da Rede", value=f"{res['density']:.5f}", help="Proporção de conexões existentes vs. possíveis.")
    with col2:
        st.metric(label="Coef. de Aglomeração (Médio)", value=f"{res['clustering']:.4f}", help="Probabilidade de dois vizinhos de um nó serem vizinhos entre si.")
    with col3:
        st.metric(label="Assortatividade", value=f"{res['assortativity']:.4f}", help="Correlação de grau.")

    st.subheader("Interpretação")
    density = res['density']
    clustering = res['clustering']
    assortativity = res['assortativity']

    dens_interp = "muito esparsa" if density < 0.01 else "esparsa" if density < 0.1 else "moderada" if density < 0.5 else "densa"
    st.markdown(f"- **Densidade:** A rede é **{dens_interp}**.")
    
    clust_interp = "baixa coesão local" if clustering < 0.1 else "alta tendência a comunidades"
    st.markdown(f"- **Clusterização:** O valor indica **{clust_interp}**.")
    
    if assortativity > 0.1:
        assort_interp = "rede elitista (Hubs conectam-se a Hubs)"
    elif assortativity < -0.1:
        assort_interp = "rede hierárquica (Hubs conectam-se a periféricos/novatos)"
    else:
        assort_interp = "rede neutra (sem preferência clara de conexão)"
    st.markdown(f"- **Assortatividade:** Indica uma **{assort_interp}**.")

    # --- GRÁFICO EXTRA: DISPERSÃO DE GRAUS ---
    st.subheader("Visualizando a Assortatividade")
    scatter_data = res['scatter_data']
    max_degree = res['max_degree']

    if len(scatter_data) > 0:
        df_scatter = pd.DataFrame(scatter_data)
        if len(df_scatter) > 5000:
                df_scatter = df_scatter.sample(n=5000, random_state=42).copy()
                st.caption("Nota: Exibindo amostra de 5000 conexões aleatórias para performance.")

        fig = px.scatter(
            df_scatter, 
            x="Grau Origem", 
            y="Grau Destino",
            hover_data=["Autor Origem", "Autor Destino"],
            opacity=0.3,
            title=f"Correlação de Graus ({len(df_scatter)} amostras)"
        )
        fig.add_shape(type="line", x0=0, y0=0, x1=max_degree, y1=max_degree,
                    line=dict(color="Red", width=1, dash="dash"))
        st.plotly_chart(fig, use_container_width=True)