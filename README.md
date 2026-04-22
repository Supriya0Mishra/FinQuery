# 💰 FinQuery — Financial Document Intelligence

A RAG-based AI system that lets you upload financial documents (invoices, receipts, reports) and extract structured insights through natural language queries.

## 🚀 Features
- 📄 Upload financial PDFs (invoices, receipts, reports)
- 🔍 Semantic search using FAISS vector embeddings
- 🧠 Retrieval-Augmented Generation (RAG) pipeline
- 🗂️ Structured field extraction (vendor, amount, date, invoice number) as JSON output
- 💬 Natural language querying over financial documents
- 🌐 Deployed on Streamlit Cloud

## 🛠️ Tech Stack
- **Python 3.10**
- **Streamlit** — Web interface
- **LangChain** — RAG pipeline
- **FAISS** — Vector similarity search
- **HuggingFace Transformers** — Embeddings and summarization
- **Sentence-Transformers** — Local embeddings (all-MiniLM-L6-v2)
- **facebook/bart-large-cnn** — Text summarization

## 🧠 How It Works
1. Upload a financial PDF document
2. Text is extracted and split into chunks
3. Chunks are embedded using Sentence-Transformers
4. FAISS retrieves the most relevant chunks for each query
5. LLM generates a structured answer with extracted fields
6. Output is returned as natural language and JSON

## 📊 Example Queries
- "What is the total amount?"
- "Who is the vendor?"
- "What is the invoice date?"
- "What items were purchased?"

## 📦 Installation
```bash
pip install -r requirements.txt
streamlit run app.py
```