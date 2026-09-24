import { test, expect } from '@playwright/test';
import { adminContext, mutate, baseURL } from './trust-helpers';

test('administrator verifies, investigates a report, hides a listing and suspends an employer', async ({
  browser,
}, info) => {
  const admin = await adminContext(browser);
  const employer = await browser.newContext({
    baseURL,
    viewport: info.project.use.viewport,
    colorScheme: info.project.use.colorScheme,
  });
  const student = await browser.newContext({ baseURL });
  const suffix = `${Date.now()}-${info.project.name}`;
  const registered = await mutate(employer, '/auth/register', {
    name: 'Safety Test Employer',
    role: 'employer',
    email: `trust-${suffix}@example.test`,
    password: 'BrowserDemo!2026',
  });
  expect(registered.ok()).toBeTruthy();
  const employerId = (await registered.json()).id;
  const ep = await employer.newPage();
  await ep.goto('/employer/profile');
  await ep.getByLabel('Company name').fill(`Trust Labs ${suffix}`);
  await ep.getByLabel('Company website').fill('https://example.org');
  await ep.getByLabel('Company location').fill('Bangkok');
  await ep.getByRole('button', { name: 'Save changes' }).click();
  await expect(ep.getByText('Changes saved').first()).toBeVisible();
  await ep.goto('/employer/verification');
  await ep.getByLabel('Legal company name').fill('Fictional Trust Labs Ltd');
  await ep.getByLabel('Business registration number').fill('TEST-ONLY');
  await ep.getByLabel('Recruiter full name').fill('Robin Test');
  await ep.getByLabel('Recruiter position').fill('Recruiter');
  await ep.getByLabel('Company contact email').fill('test@example.test');
  await ep.getByLabel('Company contact phone').fill('0123456789');
  await ep.getByRole('button', { name: 'Submit for verification' }).click();
  await expect(ep.getByText(/Verification submitted/)).toBeVisible();
  const posted = await mutate(employer, '/internships', {
    title: `Trust Intern ${suffix}`,
    description: 'Learn Python and SQL with clear responsibilities and weekly mentoring.',
    required_skills: ['Python', 'SQL'],
    location: 'Remote',
    work_mode: 'remote',
    duration: '3 months',
  });
  expect(posted.ok()).toBeTruthy();
  const id = (await posted.json()).id;
  expect((await student.request.get(`/api/internships/${id}`)).status()).toBe(404);
  const ap = await admin.newPage();
  await ap.setViewportSize(info.project.use.viewport!);
  await ap.goto('/admin/employers');
  const card = ap.locator('article').filter({
    has: ap.getByRole('heading', { name: `Trust Labs ${suffix} #${employerId}`, exact: true }),
  });
  await card
    .getByLabel('Reason shared with the recipient')
    .fill('Approved fictional local test company only.');
  await card
    .getByLabel('Private investigation notes and independent sources')
    .fill(
      'Synthetic browser fixture. Independent registry and recruiter checks simulated for tests only.',
    );
  await card.getByLabel('I checked the company against independent sources').check();
  await card
    .getByLabel('I confirmed the recruiter through independently obtained company contact details')
    .check();
  await card.getByRole('button', { name: 'Record decision' }).click();
  await expect(card.getByText('approved', { exact: true })).toBeVisible();
  expect((await student.request.get(`/api/internships/${id}`)).status()).toBe(200);
  await mutate(student, '/auth/register', {
    name: 'Safety Test Student',
    role: 'student',
    email: `report-${suffix}@example.test`,
    password: 'BrowserDemo!2026',
  });
  const sp = await student.newPage();
  await sp.goto(`/student/internships/${id}`);
  await sp.getByText('Report this internship', { exact: true }).click();
  await sp
    .getByLabel('What happened?')
    .fill('The recruiter asked for an equipment payment outside the platform.');
  await sp.getByRole('button', { name: 'Submit report' }).click();
  await expect(sp.getByText(/Report received/)).toBeVisible();
  await ap.goto('/admin/reports');
  const report = ap.locator('article').filter({
    has: ap.getByRole('heading', { name: new RegExp(`Report #\\d+ · Listing #${id}$`) }),
  });
  await report.getByRole('button', { name: 'Inspect reported listing' }).click();
  const listing = report.locator('article');
  await listing
    .getByLabel('Reason shared with the recipient')
    .fill('Hidden pending investigation of a payment request.');
  await listing.getByRole('button', { name: 'Record decision' }).click();
  await expect(listing.getByText('Hidden by administrator', { exact: true })).toBeVisible();
  expect((await student.request.get(`/api/internships/${id}`)).status()).toBe(404);
  await report.getByRole('button', { name: 'Close listing' }).click();
  await report
    .getByLabel('Reason shared with the recipient')
    .fill('We investigated your report and hid the listing.');
  await report.getByRole('button', { name: 'Record decision' }).click();
  await expect(report.getByText('resolved', { exact: true })).toBeVisible();
  await ap.goto('/admin/employers');
  await card
    .getByLabel('Reason shared with the recipient')
    .fill('Suspended during investigation of payment requests.');
  await card.getByRole('button', { name: 'Record decision' }).click();
  await expect(card.getByText('suspended', { exact: true })).toBeVisible();
  expect((await employer.request.get('/api/employer/internships')).status()).toBe(403);
  await ap.goto('/admin/dashboard');
  await ap
    .getByLabel('Color theme')
    .selectOption(info.project.name === 'mobile-dark' ? 'dark' : 'light');
  await expect(ap.getByRole('heading', { name: 'Trust & safety overview' })).toBeVisible();
  expect(await ap.evaluate(() => document.documentElement.scrollWidth <= innerWidth)).toBeTruthy();
  await ap.screenshot({ path: `test-results/${info.project.name}-admin.png`, fullPage: true });
  await ap.goto('/admin/audit');
  await expect(ap.getByRole('heading', { name: 'audit history', exact: true })).toBeVisible();
  await sp.goto('/student/reports');
  await expect(sp.getByText('resolved', { exact: true })).toBeVisible();
  await admin.close();
  await employer.close();
  await student.close();
});
