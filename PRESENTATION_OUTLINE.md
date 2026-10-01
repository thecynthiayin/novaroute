# NovaRoute Presentation Outline
## CSC 357 - AI Capstone Final Project
### Han Su Yin (2306090004)

---

## Slide 1: Title Slide
**Title:** NovaRoute: An Intelligent Internship Recommendation and Feedback Platform
**Subtitle:** AI Capstone Final Project
**Student:** Han Su Yin (2306090004)
**Course:** CSC 357 - AI Capstone
**Date:** October 2026

---

## Slide 2: Problem Statement
**University students face three key challenges:**

1. **High data entry friction** - Manually converting resume information into structured profiles is time-consuming and error-prone
2. **Generic keyword-based matching** - Traditional job boards miss semantic matches between student profiles and internship requirements
3. **Lack of actionable feedback** - Students receive minimal information when applications are rejected, hindering improvement

**Target Users:**
- University students seeking technical internships (software engineering, databases, data science)
- Employers offering entry-level technical opportunities
- Administrators responsible for verification and content moderation

---

## Slide 3: Proposed AI Solution
**Hybrid Recommendation + LLM Methodology:**

1. **Generative AI (LLM via OpenRouter / Qwen API)**
   - Parses raw PDF resumes into structured JSON
   - Generates contextual feedback for viewed/rejected applications
   - Example: Suggests highlighting secure PDO-driven SQL queries or expanding React frontend skills

2. **Recommendation System**
   - Employs vector embeddings (sentence-transformers / MiniLM)
   - Calculates cosine similarity between student profiles and internship requirements
   - Scores alignment based on coursework, projects, and skills

---

## Slide 4: Research Inspiration
**Primary Research Paper:**
- "Smart-Hiring: An Explainable end-to-end Pipeline for CV Information Extraction and Candidate Matching" (arXiv:2511.02537)

**How NovaRoute Differs:**
- **Simplified extraction:** Uses generative LLM (Qwen) for direct PDF-to-JSON parsing instead of multi-stage supervised classifiers
- **Focused scope:** Exclusively targets university internships rather than general hiring
- **Unique feedback loop:** Introduces automated email notification for post-application feedback (absent in original research)
- **Bachelor-level scope:** Appropriate complexity for capstone project timeframe

---

## Slide 5: System Architecture
**Technology Stack:**

**Frontend:**
- Next.js 15 with App Router
- React with TypeScript
- TanStack Query for data fetching
- Tailwind CSS for styling

**Backend:**
- Python 3.12 with FastAPI
- SQLAlchemy ORM with Alembic migrations
- MySQL 8.4 database
- Pydantic for validation

**AI Components:**
- sentence-transformers (MiniLM embeddings)
- OpenRouter client for LLM API (Qwen)
- pdfplumber for PDF text extraction

**Infrastructure:**
- Docker Compose for MySQL and Mailpit
- Native installation support for Windows, macOS, Linux

---

## Slide 6: Key Features
**For Students:**
- Secure authentication with session management
- Profile creation with manual entry OR AI-assisted resume extraction
- Semantic recommendation system with configurable thresholds
- Application workflow with status tracking and history
- Automated feedback generation for viewed/rejected applications
- Email notifications with durable outbox and retry logic
- Saved internships with private notes

**For Employers:**
- Employer profiles with verification workflow
- Internship listing creation with AI content moderation
- Application review with status changes and notes
- View student profiles and application-time snapshots

**For Administrators:**
- Employer verification and approval/rejection
- Content moderation review
- Student safety report investigation
- Audit trail of all administrative decisions

---

## Slide 7: AI Component 1 - Resume Extraction
**Pipeline:**
1. User uploads PDF (max 5MB, 10 pages, 24,000 characters)
2. pdfplumber extracts searchable text
3. PDF signature checked for corruption
4. In demo mode: Deterministic extraction using vocabulary matching
5. In live mode: Text redacted (email/phone/links), sent to Qwen with structured output schema
6. Student reviews and confirms extracted fields before merging into profile

**Benefits:**
- Reduces manual data entry time
- Ensures structured, consistent profiles
- Maintains privacy (PDFs stored privately with randomized names)

---

## Slide 8: AI Component 2 - Recommendation System
**Pipeline:**
1. Profile/listing edits trigger re-evaluation
2. Text normalized: skills (2x weight), coursework, projects
3. Long text chunked deterministically (max 16 chunks)
4. Each chunk encoded with MiniLM, vectors averaged with first-chunk weighting
5. Aggregate vector normalized and cached by content SHA-256
6. Cosine similarity computed against all active listings
7. Filtered by threshold (>0.80), exclude closed/flagged/expired/previous applications
8. Results ranked by score, then listing ID for deterministic ties

**Advantages:**
- Captures semantic meaning beyond keywords
- Deterministic behavior for reproducible demos
- Local-first: Works entirely offline after model download

---

## Slide 9: AI Component 3 - Content Moderation & Feedback
**Content Moderation:**
1. Employer submits listing → saved as `pending_ai_review`
2. Background task calls Qwen with moderation schema
3. LLM returns `valid` or `flagged` with risk reasons
4. Valid listings become `active`, flagged remain pending for manual review
5. Demo mode uses deterministic phrase matching (payment/credential/guarantee)

**Application Feedback:**
1. Employer changes status to `viewed` or `rejected`
2. Background task fetches application-time profile and listing snapshots
3. Qwen generates structured advice grounded in actual qualifications
4. Feedback persisted with notification
5. Email delivery attempted via outbox with retry logic

---

## Slide 10: Dataset
**Source:** Internship Opportunities Dataset (Kaggle)
**Link:** https://www.kaggle.com/datasets/everydaycodings/internship-opportunities-dataset

**Usage:**
- Provides realistic internship records (required skills, descriptions, stipends)
- Feeds the vector recommendation engine
- Allows evaluation of matching accuracy against practical student portfolio pieces
- Examples range from human motion analysis systems (CNNs, HOG, Optical Flow) to standard cloud deployment projects

**Processing:**
- Idempotent pandas importer
- 25 synthetic examples for demonstration
- Original company names preserved as provenance, not impersonated accounts
- Dataset license and provenance documented in `docs/dataset.md`

---

## Slide 11: Evaluation Results
**Backend Testing:**
- 48 pytest tests covering authentication, authorization, CSRF, version conflicts
- Integration tests for employer verification, content moderation, safety reports
- Optional real-model and Mailpit tests when explicitly enabled
- Alembic schema drift checking

**Frontend Testing:**
- 6 Playwright end-to-end tests covering both student and employer journeys
- Responsive testing at 375px, 768px, 1440px in light and dark themes
- TypeScript strict type checking
- ESLint with Next.js rules
- Production build verification

**Recommendation Evaluation:**
- Synthetic ranking experiment with 25 fictional candidates and 3 student profiles
- Comparison of MiniLM embeddings vs keyword baseline
- Metrics: Precision@5 (MiniLM: 0.80, Baseline: 0.73), MRR (both: 1.0)
- Note: Results are demonstration on synthetic data, not population-level accuracy

---

## Slide 12: Security Architecture
**Implemented Security Measures:**
- SHA-256 hashed session tokens (320 bits random input)
- HttpOnly, SameSite=Lax cookies
- CSRF protection with per-request tokens
- Origin validation on all mutations
- Rate limiting for login and uploads
- Private PDF storage with randomized names
- Employer verification workflow
- Admin audit trail
- No credentials in client-side code
- Environment-based configuration

**Production Requirements:**
- HTTPS enabled
- `COOKIE_SECURE=true`
- `ENVIRONMENT=production`
- Unique strong credentials
- Exact `ALLOWED_ORIGINS` configuration

---

## Slide 13: Demonstration Flow
**1. Landing & Authentication**
- Show landing page with light/dark/system theme switching
- Sign in as `student@novaroute.test` with `NovaRouteDemo!2026`
- Explain dashboard totals and similarity explanation

**2. Profile & Resume**
- Add coursework and project, demonstrate persistence
- Upload resume PDF, review skill draft, correct details, confirm
- Explain private PDF storage (employers never receive the PDF)

**3. Recommendations & Applications**
- Show recommendations (may be empty above 0.80 threshold - valid result)
- Browse all internships, filter by skill/work mode, save listing
- Apply with cover message, show application-time snapshot

**4. Employer Workflow**
- Open employer account in incognito window
- View applicant, set status to Viewed with note
- Show pending → active content review for new listings
- Edit description to include "upfront fee" to demonstrate flagging

**5. Feedback & Notifications**
- Refresh student inbox or wait for 25-second poll
- Show persisted status, demo advice, timeline, and Mailpit email
- Demonstrate email preferences and password change

---

## Slide 14: Limitations
**Technical Limitations:**
- Single-process rate limiting (doesn't scale across multiple backend processes)
- Model cache per process (increases memory usage with multiple processes)
- No task queue (BackgroundTasks not durable; server crash loses in-flight work)
- No Redis (no shared cache or distributed locking)
- At-least-once email delivery (crash after SMTP acceptance can produce duplicates)
- No OCR (image-only PDFs cannot be processed)

**AI Limitations:**
- Semantic similarity ≠ hiring probability (cosine scores measure text similarity, not actual job fit)
- Threshold choice arbitrary (0.80 cutoff is reasonable default but not empirically validated)
- LLM hallucinations (even with structured output, LLMs can generate incorrect information)
- No training from scratch (uses pre-trained models without fine-tuning)
- Limited evaluation (synthetic experiment with 3 profiles is not statistically significant)

**Scope Limitations:**
- Single database (MySQL required, no SQLite substitute)
- No external integrations (no LinkedIn, Indeed, or other platform APIs)
- No chat interface (no conversational AI features)
- No scheduling (no interview scheduling or calendar integration)

---

## Slide 15: Conclusion
**NovaRoute successfully demonstrates:**
- ✅ Clearly defined problem with identified target users
- ✅ Multiple AI components (MiniLM embeddings, LLM integration)
- ✅ Working prototype with meaningful user interactions
- ✅ Research inspiration from semantic recommendation and LLM extraction literature
- ✅ Appropriate scope for a bachelor-level capstone project
- ✅ Comprehensive documentation and verification

**Key Achievements:**
- Robust security architecture with CSRF protection and employer verification
- Explicit AI labeling for transparency
- Fail-safe behavior when AI is unavailable
- Comprehensive testing coverage (48 backend tests, 6 e2e tests)
- Local-first design with optional external API integration

**Future Improvements:**
- Multi-process deployment with Redis for shared caching and rate limiting
- Fine-tuning MiniLM on internship-specific data
- Expanding evaluation with larger labeled datasets
- Adding conversational AI for application assistance
- Implementing interview scheduling and video features
- Adding mobile application support

---

## Slide 16: References
**Research Papers:**
1. Smart-Hiring: An Explainable end-to-end Pipeline for CV Information Extraction and Candidate Matching (arXiv:2511.02537)
   - https://arxiv.org/abs/2511.02537

**Technical Documentation:**
- FastAPI: https://fastapi.tiangolo.com/
- Next.js: https://nextjs.org/docs
- Sentence Transformers: https://www.sbert.net/
- OpenRouter: https://openrouter.ai/docs
- SQLAlchemy: https://docs.sqlalchemy.org/
- Alembic: https://alembic.sqlalchemy.org/

**Dataset:**
- Internship Opportunities Dataset (Kaggle)
- https://www.kaggle.com/datasets/everydaycodings/internship-opportunities-dataset

**Project Documentation:**
- NovaRoute README, Architecture, AI Design, API, Verification, and Evaluation docs
