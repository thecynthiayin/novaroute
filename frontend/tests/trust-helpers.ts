import { expect, type Browser, type BrowserContext } from '@playwright/test';
export const baseURL = process.env.E2E_BASE_URL || 'http://localhost:3000';

export async function mutate(context: BrowserContext, url: string, data: unknown) {
  const token = await (await context.request.get('/api/auth/csrf')).json();
  return context.request.post(`/api${url}`, {
    headers: { Origin: baseURL, 'X-CSRF-Token': token.csrf_token },
    data,
  });
}

export async function adminContext(browser: Browser) {
  const email = process.env.E2E_ADMIN_EMAIL,
    password = process.env.E2E_ADMIN_PASSWORD;
  if (!email || !password)
    throw new Error(
      'Create a dedicated local test administrator and set E2E_ADMIN_EMAIL and E2E_ADMIN_PASSWORD.',
    );
  const context = await browser.newContext({ baseURL });
  const response = await mutate(context, '/auth/login', { email, password });
  expect(response.ok(), await response.text()).toBeTruthy();
  return context;
}

export async function approveTestEmployer(browser: Browser, employer: BrowserContext) {
  const verification = await (await employer.request.get('/api/employer/verification')).json();
  const submitted = await mutate(employer, '/employer/verification', {
    version: verification.verification_version,
    legal_name: 'Fictional Browser Test Labs',
    registration_number: 'TEST-ONLY',
    recruiter_name: 'Robin Employer',
    recruiter_position: 'Test recruiter',
    contact_email: 'browser@example.test',
    contact_phone: '0123456789',
  });
  expect(submitted.ok(), await submitted.text()).toBeTruthy();
  const record = await submitted.json();
  const admin = await adminContext(browser);
  const approved = await mutate(admin, `/admin/employers/${record.user_id}/decision`, {
    action: 'approve',
    version: record.verification_version,
    reason: 'Approved synthetic browser-test company only.',
    evidence: 'Automated local test fixture. No claim of real company verification.',
    company_checked: true,
    representative_checked: true,
  });
  expect(approved.ok(), await approved.text()).toBeTruthy();
  await admin.close();
}
