'use client';
import Link from 'next/link';
import { useQuery } from '@tanstack/react-query';
import { ArrowRight, BarChart3, FileUp, Plus } from 'lucide-react';
import { api } from '@/lib/api';
import type { Application, Match, Notice, Page, Role } from '@/lib/types';
import { useAuth } from '@/providers';
import { Empty, Failure, Heading, Loading } from './ui';
import { ListingCard } from './listings';
import { NoticeCard } from './activity';

export function Dashboard({ role }: { role: Role }) {
  const auth = useAuth(),
    query = useQuery({
      queryKey: ['dashboard'],
      queryFn: () => api<{ counts: Record<string, number>; recent_events: Notice[] }>('/dashboard'),
    });
  const matches = useQuery({
    queryKey: ['recommendations'],
    queryFn: () => api<{ items: Match[]; threshold: number }>('/student/recommendations'),
    enabled: role === 'student',
    retry: false,
  });
  const applicants = useQuery({
    queryKey: ['recent-applicants'],
    queryFn: () => api<Page<Application>>('/applications?page_size=5'),
    enabled: role === 'employer',
  });
  return (
    <>
      <Heading
        eyebrow="Your next chapter"
        title={`Welcome back, ${auth.data?.name.split(' ')[0] || 'there'}.`}
        action={
          <Link
            className="button secondary"
            href={role === 'student' ? '/student/profile' : '/employer/internships/new'}
          >
            {role === 'student' ? <FileUp size={17} /> : <Plus size={17} />}
            {role === 'student' ? 'Update my profile' : 'Post an internship'}
          </Link>
        }
      >
        {role === 'student'
          ? 'A little progress today. New possibilities tomorrow.'
          : 'Create meaningful opportunities. Discover emerging talent.'}
      </Heading>
      {query.isPending ? (
        <Loading />
      ) : query.error ? (
        <Failure error={query.error} retry={() => query.refetch()} />
      ) : (
        <div className="grid-3 metrics">
          {Object.entries(query.data.counts).map(([label, count]) => (
            <div className="card metric" key={label}>
              <div>
                <span className="muted" style={{ fontSize: 12 }}>
                  {label}
                </span>
                <div className="metric-value">
                  {count}
                  {label === 'Profile completion' ? '%' : ''}
                </div>
              </div>
              <span className="metric-icon">
                <BarChart3 size={21} />
              </span>
            </div>
          ))}
        </div>
      )}
      {role === 'student' ? (
        <>
          <div className="section-title">
            <h2>Opportunities that connect</h2>
            <Link className="text-button" href="/student/internships">
              Browse all <ArrowRight size={13} style={{ display: 'inline' }} />
            </Link>
          </div>
          <div className="feature-banner">
            <div>
              <p className="eyebrow">Built around your experience</p>
              <h3>Let your projects open doors.</h3>
              <p>
                Your confirmed skills, coursework, and projects help us find meaningful
                similarities. The default cutoff is strictly above 80%.
              </p>
            </div>
            <Link className="button secondary" href="/student/profile">
              Complete your profile
            </Link>
          </div>
          {matches.isPending ? (
            <Loading />
          ) : matches.error ? (
            <Failure error={matches.error} retry={() => matches.refetch()} />
          ) : matches.data?.items.length ? (
            <div className="grid-2">
              {matches.data.items.slice(0, 4).map((m) => (
                <ListingCard key={m.internship.id} listing={m.internship} match={m} />
              ))}
            </div>
          ) : (
            <Empty title="Your next match is still out there" href="/student/internships">
              No eligible internships currently exceed the similarity cutoff. Add your experience to
              your profile or explore all available opportunities.
            </Empty>
          )}
          <p className="match-help" style={{ marginTop: 12 }}>
            Match percentages describe semantic similarity—not hiring probability or measured model
            accuracy.
          </p>
        </>
      ) : (
        <>
          <div className="section-title">
            <h2>Recent applicants</h2>
            <Link className="text-button" href="/employer/applicants">
              View all →
            </Link>
          </div>
          {applicants.isPending ? (
            <Loading />
          ) : applicants.error ? (
            <Failure error={applicants.error} />
          ) : applicants.data?.items.length ? (
            <div className="card">
              {applicants.data.items.map((a) => (
                <div className="event" key={a.id}>
                  <Link className="text-button" href={`/employer/applicants?application=${a.id}`}>
                    {a.student_name} · {a.internship_title}
                  </Link>
                  <p>{a.status}</p>
                </div>
              ))}
            </div>
          ) : (
            <Empty
              title="A new connection starts with a listing"
              href="/employer/internships/new"
              action="Post an internship"
            >
              Applicants to your opportunities will appear here.
            </Empty>
          )}
        </>
      )}
      <div className="section-title">
        <h2>Recent activity</h2>
        <Link className="text-button" href={`/${role}/notifications`}>
          View inbox →
        </Link>
      </div>
      {query.data?.recent_events.length ? (
        <div className="card">
          {query.data.recent_events.map((n) => (
            <NoticeCard key={n.id} notice={n} role={role} />
          ))}
        </div>
      ) : (
        <Empty title="A fresh start">
          Your application events and new-match alerts will appear here.
        </Empty>
      )}
    </>
  );
}
