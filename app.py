import os
from PyPDF2 import PdfReader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
import streamlit as st
import google.generativeai as genai
from langchain.vectorstores import FAISS
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.chains.question_answering import load_qa_chain
from langchain.prompts import PromptTemplate
from dotenv import load_dotenv
 # Load file .env và lấy ra gemini api k
load_dotenv()
os.getenv("GOOGLE_API_KEY")
genai.configure(api_key=os.getenv("GOOGLE_API_KEY"))

# Đọc tất cả các trang PDF và return text


def extract_pdf_text(pdf_docs):
    content = ""
    for pdf in pdf_docs:
        pdf_reader = PdfReader(pdf)
        for page in pdf_reader.pages:
            content += page.extract_text()
    return content

# Split text thành các chunks

def split_text_into_chunks(text):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=10000, chunk_overlap=1000)
    chunks = splitter.split_text(text)
    return chunks  # list of strings

# Embedding các chunks text đã split


def get_vector_store(chunks):
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001") 
    vector_store = FAISS.from_texts(chunks, embedding=embeddings)
    # Save file local faiss_index
    vector_store.save_local("faiss_index")

# Thiết lập conversational question answering sử dụng googlge generative AI model
def get_conversational_chain():
    # Prompt mẫu
    prompt_template = """
    Answer the question as detailed as possible from the provided context, make sure to provide all the details, if the answer is not in
    provided context just say, "answer is not available in the context", don't provide the wrong answer\n\n
    Context:\n {context}?\n
    Question: \n{question}\n

    Answer:
    """

    model = ChatGoogleGenerativeAI(model="gemini-pro",
                                   client=genai,
                                   temperature=0.1,
                                   )
    prompt = PromptTemplate(template=prompt_template,
                            input_variables=["context", "question"])
    chain = load_qa_chain(llm=model, chain_type="stuff", prompt=prompt)
    return chain

# Xóa lịch sử chat
def clear_chat_history():
    st.session_state.messages = [
        {"role": "assistant", "content": "Upload file PDF của bạn và hỏi câu hỏi"}]

# Câu hỏi của người dùng
def user_input(user_question):
    embeddings = GoogleGenerativeAIEmbeddings(
        model="models/embedding-001")  # type: ignore

    new_db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True) 
    docs = new_db.similarity_search(user_question)
    

    chain = get_conversational_chain()

    response = chain(
        {"input_documents": docs, "question": user_question}, return_only_outputs=True, )

    print(response)
    return response


def main():
    st.set_page_config(
        page_title="NLP Project",
        
        
    )

    with st.sidebar:
        st.title("Menu:")
        pdf_docs = st.file_uploader(
            "Upload file PDF và click Submit", accept_multiple_files=True)
        if st.button("Submit "):
            with st.spinner("Đang tải lên"):
                raw_text = extract_pdf_text(pdf_docs)
                text_chunks = split_text_into_chunks(raw_text)
                get_vector_store(text_chunks)
                st.success("Đã tải lên")

    st.title("Question Answering PDF")
    st.write("Welcome to the chat!")
    st.sidebar.button('Xóa lịch sử chat', on_click=clear_chat_history)

    if "messages" not in st.session_state.keys():
        st.session_state.messages = [
            {"role": "assistant", "content": "Upload file PDF của bạn và đặt câu hỏi"}]

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    if prompt := st.chat_input():
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.write(prompt)
            
    if st.session_state.messages[-1]["role"] != "assistant":
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                response = user_input(prompt)
                placeholder = st.empty()
                full_response = ''
                for item in response['output_text']:
                    full_response += item
                    placeholder.markdown(full_response)
                placeholder.markdown(full_response)
        if response is not None:
            message = {"role": "assistant", "content": full_response}
            st.session_state.messages.append(message)


if __name__ == "__main__":
    main()
