from fastapi import FastAPI, Request
from langchain_xai import ChatXAI  # Вместо raw xai-sdk
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate  # Для system prompt
import redis, json, os, hashlib
from langchain_core.output_parsers import StrOutputParser

app = FastAPI()
llm = ChatXAI(model="grok-4-fast", xai_api_key=os.getenv("XAI_API_KEY"))  # Простая интеграция
r = redis.Redis(host='redis', port=6379, db=0)
embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
vectorstore = Qdrant(
    url=os.getenv("QDRANT_URL"), 
    collection_name="company_knowledge", 
    embeddings=embeddings
)

system_template = f"""Ты — ассистент компании {os.getenv('COMPANY_NAME')}.
Стиль: {os.getenv('CORPORATE_STYLE')}.
Используй контекст из базы для точных ответов. Для отчётов — JSON с полями: {{"title": "...", "table": [...], "insights": "..."}}. 
Для FAQ — кратко и по делу."""
prompt = ChatPromptTemplate.from_messages([("system", system_template), ("human", "{question}")])
chain = prompt | llm | StrOutputParser()  # Простая цепочка

def get_context(query: str) -> str:
    cache_key = f"rag:{hashlib.md5(query.encode()).hexdigest()}"
    cached = r.get(cache_key)
    if cached:
        return cached.decode()
    docs = vectorstore.similarity_search(query, k=5)
    context = "\n\n".join([d.page_content for d in docs])
    r.setex(cache_key, 86400, context)
    return context

@app.post("/ask")
async def ask(request: Request):
    body = await request.json()
    question = body.get("question", "")
    task_type = body.get("type", "general")

    context = get_context(question)
    # Добавляем контекст в промпт
    full_question = f"Тип задачи: {task_type}\nКонтекст: {context}\nВопрос: {question}"
    
    answer = chain.invoke({"question": full_question})
    return {"answer": answer}

# Для HTML (если добавляли)
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def root():
    with open("static/index.html") as f:  # Если есть HTML
        return f.read()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
