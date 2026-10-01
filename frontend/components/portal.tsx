'use client';
import { useParams } from 'next/navigation';
import type { Role } from '@/lib/types';
import { Shell } from './shell';
import { Dashboard } from './dashboard';
import { StudentProfilePage, EmployerProfilePage } from './profile';
import { Browse, EmployerListings, ListingDetail, ListingEditor, SavedPage } from './listings';
import { ApplicationsPage, Notifications } from './activity';
import { AccountSettings } from './settings';
import { Empty } from './ui';
import { AdminPage, VerificationPage, MyReports } from './trust';
import { RAGChat } from './rag-chat';

export function Portal({ role }: { role: Role }) {
  const params = useParams<{ path?: string[] }>(),
    path = params.path || ['dashboard'];
  let page: React.ReactNode;
  if (role === 'admin' && path[0] !== 'settings' && path[0] !== 'notifications')
    page = <AdminPage section={path[0]} />;
  else if (path[0] === 'verification' && role === 'employer') page = <VerificationPage />;
  else if (path[0] === 'reports' && role === 'student') page = <MyReports />;
  else if (path[0] === 'dashboard') page = <Dashboard role={role} />;
  else if (path[0] === 'profile')
    page = role === 'student' ? <StudentProfilePage /> : <EmployerProfilePage />;
  else if (path[0] === 'settings') page = <AccountSettings />;
  else if (path[0] === 'notifications') page = <Notifications role={role} />;
  else if (path[0] === 'ask-ai' && role === 'student') page = <RAGChat />;
  else if (
    (path[0] === 'applications' && role === 'student') ||
    (path[0] === 'applicants' && role === 'employer')
  )
    page = <ApplicationsPage role={role} />;
  else if (path[0] === 'saved' && role === 'student') page = <SavedPage />;
  else if (path[0] === 'internships') {
    if (role === 'student') page = path[1] ? <ListingDetail id={Number(path[1])} /> : <Browse />;
    else
      page =
        path[1] === 'new' ? (
          <ListingEditor />
        ) : path[2] === 'edit' ? (
          <ListingEditor id={Number(path[1])} />
        ) : (
          <EmployerListings />
        );
  } else
    page = <Empty title="Page not found" href={`/${role}/dashboard`} action="Back to overview" />;
  return <Shell role={role}>{page}</Shell>;
}
