import { expect, test as base } from '@playwright/test';

const paths = {
  stats: '/api/v1/stats/dashboard',
  appointments: '/api/v1/appointments',
};
type Source = keyof typeof paths;
const businessDate = '2026-11-20';
const clinic = { id: 123, name: 'Synthetic Clinic', plan: 'premium', timezone: 'Africa/Cairo' };
const user = { id: 456, username: 'Synthetic Admin', tenant_id: clinic.id, role: 'admin', tenant: clinic };
const stats = {
  business_date: businessDate,
  new_patients_today: 3,
  total_appointments_today: 1,
  today_received: 1250.6,
  today_outstanding: 51.4,
  revenue_chart: [{ name: '20/11', revenue: 1250.6 }],
};
const appointments = [{
  id: 789,
  patient_name: 'Synthetic Patient',
  date_time: businessDate + 'T10:00:00',
  status: 'Completed',
}];
const initialResponses: Record<string, unknown> = {
  '/api/auth/session': user,
  '/api/v1/users/me': user,
  '/api/v1/settings/entitlements': { can_read_clinical: true, can_create_appointments: true, effective_subscription_status: 'ACTIVE' },
  '/api/v1/global-settings': {},
  '/api/v1/onboarding/status': { enabled: false, steps: [] },
};
type DashboardApi = {
  failures: Partial<Record<Source, number | 'network'>>,
  calls: Record<Source, number>,
  stats: typeof stats,
  appointments: typeof appointments,
};

const test = base.extend<{ dashboardApi: DashboardApi }>({
  dashboardApi: async ({ baseURL, context, page }, use) => {
    const origin = new URL(baseURL ?? 'http://localhost:5173').origin;
    const api: DashboardApi = {
      calls: { stats: 0, appointments: 0 },
      failures: {},
      stats: { ...stats },
      appointments: [...appointments],
    };

    await context.addCookies([{ name: 'dentix_session_hint', value: 'synthetic-dashboard', url: origin }]);
    await page.addInitScript(() => localStorage.setItem('i18nextLng', 'en'));
    await page.route((url) => url.pathname.startsWith('/api/'), async (route) => {
      const path = new URL(route.request().url()).pathname.replace(/\/$/, '');
      const source = (Object.keys(paths) as Source[]).find((key) => paths[key] === path);
      const headers = { 'access-control-allow-origin': origin, 'access-control-allow-credentials': 'true' };
      if (source) {
        api.calls[source] += 1;
        const failure = api.failures[source];
        if (failure === 'network') return route.abort('failed');
        if (failure) return route.fulfill({ headers, status: failure, json: { detail: 'Synthetic request failure' } });
      }
      const data = source ? api[source] : initialResponses[path] ?? [];
      return route.fulfill({ headers, json: { success: true, data } });
    });
    await use(api);
  },
});

test.use({ serviceWorkers: 'block' });

const nonEmptyIncome = 'EGP\u00a01,251';
const emptySchedule = 'No remaining appointments today';

test('shows verified zero and an empty schedule after successful responses', async ({ page, dashboardApi }) => {
  dashboardApi.stats.today_received = 0;
  dashboardApi.stats.total_appointments_today = 0;
  dashboardApi.stats.revenue_chart = [];
  dashboardApi.appointments = [];
  await page.goto('/');
  await expect(page.getByRole('button', { name: /Daily Income/ })).toContainText('EGP\u00a00');
  await expect(page.getByText(emptySchedule)).toBeVisible();
  await expect(page.getByText('0%', { exact: true })).toBeVisible();
});

for (const source of ['stats', 'appointments'] as const) {
  test('retries only the failed ' + source + ' request on first load', async ({ page, dashboardApi }) => {
    dashboardApi.failures[source] = 503;
    await page.goto('/');
    const income = page.getByRole('button', { name: /Daily Income/ });
    const error = page.getByTestId(source === 'stats' ? 'dashboard-stats-error' : 'dashboard-today-error');
    await expect(error).toBeVisible();
    if (source === 'stats') {
      await expect(income).toHaveCount(0);
      await expect(page.getByText('Completed', { exact: true })).toBeVisible();
    } else {
      await expect(income).toContainText(nonEmptyIncome);
    }
    await expect(page.getByText(emptySchedule)).toHaveCount(0);
    await expect(page.getByText('0%', { exact: true })).toHaveCount(0);
    const beforeRetry = { ...dashboardApi.calls };
    delete dashboardApi.failures[source];
    await error.getByRole('button').click();
    await expect(page.getByRole('button', { name: /Synthetic Patient/ })).toBeVisible();
    await expect(income).toContainText(nonEmptyIncome);
    await expect(error).toHaveCount(0);
    expect(dashboardApi.calls).toEqual({ ...beforeRetry, [source]: beforeRetry[source] + 1 });
  });

  test('retains previous same-clinic data and identifies a failed ' + source + ' refresh', async ({ page, dashboardApi }) => {
    const now = new Date();
    await page.clock.setFixedTime(now);
    await page.goto('/');
    const income = page.getByRole('button', { name: /Daily Income/ });
    const patient = page.getByRole('button', { name: /Synthetic Patient/ });
    await expect(income).toContainText(nonEmptyIncome);
    await expect(patient).toBeVisible();

    await page.locator('#nav-patients').click();
    await expect(page).toHaveURL(/\/patients$/);
    await expect(income).toHaveCount(0);
    const callsBeforeRefresh = dashboardApi.calls[source];
    dashboardApi.failures[source] = source === 'stats' ? 503 : 'network';
    await page.clock.setFixedTime(new Date(+now + 31_000));
    await page.locator('#nav-dashboard').click();

    await expect.poll(() => dashboardApi.calls[source]).toBeGreaterThan(callsBeforeRefresh);
    const warning = page.getByTestId('dashboard-' + source + '-stale-warning');
    await expect(warning).toBeVisible();
    await expect(income).toContainText(nonEmptyIncome);
    await expect(patient).toBeVisible();

    const beforeRetry = { ...dashboardApi.calls };
    delete dashboardApi.failures[source];
    if (source === 'stats') dashboardApi.stats.today_received = 2100;
    else dashboardApi.appointments = [{ ...appointments[0], patient_name: 'Refreshed Patient' }];
    await warning.getByRole('button').click();
    await expect(warning).toHaveCount(0);
    if (source === 'stats') await expect(income).toContainText('EGP\u00a02,100');
    else await expect(page.getByRole('button', { name: /Refreshed Patient/ })).toBeVisible();
    expect(dashboardApi.calls).toEqual({ ...beforeRetry, [source]: beforeRetry[source] + 1 });
  });
}

test('identifies missing business date and formats the same amount on language change', async ({ page, dashboardApi }) => {
  dashboardApi.stats.business_date = '';
  await page.goto('/');
  await expect(page.getByTestId('dashboard-today-unavailable')).toBeVisible();
  await expect(page.getByTestId('dashboard-efficiency-unavailable')).toBeVisible();
  await expect(page.getByText(emptySchedule)).toHaveCount(0);
  await expect(page.getByText('0%', { exact: true })).toHaveCount(0);
  await expect(page.getByRole('button', { name: /Daily Income/ })).toContainText(nonEmptyIncome);
  const beforeLanguageChange = { ...dashboardApi.calls };
  await page.getByRole('button', { name: 'Language' }).click();
  await expect(page.getByRole('button', { name: /الدخل اليومي/ })).toContainText('١٬٢٥١');
  expect(dashboardApi.calls).toEqual(beforeLanguageChange);
});

test('does not restore denied statistics on a transient error after leaving the dashboard', async ({ page, dashboardApi }) => {
  const now = new Date();
  await page.clock.setFixedTime(now);
  await page.goto('/');
  const income = page.getByRole('button', { name: /Daily Income/ });
  await expect(income).toContainText(nonEmptyIncome);

  const statsError = page.getByTestId('dashboard-stats-error');
  for (const failure of [403, 503]) {
    await page.locator('#nav-patients').click();
    await expect(page).toHaveURL(/\/patients$/);
    await expect(income).toHaveCount(0);
    dashboardApi.failures.stats = failure;
    await page.clock.setFixedTime(new Date(+now + 31_000));
    await page.locator('#nav-dashboard').click();
    await expect(statsError).toBeVisible();
    await expect(income).toHaveCount(0);
    await expect(page.getByTestId('dashboard-stats-stale-warning')).toHaveCount(0);
  }
});
