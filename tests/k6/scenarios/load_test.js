import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { config } from '../config.js';
import { login, getAuthHeaders, getRandomItem } from '../utils.js';

export const options = {
    stages: [
        { duration: '30s', target: 20 }, // Ramp up to 20 users
        { duration: '1m', target: 40 },  // Ramp to 40 (Baseline)
        { duration: '5m', target: 40 },  // Stay at 40
        { duration: '30s', target: 0 },  // Ramp down
    ],
    thresholds: config.thresholds,
};

// Simulation of a standard user journey
export default function () {
    // 1. Login
    // Select a random clinic admin (manager_1 to manager_8)
    const clinicId = Math.floor(Math.random() * 8) + 1;
    const username = `admin_stress_${clinicId}`; // Created by seeder
    const password = '123456';

    const token = login(username, password);
    if (!token) return; // Skip iteration if login fails

    const params = getAuthHeaders(token);

    group('Dashboard Flow', () => {
        // 2. Load Dashboard Stats
        const resDash = http.get(`${config.BASE_URL}/api/v1/dashboard/stats`, params);
        check(resDash, { 'dashboard stats 200': (r) => r.status === 200 });
        sleep(1);
    });

    group('Patient Management', () => {
        // 3. Get Patient List
        const resPatients = http.get(`${config.BASE_URL}/api/v1/patients/?skip=0&limit=10`, params);
        check(resPatients, { 'get patients 200': (r) => r.status === 200 });

        // Pick a random patient if available
        const patients = resPatients.json();
        if (patients && patients.length > 0) {
            const patient = getRandomItem(patients);
            // 4. Get Patient Details
            const resDetail = http.get(`${config.BASE_URL}/api/v1/patients/${patient.id}`, params);
            check(resDetail, { 'get patient detail 200': (r) => r.status === 200 });
        }
        sleep(2);
    });

    group('Appointments', () => {
        // 5. Get Appointments
        const resAppt = http.get(`${config.BASE_URL}/api/v1/appointments/?skip=0&limit=20`, params);
        check(resAppt, { 'get appointments 200': (r) => r.status === 200 });
        sleep(1);
    });
}
