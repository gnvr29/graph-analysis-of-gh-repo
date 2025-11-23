<div align="center">
  

<img src="https://cdn.jsdelivr.net/gh/devicons/devicon/icons/graphql/graphql-plain.svg" width="50"/>
  
# Trabalho Prático de Grafos

  
<img src="https://img.shields.io/badge/Linguagem-Python-3776AB?style=for-the-badge&logo=python&logoColor=FFD43B"/>
<img src="https://img.shields.io/badge/Banco%20de%20Dados-Neo4j-4581C3?style=for-the-badge&logo=neo4j&logoColor=white"/>
<img src="https://img.shields.io/badge/Estrutura-Grafos-FE7A16?style=for-the-badge&logo=dependabot&logoColor=white"/>
<img src="https://img.shields.io/badge/Universidade-PUC%20Minas-lightgrey?style=for-the-badge&logo=&logoColor=black"/>

</div>

---

## 👨‍💻 Integrantes
- Diogo Caribe Brunoro
- Gabriel Nogueira Vieira Resende
- Gabriel Reis Lebron de Oliveira
- Gustavo Azi Prehl Gama
- Guilherme de Almeida Rocha Vieira
- Felipe Augusto Pereira de Sousa

---

## 🧩 Diagramas

Abaixo estão os principais diagramas que representam a estrutura e funcionamento do projeto.

### Diagrama de Classes

O diagrama de classes abaixo representa a **estrutura de dados e as relações entre as entidades do sistema**.  

Ele foi desenvolvido para **modelar as informações que serão armazenadas no banco de dados Neo4j**, incluindo classes como `Issue`, `PullRequest`, `User`, `Comment` e `Review` (representadas em vermelho), além dos respectivos estados (`Enum`) (representados em azul).


> Importante destacar que este diagrama representa apenas as relações iniciais dos dados, exatamente como foram obtidas via raspagem e API do GitHub. Ele não reflete o estado final após as transformações, tratamentos e manipulações realizadas para fins de visualização no Streamlit.

<img src="https://github.com/gnvr29/graph-analysis-of-gh-repo/blob/main/diagramas/Diagrama_de_Classes.jpg"/>

<div align="center">
  
🔗 **Visualize melhor o diagrama no Figma:**  
[Figma – Diagrama de Classes](https://www.figma.com/board/POTmm00hPMjJvgaLPOVVSI/Diagrama-de-Classes---Grafos?node-id=0-1&t=rnLFH9P9kcigVyCU-1)

</div>

---
    
### Diagrama de Componentes

O diagrama de componentes abaixo representa a **arquitetura geral do sistema**, evidenciando como os principais módulos internos se relacionam com serviços externos, como a **API do GitHub**, o **Repositório do Streamlit**, o **banco de dados Neo4j** e as próprias páginas renderezidas pelo **Streamlit**.

Ele foi desenvolvido para descrever o fluxo completo de obtenção, processamento, armazenamento e visualização das informações, desde a coleta dos dados até a entrega das métricas e visualizações na **interface Streamlit**.

> Cada área do diagrama destaca um conjunto de responsabilidades

<img src="https://github.com/gnvr29/graph-analysis-of-gh-repo/blob/main/diagramas/Diagrama_de_Componentes.jpg"/>

<div align="center">
  
🔗 **Visualize melhor o diagrama no Figma:**  
[Figma – Diagrama de Componentes](https://www.figma.com/design/5rYh43TnhMNtONOzHeIlur/UML-Class-Diagram-Components--Community-?node-id=0-1&t=FnsYxDbW9IDD2ukM-1)

</div>


  

