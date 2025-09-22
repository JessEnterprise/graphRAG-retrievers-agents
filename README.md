# GraphRAG – Retrievers & Agents (Customized)

🚀 My hands-on exploration of **GraphRAG with Neo4j**, adapted from the GraphAcademy workshop.  
This repo documents how I built **retrievers** and then wrapped them as **agent tools**, with my own additions for routing and evaluation.

---

## 📂 Repository Structure
workshop-genai/

│

├── 01_01_vector_retriever.ipynb # Vector Retriever (semantic search only)

├── 01_02_vector_cypher_retriever.ipynb # Vector + Graph Retriever (hybrid)

├── 01_03_text2cypher_retriever.ipynb # Text2Cypher Retriever (NL → Cypher)

├── 03_eval_retrievers.ipynb

│

├── 02_01_simple_agent.ipynb # Agent with Schema Tool

├── 02_02_vector_graph_agent.ipynb # Agent with Vector+Graph Tool

├── 02_03_text2cypher_agent.ipynb # Agent with Text2Cypher Tool

│

├── financial-documents/ # Example input docs

├── solutions/ # Reference solutions

│

├── test_environment.py # Verify OpenAI + Neo4j connection

├── requirements.txt # Python dependencies

└── .env.example # Template for secrets


## Additional custom files I added:

- `router.py` → **Heuristic + fallback router** (Vector → Hybrid → Text2Cypher)  
- `03_eval_retrievers.ipynb` → **Evaluation notebook** comparing retriever performance

---

## 🧠 My Understanding of GraphRAG

### Data Pipeline
1. Start with **unstructured documents**
2. Create:
   - **Vectorized dataset** → embeddings of text chunks
   - **Graphized dataset** → knowledge graph (entities + relationships)

### Retrievers (Learning Phase)
- **Vector Retriever** → broad, fuzzy search (vectors only)
- **Vector+Cypher Retriever** → semantic + graph context
- **Text2Cypher Retriever** → precise queries via Cypher

### Agent Tools (Conversational Phase)
- **Schema Tool** → explore database structure
- **Vector+Cypher Tool** → hybrid contextual retrieval
- **Text2Cypher Tool** → exact graph queries

👉 Agents add **query analysis, conversation, and automatic tool selection**.

---

## 🔑 When I Use Which

- **Exploratory** questions → *Vector Retriever*
- **Entity + relationships** → *Vector+Cypher*
- **Precise counts/lists/filters** → *Text2Cypher*
- **Confused about schema** → *Schema Tool*

---

## 🖼️ Visuals

### Retrievers
![Retrievers](images/retrievers.png)

### Agent Tools
![Agent Tools](images/agent_tools.png)

---

## 🚀 Quickstart

1. **Setup Python environment**
```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

2. **Configure secrets**

```bash
cp .env.example .env
# Fill in:
# OPENAI_API_KEY=...
# NEO4J_URI=bolt://localhost:7687
# NEO4J_USERNAME=neo4j
# NEO4J_PASSWORD=...
```

3. **Verify**
```bash
python test_environment.py
```


4. **Run notebooks**

01_* → retrievers

02_* → agent tools

03_eval_retrievers.ipynb → compare results

## 🧩 My Custom Additions

### ✅ Added router.py → heuristic + fallback agent router

### ✅ Added 03_eval_retrievers.ipynb → evaluation notebook for tool behavior

🔜 Plan: replace OpenAI embeddings with local HF model for privacy

## 📌 Roadmap

 Implement retrievers

 Wrap as agent tools

 Add router with fallback

 Add evaluation notebook

 Swap embeddings to local model


## 📝 License

MIT for my custom code. Original workshop materials © Neo4j GraphAcademy.

