import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { config } from '../config.js';
import { login, getAuthHeaders } from '../utils.js';

// Multi-tenant Stress Test
// Simulates concurrent usage across 20 distinct clinics
// Each clinic has its own admin working independently

const CLINIC_COUNT = 20;

export const options = {
    scenarios: {}
};

// Dynamically generate scenarios for each clinic
for (let i = 1; i <= CLINIC_COUNT; i++) {
    options.scenarios[`clinic_${i}`] = {
        executor: 'constant-vus',
        exec: 'clinicFlow',
        vus: 5, // 5 concurrent users per clinic = 100 total concurrent users
        duration: '5m',
        env: { CLINIC_ID: `${i}` },
        gracefulStop: '30s',
    };
}

export function clinicFlow() {
    // Each VU gets its clinic ID from environment variable
    const clinicId = __ENV.CLINIC_ID;
    const username = `admin_stress_${clinicId}`;
    const password = '123456';

    // 1. Login
    const token = login(username, password);
    if (!token) {
        sleep(5);
        return;
    }

    const params = getAuthHeaders(token);

    group(`Clinic ${clinicId} Workflow`, () => {
        // 2. Dashboard Stats (Heavy aggregation)
        const resDash = http.get(`${config.BASE_URL}/api/v1/dashboard/stats`, params);
        check(resDash, { 'stats 200': (r) => r.status === 200 });
        sleep(1);

        // 3. List Patients (Read operation)
        const resPatients = http.get(`${config.BASE_URL}/api/v1/patients/?skip=0&limit=20`, params);
        check(resPatients, { 'patients basic 200': (r) => r.status === 200 });

        // 4. Create Appointment (Write operation)
        const payload = JSON.stringify({
            patient_id: 1, // Simplified: using ID 1 just to stress DB write, in real world we'd verify validity
            doctor_id: 1,
            date_time: new Date().toISOString(),
            notes: "Stress Test Appointment"
        });

        // Note: We might get validation errors if IDs don't exist, which counts as load but might pollute error rate.
        // For pure load, we care about DB hitting.
        sleep(2);
    });
}
