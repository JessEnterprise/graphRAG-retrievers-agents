
# src/router.py
import os, re, json
from typing import Dict, Any, Tuple, List, Optional

from dotenv import load_dotenv
from neo4j import GraphDatabase

# Retrievers from the Neo4j GraphRAG package
from neo4j_graphrag.retrievers import (
    VectorRetriever,
    VectorCypherRetriever,
    Text2CypherRetriever,
)

# --- Embedders / LLM are injected; start with OpenAI, swap later (see step 3)
from neo4j_graphrag.llm import OpenAILLM
from neo4j_graphrag.embeddings import OpenAIEmbeddings

load_dotenv()

# -------- utility: quick entity probe in graph --------
def entity_exists(driver, name: str) -> bool:
    q = """
    MATCH (n)
    WHERE any(l IN labels(n) WHERE exists(n.name)) AND toLower(n.name) = toLower($name)
    RETURN count(n) > 0 AS exists
    """
    with driver.session() as s:
        return s.run(q, name=name).single()["exists"]

def extract_entities_simple(q: str) -> List[str]:
    # very lightweight NER placeholder; customize or swap for spaCy if you like
    # grabs capitalized tokens ≥ 3 chars as candidate entities
    return [w for w in re.findall(r"\b[A-Z][a-zA-Z0-9\-]{2,}\b", q)]

def is_precise_query(q: str) -> bool:
    ql = q.lower()
    return bool(re.search(r"\b(count|how many|list|show all|top \d+|sum|avg|average|min|max|greater than|less than|between)\b", ql))

def wants_schema(q: str) -> bool:
    ql = q.lower()
    return any(k in ql for k in ["schema", "labels", "properties", "relationships", "data model", "graph model"])

# -------- Router class --------
class GraphRAGRouter:
    def __init__(
        self,
        driver,
        embedder,
        llm=None,
        index_name: str = "chunkEmbeddings",
        neo4j_schema: Optional[str] = None,
        retrieval_query: Optional[str] = None,
        top_k: int = 5,
    ):
        self.driver = driver
        self.embedder = embedder
        self.llm = llm
        self.index_name = index_name
        self.top_k = top_k

        # sensible default: expand entities around matched chunks
        self.retrieval_query = retrieval_query or """
        // Given a set of relevant chunk node ids ($ids), pull chunk text and nearby entities
        MATCH (c:Chunk)
        WHERE id(c) IN $ids
        OPTIONAL MATCH (c)-[:MENTIONS]->(e)
        WITH c, collect(DISTINCT e) AS ents
        RETURN c.text AS text,
               [x IN ents | {labels: labels(x), name: coalesce(x.name, x.id, ''), id: id(x)}] AS entities
        """

        self.vector_retriever = VectorRetriever(
            driver=self.driver,
            index_name=self.index_name,
            embedder=self.embedder,
        )

        self.vector_cypher_retriever = VectorCypherRetriever(
            driver=self.driver,
            index_name=self.index_name,
            retrieval_query=self.retrieval_query,
            embedder=self.embedder,
        )

        self.text2cypher_retriever = (
            Text2CypherRetriever(driver=self.driver, llm=self.llm, neo4j_schema=neo4j_schema)
            if self.llm is not None else None
        )

    # ---- main routing logic (heuristic + fallbacks) ----
    def route(self, question: str) -> Tuple[str, Dict[str, Any]]:
        # 1) rule-based pre-routing
        if wants_schema(question):
            return "schema_tool", self.run_schema_tool()

        entities = extract_entities_simple(question)
        in_graph = any(entity_exists(self.driver, e) for e in entities) if entities else False

        # 2) choose tool
        if is_precise_query(question) and self.text2cypher_retriever:
            tool = "text2cypher_tool"
            result = self.run_text2cypher(question)
            if not self._ok(result):  # fallback to hybrid
                tool = "vector_cypher_tool"
                result = self.run_vector_cypher(question)
                if self._empty(result):  # fallback to vector
                    tool = "vector_tool"
                    result = self.run_vector(question)
            return tool, result

        if in_graph:
            tool = "vector_cypher_tool"
            result = self.run_vector_cypher(question)
            if self._empty(result):  # fallback to vector
                tool = "vector_tool"
                result = self.run_vector(question)
            return tool, result

        # default: exploratory vector
        return "vector_tool", self.run_vector(question)

    # ---- tool executors ----
    def run_vector(self, question: str) -> Dict[str, Any]:
        hits = self.vector_retriever.retrieve(question, top_k=self.top_k)
        return {"hits": hits}

    def run_vector_cypher(self, question: str) -> Dict[str, Any]:
        hits = self.vector_cypher_retriever.retrieve(question, top_k=self.top_k)
        return {"hits": hits}

    def run_text2cypher(self, question: str) -> Dict[str, Any]:
        if not self.text2cypher_retriever:
            return {"error": "Text2Cypher not configured (no LLM)."}
        return self.text2cypher_retriever.retrieve(question)

    def run_schema_tool(self) -> Dict[str, Any]:
        q = """
        CALL db.schema.visualization() YIELD nodes, relationships
        RETURN nodes, relationships
        """
        with self.driver.session() as s:
            rec = s.run(q).single()
            return {"nodes": rec["nodes"], "relationships": rec["relationships"]}

    # ---- helpers ----
    @staticmethod
    def _ok(res: Dict[str, Any]) -> bool:
        return bool(res) and not res.get("error")

    @staticmethod
    def _empty(res: Dict[str, Any]) -> bool:
        hits = res.get("hits", [])
        return not hits

# ---- CLI harness ----
def build_router() -> GraphRAGRouter:
    uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
    user = os.getenv("NEO4J_USERNAME", "neo4j")
    pwd  = os.getenv("NEO4J_PASSWORD", "password")
    index_name = os.getenv("VECTOR_INDEX_NAME", "chunkEmbeddings")
    openai_key = os.getenv("OPENAI_API_KEY")

    driver = GraphDatabase.driver(uri, auth=(user, pwd))
    embedder = OpenAIEmbeddings(api_key=openai_key)  # <-- will swap to local later
    llm = OpenAILLM(model_name=os.getenv("OPENAI_MODEL", "gpt-4o"), api_key=openai_key) if openai_key else None

    # If you already have a schema string, pass it; otherwise None (Text2Cypher retriever may build it internally)
    router = GraphRAGRouter(driver=driver, embedder=embedder, llm=llm, index_name=index_name)
    return router

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--q", required=True, help="User question")
    args = parser.parse_args()

    router = build_router()
    tool, result = router.route(args.q)
    print(json.dumps({"tool": tool, "result": result}, indent=2, default=str))
