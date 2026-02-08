import http from 'k6/http';
import { check, sleep, group } from 'k6';
import { config } from '../config.js';
import { login, getAuthHeaders } from '../utils.js';
import { options as loadOptions, default as loadTest } from './load_test.js';

export const options = {
    stages: [
        { duration: '2m', target: 50 },  // Ramp up
        { duration: '2m', target: 100 },
        { duration: '2m', target: 150 }, // Stress
        { duration: '2m', target: 200 }, // Breaking point?
        { duration: '2m', target: 0 },   // Recovery
    ],
    thresholds: {
        http_req_failed: ['rate<0.05'], // Allow 5% errors before failing test (it is a stress test after all)
        http_req_duration: ['p(95)<5000'], // Allow 5s response time
    },
};

export default loadTest; // Reuse logic
