'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { api, date, human, params } from '@/lib/api';
import type { Application, Feedback, Notice, Page, Role } from '@/lib/types';
import { useAction } from '@/providers';
import { ReportForm } from './trust';
import { Badge, Confirm, Empty, Failure, Form, Heading, Loading, Pagination } from './ui';
import { noticeHref } from './shell';

export function FeedbackView({ feedback }: { feedback: Feedback }) {
  return (
    <section className="feedback">
      <Badge>AI suggestions</Badge>
      <p style={{ marginTop: 12 }}>{feedback.summary}</p>
      {(['strengths', 'potential_gaps', 'next_steps', 'practice_questions'] as const).map(
        (key) =>
          feedback[key]?.length > 0 && (
            <div key={key}>
              <h4>{human(key)}</h4>
              <ul>
                {feedback[key].map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ul>
            </div>
          ),
      )}
    </section>
  );
}

export function NoticeCard({ notice, role }: { notice: Notice; role: Role }) {
  const action = useAction();
  return (
    <article className={`event ${notice.read_at ? '' : 'unread'}`}>
      <div className="status-row">
        <h3>
          <Link href={noticeHref(notice, role)}>{notice.title}</Link>
        </h3>
        {!notice.read_at && <Badge>New</Badge>}
      </div>
      <p>{notice.body}</p>
      <small>{date(notice.created_at)}</small>
      {notice.feedback && <FeedbackView feedback={notice.feedback} />}
      {notice.feedback_state === 'failed' && (
        <p className="alert">
          AI suggestions are temporarily unavailable. Your application status is confirmed; feedback
          can be retried by the local delivery command.
        </p>
      )}
      {notice.feedback_state === 'pending' && <p className="muted">Preparing feedback…</p>}
      <div className="actions" style={{ marginTop: 12 }}>
        <Link className="text-button" href={noticeHref(notice, role)}>
          View details
        </Link>
        <button
          className="text-button"
          disabled={action.isPending}
          onClick={() =>
            action.mutate({
              path: `/notifications/${notice.id}`,
              method: 'PATCH',
              body: { read: !notice.read_at },
            })
          }
        >
          Mark {notice.read_at ? 'unread' : 'read'}
        </button>
        <Confirm
          title="Dismiss notification?"
          description="Remove this event from your inbox. Application history remains available."
          trigger={<button className="text-button muted">Dismiss</button>}
          onConfirm={() =>
            action.mutateAsync({ path: `/notifications/${notice.id}`, method: 'DELETE' })
          }
          busy={action.isPending}
        />
      </div>
    </article>
  );
}

export function Notifications({ role }: { role: Role }) {
  const [read, setRead] = useState('all'),
    [page, setPage] = useState(1),
    action = useAction(),
    query = useQuery({
      queryKey: ['notifications', read, page],
      queryFn: () => api<Page<Notice>>(`/notifications?${params({ read, page })}`),
      refetchInterval: 25000,
      refetchIntervalInBackground: false,
    });
  return (
    <>
      <Heading
        eyebrow="Stay in the loop"
        title="Your notifications"
        action={
          <button
            className="button secondary"
            disabled={action.isPending}
            onClick={() => action.mutate({ path: '/notifications/read-all' })}
          >
            Mark all as read
          </button>
        }
      >
        Application updates, useful feedback, and new possibilities.
      </Heading>
      <label style={{ maxWidth: 200, marginBottom: 20 }}>
        Show
        <select
          value={read}
          onChange={(e) => {
            setRead(e.target.value);
            setPage(1);
          }}
        >
          <option value="all">All notifications</option>
          <option value="unread">Unread</option>
          <option value="read">Read</option>
        </select>
      </label>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Failure error={query.error} retry={() => query.refetch()} />
      ) : (
        <>
          {query.data.items.length ? (
            <div className="card">
              {query.data.items.map((n) => (
                <NoticeCard key={n.id} notice={n} role={role} />
              ))}
            </div>
          ) : (
            <Empty title="You’re all caught up">
              We’ll keep your updates here. This inbox checks for new activity every 25 seconds
              while visible.
            </Empty>
          )}
          <Pagination page={page} setPage={setPage} total={query.data.total} size={20} />
        </>
      )}
    </>
  );
}

export function ApplicationsPage({ role }: { role: Role }) {
  const search = useSearchParams(),
    [status, setStatus] = useState(''),
    [page, setPage] = useState(1),
    selected = search.get('application'),
    internship = search.get('internship');
  const list = useQuery({
    queryKey: ['applications', role, status, page, internship],
    queryFn: () =>
      api<Page<Application>>(
        `/applications?${params({ status, page, internship_id: internship || undefined })}`,
      ),
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
  });
  const detail = useQuery({
    queryKey: ['application', selected],
    queryFn: () => api<Application>(`/applications/${selected}`),
    enabled: !!selected,
    refetchInterval: 10000,
    refetchIntervalInBackground: false,
  });
  const items = selected ? (detail.data ? [detail.data] : []) : list.data?.items;
  const error = selected ? detail.error : list.error,
    pending = selected ? detail.isPending : list.isPending;
  return (
    <>
      <Heading
        eyebrow={role === 'student' ? 'Every step is progress' : 'Meet your next generation'}
        title={role === 'student' ? 'Your applications' : 'Your applicants'}
      >
        {role === 'student'
          ? 'Follow your progress and turn feedback into a next step.'
          : 'Review the experience students chose to share and keep them informed.'}
      </Heading>
      {selected ? (
        <Link
          className="text-button"
          href={`/${role}/${role === 'student' ? 'applications' : 'applicants'}`}
        >
          ← View all {role === 'student' ? 'applications' : 'applicants'}
        </Link>
      ) : (
        <div className="actions" style={{ marginBottom: 22 }}>
          <label style={{ width: 210 }}>
            Application status
            <select
              value={status}
              onChange={(e) => {
                setStatus(e.target.value);
                setPage(1);
              }}
            >
              <option value="">All statuses</option>
              {['applied', 'viewed', 'accepted', 'rejected', 'withdrawn'].map((s) => (
                <option key={s} value={s}>
                  {human(s)}
                </option>
              ))}
            </select>
          </label>
          {internship && (
            <Link className="text-button" href="/employer/applicants">
              Clear listing filter
            </Link>
          )}
        </div>
      )}
      {pending ? (
        <Loading />
      ) : error ? (
        <Failure error={error} />
      ) : (
        <>
          <div className="stack">
            {items?.map((a) => (
              <ApplicationCard key={`${a.id}-${a.version}`} application={a} role={role} />
            ))}
          </div>
          {items?.length === 0 && (
            <Empty
              title={role === 'student' ? 'Your next chapter is waiting' : 'No applicants yet'}
              href={role === 'student' ? '/student/internships' : undefined}
            >
              {role === 'student'
                ? 'Explore internships and send an application when you find a fit.'
                : 'Applications to your listings will appear here.'}
            </Empty>
          )}
          {!selected && list.data && (
            <Pagination page={page} setPage={setPage} total={list.data.total} size={20} />
          )}
        </>
      )}
    </>
  );
}

function ApplicationCard({ application: a, role }: { application: Application; role: Role }) {
  const action = useAction(),
    active = ['applied', 'viewed'].includes(a.status);
  return (
    <article className="card">
      <div className="application-head">
        <div>
          <h3>
            <Link
              href={`/${role}/${role === 'student' ? 'applications' : 'applicants'}?application=${a.id}`}
            >
              {a.internship_title}
            </Link>
          </h3>
          <small className="muted">
            {role === 'employer' ? a.student_name + ' · ' : ''}Applied {date(a.applied_at)}
          </small>
        </div>
        <div>
          <Badge>{a.status}</Badge>
        </div>
      </div>
      {role === 'employer' && (
        <div className="feedback">
          <h3>Application-time profile</h3>
          <p>{a.profile_snapshot.degree || 'Degree not provided'}</p>
          <div className="chips">
            {a.profile_snapshot.extracted_skills?.map((s) => (
              <span className="chip" key={s}>
                {s}
              </span>
            ))}
          </div>
          <p style={{ marginTop: 15 }}>
            <strong>Coursework:</strong>{' '}
            {a.profile_snapshot.coursework?.join(', ') || 'None provided'}
          </p>
          {a.profile_snapshot.projects?.map((p, i) => (
            <div key={i}>
              <strong>{p.title}</strong>
              <p>{p.description}</p>
              <small>{p.technologies.join(', ')}</small>
            </div>
          ))}
        </div>
      )}
      <h4 style={{ fontSize: 13, margin: '20px 0 8px' }}>Cover message</h4>
      {role === 'student' && <ReportForm listingId={a.internship_id} />}
      <p className="muted" style={{ fontSize: 13, whiteSpace: 'pre-wrap' }}>
        {a.cover_message || 'No cover message provided.'}
      </p>
      {role === 'student' && a.status === 'applied' && (
        <details>
          <summary className="text-button">Edit cover message</summary>
          <div style={{ marginTop: 12 }}>
            <Form
              fields={[
                {
                  name: 'cover_message',
                  label: 'Edit cover message',
                  type: 'textarea',
                  maxLength: 4000,
                },
              ]}
              initial={{ cover_message: a.cover_message }}
              onSubmit={async (values) => {
                await action.mutateAsync({
                  path: `/applications/${a.id}`,
                  method: 'PATCH',
                  body: { ...values, version: a.version },
                });
              }}
              busy={action.isPending}
              submitLabel="Save cover message"
            />
          </div>
        </details>
      )}
      <details>
        <summary className="text-button">Application timeline</summary>
        <ol className="timeline">
          {a.history.map((h) => (
            <li key={h.id}>
              <Badge>{h.new_status}</Badge>
              <small className="muted">{date(h.created_at)}</small>
              {h.employer_note && <p>{h.employer_note}</p>}
            </li>
          ))}
        </ol>
      </details>
      {role === 'employer' && active && (
        <section style={{ marginTop: 20 }}>
          <Form
            fields={[
              {
                name: 'status',
                label: 'Update application status',
                options:
                  a.status === 'applied'
                    ? ['viewed', 'accepted', 'rejected']
                    : ['accepted', 'rejected'],
              },
              {
                name: 'employer_note',
                label: 'Note to the student (optional)',
                type: 'textarea',
                maxLength: 2000,
                hint: 'This note is shared with the student and included in their notification.',
              },
            ]}
            initial={{ status: a.status === 'applied' ? 'viewed' : 'accepted', employer_note: '' }}
            onSubmit={async (values) => {
              await action.mutateAsync({
                path: `/applications/${a.id}/status`,
                method: 'PUT',
                body: { ...values, version: a.version },
              });
            }}
            busy={action.isPending}
            submitLabel="Send status update"
          />
        </section>
      )}
      {role === 'student' && active && (
        <Confirm
          title="Withdraw this application?"
          description="This is a final status. You cannot apply to this same internship again. Your decision history will remain."
          trigger={
            <button className="text-button danger-text" style={{ marginTop: 12 }}>
              Withdraw application
            </button>
          }
          onConfirm={() =>
            action.mutateAsync({
              path: `/applications/${a.id}/withdraw`,
              body: { version: a.version },
            })
          }
          busy={action.isPending}
        />
      )}
      {a.events.map((n) => (
        <section key={n.id} style={{ marginTop: 18 }}>
          {n.feedback ? (
            <FeedbackView feedback={n.feedback} />
          ) : n.feedback_state === 'failed' ? (
            <p className="alert">
              AI feedback is temporarily unavailable. The application decision is saved.
            </p>
          ) : n.feedback_state === 'pending' ? (
            <p className="muted">Feedback is being prepared…</p>
          ) : null}
          <small className="muted">
            {n.title} · Email: {n.email_state || 'disabled'}
          </small>
        </section>
      ))}
    </article>
  );
}
