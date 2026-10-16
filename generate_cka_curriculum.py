import httpx
import json
import re
import psycopg2
from bs4 import BeautifulSoup

OLLAMA_URL = "http://localhost:11434/api/chat"
MODEL = "qwen2.5:32b"

# Target Kubernetes concept pages for CKA
K8S_DOC_URLS = [
    {"slug": "k8s-pods", "url": "https://kubernetes.io/docs/concepts/workloads/pods/"},
    {"slug": "k8s-deployments", "url": "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/"},
    {"slug": "k8s-services", "url": "https://kubernetes.io/docs/concepts/services-networking/service/"},
    {"slug": "k8s-pv-pvc", "url": "https://kubernetes.io/docs/concepts/storage/persistent-volumes/"}
]

# PostgreSQL Connection settings
DB_CONFIG = {
    "dbname": "quizdb",
    "user": "postgres",
    "password": "postgres", # adjust if needed
    "host": "localhost",
    "port": "5432"
}

def fetch_and_clean_doc(url: str) -> str:
    """Fetch Kubernetes doc page and strip HTML tags/navbars."""
    print(f"🌐 Fetching {url}...")
    resp = httpx.get(url, follow_redirects=True, timeout=15.0)
    soup = BeautifulSoup(resp.text, "html.parser")
    
    main_content = soup.find("main") or soup.find("article") or soup.body
    text = main_content.get_text(separator="\n", strip=True) if main_content else ""
    return text[:4000]  # Limit to first 4000 chars for LLM context window

def generate_lesson_and_quizzes(slug: str, doc_text: str) -> dict:
    """Prompt Ollama to extract structured CKA lesson and quizzes."""
    prompt = f"""
    You are a CKA (Certified Kubernetes Administrator) Exam Instructor.
    Based on this documentation text, create a lesson summary and 3 multiple-choice quiz questions.

    DOCUMENTATION:
    {doc_text}

    OUTPUT FORMAT: You MUST return strictly valid JSON with no markdown formatting outside of JSON.
    {{
      "title": "Lesson Title",
      "content": "A detailed 2-paragraph CKA lesson summary.",
      "quizzes": [
        {{
          "question": "Clear exam-style question?",
          "options": ["Option A", "Option B", "Option C", "Option D"],
          "correct_index": 0,
          "explanation": "Why Option A is correct."
        }}
      ]
    }}
    """
    
    print(f"🤖 Generating lesson & quiz for {slug} using {MODEL}...")
    res = httpx.post(
        OLLAMA_URL, 
        json={
            "model": MODEL, 
            "messages": [{"role": "user", "content": prompt}],
            "format": "json",
            "stream": False
        }, 
        timeout=180.0
    )
    
    return json.loads(res.json()["message"]["content"])

def seed_database(lessons_data):
    """Insert generated lessons and quizzes into PostgreSQL."""
    conn = psycopg2.connect(**DB_CONFIG)
    cur = conn.cursor()
    
    for item in lessons_data:
        slug = item["slug"]
        data = item["data"]
        
        # 1. Upsert Lesson
        cur.execute("""
            INSERT INTO lessons (slug, title, content)
            VALUES (%s, %s, %s)
            ON CONFLICT (slug) DO UPDATE SET title = EXCLUDED.title, content = EXCLUDED.content
            RETURNING id;
        """, (slug, data["title"], data["content"]))
        lesson_id = cur.fetchone()[0]
        
        # 2. Insert Quizzes
        for q in data.get("quizzes", []):
            cur.execute("""
                INSERT INTO quizzes (lesson_id, question, options, correct_index, explanation)
                VALUES (%s, %s, %s, %s, %s);
            """, (
                lesson_id, 
                q["question"], 
                json.dumps(q["options"]), 
                q["correct_index"], 
                q["explanation"]
            ))
            
    conn.commit()
    cur.close()
    conn.close()
    print("✅ Database successfully updated with fresh CKA content!")

if __name__ == "__main__":
    generated_results = []
    for doc in K8S_DOC_URLS:
        try:
            raw_text = fetch_and_clean_doc(doc["url"])
            data = generate_lesson_and_quizzes(doc["slug"], raw_text)
            generated_results.append({"slug": doc["slug"], "data": data})
        except Exception as e:
            print(f"⚠️ Error processing {doc['slug']}: {e}")
            
    if generated_results:
        seed_database(generated_results)