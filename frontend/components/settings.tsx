'use client';
import { useState } from 'react';
import { useRouter } from 'next/navigation';
import { useQueryClient } from '@tanstack/react-query';
import { useAction, useAuth } from '@/providers';
import type { User } from '@/lib/types';
import { Confirm, Form, Heading } from './ui';

export function AccountSettings() {
  const auth = useAuth();
  return (
    <>
      <Heading eyebrow="Your account, your choices" title="Account settings">
        Manage your details, security, and email preferences.
      </Heading>
      {auth.data && <AccountForm key={JSON.stringify(auth.data)} user={auth.data} />}
    </>
  );
}

function AccountForm({ user }: { user: User }) {
  const [matches, setMatches] = useState(user.email_matches),
    [updates, setUpdates] = useState(user.email_applications),
    [password, setPassword] = useState(''),
    router = useRouter(),
    client = useQueryClient(),
    action = useAction();
  const signedOut = () => {
    client.clear();
    router.push('/login');
  };
  return (
    <div className="account-grid">
      <section className="card">
        <h2>Personal details</h2>
        <Form
          fields={[
            { name: 'name', label: 'Name', required: true, maxLength: 100 },
            { name: 'email', label: 'Email address', type: 'email', required: true },
            {
              name: 'current_password',
              label: 'Current password to change email',
              type: 'password',
              maxLength: 128,
            },
          ]}
          initial={{ name: user.name, email: user.email, current_password: '' }}
          onSubmit={async (values) => {
            await action.mutateAsync({
              path: '/auth/account',
              method: 'PATCH',
              body: { ...values, email_matches: matches, email_applications: updates },
            });
          }}
          busy={action.isPending}
        >
          <fieldset>
            <legend>Email preferences</legend>
            <div className="stack" style={{ gap: 12 }}>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={matches}
                  onChange={(e) => setMatches(e.target.checked)}
                />
                High-match internship alerts
              </label>
              <label className="checkbox-label">
                <input
                  type="checkbox"
                  checked={updates}
                  onChange={(e) => setUpdates(e.target.checked)}
                />
                Application status and feedback updates
              </label>
            </div>
            <p className="muted" style={{ fontSize: 12, marginTop: 14 }}>
              In-app notifications remain available when email is disabled.
            </p>
          </fieldset>
        </Form>
      </section>
      <div className="stack">
        <section className="card">
          <h2>Change password</h2>
          <Form
            fields={[
              {
                name: 'current_password',
                label: 'Current password',
                type: 'password',
                required: true,
                maxLength: 128,
              },
              {
                name: 'new_password',
                label: 'New password',
                type: 'password',
                required: true,
                maxLength: 128,
                hint: 'At least 10 characters. All sessions will be signed out.',
              },
            ]}
            onSubmit={async (values) => {
              await action.mutateAsync({ path: '/auth/password', body: values });
              signedOut();
            }}
            busy={action.isPending}
            submitLabel="Change password"
          />
        </section>
        <section className="card">
          <h2>Deactivate account</h2>
          <p className="muted" style={{ fontSize: 13 }}>
            Private resumes and profile content are removed, sessions are revoked, and employer
            listings are closed. Application decision history remains in anonymized form.
          </p>
          <label>
            Confirm your password
            <input
              type="password"
              value={password}
              maxLength={128}
              onChange={(e) => setPassword(e.target.value)}
            />
          </label>
          <div style={{ marginTop: 18 }}>
            <Confirm
              title="Deactivate your account?"
              description="Your account will stop working immediately. Resume bytes and private profile content will be removed; anonymized decision history is retained. This action cannot be undone in the app."
              trigger={
                <button className="button danger" disabled={!password}>
                  Deactivate account
                </button>
              }
              onConfirm={async () => {
                await action.mutateAsync({ path: '/auth/deactivate', body: { password } });
                signedOut();
              }}
              busy={action.isPending}
            />
          </div>
        </section>
      </div>
    </div>
  );
}
