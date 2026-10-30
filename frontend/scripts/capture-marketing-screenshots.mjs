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
        const patients = names.map((name, index) => ({ id: index + 1, name, age: 28 + index * 3, gender: index % 2 ? 'Female' : 'Male', file_number: `DEMO-00${index + 1}`, phone: '', medical_history: '', address: '', balance: [450, 0, 1200, 0, 800][index], total_cost: 2400, total_paid: 1200, created_at: `${today}T09:00:00`, medical_alert: null }));
        const subscriptionEnd = new Date(Date.now() + 21 * 86400000).toISOString().slice(0, 10);
        const tenant = { id: 99999, name: arabic ? 'عيادة العرض التجريبي' : 'Dentix Demo Clinic', plan: 'premium', is_active: true, subscription_status: 'active', subscription_end_date: subscriptionEnd, timezone: 'Africa/Cairo' };
        const user = { id: 99999, username: arabic ? 'طبيب العيادة التجريبية' : 'Demo doctor', name: arabic ? 'طبيب العيادة التجريبية' : 'Demo doctor', role: 'admin', tenant_id: 99999, is_active: true, tenant };
        const appointments = patients.map((patient, index) => ({ id: index + 1, patient_id: patient.id, patient_name: patient.name, patient, date_time: `${today}T${String(10 + index).padStart(2, '0')}:00:00`, duration_minutes: 30, status: ['Completed', 'Completed', 'Waiting', 'Scheduled', 'Scheduled'][index], notes: arabic ? 'موعد تجريبي' : 'Demonstration appointment', reason: arabic ? 'متابعة' : 'Follow-up' }));
        const stats = { business_date: today, new_patients_today: 3, total_appointments_today: 5, today_received: 3600, today_outstanding: 1250, revenue_chart: [1800, 2400, 2100, 3200, 2800, 3600, 3100].map((revenue, i) => ({ date: `${i + 1}/10`, name: `${i + 1}/10`, revenue, amount: revenue })) };
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
                else if (path === '/api/v1/patients/directory') data = patients;
                else if (path === '/api/v1/patients/1') data = patients[0];
                else if (path === '/api/v1/patients/1/clinical-workspace') data = { patient_id: 1, teeth: {
                    '16': { lifecycle: 'PRESENT', findings: [{ code: 'CARIES', targets: [{ kind: 'surface', tooth_key: '16', surface_code: 'O' }] }] },
                    '26': { lifecycle: 'PRESENT', procedures: [{ code: 'PROS_CROWN' }] },
                    '36': { lifecycle: 'PRESENT', procedures: [{ code: 'REST_COMPOSITE', targets: [{ kind: 'surface', tooth_key: '36', surface_code: 'O' }] }] },
                }, work_items: [], warnings: [] };
                else if (path === '/api/v1/settings/features') data = [];
                else if (path === '/api/v1/onboarding/status') data = { enabled: false, seen_tips: [], steps: [] };
                else if (path === '/api/v1/onboarding/events') data = {};
                else if (path === '/api/v1/global-settings') data = {};
                else if (path === '/api/v1/settings/tenant') data = tenant;
                else if (/\/(notifications|procedures|doctors|users|price-lists|insurance-providers|payments|treatments|attachments|prescriptions|lab-orders|lab_orders|tooth_status|care-sessions|clinical-plans|clinical-attachment-links)(\/.*)?$/.test(path)) data = [];
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
            ['dashboard', '/', '.stats-grid'],
            ['patients', '/patients', 'a[href="/patients/1"]'],
            ['chart', '/patients/1?tab=chart', '[data-layer="crown"][data-tooth-key="16"]'],
        ]) {
            await page.goto(`${origin}${path}`);
            await page.locator(ready).first().waitFor({ state: 'visible', timeout: 30000 });
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
