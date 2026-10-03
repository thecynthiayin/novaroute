# AI design and failure behavior

This is **pretrained embedding inference plus hosted LLM integration**, not model training from scratch.

## Resume extraction

`pdfplumber` reads searchable text from a private, signature-checked PDF. Configurable limits default to 5 MB, ten pages and 24,000 extracted characters. Corrupt, password-protected, empty and image-only PDFs receive actionable errors. No resume links are followed and nothing embedded is executed. The upload UI discloses provider processing before submission.

In live mode, email/phone/link patterns are redacted before sending text. This is data minimization, not complete anonymization; other personal details can remain in a resume. The version-controlled system prompt treats all document text as untrusted data and requires source-supported facts only. Pydantic `Extraction`, `Project`, `Moderation`, and `Feedback` models bound strings/arrays, forbid extra properties and validate all outputs, even with provider-side schema enforcement.

OpenRouter uses one OpenAI-compatible client with explicit timeout, 2 transient retries (three attempts total), exponential backoff, a bounded prompt/output, low temperature and JSON Schema. `provider.require_parameters=true` requires compatible routing. Invalid credentials fail immediately; invalid JSON does not trigger endless retry. Errors are categorized configuration/provider/timeout/validation and sanitized. The configured Qwen ID is not hardwired. During implementation, the public model catalog advertised `qwen/qwen3.8-flash` with structured output and response-format support; use `python -m app.jobs.check_provider` to recheck. No paid inference was run here.

Read [OpenRouter structured-output guidance](https://openrouter.ai/docs/guides/features/structured-outputs): support is endpoint-specific and can change. Strong schema enforcement does not prove factual extraction. The student must review/edit the draft. Alias normalization merges JS/JavaScript and Postgres/PostgreSQL while preserving Java versus JavaScript.

Demo extraction uses a documented vocabulary found in the PDF and leaves unsupported coursework/projects/education empty. It does not pretend to be a live LLM. Live errors never fall back silently to demo rules. Profiles can always be entered manually.

## Content review

Listings are committed as `pending_ai_review` before a background review. Qwen returns `valid` or `flagged`, risk reasons and suggested changes. A valid schema/result activates the current content version. Flagged output remains private; unavailable/invalid output stays pending. All edits and reopen actions require review. The result is an automated content check—not employer identity verification or a safety guarantee. Unpaid alone is not considered fraud.

Demo review checks explicit payment/credential/guarantee phrases. It is intentionally limited and labelled in the UI. Review work that is interrupted by a process crash can be restarted using the employer's re-review control.

## Semantic recommendations

`sentence-transformers/all-MiniLM-L6-v2` is loaded once per backend process on CPU. The encoding input starts with normalized confirmed skills, then coursework and project title/technologies/description; listing input starts with required skills, then title and description. Names, email addresses, raw resume/contact data and company identity do not participate.

Long input uses tokenizer IDs, deterministic nonoverlapping chunks of `model.max_seq_length - 2`, at most 16 chunks. Each chunk is normalized, their vectors are averaged with twice the weight on the first structured chunk, and the aggregate is normalized. This deliberately bounds processing and prioritizes structured evidence rather than relying on silent model truncation. The LRU cache holds at most 2,048 vectors keyed by model ID plus normalized-content SHA-256. Profile/listing edits explicitly clear the cache; content keys also prevent stale hits.

Cosine similarity follows [Sentence Transformers' semantic similarity approach](https://sbert.net/docs/sentence_transformer/usage/semantic_textual_similarity.html). The filter uses the **unrounded score > 0.50** (configurable via `RECOMMENDATION_MIN_SCORE`), then descending score and ascending listing ID for deterministic ties, then top-k. Closed, deleted, pending, flagged, expired listings and previous applications are excluded. Matches are presented directly in the student dashboard match section ("Opportunities that connect"). Model unavailability gives a 503 while manual editing/browsing continue. The percentage is presentation-only; similarity is not hiring probability or model accuracy.

Matched/missing skills are deterministic comparisons against confirmed skills and project technologies. Explanations do not invent qualifications. Notification inbox & header bell are reserved for application process updates; recommendations appear in the dashboard match section.

## Feedback and delivery

Viewed/rejected events request one structured advice result grounded in the application-time profile and listing. Rejection guidance identifies potential gaps without claiming an employer's reason unless the employer supplied a note. Accepted/withdrawn statuses use factual messages without an LLM call. The notification persists feedback, and email uses that same content. Feedback failure leaves a factual status and retryable `failed` state; status/history never roll back.

Email contains escaped HTML, plain text, and an application/listing link derived from `FRONTEND_URL`. `smtplib` is executed outside the async loop using `BackgroundTasks`. Persisted outbox leases prevent concurrent workers from sending the same fresh claim; crash recovery can still duplicate SMTP delivery after server acceptance. See architecture and README recovery notes.
