cd app/backend
node server.js

cd app/frontend
npm start


docker run -d \
  --name k8s-quiz-db \
  -p 5432:5432 \
  -e POSTGRES_USER=postgres \
  -e POSTGRES_PASSWORD=postgres \
  -e POSTGRES_DB=k8s_quiz \
  postgres:15-alpine# LLM-DevOps
# LLM-DevOps
