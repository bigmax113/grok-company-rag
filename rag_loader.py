import os
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Qdrant
from qdrant_client import QdrantClient

# Установка: pip install langchain-community sentence-transformers qdrant-client python-docx pypdf

loaders = {
    ".pdf": PyPDFLoader,
    ".docx": Docx2txtLoader,
    ".txt": TextLoader,
}
docs = []
for file in os.listdir("data/") if os.path.exists("data/") else []:
    ext = os.path.splitext(file)[1].lower()
    if ext in loaders:
        loader = loaders[ext](f"data/{file}")
        docs.extend(loader.load())

splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
chunks = splitter.split_documents(docs)

embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
client = QdrantClient(url="http://localhost:6333")
vectorstore = Qdrant.from_documents(
    chunks, embeddings, client=client, collection_name="company_knowledge"
)
print(f"Загружено {len(chunks)} фрагментов в векторную базу.")
