from fastapi import FastAPI, Request
from openai import OpenAI  # Совместимо с xAI (base_url="https://api.x.ai/v1")
from langchain_community.vectorstores import Qdrant
from langchain_community.embeddings import HuggingFaceEmbeddings
import redis, json, os, hashlib

app = FastAPI()
client = OpenAI(api_key=os.getenv("XAI_API_KEY"), base_url="https://api.x.ai/v1")
r = redis.Redis(host='redis', port=6379, db=0)
embeddings = HuggingFaceEmbeddings(model_name="intfloat/multilingual-e5-large")
vectorstore = Qdrant(
    url=os.getenv("QDRANT_URL"), 
    collection_name="company_knowledge", 
    embeddings=embeddings
)

SYSTEM_PROMPT = f"""Ты — ассистент компании {os.getenv('COMPANY_NAME')}.
Стиль: {os.getenv('CORPORATE_STYLE')}.
Используй контекст из базы для точных ответов. Для отчётов — JSON с полями: {{"title": "...", "table": [...], "insights": "..."}}. 
Для FAQ — кратко и по делу."""

def get_context(query: str) -> str:
    cache_key = f"rag:{hashlib.md5(query.encode()).hexdigest()}"
    cached = r.get(cache_key)
    if cached:
        return cached.decode()
    docs = vectorstore.similarity_search(query, k=5)
    context = "\n\n".join([d.page_content for d in docs])
    r.setex(cache_key, 86400, context)  # Кэш на 24 часа
    return context

@app.post("/ask")
async def ask(request: Request):
    body = await request.json()
    question = body.get("question", "")
    task_type = body.get("type", "general")  # "faq", "report", "autoreply"

    context = get_context(question)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT + f"\nТип задачи: {task_type}\nКонтекст: {context}"},
        {"role": "user", "content": question}
    ]

    response = client.chat.completions.create(
        model="grok-4-fast",
        messages=messages,
        max_tokens=2000 if task_type == "report" else 500,
        temperature=0.2 if task_type != "autoreply" else 0.7
    )
    return {"answer": response.choices[0].message.content}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
