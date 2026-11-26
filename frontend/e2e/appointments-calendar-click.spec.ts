/**
 * Calendar appointment open/edit regression.
 *
 * The real FullCalendar adapter is mounted, while auth and every API call are
 * intercepted at the HTTP boundary. This keeps the browser spec independent of
 * backend fixtures while still exercising the production click/tap, select,
 * drag/drop, edit-modal and update paths.
 */
import { test, expect, type Page, type Route } from '@playwright/test';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const APP_ORIGIN = new URL(BASE_URL).origin;
const API_ROUTE = (url: URL) => url.pathname === '/api' || url.pathname.startsWith('/api/');

const calendarNow = new Date('2026-06-16T12:00:00Z');
const pad = (value: number) => String(value).padStart(2, '0');

function dateInCurrentMonth(day: number, hour: number) {
  return `${calendarNow.getUTCFullYear()}-${pad(calendarNow.getUTCMonth() + 1)}-${pad(day)}T${pad(hour)}:00:00`;
}

function datePart(value: string) {
  return value.slice(0, 10);
}

function fixture() {
  return {
    patients: [
      { id: 101, name: 'Calendar Patient One', file_number: 'C-101', phone: '01000000001' },
      { id: 102, name: 'Calendar Patient Two', file_number: 'C-102', phone: '01000000002' },
    ],
    appointments: [
      {
        id: 501,
        patient_id: 101,
        patient_name: 'Calendar Patient One',
        doctor_id: 10,
        doctor_name: 'Dr. Calendar',
        status: 'Scheduled',
        date_time: dateInCurrentMonth(10, 10),
        duration_minutes: 30,
        notes: 'First calendar note',
      },
      {
        id: 502,
        patient_id: 102,
        patient_name: 'Calendar Patient Two',
        doctor_id: 10,
        doctor_name: 'Dr. Calendar',
        status: 'Completed',
        date_time: dateInCurrentMonth(20, 14),
        duration_minutes: 45,
        notes: 'Second calendar note',
      },
    ],
    mutations: [] as Array<{ method: string; path: string; body: any }>,
  };
}

type Fixture = ReturnType<typeof fixture>;

test.use({ serviceWorkers: 'block', timezoneId: 'UTC' });

function responseHeaders() {
  return {
    'access-control-allow-origin': APP_ORIGIN,
    'access-control-allow-credentials': 'true',
    'access-control-allow-methods': 'GET,POST,PUT,PATCH,DELETE,OPTIONS',
    'access-control-allow-headers': 'content-type,authorization,x-csrf-token',
    'content-type': 'application/json',
  };
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    status,
    headers: responseHeaders(),
    body: JSON.stringify(body),
  });
}

async function installApiMocks(page: Page, state: Fixture) {
  await page.route(API_ROUTE, async (route) => {
    const request = route.request();
    const method = request.method();
    const path = new URL(request.url()).pathname;

    if (method === 'OPTIONS') {
      await route.fulfill({ status: 204, headers: responseHeaders() });
      return;
    }

    if (!['GET', 'HEAD'].includes(method)) {
      let body: any = null;
      try {
        body = request.postDataJSON();
      } catch {
        body = request.postData();
      }
      state.mutations.push({ method, path, body });
    }

    if (method === 'GET' && path === '/api/auth/session') {
      await fulfillJson(route, {
        id: 7,
        username: 'e2e_admin',
        name: 'E2E Admin',
        role: 'admin',
        tenant_id: 1,
      });
      return;
    }

    if (method === 'GET' && path === '/api/v1/users/me') {
      await fulfillJson(route, {
        id: 1,
        name: 'E2E Calendar Clinic',
        plan: 'premium',
        timezone: 'UTC',
      });
      return;
    }

    if (method === 'GET' && path === '/api/v1/settings/entitlements') {
      await fulfillJson(route, {
        effective_subscription_status: 'ACTIVE',
        can_create_appointments: true,
        can_read_clinical: true,
        can_write_clinical: true,
        can_write_billable: true,
        capabilities: {
          APPOINTMENTS: { effective_allowed: true },
          PATIENTS: { effective_allowed: true },
          BILLING: { effective_allowed: true },
        },
        capacities: {},
      });
      return;
    }

    if (method === 'GET' && path === '/api/v1/settings/features') {
      await fulfillJson(route, { features: [] });
      return;
    }

    if (method === 'GET' && path === '/api/v1/users/doctors') {
      await fulfillJson(route, [{ id: 10, name: 'Dr. Calendar' }]);
      return;
    }

    if (method === 'GET' && path === '/api/v1/patients') {
      await fulfillJson(route, state.patients);
      return;
    }

    if (method === 'GET' && path === '/api/v1/patients/directory') {
      await fulfillJson(route, state.patients);
      return;
    }

    if (method === 'GET' && path === '/api/v1/notifications') {
      await fulfillJson(route, []);
      return;
    }

    if (method === 'GET' && path === '/api/v1/global-settings') {
      await fulfillJson(route, { banner: null });
      return;
    }

    if (method === 'GET' && path === '/api/v1/appointments') {
      await fulfillJson(route, state.appointments);
      return;
    }

    if (method === 'POST' && path === '/api/v1/appointments') {
      const body = request.postDataJSON();
      const patient = state.patients.find((item) => item.id === Number(body.patient_id));
      const appointment = {
        id: 600 + state.appointments.length,
        patient_id: Number(body.patient_id),
        patient_name: patient?.name || 'Unknown Patient',
        doctor_id: body.doctor_id ?? null,
        doctor_name: body.doctor_id === 10 ? 'Dr. Calendar' : '',
        status: 'Scheduled',
        date_time: body.date_time,
        duration_minutes: body.duration_minutes || 30,
        notes: body.notes || '',
      };
      state.appointments.push(appointment);
      await fulfillJson(route, appointment, 201);
      return;
    }

    const updateMatch = method === 'PUT' && path.match(/^\/api\/v1\/appointments\/(\d+)$/);
    if (updateMatch) {
      const id = Number(updateMatch[1]);
      const appointment = state.appointments.find((item) => item.id === id);
      if (!appointment) {
        await fulfillJson(route, { detail: 'Appointment not found' }, 404);
        return;
      }
      Object.assign(appointment, request.postDataJSON());
      await fulfillJson(route, appointment);
      return;
    }

    await fulfillJson(route, {});
  });
}

async function openAppointments(page: Page) {
  await page.clock.setFixedTime(calendarNow);
  await page.goto(`${BASE_URL}/appointments`);
  await expect(page.getByRole('heading', { name: 'Appointments Schedule' })).toBeVisible({ timeout: 15000 });
}

async function ensureCalendar(page: Page) {
  const calendar = page.locator('.fc');
  if (!(await calendar.isVisible().catch(() => false))) {
    await page.getByTitle('Calendar').click();
  }
  await expect(calendar).toBeVisible();
  await expect(page.locator('.fc-event').first()).toBeVisible();
}

function calendarEvent(page: Page, patientName: string) {
  return page.locator('.fc-event').filter({ hasText: patientName }).first();
}

function dayCell(page: Page, isoDate: string) {
  return page.locator(`td.fc-daygrid-day[data-date="${isoDate}"]`);
}

test.describe('Appointments calendar click/tap', () => {
  let state: Fixture;

  test.beforeEach(async ({ context, page }) => {
    state = fixture();
    await context.addCookies([
      { name: 'dentix_session_hint', value: '1', url: APP_ORIGIN },
    ]);
    await context.addInitScript(() => {
      window.localStorage.setItem('i18nextLng', 'en');
    });
    await installApiMocks(page, state);
    await openAppointments(page);
  });

  test('opens two distinct calendar appointments with their real data and closes without mutation', async ({ page }) => {
    await ensureCalendar(page);

    const firstEvent = calendarEvent(page, 'Calendar Patient One');
    await firstEvent.click();

    let dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText('Calendar Patient One', { exact: true })).toBeVisible();
    await expect(dialog.locator('textarea')).toHaveValue('First calendar note');
    await expect(dialog.locator('[data-date-time-picker-trigger]')).toContainText(datePart(state.appointments[0].date_time));
    await expect(dialog.locator('[data-date-time-picker-trigger]')).toContainText('10:00');
    await dialog.getByRole('button', { name: 'Cancel' }).click();
    await expect(dialog).toBeHidden();

    const secondEvent = calendarEvent(page, 'Calendar Patient Two');
    await secondEvent.click();

    dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText('Calendar Patient Two', { exact: true })).toBeVisible();
    await expect(dialog.locator('textarea')).toHaveValue('Second calendar note');
    await expect(dialog.locator('[data-date-time-picker-trigger]')).toContainText(datePart(state.appointments[1].date_time));
    await expect(dialog.locator('[data-date-time-picker-trigger]')).toContainText('02:00');
    await dialog.getByRole('button', { name: 'Cancel' }).click();
    await expect(dialog).toBeHidden();

    expect(state.mutations).toHaveLength(0);
  });

  test('explicit save updates the selected appointment once and renders the saved change in calendar and list', async ({ page }) => {
    await ensureCalendar(page);
    await calendarEvent(page, 'Calendar Patient Two').click();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    const originalDate = datePart(state.appointments[1].date_time);
    await dialog.locator('textarea').fill('Updated from the calendar');

    const targetDay = 25;
    const targetDate = dateInCurrentMonth(targetDay, 14).slice(0, 10);
    await dialog.locator('[data-date-time-picker-trigger]').click();
    const picker = page.locator('[data-date-time-picker-dialog]');
    await expect(picker).toBeVisible();
    await picker.getByRole('button', { name: targetDate }).click();
    await picker.getByRole('button', { name: 'Confirm' }).click();
    await expect(picker).toBeHidden();

    await dialog.getByRole('button', { name: 'Save Changes' }).click();
    await expect(dialog).toBeHidden();

    await expect.poll(() => state.mutations.length).toBe(1);
    const update = state.mutations[0];
    expect(update.method).toBe('PUT');
    expect(update.path).toBe('/api/v1/appointments/502');
    expect(update.body.notes).toBe('Updated from the calendar');

    const savedDateTime = dateInCurrentMonth(targetDay, 14);
    expect(update.body.date_time).toBe(savedDateTime);
    await expect(dayCell(page, targetDate).locator('.fc-event').filter({ hasText: 'Calendar Patient Two' })).toBeVisible();
    await expect(dayCell(page, originalDate).locator('.fc-event').filter({ hasText: 'Calendar Patient Two' })).toHaveCount(0);

    await page.getByRole('button', { name: 'List View', exact: true }).click();
    const row = page.locator('table tbody tr').filter({ hasText: 'Calendar Patient Two' });
    await expect(row).toBeVisible();
    await expect(row).toContainText('Updated from the calendar');
    const expectedListDate = new Date(savedDateTime).toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
      timeZone: 'UTC',
    });
    await expect(row).toContainText(expectedListDate);
    expect(state.mutations).toHaveLength(1);
  });

  test('clicking an empty slot still creates an appointment through the existing creation path', async ({ page }) => {
    await ensureCalendar(page);

    const slotDate = dateInCurrentMonth(28, 9).slice(0, 10);
    const slot = dayCell(page, slotDate);
    await expect(slot).toBeVisible();
    await slot.click({ position: { x: 24, y: 48 } });

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText('Book New Appointment')).toBeVisible();

    const patientCombobox = dialog.getByRole('combobox');
    await patientCombobox.click();
    await patientCombobox.press('ArrowDown');
    await page.getByRole('option', { name: /Calendar Patient One/ }).click();
    await dialog.getByRole('button', { name: 'Confirm Booking' }).click();
    await expect(dialog).toBeHidden();

    await expect.poll(() => state.mutations.length).toBe(1);
    const create = state.mutations[0];
    expect(create.method).toBe('POST');
    expect(create.path).toBe('/api/v1/appointments');
    expect(create.body.patient_id).toBe(101);
    expect(datePart(create.body.date_time)).toBe(slotDate);

    await expect(dayCell(page, slotDate).locator('.fc-event').filter({ hasText: 'Calendar Patient One' })).toBeVisible();
  });

  test('dragging an appointment reschedules it without opening the edit modal', async ({ page }) => {
    await ensureCalendar(page);

    const originalDate = datePart(state.appointments[0].date_time);
    const targetDate = dateInCurrentMonth(25, 10).slice(0, 10);
    await calendarEvent(page, 'Calendar Patient One').dragTo(dayCell(page, targetDate));

    await expect.poll(() => state.mutations.length).toBe(1);
    const update = state.mutations[0];
    expect(update.method).toBe('PUT');
    expect(update.path).toBe('/api/v1/appointments/501');
    expect(datePart(update.body.date_time)).toBe(targetDate);

    await expect(page.getByRole('dialog')).toHaveCount(0);
    await expect(dayCell(page, targetDate).locator('.fc-event').filter({ hasText: 'Calendar Patient One' })).toBeVisible();
    await expect(dayCell(page, originalDate).locator('.fc-event').filter({ hasText: 'Calendar Patient One' })).toHaveCount(0);
  });
});

test.describe('Appointments calendar mobile tap', () => {
  let state: Fixture;

  test.use({
    viewport: { width: 390, height: 844 },
    deviceScaleFactor: 2.625,
    hasTouch: true,
    isMobile: true,
  });

  test.beforeEach(async ({ context, page }) => {
    state = fixture();
    await context.addCookies([
      { name: 'dentix_session_hint', value: '1', url: APP_ORIGIN },
    ]);
    await context.addInitScript(() => {
      window.localStorage.setItem('i18nextLng', 'en');
    });
    await installApiMocks(page, state);
    await openAppointments(page);
  });

  test('tapping a calendar appointment opens the same edit modal without mutation', async ({ page }) => {
    await ensureCalendar(page);
    await calendarEvent(page, 'Calendar Patient One').tap();

    const dialog = page.getByRole('dialog');
    await expect(dialog).toBeVisible();
    await expect(dialog.getByText('Calendar Patient One', { exact: true })).toBeVisible();
    await expect(dialog.locator('textarea')).toHaveValue('First calendar note');
    await expect(dialog.locator('[data-date-time-picker-trigger]')).toContainText(datePart(state.appointments[0].date_time));
    await dialog.getByRole('button', { name: 'Cancel' }).click();
    await expect(dialog).toBeHidden();

    expect(state.mutations).toHaveLength(0);
  });
});
