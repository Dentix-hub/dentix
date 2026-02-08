import http from 'k6/http';
import { config } from '../config.js';
import { default as loadTest } from './load_test.js';

export const options = {
    stages: [
        { duration: '2m', target: 80 },  // Ramp to 80 (Peak)
        { duration: '10m', target: 80 }, // Hold Peak for 10m
        { duration: '1m', target: 0 },   // Ramp down
    ],
    thresholds: config.thresholds,
};

export default loadTest;
