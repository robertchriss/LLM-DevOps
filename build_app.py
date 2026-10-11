import os
from crewai import Agent, Task, Crew, LLM
from crewai_tools import FileWriterTool, DirectoryReadTool

# 1. Point CrewAI to your local qwen2.5:32b model running in Ollama
local_llm = LLM(
    model="ollama/qwen2.5:32b",
    base_url="http://localhost:11434"
)

# 2. File writing tools
file_writer = FileWriterTool()
dir_reader = DirectoryReadTool()

# 3. Define the Developer Agent
app_builder = Agent(
    role="Senior Fullstack & DevOps Engineer",
    goal="Write code files and manifests directly to the file system",
    backstory="You write clean production code and write files directly to disk.",
    tools=[file_writer, dir_reader],
    llm=local_llm,
    verbose=True
)

# 4. Define tasks to write actual files
task_package_json = Task(
    description="Create 'app/package.json' for a Node.js Express server with pg and typescript dependencies.",
    expected_output="File app/package.json created on disk.",
    agent=app_builder
)

task_server = Task(
    description="Create 'app/server.js' containing an Express server with a GET /healthz endpoint and GET /api/lessons endpoint.",
    expected_output="File app/server.js created on disk.",
    agent=app_builder
)

task_dockerfile = Task(
    description="Create 'app/Dockerfile' with a multi-stage Node.js build.",
    expected_output="File app/Dockerfile created on disk.",
    agent=app_builder
)

# 5. Run execution
if __name__ == "__main__":
    os.makedirs("app", exist_ok=True)
    crew = Crew(
        agents=[app_builder],
        tasks=[task_package_json, task_server, task_dockerfile],
        verbose=True
    )
    crew.kickoff()
    print("✅ Application files created inside 'app/' folder!")