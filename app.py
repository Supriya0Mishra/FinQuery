import re
import json
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader
from rag_pipeline import create_rag_pipeline

# ---------- PAGE SETUP ----------
st.set_page_config(page_title="FinQuery", layout="centered")
st.title("💰 FinQuery — Financial Document Intelligence")
st.write("Upload a financial document (invoice, receipt, report) and extract structured insights.")

# ---------- SESSION STATE ----------
if "qa_chain" not in st.session_state:
    st.session_state.qa_chain = None
if "history" not in st.session_state:
    st.session_state.history = []

# ---------- STRUCTURED EXTRACTION ----------
def extract_financial_fields(answer: str) -> dict:
    fields = {
        "vendor_name": None,
        "amount": None,
        "date": None,
        "invoice_number": None
    }
    amount_match = re.search(r"[\$₹€£]?\s?\d+[\.,]\d{2}", answer)
    date_match = re.search(r"\b(\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b", answer)
    if amount_match:
        fields["amount"] = amount_match.group()
    if date_match:
        fields["date"] = date_match.group()
    return {k: v for k, v in fields.items() if v}

# ---------- ANSWER FORMATTER ----------
def format_answer(answer: str, question: str) -> str:
    if not answer or not answer.strip():
        return "Could not find relevant information in this document."
    answer = re.sub(r"\s+", " ", answer).strip()
    fields = extract_financial_fields(answer)
    if fields:
        structured = json.dumps(fields, indent=2)
        return f"{answer}\n\n**Extracted Fields:**\n```json\n{structured}\n```"
    return answer

# ---------- FILE UPLOAD ----------
uploaded_file = st.file_uploader("Upload a financial PDF (invoice, receipt, report)", type=["pdf"])

if uploaded_file:
    with st.spinner("Processing financial document..."):
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.read())
        loader = PyPDFLoader("temp.pdf")
        documents = loader.load()
        try:
            st.session_state.qa_chain = create_rag_pipeline(documents)
            st.success("Document processed! Ask about amounts, vendors, dates, or totals.")
        except ValueError as e:
            st.error(str(e))
            st.stop()

# ---------- SUGGESTED QUESTIONS ----------
if st.session_state.qa_chain:
    st.markdown("**Suggested queries:**")
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("- What is the total amount?")
        st.markdown("- Who is the vendor?")
    with col2:
        st.markdown("- What is the invoice date?")
        st.markdown("- What items were purchased?")

    question = st.text_input("Ask a question about the financial document")
    if question:
        with st.spinner("Extracting answer..."):
            raw_answer = st.session_state.qa_chain.invoke(question)
            final_answer = format_answer(raw_answer, question)
        st.session_state.history.append((question, final_answer))

# ---------- DISPLAY HISTORY ----------
for q, a in reversed(st.session_state.history):
    with st.container():
        st.markdown(
            f"""
            <div style="
                border:1px solid #444;
                border-radius:10px;
                padding:15px;
                margin-bottom:15px;
                background-color:#111;
            ">
                <b>Question:</b><br>{q}<br><br>
                <b>Answer:</b><br>{a.replace(chr(10), '<br>')}
            </div>
            """,
            unsafe_allow_html=True
        )