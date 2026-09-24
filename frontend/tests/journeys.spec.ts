import { test, expect, type Page, type BrowserContext } from '@playwright/test';
import path from 'node:path';
import { approveTestEmployer, baseURL } from './trust-helpers';
const password = 'BrowserDemo!2026';

async function signup(page: Page, role: 'student' | 'employer', email: string) {
  await page.goto(`/signup?role=${role}`);
  await page.getByLabel('Full name').fill(role === 'student' ? 'Casey Student' : 'Robin Employer');
  await page.getByLabel('Email address').fill(email);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Create account', exact: true }).click();
  await expect(page).toHaveURL(new RegExp(`/${role}/dashboard`));
}

async function mutation(context: BrowserContext, url: string, method: string, data: unknown) {
  const token = await (await context.request.get('/api/auth/csrf')).json();
  return context.request.fetch(`/api${url}`, {
    method,
    headers: { Origin: baseURL, 'X-CSRF-Token': token.csrf_token },
    data,
  });
}

test('complete student and employer journey', async ({ page, browser }, info) => {
  const suffix = `${Date.now()}-${info.project.name}`;
  const studentEmail = `student-${suffix}@example.test`,
    employerEmail = `employer-${suffix}@example.test`;
  await signup(page, 'student', studentEmail);
  await page.goto('/student/profile');
  await page.getByLabel('Degree / major').fill('BSc Computing');
  await page.getByLabel('Preferred location').fill('Remote');
  await page.getByLabel('Add skills', { exact: true }).fill('Python, SQL');
  await page.getByLabel('Add skills', { exact: true }).press('Enter');
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.getByText('Changes saved').first()).toBeVisible();
  await page
    .getByLabel('Searchable PDF resume')
    .setInputFiles(path.join(__dirname, 'fixtures/resume.pdf'));
  await page.getByRole('button', { name: 'Upload & extract' }).click();
  await expect(page.getByRole('heading', { name: 'Review your extraction' })).toBeVisible();
  await page.getByRole('button', { name: 'Confirm profile details' }).click();
  await expect(page.getByRole('heading', { name: 'Review your extraction' })).not.toBeVisible();
  await page.reload();
  await expect(page.getByRole('button', { name: 'Remove JavaScript', exact: true })).toBeVisible();
  await page.screenshot({ path: `test-results/${info.project.name}-profile.png`, fullPage: true });

  const employerContext = await browser.newContext({
    baseURL,
    viewport: info.project.use.viewport,
    colorScheme: info.project.use.colorScheme,
  });
  const employer = await employerContext.newPage();
  await signup(employer, 'employer', employerEmail);
  await employer.goto('/employer/profile');
  await employer.getByLabel('Company name').fill('Browser Test Labs');
  await employer.getByLabel('Company website').fill('https://example.org');
  await employer.getByLabel('Company location').fill('Remote');
  await employer.getByRole('button', { name: 'Save changes' }).click();
  await expect(employer.getByText('Changes saved').first()).toBeVisible();
  await approveTestEmployer(browser, employerContext);
  await employer.goto('/employer/internships/new');
  const title = `Python Learning Intern ${suffix}`;
  await employer.getByLabel('Internship title').fill(title);
  await employer
    .getByLabel('Role description')
    .fill('Build Python and SQL software projects with mentoring, tests, and clear documentation.');
  await employer.getByLabel('Location', { exact: true }).fill('Remote');
  await employer.getByLabel('Duration', { exact: true }).fill('3 months');
  await employer.getByLabel('Add required skills').fill('Python, SQL');
  await employer.getByLabel('Add required skills').press('Enter');
  await employer.getByRole('button', { name: 'Create & request review' }).click();
  await expect(employer).toHaveURL(/\/employer\/internships\/\d+\/edit/);
  await expect(employer.getByText(/Passed automated content review/)).toBeVisible({
    timeout: 45000,
  });
  const listingId = employer.url().match(/internships\/(\d+)/)![1];
  await employer.getByLabel('Duration', { exact: true }).fill('4 months');
  await employer.getByRole('button', { name: 'Save & request review' }).click();
  await expect(employer.getByText(/Passed automated content review/)).toBeVisible();
  await expect
    .poll(async () => {
      const item = await (
        await employerContext.request.get(`/api/internships/${listingId}`)
      ).json();
      return `${item.duration}:${item.status}`;
    })
    .toBe('4 months:active');

  await page.goto(`/student/internships/${listingId}`);
  await page.getByRole('button', { name: 'Save internship', exact: true }).click();
  await expect(page.getByRole('button', { name: 'Unsave internship' })).toBeVisible();
  await page
    .getByLabel('Cover message', { exact: true })
    .fill('My Python and SQL projects prepared me to learn with your team.');
  await page.getByRole('button', { name: 'Submit application' }).click();
  await expect(page.getByText('You’ve already applied to this internship.')).toBeVisible();
  await page.getByRole('link', { name: 'View application', exact: true }).click();
  await expect(page.getByRole('heading', { name: 'Your applications' })).toBeVisible();
  const applicationId = new URL(page.url()).searchParams.get('application');
  await employer.goto(`/employer/applicants?application=${applicationId}`);
  await employer.getByLabel('Update application status').selectOption('viewed');
  await employer
    .getByLabel('Note to the student (optional)')
    .fill('We would like to learn more about your Python project.');
  await employer.getByRole('button', { name: 'Send status update' }).click();
  await expect(employer.getByText('Changes saved').first()).toBeVisible();
  await page.goto('/student/notifications');
  await expect(page.getByRole('link', { name: 'Application viewed' })).toBeVisible();
  await expect(page.getByText('AI suggestions', { exact: true }).first()).toBeVisible({
    timeout: 45000,
  });
  await page.getByRole('button', { name: 'Mark all as read' }).click();
  await page.screenshot({
    path: `test-results/${info.project.name}-notifications.png`,
    fullPage: true,
  });
  await page.goto('/student/saved');
  await page.getByLabel('Private note').fill('Prepare a small SQL example.');
  await page.getByRole('button', { name: 'Save note' }).click();
  await expect(page.getByText('Changes saved').first()).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('Private note')).toHaveValue('Prepare a small SQL example.');
  await page.goto(`/student/applications?application=${applicationId}`);
  await page.getByRole('button', { name: 'Withdraw application' }).click();
  await page.getByRole('button', { name: 'Confirm', exact: true }).click();
  await expect(page.getByText('withdrawn', { exact: true }).first()).toBeVisible();
  await employer.goto('/employer/internships');
  const card = employer
    .locator('article')
    .filter({ has: employer.getByRole('heading', { name: title }) });
  await card.getByRole('button', { name: 'Delete', exact: true }).click();
  await employer.getByRole('button', { name: 'Confirm', exact: true }).click();
  await expect(employer.getByRole('heading', { name: title })).not.toBeVisible();
  await page.goto('/student/dashboard');
  await expect(page.locator('[aria-busy="true"]')).toHaveCount(0, { timeout: 30000 });
  await expect(page.locator('body')).toHaveJSProperty(
    'scrollWidth',
    await page.evaluate(() => document.documentElement.clientWidth),
  );
  await page
    .getByLabel('Color theme')
    .selectOption(info.project.name === 'mobile-dark' ? 'dark' : 'light');
  await page.screenshot({
    path: `test-results/${info.project.name}-dashboard.png`,
    fullPage: true,
  });
  await mutation(page.context(), '/auth/logout', 'POST', {});
  await page.goto('/login');
  await page.getByLabel('Email address').fill(studentEmail);
  await page.getByLabel('Password', { exact: true }).fill(password);
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page).toHaveURL('/student/dashboard');
  await page.goto('/student/settings');
  await page.getByLabel('Name', { exact: true }).fill('Casey Updated');
  await page.getByLabel('High-match internship alerts').uncheck();
  await page.getByRole('button', { name: 'Save changes', exact: true }).click();
  await expect(page.getByText('Changes saved').first()).toBeVisible();
  await page.reload();
  await expect(page.getByLabel('Name', { exact: true })).toHaveValue('Casey Updated');
  await expect(page.getByLabel('High-match internship alerts')).not.toBeChecked();
  await page.getByLabel('Current password', { exact: true }).fill(password);
  await page.getByLabel('New password', { exact: true }).fill('BrowserChanged!2026');
  await page.getByRole('button', { name: 'Change password', exact: true }).click();
  await expect(page).toHaveURL('/login');
  await page.getByLabel('Email address').fill(studentEmail);
  await page.getByLabel('Password', { exact: true }).fill('BrowserChanged!2026');
  await page.getByRole('button', { name: 'Sign in', exact: true }).click();
  await expect(page).toHaveURL('/student/dashboard');
  await page.goto('/student/settings');
  await page.getByLabel('Confirm your password').fill('BrowserChanged!2026');
  await page.getByRole('button', { name: 'Deactivate account', exact: true }).click();
  await page.getByRole('button', { name: 'Confirm', exact: true }).click();
  await expect(page).toHaveURL('/login');
  await employerContext.close();
});

test('landing responsive layout and themes', async ({ page }, info) => {
  for (const width of [375, 768, 1440]) {
    await page.setViewportSize({ width, height: 1000 });
    await page.goto('/');
    await page
      .getByLabel('Color theme')
      .selectOption(info.project.name === 'mobile-dark' ? 'dark' : 'light');
    await expect(page.getByRole('heading', { name: /Your skills/ })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth)).toBeLessThanOrEqual(
      width,
    );
    await page.screenshot({
      path: `test-results/${info.project.name}-landing-${width}.png`,
      fullPage: true,
    });
  }
});
