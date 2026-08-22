import { expect, request as playwrightRequest, test } from '@playwright/test';

const BASE_URL = (process.env.STAGING_BASE_URL || '').replace(/\/$/, '');
const API_URL = `${BASE_URL}/api/v1`;

function runtimeSuffix() {
  const run = process.env.GITHUB_RUN_ID || String(Date.now());
  const attempt = process.env.GITHUB_RUN_ATTEMPT || '1';
  return `${run}-${attempt}-${Date.now()}`.replace(/[^0-9-]/g, '').slice(-26);
}

function apiItems(body: any) {
  return body?.data ?? body ?? [];
}

test('HF staging passes production-like auth/patient/appointment/finance/file/RBAC/frontend smoke', async ({ page }) => {
  expect(BASE_URL, 'STAGING_BASE_URL must be provided by the staging deployment job').toBeTruthy();

  const suffix = runtimeSuffix();
  const username = `stg_smoke_${suffix.replace(/-/g, '_')}`;
  const password = `Dentix-Staging-Smoke!X9-${suffix}`;
  const email = `${username}@example.invalid`;
  const phoneDigits = String(Date.now()).slice(-8);
  const contactPhone = `010${phoneDigits}`;

  const relevantBrowserErrors: string[] = [];
  const assetFailures: string[] = [];
  const errorPattern = /chunk|preload|dynamically imported|service worker|workbox|asset/i;
  const assetPattern = /\/assets\/|\/sw\.js|\/workbox-|\/registerSW\.js|\/manifest\.webmanifest/i;

  page.on('console', (message) => {
    if (message.type() === 'error' && errorPattern.test(message.text())) {
      relevantBrowserErrors.push(`console: ${message.text()}`);
    }
  });
  page.on('pageerror', (error) => {
    if (errorPattern.test(error.message)) {
      relevantBrowserErrors.push(`pageerror: ${error.message}`);
    }
  });
  page.on('response', (response) => {
    if (assetPattern.test(response.url()) && response.status() >= 400) {
      assetFailures.push(`${response.status()} ${response.url()}`);
    }
  });
  page.on('requestfailed', (request) => {
    if (assetPattern.test(request.url())) {
      assetFailures.push(`requestfailed ${request.url()}: ${request.failure()?.errorText || 'unknown'}`);
    }
  });

  const health = await page.request.get(`${API_URL}/health`, { timeout: 30_000 });
  expect(health.ok(), await health.text()).toBeTruthy();

  const registration = await page.request.post(`${API_URL}/auth/register_clinic`, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    data: new URLSearchParams({
      clinic_name: `Dentix staging smoke ${suffix}`,
      admin_username: username,
      admin_email: email,
      admin_password: password,
      contact_phone: contactPhone,
    }).toString(),
  });
  expect(registration.status(), await registration.text()).toBe(201);

  const login = await page.request.post(`${API_URL}/auth/token`, {
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    data: new URLSearchParams({ username, password }).toString(),
  });
  expect(login.ok(), await login.text()).toBeTruthy();

  const cookies = await page.context().cookies();
  const csrf = cookies.find((cookie) => cookie.name === 'csrf_token')?.value;
  expect(csrf, 'Authenticated staging session must issue a CSRF cookie').toBeTruthy();

  const session = await page.request.get(`${API_URL}/auth/session`);
  expect(session.ok(), await session.text()).toBeTruthy();
  const sessionBody = await session.json();
  const currentUser = sessionBody?.data ?? sessionBody;
  expect(currentUser?.role).toBe('admin');
  expect(currentUser?.id).toBeTruthy();

  const patientName = `Staging Smoke Patient ${suffix}`;
  const createPatient = await page.request.post(`${API_URL}/patients`, {
    headers: { 'X-CSRF-Token': csrf! },
    data: {
      name: patientName,
      age: 31,
      phone: `011${phoneDigits}`,
      address: 'Staging smoke',
      medical_history: '',
      assigned_doctor_id: null,
    },
  });
  expect(createPatient.ok(), await createPatient.text()).toBeTruthy();
  const patientBody = await createPatient.json();
  const patient = patientBody?.data ?? patientBody;
  expect(patient?.id).toBeTruthy();

  const patientRead = await page.request.get(`${API_URL}/patients/${patient.id}`);
  expect(patientRead.ok(), await patientRead.text()).toBeTruthy();

  const appointmentAt = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString();
  const createAppointment = await page.request.post(`${API_URL}/appointments`, {
    headers: { 'X-CSRF-Token': csrf! },
    data: {
      patient_id: patient.id,
      date_time: appointmentAt,
      duration_minutes: 30,
      status: 'Scheduled',
      notes: 'production-like staging smoke',
      doctor_id: null,
    },
  });
  expect(createAppointment.ok(), await createAppointment.text()).toBeTruthy();
  const appointmentBody = await createAppointment.json();
  const appointment = appointmentBody?.data ?? appointmentBody;
  expect(appointment?.id).toBeTruthy();

  const appointments = await page.request.get(`${API_URL}/appointments`);
  expect(appointments.ok(), await appointments.text()).toBeTruthy();
  expect(apiItems(await appointments.json()).some((item: any) => item.id === appointment.id)).toBeTruthy();

  const createPayment = await page.request.post(`${API_URL}/payments`, {
    headers: {
      'X-CSRF-Token': csrf!,
      'Idempotency-Key': `staging-smoke-${suffix}`,
    },
    data: {
      patient_id: patient.id,
      amount: 1,
      notes: 'production-like staging smoke',
    },
  });
  expect(createPayment.ok(), await createPayment.text()).toBeTruthy();
  const paymentBody = await createPayment.json();
  const payment = paymentBody?.data ?? paymentBody;
  expect(payment?.id).toBeTruthy();

  const payments = await page.request.get(`${API_URL}/payments?patient_id=${patient.id}`);
  expect(payments.ok(), await payments.text()).toBeTruthy();
  expect(apiItems(await payments.json()).some((item: any) => item.id === payment.id)).toBeTruthy();

  // Use an allowlisted file type with a real matching magic signature. The
  // production upload validator intentionally rejects text/plain/.txt.
  const onePixelPng = Buffer.from(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Y9Z6GQAAAAASUVORK5CYII=',
    'base64',
  );
  const upload = await page.request.post(`${API_URL}/upload?patient_id=${patient.id}&note=staging-smoke`, {
    headers: { 'X-CSRF-Token': csrf! },
    multipart: {
      file: {
        name: `staging-smoke-${suffix}.png`,
        mimeType: 'image/png',
        buffer: onePixelPng,
      },
    },
  });
  expect(upload.ok(), await upload.text()).toBeTruthy();
  const attachment = await upload.json();
  expect(attachment?.file_path).toBeTruthy();

  if (!String(attachment.file_path).startsWith('http')) {
    const filePath = String(attachment.file_path)
      .split('/')
      .map((part) => encodeURIComponent(part))
      .join('/');
    const authenticatedFile = await page.request.get(`${API_URL}/upload/file/${filePath}`);
    expect(authenticatedFile.ok(), await authenticatedFile.text()).toBeTruthy();

    const anonymous = await playwrightRequest.newContext();
    try {
      const anonymousFile = await anonymous.get(`${API_URL}/upload/file/${filePath}`);
      expect([401, 403]).toContain(anonymousFile.status());
    } finally {
      await anonymous.dispose();
    }
  } else {
    const patientAttachments = await page.request.get(`${API_URL}/patients/${patient.id}/attachments`);
    expect(patientAttachments.ok(), await patientAttachments.text()).toBeTruthy();
    const attachmentItems = apiItems(await patientAttachments.json());
    expect(attachmentItems.some((item: any) => item.id === attachment.id)).toBeTruthy();
  }

  const forbiddenSuperAdminRoute = await page.request.get(`${API_URL}/admin/tenants`);
  expect(forbiddenSuperAdminRoute.status()).toBe(403);

  await page.goto(`${BASE_URL}/`, { waitUntil: 'domcontentloaded' });
  await expect(page.locator('nav').first()).toBeVisible({ timeout: 20_000 });

  for (const path of ['/patients', '/appointments', '/billing']) {
    await page.goto(`${BASE_URL}${path}`, { waitUntil: 'domcontentloaded' });
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 20_000 });
    await expect(page.getByText(/404|page not found|الصفحة غير موجودة/i)).toHaveCount(0);
  }

  expect(assetFailures, `Staging asset/PWA requests failed:\n${assetFailures.join('\n')}`).toEqual([]);
  expect(
    relevantBrowserErrors,
    `Staging emitted asset/PWA console errors:\n${relevantBrowserErrors.join('\n')}`
  ).toEqual([]);
});
