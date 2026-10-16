import os
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings
from langchain_core.documents import Document
from generate_k8s_content import fetch_and_clean_doc

# Use Nomic embeddings (fast, local RAG)
EMBEDDING_MODEL = OllamaEmbeddings(model="nomic-embed-text")
CHROMA_DIR = "./chroma_db"

# Shared splitter for consistent chunking
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=150,
    separators=["\n\n", "\n", " ", ""]
)

def ingest_text_into_chroma(text: str, source: str):
    """Chunks and stores raw text (e.g. scraped HTML/docs) into ChromaDB."""
    chunks = text_splitter.split_text(text)
    documents = [Document(page_content=chunk, metadata={"source": source}) for chunk in chunks]
    
    if documents:
        print(f"📦 Storing {len(documents)} text chunks from [{source}] in ChromaDB...")
        Chroma.from_documents(
            documents=documents,
            embedding=EMBEDDING_MODEL,
            persist_directory=CHROMA_DIR
        )

def ingest_urls_into_chroma(urls: list[str]):
    """Fetches web pages, cleans them, and stores them in vector memory."""
    for url in urls:
        try:
            raw_text = fetch_and_clean_doc(url)
            ingest_text_into_chroma(raw_text, source=url)
        except Exception as e:
            print(f"⚠️ Failed to ingest URL {url}: {e}")

def ingest_spec_and_docs(file_paths: list[str]):
    """Chunks and stores local markdown documentation into ChromaDB."""
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    all_chunks = []
    for path in file_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                md_header_splits = markdown_splitter.split_text(f.read())
                all_chunks.extend(text_splitter.split_documents(md_header_splits))
                
    if all_chunks:
        print(f"📦 Storing {len(all_chunks)} markdown chunks in ChromaDB...")
        Chroma.from_documents(
            documents=all_chunks,
            embedding=EMBEDDING_MODEL,
            persist_directory=CHROMA_DIR
        )

def get_relevant_context(query: str, k: int = 3) -> str:
    """Searches ChromaDB for chunks relevant to the query."""
    if not os.path.exists(CHROMA_DIR):
        return "No local vector database found. Please ingest documents first."
        
    vectorstore = Chroma(persist_directory=CHROMA_DIR, embedding_function=EMBEDDING_MODEL)
    retriever = vectorstore.as_retriever(search_kwargs={"k": k})
    
    docs = retriever.invoke(query)
    return "\n\n".join([doc.page_content for doc in docs])

if __name__ == "__main__":
    # Test Ingestion when running rag_engine.py directly
    ingest_spec_and_docs(["spec.md"])
    ingest_urls_into_chroma([
        "https://kubernetes.io/docs/concepts/workloads/pods/",
        "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/"
    ])
    print("✅ RAG Database fully populated!")