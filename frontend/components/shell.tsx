'use client';
import { useEffect, useState } from 'react';
import Link from 'next/link';
import { usePathname, useRouter } from 'next/navigation';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import * as Dialog from '@radix-ui/react-dialog';
import { toast } from 'sonner';
import {
  Bell,
  Bookmark,
  BriefcaseBusiness,
  FileText,
  LayoutDashboard,
  LogOut,
  Menu,
  Settings,
  Sparkles,
  UserRound,
  Users,
  X,
} from 'lucide-react';
import { useAuth } from '@/providers';
import { api, ApiError } from '@/lib/api';
import type { Notice, Page, Role, User } from '@/lib/types';
import { Brand, Failure, Loading, ThemeSelect } from './ui';

export function noticeHref(notice: Notice, role: Role) {
  return notice.related.application_id
    ? `/${role}/${role === 'student' ? 'applications' : 'applicants'}?application=${notice.related.application_id}`
    : notice.related.internship_id
      ? `/student/internships/${notice.related.internship_id}`
      : `/${role}/notifications`;
}

function NotificationBell({ role }: { role: Role }) {
  const [open, setOpen] = useState(false);
  useEffect(() => {
    const close = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setOpen(false);
    };
    document.addEventListener('keydown', close);
    return () => document.removeEventListener('keydown', close);
  }, []);
  const count = useQuery({
    queryKey: ['notification-count'],
    queryFn: () => api<{ unread: number }>('/notifications/count'),
    refetchInterval: 25000,
    refetchIntervalInBackground: false,
  });
  const preview = useQuery({
    queryKey: ['notification-preview'],
    queryFn: () => api<Page<Notice>>('/notifications?page_size=4'),
    enabled: open,
    refetchInterval: open ? 25000 : false,
    refetchIntervalInBackground: false,
  });
  return (
    <div className="notification-wrap">
      <button
        className="icon-button"
        aria-label={`Notifications (${count.data?.unread || 0} unread)`}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
      >
        <Bell size={18} />
        {!!count.data?.unread && <span className="count-dot">{count.data.unread}</span>}
      </button>
      {open && (
        <div className="notification-dropdown">
          <div className="status-row">
            <strong>Notifications</strong>
            <button aria-label="Close notifications" onClick={() => setOpen(false)}>
              <X size={16} />
            </button>
          </div>
          {preview.data?.items.map((n) => (
            <article key={n.id}>
              <Link href={noticeHref(n, role)} onClick={() => setOpen(false)}>
                {n.title}
              </Link>
              <p>{n.body}</p>
            </article>
          ))}
          {preview.data?.items.length === 0 && (
            <p style={{ paddingTop: 15 }}>You’re all caught up.</p>
          )}
          <Link
            className="text-button"
            href={`/${role}/notifications`}
            onClick={() => setOpen(false)}
          >
            View all notifications →
          </Link>
        </div>
      )}
    </div>
  );
}

function Nav({ user, onNavigate }: { user: User; onNavigate?: () => void }) {
  const path = usePathname(),
    router = useRouter(),
    client = useQueryClient();
  const links =
    user.role === 'student'
      ? ([
          ['dashboard', 'Overview', LayoutDashboard],
          ['profile', 'My profile', UserRound],
          ['internships', 'Find internships', BriefcaseBusiness],
          ['saved', 'Saved internships', Bookmark],
          ['applications', 'My applications', FileText],
          ['ask-ai', 'Ask AI', Sparkles],
          ['reports', 'My reports', FileText],
          ['notifications', 'Notifications', Bell],
        ] as const)
      : user.role === 'admin'
        ? ([
            ['dashboard', 'Review overview', LayoutDashboard],
            ['employers', 'Employer verification', BriefcaseBusiness],
            ['listings', 'Content review', FileText],
            ['reports', 'Student reports', Users],
            ['audit', 'Audit history', FileText],
          ] as const)
        : ([
            ['dashboard', 'Overview', LayoutDashboard],
            ['profile', 'Company profile', BriefcaseBusiness],
            ['verification', 'Verification', UserRound],
            ['internships', 'My listings', FileText],
            ['applicants', 'Applicants', Users],
            ['notifications', 'Notifications', Bell],
          ] as const);
  return (
    <>
      <Brand role={user.role} />
      <div className="workspace-label">{user.role} workspace</div>
      <nav className="nav-list" aria-label="Workspace">
        {links.map(([slug, label, Icon]) => (
          <Link
            key={slug}
            onClick={onNavigate}
            className={`nav-link ${path.startsWith(`/${user.role}/${slug}`) ? 'active' : ''}`}
            href={`/${user.role}/${slug}`}
          >
            <Icon size={18} />
            {label}
          </Link>
        ))}
      </nav>
      <div className="sidebar-bottom">
        <Link
          onClick={onNavigate}
          className={`nav-link ${path.endsWith('/settings') ? 'active' : ''}`}
          href={`/${user.role}/settings`}
        >
          <Settings size={18} />
          Account settings
        </Link>
        <button
          className="nav-link"
          onClick={async () => {
            await api('/auth/logout', 'POST');
            client.clear();
            router.push('/login');
          }}
        >
          <LogOut size={18} />
          Sign out
        </button>
        <div className="sidebar-note">
          <strong>A little progress, every day.</strong>
          <p>
            {user.role === 'student'
              ? 'Keep your projects and skills up to date for more useful matches.'
              : 'Give students clear expectations and thoughtful feedback.'}
          </p>
        </div>
      </div>
    </>
  );
}

function AccountMenu({ user }: { user: User }) {
  const router = useRouter(),
    client = useQueryClient();
  return (
    <details className="account-menu">
      <summary className="account-link" aria-label="Account menu">
        <span className="avatar">
          {user.name
            .split(' ')
            .map((n) => n[0])
            .slice(0, 2)
            .join('')}
        </span>
        <span>{user.name}</span>
      </summary>
      <div className="account-dropdown">
        <Link className="nav-link" href={`/${user.role}/settings`}>
          <Settings size={16} />
          Account settings
        </Link>
        <button
          className="nav-link"
          onClick={async () => {
            try {
              await api('/auth/logout', 'POST');
              client.clear();
              router.push('/login');
            } catch (error) {
              toast.error(error instanceof Error ? error.message : 'Sign out failed');
            }
          }}
        >
          <LogOut size={16} />
          Sign out
        </button>
      </div>
    </details>
  );
}

export function Shell({ role, children }: { role: Role; children: React.ReactNode }) {
  const auth = useAuth(),
    router = useRouter(),
    [menu, setMenu] = useState(false);
  const health = useQuery({
    queryKey: ['health'],
    queryFn: () => api<{ ai_mode: string }>('/health'),
  });
  useEffect(() => {
    if (auth.error instanceof ApiError && auth.error.status === 401) router.replace('/login');
    else if (auth.data && auth.data.role !== role) router.replace(`/${auth.data.role}/dashboard`);
  }, [auth.error, auth.data, role, router]);
  if (auth.isPending)
    return (
      <main className="landing" style={{ paddingTop: 60 }}>
        <Loading />
      </main>
    );
  if (auth.error)
    return (
      <main className="landing" style={{ paddingTop: 60 }}>
        <Failure error={auth.error} retry={() => auth.refetch()} />
        <Link className="button" href="/login">
          Sign in
        </Link>
      </main>
    );
  if (!auth.data || auth.data.role !== role) return <Loading />;
  const user = auth.data;
  return (
    <div className="shell">
      <a className="skip-link" href="#main-content">
        Skip to content
      </a>
      <aside className="sidebar">
        <Nav user={user} />
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <div className="actions">
            <Dialog.Root open={menu} onOpenChange={setMenu}>
              <Dialog.Trigger className="icon-button mobile-menu" aria-label="Open navigation">
                <Menu size={20} />
              </Dialog.Trigger>
              <Dialog.Portal>
                <Dialog.Overlay className="overlay" />
                <Dialog.Content className="drawer-sidebar">
                  <Dialog.Title className="sr-only">Navigation</Dialog.Title>
                  <Dialog.Description className="sr-only">Your workspace pages</Dialog.Description>
                  <Nav user={user} onNavigate={() => setMenu(false)} />
                  <Dialog.Close className="modal-close" aria-label="Close navigation">
                    <X size={20} />
                  </Dialog.Close>
                </Dialog.Content>
              </Dialog.Portal>
            </Dialog.Root>
            <span className="topbar-title">Your next chapter starts with a next step.</span>
          </div>
          <div className="actions">
            <ThemeSelect />
            <NotificationBell role={role} />
            <AccountMenu user={user} />
          </div>
        </header>
        {health.data?.ai_mode === 'demo' && (
          <div className="demo-strip">
            Demo AI · Resume extraction, review, and feedback use deterministic rules.
            Recommendations use the real local embedding model.
          </div>
        )}
        <main id="main-content" className="content">
          {children}
          <p className="footer-note">NovaRoute · Make your next step a meaningful one.</p>
        </main>
      </div>
    </div>
  );
}
