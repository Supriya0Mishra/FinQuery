"""
RAG pipeline for financial document Q&A and structured extraction.

Architecture:
- Embeddings: HuggingFace sentence-transformers (local, no API)
- Vector store: FAISS (in-memory)
- LLM: Groq Llama-3.1-8b-instant (free tier, ~500 tok/s)
- Q&A: retrieval-augmented generation with citation-style prompt
- Extraction: LLM with Pydantic-enforced structured output (function calling)
"""
import os
from typing import List, Optional

from dotenv import load_dotenv
from pydantic import BaseModel, Field

from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

load_dotenv()


# ============================================================
# PYDANTIC SCHEMAS — define the shape of "what we want extracted"
# ============================================================
class LineItem(BaseModel):
    """A single line item from an invoice or receipt."""
    description: str = Field(description="Description of the item or service")
    quantity: Optional[str] = Field(default=None, description="Quantity as it appears")
    unit_price: Optional[str] = Field(default=None, description="Unit price as it appears")
    amount: Optional[str] = Field(default=None, description="Line total as it appears")


class FinancialDocument(BaseModel):
    """Structured fields extracted from a financial document."""
    document_type: Optional[str] = Field(
        default=None,
        description="Type of document: invoice, receipt, bill, bank statement, etc.",
    )
    vendor_name: Optional[str] = Field(default=None, description="Name of the issuer / vendor")
    customer_name: Optional[str] = Field(default=None, description="Name of the customer / recipient")
    invoice_number: Optional[str] = Field(default=None, description="Invoice number or document ID")
    issue_date: Optional[str] = Field(default=None, description="Date issued, in original format")
    due_date: Optional[str] = Field(default=None, description="Payment due date if present")
    currency: Optional[str] = Field(default=None, description="Currency symbol or code (e.g. ₹, $, INR, USD)")
    subtotal: Optional[str] = Field(default=None, description="Subtotal exactly as it appears")
    tax_amount: Optional[str] = Field(default=None, description="Total tax amount exactly as it appears")
    total_amount: Optional[str] = Field(default=None, description="Total amount due exactly as it appears")
    payment_terms: Optional[str] = Field(default=None, description="Payment terms, e.g. Net 14, Net 30")
    line_items: List[LineItem] = Field(default_factory=list, description="All line items in the document")


# ============================================================
# DOCUMENT PROCESSING
# ============================================================
def split_documents(documents):
    """Split documents into overlapping chunks tuned for financial text."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)


def create_embeddings():
    """Local sentence-transformer embeddings (no API call, runs on CPU)."""
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        encode_kwargs={"normalize_embeddings": True},
    )


def build_vectorstore(chunks, embeddings):
    """Build a FAISS vector index from non-empty chunks."""
    texts = [doc.page_content for doc in chunks if doc.page_content.strip()]
    if not texts:
        raise ValueError(
            "Could not extract text from this PDF. "
            "It may be scanned or image-based — OCR support is planned."
        )
    return FAISS.from_texts(texts, embeddings)


# ============================================================
# LLM
# ============================================================
def get_llm():
    """Initialize Groq LLM (Llama-3.1-8b-instant). Free tier, sub-second latency."""
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
        max_tokens=1024,
    )


# ============================================================
# PROMPTS
# ============================================================
QA_PROMPT = ChatPromptTemplate.from_template(
    """You are a financial document analyst. Answer the user's question using ONLY the context provided below.

Rules:
- If the answer is not in the context, respond exactly: "I could not find this information in the document."
- Be concise and specific.
- For monetary amounts, always include the full amount with currency symbol exactly as it appears in the document (e.g., ₹1,58,415.00, not ₹1.58 or 158415).
- For dates, preserve the format used in the document.
- Do not invent or assume information that is not present.

Context:
{context}

Question: {question}

Answer:"""
)

EXTRACTION_PROMPT = ChatPromptTemplate.from_messages([
    (
        "system",
        "You are a precise financial document parser. Extract structured fields from the document text. "
        "Copy values EXACTLY as they appear — do not reformat numbers, dates, or currencies. "
        "Be especially careful with Indian number formats like 1,58,415.00 (do not truncate at the first comma). "
        "If a field is not present in the document, leave it null. Do not guess or fabricate."
    ),
    (
        "human",
        "Document text:\n\n{document_text}\n\nExtract all structured fields you can find."
    ),
])


# ============================================================
# Q&A CHAIN
# ============================================================
def build_qa_chain(vectorstore, llm):
    """Compose retriever → prompt → LLM → string output."""
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | QA_PROMPT
        | llm
        | StrOutputParser()
    )


# ============================================================
# STRUCTURED EXTRACTION
# ============================================================
def extract_structured_fields(documents, llm) -> FinancialDocument:
    """
    Run the document text through the LLM with Pydantic schema enforcement.
    Uses Groq's function-calling capability via LangChain's with_structured_output.
    Falls back to an empty schema if extraction fails.
    """
    full_text = "\n\n".join(doc.page_content for doc in documents)
    # Truncate to stay well within Groq's context window
    if len(full_text) > 8000:
        full_text = full_text[:8000]

    structured_llm = llm.with_structured_output(FinancialDocument)
    chain = EXTRACTION_PROMPT | structured_llm

    try:
        return chain.invoke({"document_text": full_text})
    except Exception as e:
        print(f"[FinQuery] Structured extraction failed: {e}")
        return FinancialDocument()


# ============================================================
# ENTRY POINT
# ============================================================
def create_rag_pipeline(documents):
    """
    Build the full pipeline.

    Returns:
        qa_chain: invoke with a question string, returns answer string
        structured_data: FinancialDocument with all extractable fields filled in
    """
    chunks = split_documents(documents)
    embeddings = create_embeddings()
    vectorstore = build_vectorstore(chunks, embeddings)
    llm = get_llm()

    qa_chain = build_qa_chain(vectorstore, llm)
    structured_data = extract_structured_fields(documents, llm)

    return qa_chain, structured_data