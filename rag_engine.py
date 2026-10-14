import os
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

# Use Nomic embeddings (very fast, designed for local RAG)
EMBEDDING_MODEL = OllamaEmbeddings(model="nomic-embed-text")
CHROMA_DIR = "./chroma_db"

def ingest_spec_and_docs(file_paths: list[str]):
    """Chunks and stores documentation into the local Chroma vector database."""
    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]
    markdown_splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    
    # Safety net to prevent "Lost in the Middle" syndrome
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        separators=["\n\n", "\n", " ", ""]
    )
    
    all_chunks = []
    for path in file_paths:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                md_header_splits = markdown_splitter.split_text(f.read())
                all_chunks.extend(text_splitter.split_documents(md_header_splits))
                
    if all_chunks:
        print(f"📦 Storing {len(all_chunks)} chunks in ChromaDB...")
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