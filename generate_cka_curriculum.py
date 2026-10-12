import re
import json
import requests
import subprocess

# Query Ollama directly for fast batch generation
OLLAMA_URL = "http://localhost:11434/api/generate"

CKA_TOPICS = [
    {"domain": "Workloads", "topic": "Pods & Multi-Container Pods", "slug": "pods-and-containers"},
    {"domain": "Workloads", "topic": "Deployments & Rollouts", "slug": "deployments-and-rollouts"},
    {"domain": "Workloads", "topic": "StatefulSets & DaemonSets", "slug": "statefulsets-daemonsets"},
    {"domain": "Networking", "topic": "Services (ClusterIP, NodePort, LoadBalancer)", "slug": "kubernetes-services"},
    {"domain": "Networking", "topic": "Ingress Routing & Ingress Controllers", "slug": "ingress-routing"},
    {"domain": "Networking", "topic": "NetworkPolicies & Pod Security", "slug": "network-policies"},
    {"domain": "Storage", "topic": "PersistentVolumes, PVCs & StorageClasses", "slug": "pv-pvc-storageclasses"},
    {"domain": "Cluster Setup", "topic": "RBAC Roles, RoleBindings, ServiceAccounts", "slug": "rbac-security"},
    {"domain": "Cluster Setup", "topic": "ETCD Backup and Restore", "slug": "etcd-backup-restore"},
    {"domain": "Troubleshooting", "topic": "Debugging Pods, Kubelet, & Control Plane", "slug": "k8s-troubleshooting"}
]

def clean_sql(text: str) -> str:
    """Extract raw SQL content inside markdown backticks."""
    match = re.search(r"```(?:sql)?\n(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    return text.replace("```sql", "").replace("```", "").strip()

def generate_and_seed():
    for item in CKA_TOPICS:
        print(f"🚀 Generating CKA Lesson: {item['topic']}...")
        
        prompt = f"""
Act as a world-class DevOps instructor preparing a student for the CKA exam.
Generate a concise, friendly lesson and 2 quiz questions for topic: "{item['topic']}".

OUTPUT FORMAT REQUIREMENTS:
Return ONLY valid PostgreSQL INSERT statements. Do NOT write markdown prose outside code blocks.

Format:
INSERT INTO lessons (slug, title, content) VALUES ('{item['slug']}', '{item['topic']}', 'Markdown lesson content here') ON CONFLICT (slug) DO NOTHING;
INSERT INTO quizzes (lesson_id, question, options, correct_index, explanation) VALUES 
  ((SELECT id FROM lessons WHERE slug='{item['slug']}'), 'Question 1 text', '["Option A", "Option B", "Option C", "Option D"]'::jsonb, 0, 'Explanation text'),
  ((SELECT id FROM lessons WHERE slug='{item['slug']}'), 'Question 2 text', '["Option A", "Option B", "Option C", "Option D"]'::jsonb, 1, 'Explanation text');
"""

        try:
            res = requests.post(
                OLLAMA_URL,
                json={
                    "model": "qwen2.5:32b",
                    "prompt": prompt,
                    "stream": False
                },
                timeout=600
            )
            res_data = res.json()
            raw_text = res_data.get("response", "")
            sql_code = clean_sql(raw_text)

            # Save temporary batch SQL file
            tmp_sql = "tmp_batch.sql"
            with open(tmp_sql, "w", encoding="utf-8") as f:
                f.write(sql_code)

            # Execute directly against PostgreSQL container
            cmd = f"docker exec -i k8s-quiz-db psql -U postgres -d quizdb < {tmp_sql}"
            subprocess.run(cmd, shell=True, check=True)
            print(f"✅ Successfully seeded: {item['topic']}\n")

        except Exception as e:
            print(f"❌ Failed to process {item['topic']}: {e}\n")

if __name__ == "__main__":
    generate_and_seed()