import { test, expect, type Page } from '@playwright/test';
import { loginAsAdmin, generateRandomName, generateRandomPhone } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';

async function createPatientFixture(
  page: Page,
  overrides: Partial<{ name: string; phone: string; age: number }> = {},
) {
  const csrfCookie = (await page.context().cookies()).find((cookie) => cookie.name === 'csrf_token');
  expect(csrfCookie?.value).toBeTruthy();

  const fixture = {
    name: overrides.name || generateRandomName('Patient'),
    phone: overrides.phone || generateRandomPhone(),
    age: overrides.age ?? 32,
  };

  const response = await page.request.post(`${API_URL}/patients`, {
    headers: { 'X-CSRF-Token': csrfCookie!.value },
    data: {
      ...fixture,
      address: 'E2E Chart Test Street',
      medical_history: 'None',
      assigned_doctor_id: null,
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  const body = await response.json();
  return { ...fixture, ...(body?.data ?? body) };
}

async function createToothStatusFixture(
  page: Page,
  patientId: number,
  toothNumber: number = 16,
  condition: string = 'Decayed',
) {
  const csrfCookie = (await page.context().cookies()).find((cookie) => cookie.name === 'csrf_token');
  expect(csrfCookie?.value).toBeTruthy();

  const response = await page.request.post(`${API_URL}/treatments/tooth_status`, {
    headers: { 'X-CSRF-Token': csrfCookie!.value },
    data: {
      patient_id: patientId,
      tooth_number: toothNumber,
      condition,
      notes: 'E2E Decayed Tooth Status',
    },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
  const body = await response.json();
  return body?.data ?? body;
}

test.describe('Patient Details - Clinical Workspace Chart', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('loads /patients/:id?tab=chart, observes clinical-workspace 200, and verifies chart projection state', async ({ page }) => {
    // 1. Create a live test patient via authenticated API
    const patient = await createPatientFixture(page);
    expect(patient.id).toBeTruthy();

    // 2. Create a real legacy clinical tooth-status record before opening Patient Details
    const toothStatus = await createToothStatusFixture(page, patient.id, 16, 'Decayed');
    expect(toothStatus).toBeTruthy();

    // 3. Set up observation for the clinical-workspace snapshot endpoint
    const workspaceResponsePromise = page.waitForResponse(
      (response) =>
        response.url().includes(`/patients/${patient.id}/clinical-workspace`) &&
        response.status() === 200,
      { timeout: 20000 },
    );

    // 4. Navigate directly to patient details with chart tab active
    await page.goto(`${BASE_URL}/patients/${patient.id}?tab=chart`);

    // 5. Await and inspect live 200 response from /patients/:id/clinical-workspace
    const workspaceResponse = await workspaceResponsePromise;
    expect(workspaceResponse.status()).toBe(200);

    const json = await workspaceResponse.json();
    expect(json.success).toBe(true);

    const snapshot = json.data;
    expect(snapshot.schema_version).toBe(1);
    expect(snapshot.patient_id).toBe(patient.id);
    expect(['LEGACY_ONLY', 'SHADOW', 'VNEXT_PRIMARY']).toContain(snapshot.read_mode);
    expect(snapshot.coverage).toBeDefined();
    expect(snapshot.coverage.teeth).toBeDefined();
    expect(snapshot.coverage.treatments).toBeDefined();
    expect(snapshot.coverage.sessions).toBeDefined();

    // Assert workspace response contains mapped clinical evidence / fallback for tooth 16
    expect(snapshot.teeth).toBeDefined();
    const tooth16 = snapshot.teeth['16'];
    expect(tooth16).toBeDefined();
    expect(tooth16.condition).toBe('Decayed');
    expect(tooth16.provenance).toBe('legacy_fallback');
    expect(tooth16.findings).toBeDefined();
    expect(tooth16.findings.some((f: { code: string }) => f.code === 'CARIES')).toBe(true);

    // 6. Assert live production chart UI and metadata elements
    const workspaceStatus = page.getByTestId('clinical-workspace-status');
    await expect(workspaceStatus).toBeVisible({ timeout: 15000 });

    // Read mode badge agrees with server snapshot read_mode
    const readModeBadge = page.getByTestId('clinical-workspace-read-mode');
    await expect(readModeBadge).toBeVisible();
    await expect(readModeBadge).toContainText(snapshot.read_mode);

    // Coverage container contains each domain and the exact status from the real response
    const coverageContainer = page.getByTestId('clinical-workspace-coverage');
    await expect(coverageContainer).toBeVisible();
    for (const [domain, status] of Object.entries(snapshot.coverage)) {
      await expect(coverageContainer).toContainText(domain);
      await expect(coverageContainer).toContainText(status as string);
    }

    // If fallback notice active, assert banner visibility
    const hasFallbackWarning = (snapshot.warnings || []).some(
      (w: { code: string }) => w.code === 'FALLBACK_DATA_ACTIVE',
    );
    if (hasFallbackWarning) {
      await expect(page.getByTestId('clinical-workspace-fallback-banner')).toBeVisible();
    }

    // Chart odontogram SVG elements rendered
    const crownLayers = page.locator('[data-layer="crown"]');
    await expect(crownLayers.first()).toBeVisible();
    expect(await crownLayers.count()).toBeGreaterThanOrEqual(20);

    // Live renderer contains real data-code visual for mapped Decayed -> CARIES finding
    const cariesVisual = page.locator('[data-tooth-key="16"] [data-code="CARIES"]').first();
    await expect(cariesVisual).toBeVisible();
  });
});
