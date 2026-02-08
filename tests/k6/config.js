export const config = {
    BASE_URL: __ENV.BASE_URL || 'http://localhost:8000',
    // Admin credentials for seeding/setup if needed
    ADMIN_USER: 'manager_1',
    ADMIN_PASS: '123456',

    // Standard Thresholds
    thresholds: {
        http_req_duration: ['p(95)<2000'], // 95% of requests should be below 2s
        http_req_failed: ['rate<0.01'],   // Less than 1% failure
    },

    // Custom headers if needed globally
    headers: {
        'Content-Type': 'application/json',
    },
};
