# UI/UX Integration - LLM, RAG, and Recommendations

## Complete System Overview

Your NovaRoute project now has **three AI-powered features** fully integrated into the UI:

### 1. ✅ Recommendations (Fully Integrated)

**Backend:** `app/services/recommendations.py`
**Frontend:** `components/dashboard.tsx`, `components/listings.tsx`

**Where it appears in UI:**
- **Student Dashboard** (`/student/dashboard`)
  - Shows top 4 recommended internships with match percentages
  - Displays "Opportunities that connect" section
  - Shows similarity badges (e.g., "85% Match")
  - Includes explanation: "Why this appeared"

- **Internship Listings** (`/student/internships`)
  - Each listing card shows match percentage if it's a recommendation
  - Badge displays: "XX% Match"
  - Help text: "Semantic similarity · not hiring probability"

- **Internship Detail Page** (`/student/internships/{id}`)
  - Sidebar shows match percentage for that specific internship
  - Displays explanation of why it appeared
  - Shows matched/missing skills

**How it works:**
1. User completes profile (skills, coursework, projects)
2. System encodes profile using MiniLM embeddings
3. Computes similarity with all active internships
4. Returns top matches above 80% threshold
5. Displays in UI with similarity scores and explanations

---

### 2. ✅ LLM Feedback (Fully Integrated)

**Backend:** `app/services/feedback.py`, `app/services/openrouter.py`
**Frontend:** `components/activity.tsx`

**Where it appears in UI:**
- **Notifications** (`/student/notifications`)
  - When application is viewed or rejected
  - Shows "AI suggestions" badge
  - Displays feedback summary
  - Lists: strengths, potential gaps, next steps, practice questions

- **Application Detail** (`/student/applications?application={id}`)
  - Shows feedback in application timeline
  - Displays feedback state (pending, failed, or ready)
  - Shows email delivery status

**How it works:**
1. Employer updates application status (viewed/rejected)
2. System generates feedback using LLM (OpenRouter) or demo rules
3. Creates notification with feedback
4. Sends email with feedback
5. Displays in notifications and application timeline

**Demo vs Live Mode:**
- **Demo**: Simple rule-based feedback
- **Live**: Full LLM responses via OpenRouter Qwen model

---

### 3. ✅ RAG Q&A (NEW - Just Added)

**Backend:** `app/services/simple_rag.py`
**Frontend:** `components/rag-chat.tsx` (NEW)

**Where it appears in UI:**
- **Ask AI Page** (`/student/ask-ai`) - NEW!
  - Chat interface for asking questions about internships
  - Shows AI responses with similar internships
  - Displays similarity scores for sources
  - Chat history preserved

- **Navigation Sidebar**
  - New "Ask AI" menu item with Sparkles icon
  - Available for student role only

**How it works:**
1. Student types a question (e.g., "What skills are needed for data science roles?")
2. System encodes question using MiniLM
3. Computes similarity with all active internships
4. Returns top 3 most similar internships
5. Generates answer using LLM or demo rules
6. Displays answer with source internships and similarity scores

**Features:**
- Chat history (previous Q&A preserved)
- Source attribution (shows which internships informed the answer)
- Similarity scores (shows how relevant each source is)
- Error handling and loading states
- Responsive design

---

## Navigation Structure

### Student Workspace
```
/dashboard          - Overview with recommendations ✅
/profile            - Edit profile ✅
/internships        - Browse all internships ✅
/saved              - Saved internships ✅
/applications       - My applications with feedback ✅
/ask-ai             - AI Q&A about internships 🆕
/reports            - My reports ✅
/notifications      - Notifications with AI feedback ✅
/settings           - Account settings ✅
```

### Employer Workspace
```
/dashboard          - Overview
/profile            - Company profile
/verification       - Verification status
/internships        - Manage listings
/applicants         - View applicants
/notifications      - Notifications
/settings           - Account settings
```

### Admin Workspace
```
/dashboard          - Review overview
/employers          - Employer verification
/listings           - Content review
/reports            - Student reports
/audit              - Audit history
```

---

## API Endpoints Summary

### Recommendations
- `GET /student/recommendations` - Get personalized internship matches

### LLM Feedback
- Generated automatically when application status changes
- Delivered via notifications
- No direct API endpoint needed for UI

### RAG Q&A
- `POST /api/simple-rag/query` - Ask questions about internships
  - Request: `{ question: string, top_k: number }`
  - Response: `{ answer: string, sources: array, num_results: number }`

---

## Configuration

### Demo Mode (Default)
- Recommendations: ✅ Real MiniLM embeddings
- LLM Feedback: Simple rule-based
- RAG Q&A: Simple pattern matching

### Live Mode (Requires OpenRouter API Key)
- Recommendations: ✅ Real MiniLM embeddings
- LLM Feedback: Full OpenRouter Qwen responses
- RAG Q&A: Full OpenRouter Qwen responses

Set in `.env`:
```bash
AI_MODE=live
OPENROUTER_API_KEY=your_key
OPENROUTER_MODEL=qwen/qwen3-235b-a22b-2507
```

---

## User Flow Examples

### Example 1: Student Using Recommendations
1. Student logs in → Dashboard
2. Sees "Opportunities that connect" with 4 recommended internships
3. Each shows match percentage (e.g., "85% Match")
4. Clicks on "View role" → Internship detail page
5. Sees "Why this appeared" explanation
6. Applies to internship

### Example 2: Student Getting AI Feedback
1. Student applies to internship
2. Employer views application → status changes to "viewed"
3. System generates AI feedback
4. Student receives notification with "AI suggestions"
5. Student opens notification → sees strengths, gaps, next steps
6. Uses feedback to improve profile

### Example 3: Student Using RAG Q&A
1. Student navigates to "Ask AI" in sidebar
2. Types: "What skills are needed for data science roles?"
3. AI responds with answer based on similar internships
4. Shows 3 source internships with similarity scores
5. Student clicks on source internships to learn more
6. Can ask follow-up questions

---

## Technical Implementation

### Shared Components
- **Embeddings**: All three features use the same MiniLM model (`sentence-transformers/all-MiniLM-L6-v2`)
- **Database**: All features query the same internship database
- **Configuration**: All features respect `AI_MODE` setting

### Performance
- **Recommendations**: Fast (cached embeddings, in-memory similarity)
- **LLM Feedback**: Medium (depends on OpenRouter response time)
- **RAG Q&A**: Fast (simple similarity search, no complex indexing)

### Memory Usage
- **Recommendations**: Low (embeddings cached)
- **LLM Feedback**: Low (no persistent state)
- **RAG Q&A**: Low (in-memory search, no vector DB)

---

## Summary

| Feature | UI Location | Status | Mode Support |
|---------|-------------|--------|--------------|
| **Recommendations** | Dashboard, Listings, Detail | ✅ Full | Demo + Live |
| **LLM Feedback** | Notifications, Applications | ✅ Full | Demo + Live |
| **RAG Q&A** | Ask AI page | ✅ New | Demo + Live |

**All three features work together seamlessly and share the same embedding infrastructure!**
