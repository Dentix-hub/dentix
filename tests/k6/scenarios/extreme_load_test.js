import http from 'k6/http';
import { check, sleep } from 'k6';
import { config } from '../config.js';
import { default as loadTest } from './load_test.js';

// Extreme Load Test - Finding the Breaking Point
// Ramps up users until the system likely fails

export const options = {
    stages: [
        { duration: '30s', target: 100 }, // Warm up fast
        { duration: '30s', target: 200 }, // Stress level
        { duration: '30s', target: 300 }, // Extreme level
        { duration: '30s', target: 400 }, // Breaking point?
        { duration: '30s', target: 500 }, // Destruction
        { duration: '30s', target: 0 },   // Recovery
    ],
    thresholds: {
        http_req_failed: ['rate<0.10'], // Allow 10% failure at extreme load before aborting
        http_req_duration: ['p(95)<10000'], // Allow 10s response time
    },
};

export default loadTest;
