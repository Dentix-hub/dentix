/**
 * Capture the actual React screens with fictional data, without any backend.
 * Run Vite locally, then: node scripts/capture-marketing-screenshots.mjs
 * No credentials, clinic records, production requests, or production UI overrides.
 */
import { chromium } from '@playwright/test';
import { mkdirSync, writeFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';

const origin = 'http://127.0.0.1:5178';
const destination = fileURLToPath(new URL('../public/marketing/screens/', import.meta.url));
mkdirSync(destination, { recursive: true });
const browser = await chromium.launch();

try {
    for (const language of ['ar', 'en']) {
        const arabic = language === 'ar';
        const context = await browser.newContext({ viewport: { width: 1440, height: 1000 }, deviceScaleFactor: 1, serviceWorkers: 'block', reducedMotion: 'reduce' });
        const page = await context.newPage();
        const unknown = new Set();
        const today = new Date().toISOString().slice(0, 10);
        const names = arabic ? ['مريض تجريبي ١', 'مريض تجريبي ٢', 'مريض تجريبي ٣', 'مريض تجريبي ٤', 'مريض تجريبي ٥'] : ['Demo patient 01', 'Demo patient 02', 'Demo patient 03', 'Demo patient 04', 'Demo patient 05'];
        const doctors = arabic
            ? [{ id: 101, name: 'د. سارة منصور', username: 'dr.sara', role: 'doctor' }, { id: 102, name: 'د. كريم عادل', username: 'dr.karim', role: 'doctor' }]
            : [{ id: 101, name: 'Dr. Sara Mansour', username: 'dr.sara', role: 'doctor' }, { id: 102, name: 'Dr. Karim Adel', username: 'dr.karim', role: 'doctor' }];
        const patients = names.map((name, index) => ({ id: index + 1, name, age: 28 + index * 3, gender: index % 2 ? 'Female' : 'Male', file_number: `DEMO-00${index + 1}`, phone: '', medical_history: '', address: '', balance: [450, 0, 1200, 0, 800][index], total_cost: 2400, total_paid: 1200, created_at: `${today}T09:00:00`, medical_alert: null }));
        const subscriptionEnd = new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10);
        const tenant = { id: 99999, name: arabic ? 'عيادة العرض التجريبي' : 'Dentix Demo Clinic', plan: 'premium', is_active: true, subscription_status: 'active', subscription_end_date: subscriptionEnd, timezone: 'Africa/Cairo' };
        const user = { id: 99999, username: arabic ? 'طبيب العيادة التجريبية' : 'Demo doctor', name: arabic ? 'طبيب العيادة التجريبية' : 'Demo doctor', role: 'admin', tenant_id: 99999, is_active: true, tenant };
        const offsetDate = (deltaDays) => new Date(Date.now() + deltaDays * 86400000).toISOString().slice(0, 10);
        const appointments = patients.map((patient, index) => ({
            id: index + 1,
            patient_id: patient.id,
            patient_name: patient.name,
            patient,
            doctor_id: doctors[index % doctors.length].id,
            doctor_name: doctors[index % doctors.length].name,
            date_time: `${offsetDate([0, 0, -1, -2, -3][index])}T${['09:00:00', '10:30:00', '10:00:00', '11:30:00', '09:30:00'][index]}`,
            duration_minutes: [45, 45, 60, 45, 60][index],
            status: ['Completed', 'In-Chair', 'Waiting', 'Scheduled', 'Scheduled'][index],
            notes: arabic ? 'متابعة علاجية' : 'Clinical follow-up',
            reason: arabic ? 'متابعة' : 'Follow-up',
        }));
        const stats = { business_date: today, new_patients_today: 3, total_appointments_today: 5, today_received: 3600, today_outstanding: 1250, revenue_chart: [1800, 2400, 2100, 3200, 2800, 3600, 3100].map((revenue, i) => ({ date: `${i + 1}/10`, name: `${i + 1}/10`, revenue, amount: revenue })) };
        const financeSummary = {
            income: { net_revenue: 48500, total_revenue: 51000, total_collected: 42300, all_time_outstanding: 6200, outstanding: 6200, period_balance: 6200 },
            deductions: { total_deductions: 14800, doctor_dues: { total: 8500 }, staff_dues: { total: 3500 }, expenses: 2800 },
            obligations: { lab_debt: 2400 },
            net_operational_result: 27500,
            net_profit: 27500,
        };
        const financeTrend = {
            timeline: [6, 5, 4, 3, 2, 1, 0].map((daysAgo, idx) => ({
                date: offsetDate(-daysAgo),
                revenue: [4200, 5600, 4900, 6800, 5900, 7400, 7500][idx],
                expenses: [1400, 1800, 1500, 2100, 1700, 2300, 2000][idx],
                net_profit: [2800, 3800, 3400, 4700, 4200, 5100, 5500][idx],
            })),
        };
        const payments = patients.slice(0, 4).map((patient, idx) => ({
            id: idx + 1,
            patient_id: patient.id,
            patient_name: patient.name,
            amount: [1200, 1800, 950, 2400][idx],
            date: `${offsetDate(-idx)}T12:30:00`,
            notes: arabic ? 'دفعة جلسة علاجية' : 'Treatment session payment',
            doctor_name: doctors[idx % doctors.length].name,
        }));
        const expenses = [
            { id: 1, title: arabic ? 'خامات حشو وتعقيم' : 'Composite & sterilization stock', category: arabic ? 'مستلزمات' : 'Supplies', cost: 1450, amount: 1450, date: `${offsetDate(-1)}T15:00:00` },
            { id: 2, title: arabic ? 'دفعة معمل تركيبات' : 'Crown lab settlement', category: arabic ? 'معمل' : 'Lab', cost: 1350, amount: 1350, date: `${offsetDate(-2)}T16:00:00` },
        ];
        await context.addCookies([{ name: 'dentix_session_hint', value: 'fictional-local-capture', url: origin }]);
        await page.addInitScript(({ language }) => {
            localStorage.setItem('i18nextLng', language);
            localStorage.setItem('theme', 'light');
        }, { language });
        await page.route('**/*', async route => {
            const request = route.request();
            const url = new URL(request.url());
            if (url.pathname.startsWith('/api/')) {
                const path = url.pathname.replace(/\/$/, '');
                let data;
                if (path === '/api/auth/session' || path === '/api/v1/users/me') data = user;
                else if (path === '/api/v1/stats/dashboard') data = stats;
                else if (path === '/api/v1/appointments') data = appointments;
                else if (path === '/api/v1/next-visit-requests') data = [];
                else if (path === '/api/v1/users/doctors' || path === '/api/v1/doctors') data = doctors;
                else if (path === '/api/v1/patients/directory' || path === '/api/v1/patients') data = patients;
                else if (path === '/api/v1/patients/1') data = patients[0];
                else if (path === '/api/v1/patients/1/clinical-workspace') data = { patient_id: 1, teeth: {
                    '16': { lifecycle: 'PRESENT', findings: [{ code: 'CARIES', targets: [{ kind: 'surface', tooth_key: '16', surface_code: 'O' }] }] },
                    '26': { lifecycle: 'PRESENT', procedures: [{ code: 'PROS_CROWN' }] },
                    '36': { lifecycle: 'PRESENT', procedures: [{ code: 'REST_COMPOSITE', targets: [{ kind: 'surface', tooth_key: '36', surface_code: 'O' }] }] },
                }, work_items: [], warnings: [] };
                else if (path === '/api/v1/accounting/comprehensive-stats') data = financeSummary;
                else if (path === '/api/v1/metrics/profitability/trend') data = financeTrend;
                else if (path === '/api/v1/payments') data = payments;
                else if (path === '/api/v1/expenses') data = expenses;
                else if (path === '/api/v1/settings/features') data = [];
                else if (path === '/api/v1/onboarding/status') data = { enabled: false, seen_tips: [], steps: [] };
                else if (path === '/api/v1/onboarding/events') data = {};
                else if (path === '/api/v1/global-settings') data = {};
                else if (path === '/api/v1/settings/tenant') data = tenant;
                else if (path === '/api/v1/settings/entitlements') data = {
                    tenant_id: tenant.id, tenant_name: tenant.name, plan_name: tenant.plan,
                    can_read_clinical: true, is_hard_disabled: false, capabilities: {},
                };
                else if (path === '/api/v1/patients/1/payments') data = payments.filter((p) => p.patient_id === 1);
                else if (/\/(notifications|procedures|users|price-lists|insurance-providers|treatments|attachments|prescriptions|lab-orders|lab_orders|tooth_status|care-sessions|clinical-plans|clinical-attachment-links)(\/.*)?$/.test(path)) data = [];
                else {
                    unknown.add(`${request.method()} ${path}`);
                    return route.fulfill({ status: 404, json: { detail: 'No local screenshot fixture' } });
                }
                return route.fulfill({ json: { success: true, data } });
            }
            // Browser fixtures intercept every API request, including writes.
            // Only the local Vite UI and the app's existing font host can load.
            if (url.origin === origin || ['fonts.googleapis.com', 'fonts.gstatic.com'].includes(url.hostname)) return route.continue();
            return route.abort('blockedbyclient');
        });
        for (const [name, path, ready] of [
            ['dashboard', '/', '.stats-grid button'],
            ['appointments', '/appointments', '.fc-view-harness'],
            ['patients', '/patients', 'a[href="/patients/1"]'],
            ['chart', '/patients/1?tab=chart', '[data-layer="crown"][data-tooth-key="16"]'],
            ['finance', '/finance/overview', '.recharts-surface'],
        ]) {
            await page.goto(`${origin}${path}`);
            await page.locator(ready).first().waitFor({ state: 'visible', timeout: 30000 });
            if (name === 'appointments') {
                const collapseBtn = page.locator('[data-testid="reception-next-visit-queue"] button[aria-expanded="true"]');
                if (await collapseBtn.count()) await collapseBtn.first().click();
                const weekBtn = page.locator('.fc-timeGridWeek-button');
                if (await weekBtn.count()) await weekBtn.first().click();
            }
            await page.evaluate(() => Promise.race([document.fonts.ready, new Promise(resolve => setTimeout(resolve, 5000))]));
            await page.waitForTimeout(1600);
            const png = await page.screenshot({ animations: 'disabled', ...(name === 'dashboard' ? { clip: { x: 0, y: 0, width: 1440, height: 620 } } : {}) });
            // Encode the screenshot as WebP in Chromium; do not alter the UI.
            const webp = await page.evaluate(async base64 => {
                const image = new Image();
                image.src = `data:image/png;base64,${base64}`;
                await image.decode();
                const canvas = document.createElement('canvas');
                canvas.width = image.width;
                canvas.height = image.height;
                canvas.getContext('2d').drawImage(image, 0, 0);
                return canvas.toDataURL('image/webp', 0.92).split(',')[1];
            }, png.toString('base64'));
            writeFileSync(`${destination}${name}-${language}.webp`, Buffer.from(webp, 'base64'));
            console.log(`Captured ${name}-${language}.webp`);
        }
        await context.close();
        if (unknown.size) throw new Error(`Missing screenshot fixtures: ${[...unknown].join(', ')}`);
    }
} finally {
    await browser.close();
}
