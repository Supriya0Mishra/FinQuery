"""
RAG pipeline for financial document Q&A and structured extraction.

Architecture
------------
- Embeddings: HuggingFace sentence-transformers (local, no API)
- Vector store: FAISS (in-memory)
- LLM (Q&A): Groq Llama-3.1-8b-instant - fast, low-cost interactive answers
- LLM (extraction): Groq Llama-3.3-70b-versatile - higher accuracy for one-shot
  structured extraction with function calling
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


# ---------- PYDANTIC SCHEMAS ----------
class LineItem(BaseModel):
    """A single line item from an invoice or receipt."""
    description: str = Field(description="Description of the item or service")
    quantity: Optional[str] = Field(default=None, description="Quantity as it appears")
    unit_price: Optional[str] = Field(default=None, description="Unit price as it appears")
    amount: Optional[str] = Field(default=None, description="Line total as it appears")


class FinancialDocument(BaseModel):
    """Structured fields extracted from a financial document."""
    document_type: Optional[str] = Field(default=None, description="invoice, receipt, bill, etc.")
    vendor_name: Optional[str] = Field(default=None, description="Issuer / vendor name")
    customer_name: Optional[str] = Field(default=None, description="Customer / recipient name")
    invoice_number: Optional[str] = Field(default=None, description="Invoice number or document ID")
    issue_date: Optional[str] = Field(default=None, description="Date issued in original format")
    due_date: Optional[str] = Field(default=None, description="Payment due date if present")
    currency: Optional[str] = Field(default=None, description="Currency symbol or code")
    subtotal: Optional[str] = Field(default=None, description="Subtotal exactly as it appears")
    tax_amount: Optional[str] = Field(default=None, description="Total tax exactly as it appears")
    total_amount: Optional[str] = Field(default=None, description="Total due exactly as it appears")
    payment_terms: Optional[str] = Field(default=None, description="e.g. Net 14, Net 30")
    line_items: List[LineItem] = Field(default_factory=list, description="All line items")


# ---------- DOCUMENT PROCESSING ----------
def split_documents(documents):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=600,
        chunk_overlap=100,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    return splitter.split_documents(documents)


def create_embeddings():
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        encode_kwargs={"normalize_embeddings": True},
    )


def build_vectorstore(chunks, embeddings):
    texts = [doc.page_content for doc in chunks if doc.page_content.strip()]
    if not texts:
        raise ValueError(
            "Could not extract text from this PDF. "
            "It may be scanned or image-based - OCR support is planned."
        )
    return FAISS.from_texts(texts, embeddings)


# ---------- LLMs (two-tier strategy) ----------
def _check_api_key():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError(
            "GROQ_API_KEY not found in environment. "
            "Add it to your .env file. Get a free key at https://console.groq.com"
        )
    return api_key


def get_qa_llm():
    """Fast 8B model for interactive Q&A. Sub-second latency."""
    return ChatGroq(
        model="llama-3.1-8b-instant",
        temperature=0,
        api_key=_check_api_key(),
        max_tokens=512,
    )


def get_extraction_llm():
    """Larger 70B model for one-shot structured extraction. More reliable function calling."""
    return ChatGroq(
        model="llama-3.3-70b-versatile",
        temperature=0,
        api_key=_check_api_key(),
        max_tokens=2048,
    )


# ---------- PROMPTS ----------
QA_PROMPT = ChatPromptTemplate.from_template(
    """You are a financial document analyst. Answer the user's question using ONLY the context provided below.

Rules:
- If the answer is not in the context, respond exactly: "I could not find this information in the document."
- Be concise and specific.
- For monetary amounts, always include the FULL amount with currency symbol exactly as it appears in the document.
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
        "You are a precise financial document parser. Extract structured fields from the document. "
        "Copy values EXACTLY as they appear - do not reformat numbers, dates, or currencies. "
        "Be especially careful with Indian number formats like 1,58,415.00 (do not truncate at commas). "
        "Extract ALL line items you find. "
        "If a field is not present, leave it null. Do not guess or fabricate.",
    ),
    (
        "human",
        "Document text:\n\n{document_text}\n\nExtract all structured fields and line items.",
    ),
])


# ---------- Q&A CHAIN ----------
def build_qa_chain(vectorstore, llm):
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})

    def format_docs(docs):
        return "\n\n".join(doc.page_content for doc in docs)

    return (
        {"context": retriever | format_docs, "question": RunnablePassthrough()}
        | QA_PROMPT
        | llm
        | StrOutputParser()
    )


# ---------- STRUCTURED EXTRACTION ----------
def extract_structured_fields(documents, llm) -> FinancialDocument:
    """
    Run document text through the LLM with Pydantic schema enforcement.
    Uses Groq's function calling capability via LangChain's with_structured_output.
    """
    full_text = "\n\n".join(doc.page_content for doc in documents)
    if len(full_text) > 12000:
        full_text = full_text[:12000]

    structured_llm = llm.with_structured_output(FinancialDocument)
    chain = EXTRACTION_PROMPT | structured_llm

    result = chain.invoke({"document_text": full_text})

    # Defensive: if the model returned a dict (rare), coerce it
    if isinstance(result, dict):
        result = FinancialDocument(**result)

    return result


# ---------- ENTRY POINT ----------
def create_rag_pipeline(documents):
    """
    Build the full pipeline.

    Returns:
        qa_chain: invoke with question string -> answer string
        structured_data: FinancialDocument with extracted fields
    """
    chunks = split_documents(documents)
    embeddings = create_embeddings()
    vectorstore = build_vectorstore(chunks, embeddings)

    qa_llm = get_qa_llm()
    extraction_llm = get_extraction_llm()

    qa_chain = build_qa_chain(vectorstore, qa_llm)
    structured_data = extract_structured_fields(documents, extraction_llm)

    return qa_chain, structured_data