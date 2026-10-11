-- Create the lessons table
CREATE TABLE lessons (
    id SERIAL PRIMARY KEY,
    slug VARCHAR UNIQUE NOT NULL,
    title VARCHAR NOT NULL,
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Create the quizzes table with a foreign key reference to lessons
CREATE TABLE quizzes (
    id SERIAL PRIMARY KEY,
    lesson_id INT REFERENCES lessons(id) ON DELETE CASCADE,
    question TEXT NOT NULL,
    options JSONB NOT NULL,
    correct_index INT NOT NULL,
    explanation TEXT NOT NULL
);

-- Create the user_scores table with a foreign key reference to lessons
CREATE TABLE user_scores (
    id SERIAL PRIMARY KEY,
    username VARCHAR NOT NULL,
    lesson_id INT REFERENCES lessons(id) ON DELETE CASCADE,
    score INT NOT NULL,
    total INT NOT NULL,
    submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Add indexes on 'slug' in lessons table and 'lesson_id' in quizzes table
CREATE INDEX idx_lessons_slug ON lessons(slug);
CREATE INDEX idx_quizzes_lesson_id ON quizzes(lesson_id);

-- Insert seed data into 'lessons' and 'quizzes' for 'Pods' and 'Deployments'
INSERT INTO lessons (slug, title, content) VALUES
('k8s-pods', 'Understanding Pods', 'A pod is the smallest deployable unit in Kubernetes...'),
('k8s-deployments', 'Managing Deployments', 'A deployment is a Kubernetes resource that manages a set of pods...');

INSERT INTO quizzes (lesson_id, question, options, correct_index, explanation) VALUES
(1, 'What is a Pod?', '[{"option": "A group of containers"}, {"option": "A single container"}, {"option": "A network interface"}, {"option": "A storage volume"}]', 0, 'A pod is a single instance of a container...'),
(1, 'Which of the following is NOT a Pod IP?', '[{"option": "10.0.0.1"}, {"option": "10.0.0.2"}, {"option": "10.0.0.3"}, {"option": "127.0.0.1"}]', 3, '127.0.0.1 is the loopback address...'),
(1, 'What is Pod Restart Policy?', '[{"option": "Always"}, {"option": "OnFailure"}, {"option": "Never"}, {"option": "Recreate"}]', 1, 'OnFailure restarts the pod if it fails...'),
(2, 'What does Deployment manage?', '[{"option": "Pods"}, {"option": "Services"}, {"option": "Volumes"}, {"option": "Nodes"}]', 0, 'Deployment manages pods in a replicated...'),
(2, 'What is Deployment Rolling Update?', '[{"option": "Update all pods at once"}, {"option": "Update pods one by one"}, {"option": "Update pods two by two"}, {"option": "Update pods based on availability"}]', 1, 'Rolling update replaces old pods...'),
(2, 'What is the default Deployment Replica Count?', '[{"option": "1"}, {"option": "2"}, {"option": "3"}, {"option": "5"}]', 0, 'The default replica count is 1...');