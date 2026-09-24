'use client';
import { useState } from 'react';
import Link from 'next/link';
import { useRouter } from 'next/navigation';
import { useQuery } from '@tanstack/react-query';
import { Bookmark, BookmarkCheck, Clock3, MapPin, Plus, ArrowUpRight } from 'lucide-react';
import { api, date, human, params } from '@/lib/api';
import { useInternshipStates } from '@/lib/states';
import type { Application, Listing, Match, Page, Saved } from '@/lib/types';
import { useAction } from '@/providers';
import { ReportForm } from './trust';
import { Badge, Confirm, Empty, Failure, Form, Heading, Loading, Pagination, Tags } from './ui';

export function ListingCard({ listing, match }: { listing: Listing; match?: Match }) {
  const action = useAction();
  const states = useInternshipStates();
  const saved = states.data?.saved_ids.includes(listing.id) || false;
  const applied = states.data?.applied_ids.includes(listing.id) || false;
  return (
    <article className="card listing-card">
      <div className="company-row">
        <span className="company-icon">
          {listing.company.company_name.slice(0, 2).toUpperCase()}
        </span>
        <div style={{ flex: 1 }}>
          <h3>
            <Link href={`/student/internships/${listing.id}`}>{listing.title}</Link>
          </h3>
          <small className="muted">{listing.company.company_name}</small>
        </div>
        <button
          className="icon-button"
          aria-label={saved ? `Unsave ${listing.title}` : `Save ${listing.title}`}
          disabled={action.isPending || !states.data}
          onClick={() =>
            action.mutate({
              path: `/student/saved/${listing.id}`,
              method: saved ? 'DELETE' : 'POST',
              body: saved ? undefined : { note: '' },
            })
          }
        >
          {saved ? <BookmarkCheck size={17} /> : <Bookmark size={17} />}
        </button>
      </div>
      <div className="listing-meta">
        <span>
          <MapPin size={13} />
          {listing.location} · {human(listing.work_mode)}
        </span>
        <span>
          <Clock3 size={13} />
          {listing.duration}
        </span>
      </div>
      <p className="listing-description">{listing.description}</p>
      <div className="chips">
        {listing.required_skills.slice(0, 5).map((s) => (
          <span className="chip" key={s}>
            {s}
          </span>
        ))}
        {listing.required_skills.length > 5 && (
          <span className="chip">+{listing.required_skills.length - 5}</span>
        )}
      </div>
      {match && (
        <div>
          <Badge>{`${match.percentage}% Match`}</Badge>
          <p className="match-help">Semantic similarity · not hiring probability or accuracy</p>
        </div>
      )}
      <div className="listing-bottom">
        <div>
          <small className="muted">
            {listing.stipend_min
              ? `${listing.currency} ${listing.stipend_min}${listing.stipend_max ? '–' + listing.stipend_max : ''}`
              : 'Stipend not specified'}
          </small>
          {applied && (
            <div>
              <Badge>Applied</Badge>
            </div>
          )}
        </div>
        <Link className="button secondary" href={`/student/internships/${listing.id}`}>
          View role
          <ArrowUpRight size={14} />
        </Link>
      </div>
    </article>
  );
}

export function Browse() {
  const [filters, setFilters] = useState({
      q: '',
      skill: '',
      location: '',
      work_mode: '',
      sort: 'newest',
    }),
    [page, setPage] = useState(1);
  const listings = useQuery({
    queryKey: ['listings', filters, page],
    queryFn: () => api<Page<Listing>>(`/internships?${params({ ...filters, page })}`),
  });
  const change = (key: string, value: string) => {
    setFilters({ ...filters, [key]: value });
    setPage(1);
  };
  return (
    <>
      <Heading eyebrow="Explore what’s next" title="Find your next opportunity">
        Technical internships, with room to learn and grow.
      </Heading>
      <div className="filters">
        <label>
          Search internships
          <input
            placeholder="Role, keyword, or technology"
            value={filters.q}
            onChange={(e) => change('q', e.target.value)}
          />
        </label>
        <label>
          Required skill
          <input
            placeholder="e.g. Python"
            value={filters.skill}
            onChange={(e) => change('skill', e.target.value)}
          />
        </label>
        <label>
          Location
          <input
            placeholder="City or region"
            value={filters.location}
            onChange={(e) => change('location', e.target.value)}
          />
        </label>
        <label>
          Work mode
          <select value={filters.work_mode} onChange={(e) => change('work_mode', e.target.value)}>
            <option value="">All work modes</option>
            {['remote', 'hybrid', 'onsite'].map((v) => (
              <option key={v} value={v}>
                {human(v)}
              </option>
            ))}
          </select>
        </label>
      </div>
      <div className="status-row" style={{ marginBottom: 20 }}>
        <span className="muted" style={{ fontSize: 13 }}>
          {listings.data?.total ?? '…'} opportunities to explore
        </span>
        <label className="actions">
          Sort
          <select
            aria-label="Sort internships"
            style={{ width: 'auto' }}
            value={filters.sort}
            onChange={(e) => change('sort', e.target.value)}
          >
            <option value="newest">Newest first</option>
            <option value="oldest">Oldest first</option>
            <option value="title">Title A–Z</option>
          </select>
        </label>
      </div>
      {listings.isPending ? (
        <Loading />
      ) : listings.error ? (
        <Failure error={listings.error} retry={() => listings.refetch()} />
      ) : (
        <>
          {listings.data.items.length ? (
            <div className="grid-2">
              {listings.data.items.map((item) => (
                <ListingCard key={item.id} listing={item} />
              ))}
            </div>
          ) : (
            <Empty title="No internships match those filters">
              Try another skill or location, or clear your search.
            </Empty>
          )}
          <Pagination page={page} setPage={setPage} total={listings.data.total} size={12} />
        </>
      )}
    </>
  );
}

export function ListingDetail({ id }: { id: number }) {
  const query = useQuery({
      queryKey: ['listing', id],
      queryFn: () => api<Listing>(`/internships/${id}`),
    }),
    action = useAction();
  const states = useInternshipStates();
  const applications = useQuery({
    queryKey: ['application-for-listing', id],
    queryFn: () => api<Page<Application>>(`/applications?internship_id=${id}`),
  });
  const matches = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => api<{ items: Match[] }>('/student/recommendations'),
    retry: false,
  });
  if (query.isPending) return <Loading />;
  if (query.error) return <Failure error={query.error} retry={() => query.refetch()} />;
  const item = query.data,
    isSaved = states.data?.saved_ids.includes(id),
    application = applications.data?.items[0],
    match = matches.data?.items.find((m) => m.internship.id === id);
  return (
    <>
      <Link className="text-button" href="/student/internships">
        ← Back to internships
      </Link>
      <Heading
        eyebrow={item.company.company_name}
        title={item.title}
        action={
          <button
            className="button secondary"
            disabled={action.isPending}
            onClick={() =>
              action.mutate({
                path: `/student/saved/${id}`,
                method: isSaved ? 'DELETE' : 'POST',
                body: isSaved ? undefined : { note: '' },
              })
            }
          >
            <Bookmark size={16} />
            {isSaved ? 'Unsave internship' : 'Save internship'}
          </button>
        }
      >
        {item.location} · {human(item.work_mode)}
      </Heading>
      <div className="split">
        <section className="card">
          <Badge>
            {item.provenance.kind === 'synthetic'
              ? 'Synthetic demo listing'
              : item.provenance.kind === 'kaggle'
                ? 'Historical dataset example'
                : 'Internship'}
          </Badge>
          <div className="detail-meta">
            <div>
              <small>Duration</small>
              {item.duration}
            </div>
            <div>
              <small>Stipend</small>
              {item.stipend_min
                ? `${item.currency} ${item.stipend_min}${item.stipend_max ? '–' + item.stipend_max : ''}`
                : 'Not specified'}
            </div>
            <div>
              <small>Work arrangement</small>
              {human(item.work_mode)}
            </div>
            <div>
              <small>Apply by</small>
              {item.deadline ? date(item.deadline) : 'No deadline specified'}
            </div>
          </div>
          <h2>About the opportunity</h2>
          <p className="listing-body">{item.description}</p>
          <h3>Skills you’ll bring</h3>
          <div className="chips">
            {item.required_skills.map((s) => (
              <span className="chip" key={s}>
                {s}
              </span>
            ))}
          </div>
          <hr />
          <h3>About {item.company.company_name}</h3>
          <Badge>
            {item.company.demo_company
              ? 'Demo company — not independently verified'
              : 'Company and representative checked'}
          </Badge>
          {item.company.reviewed_at && (
            <p className="muted">Reviewed {date(item.company.reviewed_at)}</p>
          )}
          <p className="muted">
            {item.company.description || 'The employer has not added a company description.'}
          </p>
          {item.company.website && (
            <a
              className="text-button"
              href={item.company.website}
              target="_blank"
              rel="noopener noreferrer"
            >
              Company website ↗
            </a>
          )}
          <p className="match-help" style={{ marginTop: 20 }}>
            Verification and content review reduce risk but do not guarantee safety. Never pay to
            apply.
          </p>
        </section>
        <aside className="stack">
          <ReportForm listingId={id} />
          {match && (
            <div className="card">
              <Badge>{`${match.percentage}% Match`}</Badge>
              <p className="match-help">
                Semantic similarity, not hiring probability or measured accuracy.
              </p>
              <h3 style={{ marginTop: 18 }}>Why this appeared</h3>
              <p className="muted" style={{ fontSize: 13 }}>
                {match.explanation}
              </p>
            </div>
          )}
          <div className="card">
            <h2>Your next step</h2>
            {applications.isPending ? (
              <Loading />
            ) : applications.error ? (
              <Failure error={applications.error} />
            ) : application ? (
              <>
                <Badge>{application.status}</Badge>
                <p className="muted" style={{ marginTop: 15 }}>
                  You’ve already applied to this internship.
                </p>
                <Link
                  className="button secondary"
                  href={`/student/applications?application=${application.id}`}
                >
                  View application
                </Link>
              </>
            ) : (
              <>
                <p className="muted" style={{ fontSize: 13 }}>
                  Your confirmed skills, coursework, and projects will be shared as a snapshot. Your
                  private resume file stays private.
                </p>
                <Form
                  fields={[
                    {
                      name: 'cover_message',
                      label: 'Cover message',
                      type: 'textarea',
                      maxLength: 4000,
                      hint: 'Tell the employer what interests you about this role.',
                    },
                  ]}
                  onSubmit={async (values) => {
                    await action.mutateAsync({
                      path: '/applications',
                      body: { internship_id: id, cover_message: values.cover_message || '' },
                    });
                  }}
                  busy={action.isPending}
                  submitLabel="Submit application"
                />
              </>
            )}
          </div>
        </aside>
      </div>
    </>
  );
}

export function SavedPage() {
  const [page, setPage] = useState(1),
    query = useQuery({
      queryKey: ['saved', page],
      queryFn: () => api<Page<Saved>>(`/student/saved?page=${page}`),
    }),
    action = useAction();
  return (
    <>
      <Heading eyebrow="Keep the possibilities close" title="Saved internships">
        A shortlist for your next step, with notes just for you.
      </Heading>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Failure error={query.error} retry={() => query.refetch()} />
      ) : (
        <>
          {query.data.items.length ? (
            <div className="grid-2">
              {query.data.items.map((item) => (
                <article className="card" key={item.id}>
                  <div className="status-row">
                    <h3>{item.internship.title}</h3>
                    <button
                      className="text-button"
                      disabled={action.isPending}
                      onClick={() =>
                        action.mutate({
                          path: `/student/saved/${item.internship_id}`,
                          method: 'DELETE',
                        })
                      }
                    >
                      Unsave
                    </button>
                  </div>
                  {item.available ? (
                    <Link
                      className="text-button"
                      href={`/student/internships/${item.internship_id}`}
                    >
                      View opportunity →
                    </Link>
                  ) : (
                    <Badge>No longer available</Badge>
                  )}
                  <div style={{ marginTop: 20 }}>
                    <Form
                      key={`${item.id}-${item.note}`}
                      fields={[
                        { name: 'note', label: 'Private note', type: 'textarea', maxLength: 2000 },
                      ]}
                      initial={{ note: item.note }}
                      onSubmit={async (data) => {
                        await action.mutateAsync({
                          path: `/student/saved/${item.internship_id}`,
                          method: 'PATCH',
                          body: data,
                        });
                      }}
                      busy={action.isPending}
                      submitLabel="Save note"
                    />
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <Empty title="Make room for your favorites" href="/student/internships">
              Save interesting roles to compare them later.
            </Empty>
          )}
          <Pagination page={page} setPage={setPage} total={query.data.total} size={20} />
        </>
      )}
    </>
  );
}

export function EmployerListings() {
  const [q, setQ] = useState(''),
    [status, setStatus] = useState(''),
    [page, setPage] = useState(1),
    action = useAction();
  const query = useQuery({
    queryKey: ['employer-listings', q, status, page],
    queryFn: () => api<Page<Listing>>(`/employer/internships?${params({ q, status, page })}`),
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });
  return (
    <>
      <Heading
        eyebrow="Build your next team"
        title="Your internship listings"
        action={
          <Link className="button" href="/employer/internships/new">
            <Plus size={17} />
            Post an internship
          </Link>
        }
      >
        Manage opportunities and see their automated review status.
      </Heading>
      <p className="alert">
        Public visibility requires employer approval and content review.{' '}
        <Link href="/employer/verification">Check your verification status →</Link>
      </p>
      <div className="filters">
        <label>
          Search your listings
          <input
            value={q}
            onChange={(e) => {
              setQ(e.target.value);
              setPage(1);
            }}
            placeholder="Search titles"
          />
        </label>
        <label>
          Review status
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All states</option>
            {['active', 'pending_ai_review', 'flagged', 'closed'].map((s) => (
              <option value={s} key={s}>
                {human(s)}
              </option>
            ))}
          </select>
        </label>
      </div>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Failure error={query.error} />
      ) : (
        <>
          <div className="stack">
            {query.data.items.map((item) => (
              <article className="card" key={item.id}>
                <div className="application-head">
                  <div>
                    <h3>{item.title}</h3>
                    <p className="muted" style={{ fontSize: 13 }}>
                      {item.location} · {human(item.work_mode)} · {item.duration}
                    </p>
                  </div>
                  <Badge>{item.status}</Badge>
                </div>
                <Review listing={item} />
                <div className="actions">
                  <Link className="button secondary" href={`/employer/internships/${item.id}/edit`}>
                    Edit listing
                  </Link>
                  <Link className="text-button" href={`/employer/applicants?internship=${item.id}`}>
                    View applicants
                  </Link>
                  {item.status === 'active' ? (
                    <Confirm
                      title="Close this internship?"
                      description="New applications will stop. Existing application history will remain."
                      trigger={<button className="text-button">Close listing</button>}
                      onConfirm={() =>
                        action.mutateAsync({
                          path: `/internships/${item.id}/close`,
                          body: { version: item.content_version },
                        })
                      }
                      busy={action.isPending}
                    />
                  ) : (
                    <button
                      className="text-button"
                      disabled={action.isPending}
                      onClick={() =>
                        action.mutate({
                          path: `/internships/${item.id}/${item.status === 'closed' ? 'reopen' : 'review'}`,
                          body: { version: item.content_version },
                        })
                      }
                    >
                      {item.status === 'closed' ? 'Reopen & review' : 'Request re-review'}
                    </button>
                  )}
                  <Confirm
                    title="Delete this listing?"
                    description="It will be removed from discovery. Application and decision history will remain."
                    trigger={<button className="text-button danger-text">Delete</button>}
                    onConfirm={() =>
                      action.mutateAsync({ path: `/internships/${item.id}`, method: 'DELETE' })
                    }
                    busy={action.isPending}
                  />
                </div>
              </article>
            ))}
          </div>
          {query.data.items.length === 0 && (
            <Empty
              title="Your next great intern starts here"
              href="/employer/internships/new"
              action="Create a listing"
            >
              Describe the role, the learning opportunities, and the skills you need.
            </Empty>
          )}
          <Pagination page={page} setPage={setPage} total={query.data.total} size={20} />
        </>
      )}
    </>
  );
}

export function Review({ listing }: { listing: Listing }) {
  return (
    <>
      {listing.admin_hidden && (
        <p className="alert">
          Hidden by an administrator. Editing or requesting automated review cannot restore
          publication.
        </p>
      )}
      {listing.company.verification_status !== 'approved' && (
        <p className="alert">
          Employer verification: {human(listing.company.verification_status)}. This listing is not
          public. <Link href="/employer/verification">View verification →</Link>
        </p>
      )}
      {listing.status === 'pending_ai_review' && (
        <p className="alert">
          {listing.moderation?.error ||
            'Automated content review is pending. This listing is private until a valid result is received.'}
        </p>
      )}
      {listing.moderation?.risk_reasons?.map((r) => (
        <p className="alert" key={r}>
          {r}
        </p>
      ))}
      {listing.moderation?.suggested_changes?.map((s) => (
        <p className="muted" key={s}>
          {s}
        </p>
      ))}
      {listing.status === 'active' && (
        <p className="match-help" style={{ marginBottom: 15 }}>
          {listing.moderation?.manual_review
            ? 'Approved after administrator content review'
            : 'Passed automated content review'}{' '}
          · not a guarantee of safety.
        </p>
      )}
    </>
  );
}

export function ListingEditor({ id }: { id?: number }) {
  const query = useQuery({
    queryKey: ['listing', id],
    queryFn: () => api<Listing>(`/internships/${id}`),
    enabled: !!id,
    refetchInterval: 5000,
    refetchIntervalInBackground: false,
  });
  if (id && query.isPending) return <Loading />;
  if (query.error) return <Failure error={query.error} />;
  return (
    <>
      <Heading
        eyebrow="Open a door to new talent"
        title={id ? 'Edit internship' : 'Post an internship'}
      >
        Clear expectations help students find their fit.
      </Heading>
      {query.data && <Review listing={query.data} />}
      <ListingEditorForm key={query.data?.content_version || 'new'} listing={query.data} />
    </>
  );
}

function ListingEditorForm({ listing }: { listing?: Listing }) {
  const router = useRouter(),
    [skills, setSkills] = useState(listing?.required_skills || []),
    action = useAction<Listing>((result) => router.push(`/employer/internships/${result.id}/edit`));
  const initial: Record<string, string> = {
    title: listing?.title || '',
    description: listing?.description || '',
    location: listing?.location || '',
    work_mode: listing?.work_mode || 'remote',
    duration: listing?.duration || '',
    stipend_min: listing?.stipend_min || '',
    stipend_max: listing?.stipend_max || '',
    currency: listing?.currency || '',
    deadline: listing?.deadline?.slice(0, 16) || '',
  };
  return (
    <section className="card narrow">
      <Form
        fields={[
          { name: 'title', label: 'Internship title', required: true, maxLength: 200 },
          {
            name: 'description',
            label: 'Role description',
            type: 'textarea',
            required: true,
            hint: 'At least 30 characters. Describe responsibilities, support, and learning outcomes.',
          },
          { name: 'location', label: 'Location', required: true, maxLength: 200 },
          { name: 'work_mode', label: 'Work mode', options: ['remote', 'hybrid', 'onsite'] },
          { name: 'duration', label: 'Duration', required: true, maxLength: 100 },
          { name: 'stipend_min', label: 'Minimum stipend (optional)', type: 'number' },
          { name: 'stipend_max', label: 'Maximum stipend (optional)', type: 'number' },
          {
            name: 'currency',
            label: 'Currency code',
            hint: 'Three uppercase letters, e.g. USD. Required for a numeric stipend.',
            maxLength: 3,
          },
          {
            name: 'deadline',
            label: 'Application deadline (UTC, optional)',
            type: 'datetime-local',
          },
        ]}
        initial={initial}
        onSubmit={async (values) => {
          const body = {
            ...values,
            required_skills: skills,
            stipend_min: values.stipend_min || null,
            stipend_max: values.stipend_max || null,
            currency: values.currency?.toUpperCase() || null,
            deadline: values.deadline ? values.deadline + ':00Z' : null,
            ...(listing ? { content_version: listing.content_version } : {}),
          };
          await action.mutateAsync({
            path: listing ? `/internships/${listing.id}` : '/internships',
            method: listing ? 'PATCH' : 'POST',
            body,
          });
        }}
        busy={action.isPending}
        submitLabel={listing ? 'Save & request review' : 'Create & request review'}
      >
        <Tags label="Required skills" values={skills} onChange={setSkills} />
        <p className="alert">
          Submitting starts an automated content review. The listing stays private while review is
          pending or flagged. All edits trigger a new review. Employer approval is also required,
          and an administrator hide remains in effect after edits.
        </p>
      </Form>
    </section>
  );
}
