-- Manual schema equivalent to Alembic 0002_employer_trust. Fresh databases only; prefer alembic upgrade head.
SET NAMES utf8mb4;

CREATE TABLE users (
	id INTEGER NOT NULL AUTO_INCREMENT,
	`role` ENUM('student','employer','admin') NOT NULL,
	name VARCHAR(100) NOT NULL,
	email VARCHAR(254) NOT NULL,
	password_hash VARCHAR(255) NOT NULL,
	email_matches BOOL NOT NULL,
	email_applications BOOL NOT NULL,
	is_demo BOOL NOT NULL,
	deactivated_at DATETIME,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (email)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;

CREATE TABLE admin_audit (
	id INTEGER NOT NULL AUTO_INCREMENT,
	actor_id INTEGER NOT NULL,
	target_type VARCHAR(30) NOT NULL,
	target_id INTEGER NOT NULL,
	action VARCHAR(40) NOT NULL,
	reason TEXT NOT NULL,
	evidence TEXT NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(actor_id) REFERENCES users (id)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;

CREATE TABLE employer_profiles (
	id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER NOT NULL,
	company_name VARCHAR(150) NOT NULL,
	website VARCHAR(500) NOT NULL,
	industry VARCHAR(150) NOT NULL,
	location VARCHAR(200) NOT NULL,
	description TEXT NOT NULL,
	legal_name VARCHAR(200) NOT NULL,
	registration_number VARCHAR(150) NOT NULL,
	registration_explanation VARCHAR(1000) NOT NULL,
	recruiter_name VARCHAR(100) NOT NULL,
	recruiter_position VARCHAR(150) NOT NULL,
	contact_email VARCHAR(254) NOT NULL,
	contact_phone VARCHAR(80) NOT NULL,
	verification_status VARCHAR(20) NOT NULL,
	verification_version INTEGER NOT NULL,
	submitted_at DATETIME,
	reviewed_at DATETIME,
	review_reason TEXT NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;
CREATE INDEX ix_employer_profiles_verification_status ON employer_profiles (verification_status);

CREATE TABLE internships (
	id INTEGER NOT NULL AUTO_INCREMENT,
	employer_id INTEGER NOT NULL,
	title VARCHAR(200) NOT NULL,
	description TEXT NOT NULL,
	required_skills JSON NOT NULL,
	location VARCHAR(200) NOT NULL,
	work_mode ENUM('remote','hybrid','onsite') NOT NULL,
	duration VARCHAR(100) NOT NULL,
	stipend_min NUMERIC(12, 2),
	stipend_max NUMERIC(12, 2),
	currency VARCHAR(3),
	deadline DATETIME,
	status ENUM('pending_ai_review','active','flagged','closed') NOT NULL,
	moderation JSON NOT NULL,
	moderation_model VARCHAR(200),
	content_version INTEGER NOT NULL,
	source_key VARCHAR(64),
	provenance JSON NOT NULL,
	deleted_at DATETIME,
	admin_hidden BOOL NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(employer_id) REFERENCES users (id),
	UNIQUE (source_key)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;
CREATE INDEX ix_internship_eligible ON internships (status, deleted_at, deadline);
CREATE INDEX ix_internships_employer_id ON internships (employer_id);
CREATE INDEX ix_internships_status ON internships (status);

CREATE TABLE notifications (
	id INTEGER NOT NULL AUTO_INCREMENT,
	recipient_id INTEGER NOT NULL,
	type VARCHAR(50) NOT NULL,
	title VARCHAR(200) NOT NULL,
	body TEXT NOT NULL,
	related JSON NOT NULL,
	feedback JSON,
	feedback_state VARCHAR(30) NOT NULL,
	event_key VARCHAR(150) NOT NULL,
	read_at DATETIME,
	dismissed_at DATETIME,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(recipient_id) REFERENCES users (id),
	UNIQUE (event_key)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;
CREATE INDEX ix_notifications_recipient_id ON notifications (recipient_id);

CREATE TABLE resumes (
	id INTEGER NOT NULL AUTO_INCREMENT,
	student_id INTEGER NOT NULL,
	storage_ref VARCHAR(100) NOT NULL,
	filename VARCHAR(200) NOT NULL,
	content_hash VARCHAR(64) NOT NULL,
	parse_state VARCHAR(30) NOT NULL,
	extracted JSON NOT NULL,
	raw_text TEXT,
	failure VARCHAR(250),
	profile_version INTEGER NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(student_id) REFERENCES users (id)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;
CREATE INDEX ix_resumes_student_id ON resumes (student_id);

CREATE TABLE sessions (
	id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER,
	token_hash VARCHAR(64) NOT NULL,
	csrf_token VARCHAR(100) NOT NULL,
	expires_at DATETIME NOT NULL,
	revoked_at DATETIME,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	FOREIGN KEY(user_id) REFERENCES users (id),
	UNIQUE (token_hash)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;
CREATE INDEX ix_sessions_user_id ON sessions (user_id);
CREATE INDEX ix_sessions_expires_at ON sessions (expires_at);

CREATE TABLE student_profiles (
	id INTEGER NOT NULL AUTO_INCREMENT,
	user_id INTEGER NOT NULL,
	extracted_skills JSON NOT NULL,
	coursework JSON NOT NULL,
	projects JSON NOT NULL,
	resume_derived JSON NOT NULL,
	raw_resume_text TEXT,
	degree VARCHAR(200) NOT NULL,
	location VARCHAR(200) NOT NULL,
	preferences JSON NOT NULL,
	version INTEGER NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	UNIQUE (user_id),
	FOREIGN KEY(user_id) REFERENCES users (id)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;

CREATE TABLE applications (
	id INTEGER NOT NULL AUTO_INCREMENT,
	student_id INTEGER NOT NULL,
	internship_id INTEGER NOT NULL,
	cover_message TEXT NOT NULL,
	status ENUM('applied','viewed','rejected','accepted','withdrawn') NOT NULL,
	profile_snapshot JSON NOT NULL,
	match_score FLOAT,
	version INTEGER NOT NULL,
	applied_at DATETIME NOT NULL,
	withdrawn_at DATETIME,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_application_student_listing UNIQUE (student_id, internship_id),
	FOREIGN KEY(student_id) REFERENCES users (id),
	FOREIGN KEY(internship_id) REFERENCES internships (id)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;
CREATE INDEX ix_applications_student_id ON applications (student_id);
CREATE INDEX ix_applications_internship_id ON applications (internship_id);

CREATE TABLE email_outbox (
	id INTEGER NOT NULL AUTO_INCREMENT,
	notification_id INTEGER NOT NULL,
	event_key VARCHAR(160) NOT NULL,
	state VARCHAR(30) NOT NULL,
	retry_count INTEGER NOT NULL,
	last_error VARCHAR(250),
	next_attempt_at DATETIME NOT NULL,
	claimed_at DATETIME,
	sent_at DATETIME,
	PRIMARY KEY (id),
	UNIQUE (notification_id),
	FOREIGN KEY(notification_id) REFERENCES notifications (id),
	UNIQUE (event_key)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;
CREATE INDEX ix_email_outbox_state ON email_outbox (state);

CREATE TABLE listing_reports (
	id INTEGER NOT NULL AUTO_INCREMENT,
	listing_id INTEGER NOT NULL,
	reporter_id INTEGER NOT NULL,
	category VARCHAR(40) NOT NULL,
	details TEXT NOT NULL,
	status VARCHAR(20) NOT NULL,
	resolution TEXT NOT NULL,
	version INTEGER NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_report_student_listing UNIQUE (listing_id, reporter_id),
	FOREIGN KEY(listing_id) REFERENCES internships (id),
	FOREIGN KEY(reporter_id) REFERENCES users (id)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;
CREATE INDEX ix_listing_reports_status ON listing_reports (status);
CREATE INDEX ix_listing_reports_listing_id ON listing_reports (listing_id);
CREATE INDEX ix_listing_reports_reporter_id ON listing_reports (reporter_id);

CREATE TABLE saved_internships (
	id INTEGER NOT NULL AUTO_INCREMENT,
	student_id INTEGER NOT NULL,
	internship_id INTEGER NOT NULL,
	note TEXT NOT NULL,
	created_at DATETIME NOT NULL,
	updated_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_saved_pair UNIQUE (student_id, internship_id),
	FOREIGN KEY(student_id) REFERENCES users (id),
	FOREIGN KEY(internship_id) REFERENCES internships (id)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;
CREATE INDEX ix_saved_internships_student_id ON saved_internships (student_id);

CREATE TABLE application_status_history (
	id INTEGER NOT NULL AUTO_INCREMENT,
	application_id INTEGER NOT NULL,
	previous_status VARCHAR(30),
	new_status VARCHAR(30) NOT NULL,
	actor_id INTEGER NOT NULL,
	employer_note TEXT,
	event_version INTEGER NOT NULL,
	created_at DATETIME NOT NULL,
	PRIMARY KEY (id),
	CONSTRAINT uq_history_version UNIQUE (application_id, event_version),
	FOREIGN KEY(application_id) REFERENCES applications (id),
	FOREIGN KEY(actor_id) REFERENCES users (id)
)CHARSET=utf8mb4 COLLATE utf8mb4_unicode_ci

;
CREATE INDEX ix_application_status_history_application_id ON application_status_history (application_id);
