"""
FinQuery - Streamlit interface for financial document intelligence.
"""
import streamlit as st
from langchain_community.document_loaders import PyPDFLoader

from rag_pipeline import create_rag_pipeline


# ---------- PAGE SETUP ----------
st.set_page_config(page_title="FinQuery", layout="centered")
st.title("FinQuery — Financial Document Intelligence")
st.caption(
    "Upload a financial document and extract structured insights "
    "through natural language queries."
)


# ---------- SESSION STATE ----------
if "qa_chain" not in st.session_state:
    st.session_state.qa_chain = None
if "structured_data" not in st.session_state:
    st.session_state.structured_data = None
if "history" not in st.session_state:
    st.session_state.history = []


# ---------- FILE UPLOAD ----------
uploaded_file = st.file_uploader(
    "Upload a financial PDF (invoice, receipt, report)", type=["pdf"]
)

if uploaded_file:
    with st.spinner("Processing document and extracting fields..."):
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.read())

        loader = PyPDFLoader("temp.pdf")
        documents = loader.load()

        try:
            qa_chain, structured_data = create_rag_pipeline(documents)
            st.session_state.qa_chain = qa_chain
            st.session_state.structured_data = structured_data
            st.success("Document processed. Structured fields extracted below.")
        except ValueError as e:
            st.error(str(e))
            st.stop()
        except Exception as e:
            st.error(f"Failed to process document: {type(e).__name__}: {e}")
            st.stop()


# ---------- STRUCTURED FIELDS ----------
if st.session_state.structured_data:
    data = st.session_state.structured_data

    st.markdown("### Extracted Fields")

    col1, col2, col3 = st.columns(3)
    col1.metric("Vendor", data.vendor_name or "—")
    col2.metric("Total Amount", data.total_amount or "—")
    col3.metric("Invoice #", data.invoice_number or "—")

    with st.expander("View all extracted fields"):
        col_a, col_b = st.columns(2)
        with col_a:
            st.markdown(f"**Document Type:** {data.document_type or '—'}")
            st.markdown(f"**Customer:** {data.customer_name or '—'}")
            st.markdown(f"**Issue Date:** {data.issue_date or '—'}")
            st.markdown(f"**Due Date:** {data.due_date or '—'}")
            st.markdown(f"**Payment Terms:** {data.payment_terms or '—'}")
        with col_b:
            st.markdown(f"**Currency:** {data.currency or '—'}")
            st.markdown(f"**Subtotal:** {data.subtotal or '—'}")
            st.markdown(f"**Tax Amount:** {data.tax_amount or '—'}")
            st.markdown(f"**Total Amount:** {data.total_amount or '—'}")

        if data.line_items:
            st.markdown("**Line Items:**")
            line_items_data = [
                {
                    "Description": item.description,
                    "Quantity": item.quantity or "—",
                    "Unit Price": item.unit_price or "—",
                    "Amount": item.amount or "—",
                }
                for item in data.line_items
            ]
            st.dataframe(line_items_data, hide_index=True, use_container_width=True)

    st.download_button(
        "Download extracted fields as JSON",
        data=data.model_dump_json(indent=2),
        file_name="extracted_fields.json",
        mime="application/json",
    )


# ---------- Q&A ----------
if st.session_state.qa_chain:
    st.markdown("### Ask a Question")
    st.caption(
        "Suggested: *What is the total amount?* · *Who is the vendor?* · "
        "*What is the SGST amount?* · *What items were purchased?*"
    )

    question = st.text_input("Your question:", key="question_input")
    if question:
        with st.spinner("Thinking..."):
            answer = st.session_state.qa_chain.invoke(question)
        st.session_state.history.append((question, answer))


# ---------- CONVERSATION ----------
if st.session_state.history:
    st.markdown("### Conversation")
    for q, a in reversed(st.session_state.history):
        with st.container():
            st.markdown(f"**Q:** {q}")
            st.markdown(f"**A:** {a}")
            st.divider()