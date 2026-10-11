import asyncio
import json
import os
from crawl4ai import AsyncWebCrawler
from litellm import acompletion

OLLAMA_BASE = "http://localhost:11434"
MODEL_REASONER = "ollama/deepseek-r1:14b"
MODEL_CODER = "ollama/qwen2.5:14b"

# Official K8s Documentation URLs to scrape
LESSON_URLS = [
    {"topic": "Pods", "url": "https://kubernetes.io/docs/concepts/workloads/pods/"},
    {"topic": "Deployments", "url": "https://kubernetes.io/docs/concepts/workloads/controllers/deployment/"},
    {"topic": "Services", "url": "https://kubernetes.io/docs/concepts/services-networking/service/"},
    {"topic": "Ingress", "url": "https://kubernetes.io/docs/concepts/services-networking/ingress/"}
]

async def generate_quiz_from_markdown(topic: str, markdown_content: str):
    prompt = f"""
Analyze the following Kubernetes documentation markdown for '{topic}'.
Generate 3 challenging multiple-choice quiz questions to test a candidate's DevOps knowledge on this lesson.

Format your response as strict valid JSON only matching this schema:
[
  {{
    "question": "What is the primary function of a Pod?",
    "options": ["Option A", "Option B", "Option C", "Option D"],
    "correct_index": 0,
    "explanation": "Detailed explanation of why Option A is correct."
  }}
]

MARKDOWN CONTENT:
{markdown_content[:6000]}  # Truncated to fit context window
"""
    print(f"🧠 DeepSeek R1 14B generating quiz for: {topic}...")
    response = await acompletion(
        model=MODEL_REASONER,
        messages=[
            {"role": "system", "content": "You are a DevOps exam question creator. Output valid JSON only."},
            {"role": "user", "content": prompt}
        ],
        api_base=OLLAMA_BASE
    )
    return response.choices[0].message.content

async def main():
    os.makedirs("content", exist_ok=True)
    async with AsyncWebCrawler() as crawler:
        for lesson in LESSON_URLS:
            print(f"\n🕷️ Crawling {lesson['topic']} docs from {lesson['url']}...")
            result = await crawler.arun(url=lesson['url'])
            
            # Save raw scraped docs
            doc_file = f"content/{lesson['topic'].lower()}_doc.md"
            with open(doc_file, "w", encoding="utf-8") as f:
                f.write(result.markdown)
            print(f"✅ Saved doc to {doc_file}")

            # Generate quiz via local model
            quiz_json = await generate_quiz_from_markdown(lesson['topic'], result.markdown)
            quiz_file = f"content/{lesson['topic'].lower()}_quiz.json"
            with open(quiz_file, "w", encoding="utf-8") as f:
                f.write(quiz_json)
            print(f"✅ Saved quiz to {quiz_file}")

if __name__ == "__main__":
    asyncio.run(main())