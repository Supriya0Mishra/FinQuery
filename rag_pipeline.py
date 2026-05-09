"""
RAG pipeline for financial document Q&A.
Uses Groq (Llama-3.1) for fast LLM inference and HuggingFace embeddings
for local semantic retrieval.
"""

import os
from dotenv import load_dotenv
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Load GROQ_API_KEY (and any other env vars) from .env file
load_dotenv()


# ---------- DOCUMENT SPLITTING ----------
def split_documents(documents):
    """Split documents into overlapping chunks tuned for financial text."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)


# ---------- EMBEDDINGS ----------
def create_embeddings():
    """Local sentence-transformer embeddings (no API call, free)."""
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        encode_kwargs={"normalize_embeddings": True},
    )


# ---------- VECTOR STORE ----------
def build_vectorstore(chunks, embeddings):
    """Build a FAISS index from non-empty chunks."""
    texts = [doc.page_content for doc in chunks if doc.page_content.strip()]
    if not texts:
        raise ValueError(
            "Could not extract text from this PDF. "
            "It may be scanned or image-based — OCR support is planned."
        )
    return FAISS.from_texts(texts, embeddings)


# ---------- LLM ----------
def get_llm():
    """Initialize Groq LLM. Free tier, ~500 tok/s, no GPU needed."""
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found in environment. "
            "Add it to your .env file. Get a free key at https://console.groq.com"
        )
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=api_key,
        max_tokens=512,
    )


# ---------- PROMPT ----------
FINANCIAL_QA_PROMPT = ChatPromptTemplate.from_template(
    """You are a financial document analyst. Answer the user's question using ONLY the context provided below.

Rules:
- If the answer is not in the context, respond exactly: "I could not find this information in the document."
- Be concise and specific.
- For monetary amounts, always include the currency symbol or code.
- For dates, preserve the format used in the document.
- Do not invent or assume information that is not present.

Context:
{context}

Question: {question}

Answer:"""
)


# ---------- RAG CHAIN ----------
def build_rag_chain(vectorstore):
    """Compose retriever → prompt → LLM → string output."""
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    llm = get_llm()

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    rag_chain = (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | FINANCIAL_QA_PROMPT
        | llm
        | StrOutputParser()
    )
    return rag_chain


# ---------- ENTRY POINT ----------
def create_rag_pipeline(documents):
    """Create the full RAG pipeline from loaded documents."""
    chunks = split_documents(documents)
    embeddings = create_embeddings()
    vectorstore = build_vectorstore(chunks, embeddings)
    return build_rag_chain(vectorstore)