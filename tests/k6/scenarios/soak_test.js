import http from 'k6/http';
import { config } from '../config.js';
import { default as loadTest } from './load_test.js';

export const options = {
    stages: [
        { duration: '2m', target: 40 },   // Ramp up
        { duration: '4h', target: 40 },   // Soak for 4 hours (shortened for demo, usually 8h+)
        { duration: '2m', target: 0 },    // Ramp down
    ],
    thresholds: config.thresholds,
};

export default loadTest;
