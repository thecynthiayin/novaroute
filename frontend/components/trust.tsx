'use client';
import { useState, useRef, useEffect, useId } from 'react';
import * as Dialog from '@radix-ui/react-dialog';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { api, date, human } from '@/lib/api';
import { useAction } from '@/providers';
import type { Company, Listing, Page } from '@/lib/types';
import { Badge, Empty, Failure, Form, Heading, Loading, Submit } from './ui';

type Verification = Company & {
  user_id: number;
  legal_name: string;
  registration_number: string;
  registration_explanation: string;
  recruiter_name: string;
  recruiter_position: string;
  contact_email: string;
  contact_phone: string;
  verification_version: number;
  submitted_at: string | null;
  review_reason: string;
};
type Report = {
  id: number;
  listing_id: number;
  category: string;
  details: string;
  status: string;
  resolution: string;
  version: number;
  created_at: string;
};
type Audit = {
  id: number;
  actor_id: number;
  target_type: string;
  target_id: number;
  action: string;
  reason: string;
  evidence: string;
  created_at: string;
};

export function VerificationPage() {
  const query = useQuery({
    queryKey: ['verification'],
    queryFn: () => api<Verification>('/employer/verification'),
  });
  const action = useAction();
  if (query.isPending) return <Loading />;
  if (query.error) return <Failure error={query.error} />;
  const company = query.data;
  const names = [
    'legal_name',
    'registration_number',
    'registration_explanation',
    'recruiter_name',
    'recruiter_position',
    'contact_email',
    'contact_phone',
  ] as const;
  return (
    <>
      <Heading eyebrow="Trust starts with transparency" title="Employer verification">
        An administrator checks the company and your authority to recruit before listings become
        public.
      </Heading>
      <section className="card narrow stack">
        <Badge>{human(company.verification_status)}</Badge>
        <p>
          {company.review_reason ||
            'Complete your company profile, then submit these details for review.'}
        </p>
        {company.reviewed_at && <p>Reviewed {date(company.reviewed_at)}</p>}
        <Link className="text-button" href="/employer/profile">
          Edit company website and location →
        </Link>
        <p className="muted">
          Registration and contact details are visible only to you and administrators. Do not submit
          passwords, bank details, or identity-document numbers.
        </p>
        {company.verification_status !== 'suspended' && (
          <Form
            key={company.verification_version}
            fields={[
              { name: 'legal_name', label: 'Legal company name', required: true, maxLength: 200 },
              {
                name: 'registration_number',
                label: 'Business registration number',
                maxLength: 150,
              },
              {
                name: 'registration_explanation',
                label: 'If registration is not applicable, explain why',
                type: 'textarea',
                maxLength: 1000,
              },
              {
                name: 'recruiter_name',
                label: 'Recruiter full name',
                required: true,
                maxLength: 100,
              },
              {
                name: 'recruiter_position',
                label: 'Recruiter position',
                required: true,
                maxLength: 150,
              },
              {
                name: 'contact_email',
                label: 'Company contact email',
                type: 'email',
                required: true,
                maxLength: 254,
              },
              {
                name: 'contact_phone',
                label: 'Company contact phone',
                required: true,
                maxLength: 80,
              },
            ]}
            initial={Object.fromEntries(names.map((k) => [k, company[k]]))}
            busy={action.isPending}
            submitLabel="Submit for verification"
            onSubmit={async (values) => {
              await action.mutateAsync({
                path: '/employer/verification',
                body: { ...values, version: company.verification_version },
              });
            }}
          />
        )}
      </section>
    </>
  );
}

export function ReportForm({ listingId }: { listingId: number }) {
  const [sent, setSent] = useState(false);
  const action = useAction(() => setSent(true));
  if (sent)
    return (
      <p role="status">
        Report received. <Link href="/student/reports">Track your report</Link>.
      </p>
    );
  return (
    <details className="card">
      <summary>Report this internship</summary>
      <p className="muted">
        Describe what happened. Your report details are private to administrators; employers do not
        see your identity. Do not include passwords or financial account numbers.
      </p>
      <Form
        fields={[
          {
            name: 'category',
            label: 'Report category',
            type: 'select',
            options: ['payment_request', 'impersonation', 'personal_data', 'misleading', 'other'],
            required: true,
          },
          {
            name: 'details',
            label: 'What happened?',
            type: 'textarea',
            required: true,
            maxLength: 2000,
          },
        ]}
        initial={{ category: 'payment_request', details: '' }}
        submitLabel="Submit report"
        busy={action.isPending}
        onSubmit={async (values) => {
          await action.mutateAsync({ path: `/internships/${listingId}/report`, body: values });
        }}
      />
    </details>
  );
}

export function MyReports() {
  const [page, setPage] = useState(1);
  const query = useQuery({
    queryKey: ['my-reports', page],
    queryFn: () => api<Page<Report>>(`/student/reports?page=${page}`),
  });
  return (
    <>
      <Heading eyebrow="Your safety matters" title="My reports">
        Track administrator responses to your reports.
      </Heading>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Failure error={query.error} />
      ) : (
        <>
          {!query.data.items.length && <Empty title="No reports submitted" />}
          {query.data.items.map((report) => (
            <article className="card" key={report.id}>
              <h2>Listing #{report.listing_id}</h2>
              <Badge>{report.status}</Badge>
              <p>
                {human(report.category)} · {date(report.created_at)}
              </p>
              <p className="listing-body">{report.details}</p>
              <p>{report.resolution || 'Waiting for administrator review.'}</p>
            </article>
          ))}
          <Pages page={page} total={query.data.total} change={setPage} />
        </>
      )}
    </>
  );
}

function Pages({
  page,
  total,
  change,
}: {
  page: number;
  total: number;
  change: (page: number) => void;
}) {
  return (
    <div className="actions" style={{ marginTop: 20 }}>
      <button className="button secondary" disabled={page <= 1} onClick={() => change(page - 1)}>
        Previous
      </button>
      <span>
        Page {page} · {total} records
      </span>
      <button
        className="button secondary"
        disabled={page * 20 >= total}
        onClick={() => change(page + 1)}
      >
        Next
      </button>
    </div>
  );
}

function DecisionForm({
  path,
  version,
  actions,
  employer = false,
}: {
  path: string;
  version: number;
  actions: string[];
  employer?: boolean;
}) {
  const mutation = useAction();
  const [action, setAction] = useState(actions[0]),
    [reason, setReason] = useState(''),
    [evidence, setEvidence] = useState('');
  const [company, setCompany] = useState(false),
    [representative, setRepresentative] = useState(false);
  return (
    <form
      className="form-stack"
      onSubmit={async (e) => {
        e.preventDefault();
        try {
          await mutation.mutateAsync({
            path,
            body: {
              action,
              version,
              reason,
              evidence,
              ...(employer
                ? { company_checked: company, representative_checked: representative }
                : {}),
            },
          });
          setReason('');
          setEvidence('');
        } catch {
          /* Toast preserves entered evidence on failure. */
        }
      }}
    >
      <label>
        Decision
        <select value={action} onChange={(e) => setAction(e.target.value)}>
          {actions.map((x) => (
            <option key={x} value={x}>
              {human(x)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Reason shared with the recipient
        <textarea
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          minLength={10}
          maxLength={2000}
          required
        />
      </label>
      <label>
        Private investigation notes and independent sources
        <textarea
          value={evidence}
          onChange={(e) => setEvidence(e.target.value)}
          maxLength={4000}
          minLength={action === 'approve' ? 20 : undefined}
          required={action === 'approve'}
        />
      </label>
      {employer && action === 'approve' && (
        <fieldset>
          <legend>Required verification checks</legend>
          <label>
            <input
              type="checkbox"
              checked={company}
              onChange={(e) => setCompany(e.target.checked)}
              required
            />{' '}
            I checked the company against independent sources
          </label>
          <label>
            <input
              type="checkbox"
              checked={representative}
              onChange={(e) => setRepresentative(e.target.checked)}
              required
            />{' '}
            I confirmed the recruiter through independently obtained company contact details
          </label>
        </fieldset>
      )}
      <p className="muted">
        {action === 'suspend'
          ? 'Suspension immediately hides this employer’s listings and blocks employer actions. Applicants receive a safety notice.'
          : action === 'hide'
            ? 'Hiding immediately stops new applications; existing applicants receive a safety notice.'
            : 'Decisions are recorded in the audit history. Approval is not a safety guarantee.'}
      </p>
      <Submit busy={mutation.isPending}>Record decision</Submit>
    </form>
  );
}

function EmployerActionButtons({
  item,
  onStatusChange,
}: {
  item: Verification;
  onStatusChange: (status: string, reason?: string, evidence?: string) => void;
}) {
  const [showDropdown, setShowDropdown] = useState(false);
  const [showRejectModal, setShowRejectModal] = useState(false);
  const [showApproveModal, setShowApproveModal] = useState(false);
  const [rejectReason, setRejectReason] = useState('');
  const [approveEvidence, setApproveEvidence] = useState('');
  const [companyChecked, setCompanyChecked] = useState(false);
  const [representativeChecked, setRepresentativeChecked] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const statusButtonRef = useRef<HTMLButtonElement>(null);
  const evidenceHintId = useId();

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false);
      }
    };

    if (showDropdown) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [showDropdown]);

  const handleStatusChange = (status: string) => {
    if (status === 'reject') {
      setShowRejectModal(true);
      setShowDropdown(false);
    } else if (status === 'approve') {
      setShowApproveModal(true);
      setShowDropdown(false);
    } else {
      onStatusChange(status);
      setShowDropdown(false);
    }
  };

  const handleRejectConfirm = () => {
    if (rejectReason.length < 10) {
      alert('Please provide a reason (at least 10 characters)');
      return;
    }
    onStatusChange('reject', rejectReason);
    setShowRejectModal(false);
    setRejectReason('');
  };

  const handleApproveConfirm = () => {
    if (!companyChecked || !representativeChecked) {
      alert('Please confirm both verification checks');
      return;
    }
    if (approveEvidence.length < 20) {
      alert('Please provide evidence (at least 20 characters)');
      return;
    }
    onStatusChange('approve', 'Employer verification approved after review', approveEvidence);
    setShowApproveModal(false);
    setApproveEvidence('');
    setCompanyChecked(false);
    setRepresentativeChecked(false);
  };

  // Define available status options based on current status
  const getStatusOptions = () => {
    const currentStatus = item.verification_status;
    const hasSubmission = item.submitted_at;

    if (currentStatus === 'suspended') {
      return [{ value: 'reopen', label: 'Reopen to Review', className: 'button secondary' }];
    }

    if (currentStatus === 'rejected') {
      return [
        { value: 'reopen', label: 'Reopen to Review', className: 'button secondary' },
        { value: 'suspend', label: 'Suspend', className: 'button danger' },
      ];
    }

    if (currentStatus === 'approved') {
      return [{ value: 'suspend', label: 'Suspend', className: 'button danger' }];
    }

    // For pending status (with or without submission)
    if (currentStatus === 'pending') {
      if (hasSubmission) {
        return [
          { value: 'approve', label: 'Approve', className: 'button' },
          { value: 'request_info', label: 'Request More Info', className: 'button secondary' },
          { value: 'reject', label: 'Reject', className: 'button danger' },
          { value: 'suspend', label: 'Suspend', className: 'button danger' },
        ];
      } else {
        // Pending without submission - allow admin to take action anyway
        return [
          { value: 'reject', label: 'Reject (No Submission)', className: 'button danger' },
          { value: 'suspend', label: 'Suspend', className: 'button danger' },
        ];
      }
    }

    // Default case - any other status
    return [{ value: 'suspend', label: 'Suspend', className: 'button danger' }];
  };

  const statusOptions = getStatusOptions();

  return (
    <>
      <div className="actions">
        <div className="dropdown" style={{ position: 'relative' }} ref={dropdownRef}>
          <button
            ref={statusButtonRef}
            className="button secondary"
            onClick={() => setShowDropdown(!showDropdown)}
          >
            Change Status ▼
          </button>
          {showDropdown && (
            <div
              className="dropdown-menu"
              style={{
                position: 'absolute',
                right: 0,
                top: '100%',
                zIndex: 10,
                background: 'var(--surface)',
                border: '1px solid var(--border)',
                borderRadius: '9px',
                padding: '8px',
                minWidth: '200px',
                boxShadow: '0 8px 30px rgba(0,0,0,0.1)',
              }}
            >
              {statusOptions.map((option) => (
                <button
                  key={option.value}
                  className={option.className}
                  onClick={() => handleStatusChange(option.value)}
                  style={{
                    width: '100%',
                    textAlign: 'left',
                    marginBottom: '4px',
                    display: 'block',
                  }}
                >
                  {option.label}
                </button>
              ))}
            </div>
          )}
        </div>
      </div>

      <Dialog.Root open={showRejectModal} onOpenChange={setShowRejectModal}>
        <Dialog.Portal>
          <Dialog.Overlay className="overlay employer-review-overlay" />
          <Dialog.Content
            className="modal employer-review-dialog"
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              statusButtonRef.current?.focus();
            }}
          >
            <Dialog.Title>Reject Request</Dialog.Title>
            <Dialog.Description>
              Please provide a reason for rejection (at least 10 characters).
            </Dialog.Description>
            <label>
              Rejection reason
              <textarea
                value={rejectReason}
                onChange={(e) => setRejectReason(e.target.value)}
                minLength={10}
                maxLength={2000}
              />
            </label>
            <div className="actions">
              <Dialog.Close className="button secondary">Cancel</Dialog.Close>
              <button className="button danger" onClick={handleRejectConfirm}>
                Confirm Rejection
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>

      <Dialog.Root open={showApproveModal} onOpenChange={setShowApproveModal}>
        <Dialog.Portal>
          <Dialog.Overlay className="overlay employer-review-overlay" />
          <Dialog.Content
            className="modal employer-review-dialog"
            onCloseAutoFocus={(event) => {
              event.preventDefault();
              statusButtonRef.current?.focus();
            }}
          >
            <Dialog.Title>Approve Employer</Dialog.Title>
            <Dialog.Description>
              Confirm both verification checks and record the evidence for your decision.
            </Dialog.Description>

            <fieldset>
              <legend>Required verification checks</legend>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={companyChecked}
                  onChange={(e) => setCompanyChecked(e.target.checked)}
                />
                <span>I checked the company against independent sources</span>
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={representativeChecked}
                  onChange={(e) => setRepresentativeChecked(e.target.checked)}
                />
                <span>
                  I confirmed the recruiter through independently obtained company contact details
                </span>
              </label>
            </fieldset>

            <label>
              Private investigation notes and independent sources
              <textarea
                value={approveEvidence}
                onChange={(e) => setApproveEvidence(e.target.value)}
                minLength={20}
                maxLength={4000}
                aria-describedby={evidenceHintId}
                placeholder="Record the sources you checked and how you confirmed the recruiter."
              />
            </label>
            <p id={evidenceHintId} className="employer-review-hint">
              At least 20 characters. These notes are private to administrators.
            </p>

            <div className="actions">
              <Dialog.Close className="button secondary">Cancel</Dialog.Close>
              <button className="button" onClick={handleApproveConfirm}>
                Confirm Approval
              </button>
            </div>
          </Dialog.Content>
        </Dialog.Portal>
      </Dialog.Root>
    </>
  );
}

function EmployerReview({ item }: { item: Verification }) {
  const mutation = useAction();

  const handleStatusChange = async (status: string, reason?: string, evidence?: string) => {
    try {
      await mutation.mutateAsync({
        path: `/admin/employers/${item.user_id}/decision`,
        body: {
          action: status,
          version: item.verification_version,
          reason: reason || 'Admin action performed',
          evidence: evidence || '',
          ...(status === 'approve' ? { company_checked: true, representative_checked: true } : {}),
        },
      });
    } catch (error) {
      console.error('Action failed:', error);
    }
  };

  return (
    <article className="card trust-review">
      <h2>
        {item.company_name || 'Company profile incomplete'} <small>#{item.user_id}</small>
      </h2>
      <Badge>{item.verification_status}</Badge>
      <dl className="trust-facts">
        <dt>Legal name</dt>
        <dd>{item.legal_name || 'Not submitted'}</dd>
        <dt>Registration</dt>
        <dd>{item.registration_number || item.registration_explanation || 'Not submitted'}</dd>
        <dt>Website</dt>
        <dd>{item.website || 'Not provided'}</dd>
        <dt>Location</dt>
        <dd>{item.location || 'Not provided'}</dd>
        <dt>Representative</dt>
        <dd>
          {item.recruiter_name} · {item.recruiter_position}
        </dd>
        <dt>Contact supplied by employer</dt>
        <dd>
          {item.contact_email} · {item.contact_phone}
        </dd>
        <dt>Submitted</dt>
        <dd>
          {item.submitted_at ? date(item.submitted_at) : 'Not submitted — approval unavailable'}
        </dd>
      </dl>
      <p>{item.review_reason}</p>
      <p className="muted">
        Use the relevant official business registry and independently obtained company contact
        details. The supplied website and contact information are unverified claims.
      </p>
      <EmployerActionButtons item={item} onStatusChange={handleStatusChange} />
    </article>
  );
}

function ListingReview({ item }: { item: Listing }) {
  const actions = [
    ...(item.status === 'flagged' || item.status === 'pending_ai_review' ? ['approve'] : []),
    item.admin_hidden ? 'restore' : 'hide',
  ];
  return (
    <article className="card trust-review">
      <h2>
        {item.title} <small>#{item.id}</small>
      </h2>
      <p>
        {item.company.company_name} · Employer #{item.employer_id} ·{' '}
        {item.company.verification_status}
      </p>
      <Badge>{item.admin_hidden ? 'Hidden by administrator' : human(item.status)}</Badge>
      <p className="listing-body">{item.description}</p>
      <p>
        {item.location} · {item.duration} · {item.required_skills.join(', ')}
      </p>
      <h3>Automated review signals</h3>
      <p>
        {item.moderation?.risk_reasons?.join('; ') ||
          item.moderation?.error ||
          'No automated risk reasons recorded.'}
      </p>
      <p className="muted">
        {item.moderation_model || 'Review not completed'}. These signals require investigation; they
        do not establish fraud.
      </p>
      <DecisionForm
        path={`/admin/listings/${item.id}/decision`}
        version={item.content_version}
        actions={actions}
      />
    </article>
  );
}

function ReportReview({ item }: { item: Report }) {
  const [inspect, setInspect] = useState(false);
  const listing = useQuery({
    queryKey: ['admin-reported-listing', item.listing_id],
    queryFn: () => api<Listing>(`/admin/listings/${item.listing_id}`),
    enabled: inspect,
  });
  return (
    <article className="card trust-review">
      <h2>
        Report #{item.id} · Listing #{item.listing_id}
      </h2>
      <Badge>{item.status}</Badge>
      <p>
        {human(item.category)} · {date(item.created_at)}
      </p>
      <p className="listing-body">{item.details}</p>
      <button className="button secondary" onClick={() => setInspect(!inspect)}>
        {inspect ? 'Close listing' : 'Inspect reported listing'}
      </button>
      {inspect &&
        (listing.isPending ? (
          <Loading />
        ) : listing.error ? (
          <Failure error={listing.error} />
        ) : (
          <ListingReview item={listing.data} />
        ))}
      <p>{item.resolution}</p>
      {item.status === 'open' && (
        <>
          <p className="muted">
            Hide the listing or suspend the employer separately if warranted. Resolving a report
            alone does not change publication.
          </p>
          <DecisionForm
            path={`/admin/reports/${item.id}/decision`}
            version={item.version}
            actions={['resolved', 'dismissed']}
          />
        </>
      )}
    </article>
  );
}

export function AdminPage({ section }: { section: string }) {
  const [filter, setFilter] = useState(''),
    [page, setPage] = useState(1);
  const overview = section === 'dashboard';
  const resource = ['employers', 'listings', 'reports', 'audit'].includes(section)
    ? section
    : 'employers';
  const stats = useQuery({
    queryKey: ['admin-summary'],
    queryFn: () => api<Record<string, number>>('/admin/summary'),
  });
  const query = useQuery({
    queryKey: ['admin', resource, filter, page],
    queryFn: () =>
      api<Page<Verification | Listing | Report | Audit>>(
        `/admin/${resource}?status=${filter}&page=${page}`,
      ),
    enabled: !overview,
  });
  const options =
    resource === 'employers'
      ? ['pending', 'approved', 'rejected', 'suspended']
      : resource === 'listings'
        ? ['flagged', 'pending_ai_review', 'active', 'closed', 'hidden']
        : ['open', 'resolved', 'dismissed'];
  return (
    <>
      <Heading
        eyebrow="Administration"
        title={
          overview
            ? 'Trust & safety overview'
            : human(
                resource === 'employers'
                  ? 'employer_verification'
                  : resource === 'listings'
                    ? 'content_review'
                    : resource === 'reports'
                      ? 'student_reports'
                      : 'audit_history',
              )
        }
      >
        Review evidence, record decisions, and protect applicants.
      </Heading>
      {overview ? (
        <>
          {stats.isPending ? (
            <Loading />
          ) : stats.error ? (
            <Failure error={stats.error} />
          ) : (
            <div className="trust-stats">
              {Object.entries(stats.data).map(([key, value]) => (
                <section className="card" key={key}>
                  <span className="muted">{human(key)}</span>
                  <h2>{value}</h2>
                </section>
              ))}
            </div>
          )}
          <section className="card">
            <h2>Review queues</h2>
            <div className="actions">
              {['employers', 'listings', 'reports', 'audit'].map((x) => (
                <Link className="button secondary" key={x} href={`/admin/${x}`}>
                  {human(x)}
                </Link>
              ))}
            </div>
            <p>
              Approve only after confirming company identity and recruiting authority through
              independent sources. Pending companies remain unpublished even when their listing
              passes automated review.
            </p>
          </section>
        </>
      ) : (
        <>
          {resource !== 'audit' && (
            <label className="trust-filter">
              Filter by status
              <select
                value={filter}
                onChange={(e) => {
                  setFilter(e.target.value);
                  setPage(1);
                }}
              >
                <option value="">All statuses</option>
                {options.map((x) => (
                  <option value={x} key={x}>
                    {human(x)}
                  </option>
                ))}
              </select>
            </label>
          )}
          {query.isPending ? (
            <Loading />
          ) : query.error ? (
            <Failure error={query.error} />
          ) : (
            <>
              {!query.data.items.length && <Empty title="No records in this queue" />}
              <div className="stack">
                {query.data.items.map((item) =>
                  resource === 'employers' ? (
                    <EmployerReview
                      key={`${(item as Verification).user_id}-${(item as Verification).verification_version}`}
                      item={item as Verification}
                    />
                  ) : resource === 'listings' ? (
                    <ListingReview
                      key={`${(item as Listing).id}-${(item as Listing).content_version}`}
                      item={item as Listing}
                    />
                  ) : resource === 'reports' ? (
                    <ReportReview
                      key={`${(item as Report).id}-${(item as Report).version}`}
                      item={item as Report}
                    />
                  ) : (
                    <article className="card" key={(item as Audit).id}>
                      <h2>
                        {(item as Audit).action} · {(item as Audit).target_type} #
                        {(item as Audit).target_id}
                      </h2>
                      <p>
                        Actor #{(item as Audit).actor_id} · {date((item as Audit).created_at)}
                      </p>
                      <p>{(item as Audit).reason}</p>
                      <p className="listing-body">{(item as Audit).evidence}</p>
                    </article>
                  ),
                )}
              </div>
              <Pages page={page} total={query.data.total} change={setPage} />
            </>
          )}
        </>
      )}
    </>
  );
}
