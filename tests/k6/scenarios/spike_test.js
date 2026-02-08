import http from 'k6/http';
import { config } from '../config.js';
import { default as loadTest } from './load_test.js';

export const options = {
    stages: [
        { duration: '30s', target: 30 },  // Baseline
        { duration: '30s', target: 120 }, // SPIKE!
        { duration: '1m', target: 120 },  // Hold Spike
        { duration: '30s', target: 30 },  // Recovery
        { duration: '30s', target: 0 },
    ],
    thresholds: config.thresholds,
};

export default loadTest;
