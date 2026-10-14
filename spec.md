# 3-Tier CKA Learning Platform Specification

## 1. Database Layer (PostgreSQL - `quizdb`)
- **Table `lessons`**: `id`, `slug`, `title`, `content`.
- **Table `quizzes`**: `id`, `lesson_id`, `question`, `options` (JSONB Array), `correct_index`, `explanation`.

## 2. Backend Layer (Express - Port 5000)
- `GET /api/lessons`: Returns all lessons.
- `GET /api/lessons/:slug`: Returns single lesson with quizzes.

## 3. Frontend Layer (React - Port 3000)
- Sidebar navigation for CKA domains.
- Main area for Markdown lesson rendering.
- Interactive multiple-choice Quiz component.

## 4. Autonomous Validation Rules (Agent Instructions)
If you are tasked with building or fixing this application, your `[STATUS: FINISHED]` condition is ONLY met when Playwright confirms all of the following:
1. `http://localhost:3000` loads without compiling errors (e.g., no JSX adjacent element errors).
2. The "Take Quiz" button renders successfully.
3. Clicking the quiz button displays the JSONB options fetched from the backend without triggering `.map() undefined` runtime crashes.
If any of these fail, you are required to transition to `[STATUS: RETRYING]` and fix the codebase.