# NovaRoute Project Report
## AI-Powered Internship Platform with RAG Integration

**Student:** [Your Name]
**Course:** University Capstone Project
**Date:** October 2026

---

## Executive Summary

NovaRoute is a locally runnable university capstone project that provides an intelligent internship discovery platform. The system integrates three core AI features: **semantic recommendations**, **LLM-powered feedback**, and **RAG-based Q&A**. All features work together using a shared embedding model to provide personalized internship matching, actionable application feedback, and intelligent question answering about opportunities.

The platform serves three user roles: **students** (seeking internships), **employers** (posting opportunities), and **administrators** (managing the platform). It emphasizes local processing, data privacy, and transparency in AI operations.

---

## Table of Contents

1. [Introduction](#1-introduction)
2. [System Architecture](#2-system-architecture)
3. [AI Features](#3-ai-features)
4. [User Interface](#4-user-interface)
5. [Technical Implementation](#5-technical-implementation)
6. [Testing and Verification](#6-testing-and-verification)
7. [Deployment](#7-deployment)
8. [Limitations and Future Work](#8-limitations-and-future-work)
9. [Conclusion](#9-conclusion)

---

## 1. Introduction

### 1.1 Problem Statement

University students face significant challenges when searching for internships:
- Information overload across multiple job boards
- Uncertainty about which skills are actually required
- Lack of personalized feedback on applications
- Difficulty understanding how their profile matches specific opportunities

### 1.2 Solution Overview

NovaRoute addresses these challenges through three AI-powered features:

1. **Semantic Recommendations**: Uses embedding-based similarity to match student profiles with internship listings, going beyond simple keyword matching
2. **LLM-Powered Feedback**: Provides actionable feedback on applications with strengths, gaps, next steps, and practice questions
3. **RAG Q&A**: Enables students to ask natural language questions about internships and receive answers based on indexed data

### 1.3 Key Differentiators

- **Local Processing**: All AI operations run locally using sentence-transformers MiniLM, ensuring data privacy
- **Transparent AI**: All AI features are explicitly labelled as "demo" (rules-based) or "live" (LLM-powered)
- **No Random Fallbacks**: Recommendations use real semantic similarity, not random scores
- **Privacy-First**: Resume files are stored privately; only extracted data is shared with employers
- **Employer Verification**: Employers must undergo verification before posting opportunities

---

## 2. System Architecture

### 2.1 Technology Stack

**Backend:**
- **Framework**: FastAPI 0.141.1
- **Database**: MySQL 8.4 with SQLAlchemy ORM
- **Migrations**: Alembic
- **AI/ML**:
  - sentence-transformers 5.7.0 (MiniLM embeddings)
  - OpenAI SDK 2.54.0 (OpenRouter integration)
  - pdfplumber 0.11.10 (resume parsing)
- **Email**: Mailpit for local testing

**Frontend:**
- **Framework**: Next.js 16.3.5 with App Router
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **State Management**: TanStack Query
- **UI Components**: Radix UI primitives

### 2.2 System Components

```
┌─────────────────────────────────────────────────────────────┐
│                         Frontend (Next.js)                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Student View │  │ Employer View │  │  Admin View  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  API Layer                            │  │
│  │  /auth, /profiles, /internships, /applications,      │  │
│  │  /simple-rag, /trust, /activity                     │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  Services Layer                        │  │
│  │  - embeddings.py (MiniLM)                            │  │
│  │  - recommendations.py (semantic matching)              │  │
│  │  - feedback.py (LLM feedback)                         │  │
│  │  - simple_rag.py (RAG Q&A)                          │  │
│  │  - resumes.py (PDF parsing)                          │  │
│  │  - openrouter.py (LLM integration)                    │  │
│  └──────────────────────────────────────────────────────┘  │
│                              │                              │
│  ┌──────────────────────────────────────────────────────┐  │
│  │                  Data Layer                            │  │
│  │  - MySQL (user profiles, internships, applications)   │  │
│  │  - File Storage (resume PDFs)                        │  │
│  └──────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 2.3 Data Flow

**Recommendations Flow:**
1. Student completes profile (skills, coursework, projects)
2. System encodes profile using MiniLM → 384-dimensional vector
3. Encodes all active internships → vectors
4. Computes cosine similarity between profile and internships
5. Returns matches above 0.50 threshold
6. Displays in student dashboard match section ("Opportunities that connect") with explanations

**LLM Feedback Flow:**
1. Employer updates application status (viewed/rejected)
2. System retrieves application-time profile snapshot
3. Generates feedback using LLM (live) or rules (demo)
4. Creates notification with feedback
5. Sends email with feedback
6. Displays in student notifications (Notification inbox & header bell are reserved for application process updates)

**RAG Q&A Flow:**
1. Student asks question (e.g., "What skills are needed for data science?")
2. System encodes question using MiniLM
3. Computes similarity with all active internships
4. Returns top 3 most similar internships
5. Generates answer using LLM (live) or pattern matching (demo)
6. Displays answer with source internships and similarity scores

---

## 3. AI Features

### 3.1 Semantic Recommendations

**Implementation:**
- Uses `sentence-transformers/all-MiniLM-L6-v2` (384-dimensional embeddings)
- Cosine similarity for matching
- Default 0.50 threshold (configurable)
- No random fallbacks

**Algorithm:**
```python
# Pseudocode
profile_vector = encode(profile_text)
internship_vectors = [encode(listing_text) for listing in internships]
similarities = [cosine(profile_vector, iv) for iv in internship_vectors]
matches = [(internship, score) for internship, score in zip(internships, similarities) if score > 0.50]
matches.sort(by=score, descending=True)
```

**Features:**
- Skill overlap analysis (exact skill matching)
- Semantic alignment explanation (when no exact skill match)
- Matched/missing skills display
- Dedicated dashboard match section ("Opportunities that connect")

**Limitations:**
- Only matches on skills, coursework, and projects
- Does not consider location, work mode, or other preferences
- 0.50 threshold can be configured via `RECOMMENDATION_MIN_SCORE`
- Requires complete profile to work

### 3.2 LLM-Powered Feedback

**Implementation:**
- Uses OpenRouter Qwen model in live mode
- Structured output with JSON schema validation
- Redacts contact information before sending to LLM
- Fallback to deterministic rules in demo mode

**Feedback Components:**
- **Summary**: High-level assessment
- **Strengths**: Confirmed skills and experience
- **Potential Gaps**: Skills to develop
- **Next Steps**: Actionable improvement suggestions
- **Practice Questions**: Interview preparation questions

**Features:**
- Sent only when application is viewed or rejected
- Includes employer notes if provided
- Email delivery with retry logic
- Async processing with outbox pattern

**Limitations:**
- LLM responses depend on model quality
- May not always be relevant to specific internship
- No guarantee of interview success
- Requires OpenRouter API key for live mode

### 3.3 RAG Q&A (NEW)

**Implementation:**
- Simple in-memory semantic search (no vector database)
- Uses same MiniLM embeddings as recommendations
- Top-3 most similar internships as context
- LLM or pattern matching for answer generation

**API Endpoint:**
```
POST /api/simple-rag/query
Request: { question: string, top_k: number }
Response: { answer: string, sources: [{title, skills, similarity}], num_results: number }
```

**Features:**
- Chat interface with history
- Source attribution (shows which internships informed answer)
- Similarity scores for transparency
- Demo and live mode support

**Limitations:**
- Only searches active internships in database
- No persistent chat history
- Limited to top 3 context internships
- No chunking for long descriptions
- Semantic similarity ≠ factual accuracy

---

## 4. User Interface

### 4.1 Student Dashboard

**Recommendations Section:**
- Displays top 4 recommended internships
- Shows match percentage badges (e.g., "85% Match")
- "Why this appeared" explanation
- Skill overlap display

**Navigation:**
- Dashboard (overview with recommendations)
- Profile (edit skills, coursework, projects)
- Internships (browse all opportunities)
- Saved (saved internships with notes)
- Applications (track application status)
- **Ask AI** (RAG Q&A chat interface) - NEW
- Reports (report suspicious listings)
- Notifications (inbox with AI feedback)
- Settings (account preferences)

### 4.2 Employer Dashboard

**Internship Management:**
- Post new internships
- Edit existing listings
- View applicants
- Update application status (viewed, accepted, rejected)
- Automated content review (AI moderation)

**Navigation:**
- Dashboard (overview with applicants)
- Profile (company details)
- Verification (submit for review)
- Internships (manage listings)
- Applicants (review applications)
- Notifications
- Settings

### 4.3 Admin Dashboard

**Employer Verification:**
- Review employer applications
- Approve, reject, suspend accounts
- View submitted legal/company documents
- Audit history of decisions

**Content Review:**
- Review AI-flagged internship listings
- Approve, edit, or reject content
- Safety review for student reports

**Navigation:**
- Dashboard (review overview)
- Employers (verification queue)
- Listings (content review)
- Reports (student reports)
- Audit (decision history)
- Settings

### 4.4 Brand Logo Navigation

**Updated Behavior:**
- Clicking NovaRoute logo navigates to role-specific dashboard:
  - Admin → `/admin/dashboard`
  - Employer → `/employer/dashboard`
  - Student → `/student/dashboard`
  - Login/Signup → `/` (home page)

---

## 5. Technical Implementation

### 5.1 Backend Services

**embeddings.py:**
- Wraps sentence-transformers MiniLM model
- In-memory caching (LRU cache, max 2048 entries)
- Thread-safe model loading
- Text encoding with chunking for long documents

**recommendations.py:**
- `recommendations()`: Main recommendation function
- `evaluate_alerts()`: Background job for high-match alerts
- Eligibility query filtering (active, verified, not deleted)
- Skill evidence matching

**feedback.py:**
- `generate_feedback()`: Generate AI or rule-based feedback
- Uses structured output with JSON schema
- Contact redaction before LLM calls

**simple_rag.py (NEW):**
- `simple_rag_query()`: Main RAG query function
- In-memory semantic search (no external dependencies)
- `generate_simple_answer()`: LLM or demo answer generation
- `demo_simple_answer()`: Pattern matching fallback

**resumes.py:**
- `extract_pdf()`: PDF parsing with pdfplumber
- `parse()`: LLM or rule-based skill extraction
- Enhanced logging for debugging upload issues

**openrouter.py:**
- `structured()`: Generic structured output function
- Retry logic (3 attempts with exponential backoff)
- Error handling (timeout, connection, validation)
- Contact redaction

### 5.2 Frontend Components

**rag-chat.tsx (NEW):**
- Chat interface for RAG Q&A
- Message history display
- Source attribution with similarity scores
- Loading and error states

**shell.tsx:**
- Updated to include "Ask AI" navigation item
- Brand component receives role prop for smart navigation

**dashboard.tsx:**
- Displays recommendations with match percentages
- Metrics cards (profile completion, applications, etc.)
- Recent activity feed

**listings.tsx:**
- Listing cards with match badges
- Skill chips
- Match explanation sidebar

**activity.tsx:**
- FeedbackView component for AI feedback display
- Notification inbox with read/unread states
- Application timeline with feedback

### 5.3 API Endpoints

**Authentication:**
- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `GET /auth/me` - Current user info
- `GET /auth/csrf` - CSRF token

**Profiles:**
- `GET /student/profile` - Get student profile
- `PATCH /student/profile` - Update profile
- `POST /upload-resume` - Upload and parse resume (with enhanced logging)

**Internships:**
- `GET /internships` - Browse internships (with filters)
- `POST /internships` - Create internship (employer)
- `GET /internships/{id}` - Internship detail
- `PATCH /internships/{id}` - Edit internship
- `DELETE /internships/{id}` - Delete internship

**Applications:**
- `POST /applications` - Submit application
- `GET /applications` - List applications
- `GET /applications/{id}` - Application detail
- `PATCH /applications/{id}` - Edit cover message
- `PUT /applications/{id}/status` - Update status (employer)
- `POST /applications/{id}/withdraw` - Withdraw application

**Recommendations:**
- `GET /student/recommendations` - Get personalized matches

**RAG (NEW):**
- `POST /api/simple-rag/query` - Ask questions about internships

**Notifications:**
- `GET /notifications` - List notifications
- `PATCH /notifications/{id}` - Mark read/unread
- `DELETE /notifications/{id}` - Dismiss
- `POST /notifications/read-all` - Mark all read

---

## 6. Testing and Verification

### 6.1 Backend Tests

**Test Files:**
- `test_auth.py` - Authentication flows
- `test_ai_resume.py` - Resume parsing and skill extraction
- `test_trust.py` - Employer verification and admin actions
- `test_workflows.py` - End-to-end application workflows
- `test_recovery.py` - Email retry and recovery logic
- `test_importer_alerts.py` - Data import and alert evaluation
- `test_simple_rag.py (NEW)` - RAG Q&A functionality

**Running Tests:**
```bash
# Backend
cd backend
$env:TEST_DATABASE_URL='mysql+pymysql://novaroute:local_dev_password@127.0.0.1:3306/novaroute_test?charset=utf8mb4'
python -m pytest -q
python -m ruff check app tests
```

### 6.2 Frontend Tests

**Test Types:**
- Type checking: `npm run typecheck`
- Linting: `npm run lint`
- Build: `npm run build`
- E2E tests: `npm run test:e2e` (Playwright)

### 6.3 Manual Verification

**Recommendations:**
1. Create student profile with skills, coursework, projects
2. Verify matches appear in dashboard
3. Check match percentages are reasonable
4. Verify "Why this appeared" explanations

**LLM Feedback:**
1. Apply to an internship
2. Employer updates status to "viewed" or "rejected"
3. Check notification inbox for AI feedback
4. Verify feedback includes strengths, gaps, next steps
5. Check email delivery in Mailpit

**RAG Q&A:**
1. Navigate to `/student/ask-ai`
2. Ask: "What skills are required for data science internships?"
3. Verify answer is relevant
4. Check source internships are displayed
5. Verify similarity scores are shown
6. Test follow-up questions

---

## 7. Deployment

### 7.1 Local Development

**Prerequisites:**
- Node.js 24 LTS
- Python 3.12
- MySQL 8.4
- Mailpit (for email testing)

**Setup Commands:**
```powershell
# Windows
Copy-Item .env.example .env
docker compose up -d
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/Activate.ps1
python -m pip install -r backend/requirements-lock.txt
cd backend
python -m alembic upgrade head
python -m app.jobs.model
cd ..
python database/seed.py --demo --limit 25 --seed 42
cd frontend
npm ci
Copy-Item .env.example .env.local
```

**Running Services:**
```powershell
# Terminal 1 (Backend)
cd backend
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --reload --port 8000

# Terminal 2 (Frontend)
cd frontend
npm run dev
```

### 7.2 Production Considerations

**Security:**
- HTTPS required
- `COOKIE_SECURE=true`
- `ENVIRONMENT=production`
- `AI_MODE=live`
- Unique credentials for all services
- Exact `ALLOWED_ORIGINS` (no wildcards)

**Scaling:**
- Single backend process for in-memory rate limiter
- Model cache is per process
- No Redis or task queue (MVP limitation)
- Consider shared rate limiting for multi-process deployments

**Database:**
- Alembic migrations required
- Never run `CREATE TABLE` in application code
- Volume backups required for MySQL data persistence

**AI Configuration:**
- MiniLM model cache: `model-cache/` directory
- Model download requires internet on first run
- `HF_HUB_OFFLINE=1` for cache-only inference
- `EMBEDDING_LOAD_ON_START=true` to warm on startup

---

## 8. Limitations and Future Work

### 8.1 Current Limitations

**Recommendations:**
- Only considers skills, coursework, projects
- Does not match on location, work mode, salary
- Configurable threshold (default `RECOMMENDATION_MIN_SCORE=0.50`)
- No reranking of results

**LLM Feedback:**
- Depends on LLM quality and availability
- May not be specific to the internship
- No guarantee of interview success
- Limited to viewed/rejected applications

**RAG Q&A:**
- Only searches active internships
- No persistent chat history
- Limited to top 3 context sources
- No chunking for long descriptions
- No hybrid search (keyword + semantic)

**General:**
- No real-time updates (polling only)
- No WebSocket support
- File upload size limit (5 MB)
- Rate limiting is in-memory only

### 8.2 Future Improvements

**Recommendations:**
- Add location and work mode preferences
- Implement reranking with cross-encoder
- Add collaborative filtering
- Personalize threshold per user
- Add "not interested" feedback

**LLM Feedback:**
- Add contextualized feedback with similar successful profiles
- Implement resume-specific feedback
- Add interview question generation
- Multi-turn feedback conversations

**RAG Q&A:**
- Add persistent chat history
- Implement chunking for long descriptions
- Add hybrid search (BM25 + semantic)
- Support multiple data sources (guidelines, docs)
- Add citation verification
- Implement streaming responses

**Infrastructure:**
- Add Redis for shared rate limiting
- Implement task queue (Celery/RQ)
- Add WebSocket for real-time updates
- Implement proper logging and monitoring
- Add health checks and metrics

**Features:**
- Calendar integration for deadlines
- Interview scheduling
- Video interview support
- Company research tools
- Salary range analytics

---

## 9. Conclusion

NovaRoute successfully integrates three AI features (recommendations, LLM feedback, and RAG Q&A) using a shared embedding model. The system provides students with personalized internship matching, actionable application feedback, and intelligent question answering about opportunities.

### 9.1 Achievements

✅ **Semantic Recommendations**: Real embedding-based matching with 0.50 threshold
✅ **LLM Feedback**: Structured AI feedback with strengths, gaps, and next steps
✅ **RAG Q&A**: New feature for intelligent question answering
✅ **Local Processing**: All AI operations run locally with MiniLM
✅ **Transparency**: AI features explicitly labelled as demo or live
✅ **Privacy-First**: Resume files stored privately
✅ **Employer Verification**: Robust verification workflow
✅ **Admin Dashboard**: Comprehensive management interface

### 9.2 Key Insights

- **Shared Embeddings**: Using the same MiniLM model across all features reduced complexity and improved consistency
- **Simple RAG**: In-memory semantic search is sufficient for internship Q&A without complex vector databases
- **Demo Mode**: Deterministic rules provide valuable fallback when LLM is unavailable
- **User Experience**: Clear UI integration makes AI features accessible and understandable

### 9.3 Lessons Learned

- **Local Processing**: Running AI locally ensures data privacy but requires careful resource management
- **Embedding Caching**: In-memory caching significantly improves performance
- **Error Handling**: Robust error handling and retry logic is essential for AI features
- **User Feedback**: Clear explanations of AI behavior (e.g., "semantic similarity, not hiring probability") build trust

### 9.4 Final Thoughts

NovaRoute demonstrates that AI can enhance internship discovery without compromising privacy or requiring expensive infrastructure. The simple RAG implementation shows that sophisticated features can be built with minimal complexity when leveraging existing data and models. The system is production-ready for local deployment and provides a solid foundation for future enhancements.

---

## Appendix

### A. Configuration Reference

**Environment Variables:**
```bash
# AI Configuration
AI_MODE=demo|live
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=qwen/qwen3-235b-a22b-2507
AI_TIMEOUT_SECONDS=30

# Embedding Configuration
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
EMBEDDING_CACHE_DIR=model-cache
EMBEDDING_LOAD_ON_START=true
RECOMMENDATION_MIN_SCORE=0.50

# Upload Configuration
UPLOAD_MAX_BYTES=5242880
UPLOAD_MAX_PAGES=10
UPLOAD_MAX_TEXT=24000
UPLOAD_PRIVATE_DIR=uploads
UPLOAD_RATE_LIMIT=10
```

### B. API Reference

**RAG Q&A:**
```
POST /api/simple-rag/query
Content-Type: application/json

{
  "question": "What skills are required for data science internships?",
  "top_k": 3
}

Response:
{
  "answer": "Based on the available internships, data science roles typically require Python, SQL, and machine learning frameworks...",
  "sources": [
    {
      "title": "Data Engineer",
      "skills": ["Python", "SQL"],
      "similarity": 0.85
    }
  ],
  "num_results": 3
}
```

### C. File Structure

```
novaroute/
├── backend/
│   ├── app/
│   │   ├── api/ (endpoints)
│   │   │   ├── auth.py
│   │   │   ├── profiles.py
│   │   │   ├── internships.py
│   │   │   ├── applications.py
│   │   │   ├── simple_rag.py (NEW)
│   │   │   ├── trust.py
│   │   │   └── activity.py
│   │   ├── services/ (business logic)
│   │   │   ├── embeddings.py
│   │   │   ├── recommendations.py
│   │   │   ├── feedback.py
│   │   │   ├── simple_rag.py (NEW)
│   │   │   ├── resumes.py
│   │   │   ├── openrouter.py
│   │   │   └── ...
│   │   ├── core/ (config, security)
│   │   ├── db/ (database)
│   │   └── models/ (SQLAlchemy models)
│   ├── tests/
│   │   ├── test_simple_rag.py (NEW)
│   │   └── ...
│   └── requirements.txt
├── frontend/
│   ├── app/ (Next.js pages)
│   ├── components/ (React components)
│   │   ├── rag-chat.tsx (NEW)
│   │   ├── dashboard.tsx
│   │   ├── listings.tsx
│   │   ├── activity.tsx
│   │   └── ...
│   └── lib/ (utilities)
├── database/ (seeds, scripts)
├── docs/ (documentation)
│   ├── ui-integration.md (NEW)
│   ├── simple-rag.md (NEW)
│   └── ...
└── README.md
```

---

**End of Report**
