import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
    isPerfDiagnosticsEnabled,
    setupApiPerfInterceptor,
    startRoutePerfSession,
    resetRecordedRoutesForTesting,
} from './perfDiagnostics';

describe('Frontend Perf Diagnostics (PR4)', () => {
    let mockAxios;
    let requestInterceptor;
    let responseSuccessInterceptor;
    let responseErrorInterceptor;

    beforeEach(() => {
        resetRecordedRoutesForTesting();
        vi.clearAllMocks();
        localStorage.clear();

        requestInterceptor = null;
        responseSuccessInterceptor = null;
        responseErrorInterceptor = null;

        mockAxios = {
            interceptors: {
                request: {
                    use: vi.fn((fn) => {
                        requestInterceptor = fn;
                    }),
                },
                response: {
                    use: vi.fn((successFn, errorFn) => {
                        responseSuccessInterceptor = successFn;
                        responseErrorInterceptor = errorFn;
                    }),
                },
            },
        };
    });

    afterEach(() => {
        vi.useRealTimers();
        localStorage.clear();
        resetRecordedRoutesForTesting();
    });

    it('detects enabled state via localStorage flag', () => {
        expect(isPerfDiagnosticsEnabled()).toBe(false);
        localStorage.setItem('PERF_DIAGNOSTICS', '1');
        expect(isPerfDiagnosticsEnabled()).toBe(true);
    });

    it('does not attach interceptor when disabled', () => {
        setupApiPerfInterceptor(mockAxios);
        expect(mockAxios.interceptors.request.use).not.toHaveBeenCalled();
    });

    it('measures API requests and records peak parallelism during route load', async () => {
        vi.useFakeTimers();
        localStorage.setItem('PERF_DIAGNOSTICS', '1');
        const consoleGroupSpy = vi.spyOn(console, 'group').mockImplementation(() => {});
        const consoleLogSpy = vi.spyOn(console, 'log').mockImplementation(() => {});
        const consoleTableSpy = vi.spyOn(console, 'table').mockImplementation(() => {});
        const consoleGroupEndSpy = vi.spyOn(console, 'groupEnd').mockImplementation(() => {});

        setupApiPerfInterceptor(mockAxios);
        expect(mockAxios.interceptors.request.use).toHaveBeenCalled();

        startRoutePerfSession('Dashboard (/)');

        // Request 1 starts
        const req1 = requestInterceptor({ url: '/api/v1/patients', method: 'get' });
        // Request 2 starts concurrently
        const req2 = requestInterceptor({ url: '/api/v1/appointments', method: 'get' });

        expect(req1._perf.activeAtStart).toBe(1);
        expect(req2._perf.activeAtStart).toBe(2);

        // Request 1 completes
        responseSuccessInterceptor({
            config: req1,
            status: 200,
            headers: { 'server-timing': 'db;dur=2.50, total;dur=5.00' },
        });

        // Request 2 completes
        responseSuccessInterceptor({
            config: req2,
            status: 200,
            headers: {},
        });

        // Advance timers to trigger session settlement
        vi.advanceTimersByTime(2000);

        expect(consoleGroupSpy).toHaveBeenCalledWith(
            expect.stringContaining('[PERF_TIMING] First Load: Dashboard (/)'),
            expect.any(String)
        );
        expect(consoleLogSpy).toHaveBeenCalledWith(
            expect.stringContaining('Total API Calls: 2 | Peak Parallelism: 2')
        );
        expect(consoleTableSpy).toHaveBeenCalledWith(
            expect.arrayContaining([
                expect.objectContaining({
                    Endpoint: '/api/v1/patients',
                    Method: 'GET',
                    Status: 200,
                    'Server-Timing': 'db;dur=2.50, total;dur=5.00',
                }),
                expect.objectContaining({
                    Endpoint: '/api/v1/appointments',
                    Method: 'GET',
                    Status: 200,
                }),
            ])
        );

        consoleGroupSpy.mockRestore();
        consoleLogSpy.mockRestore();
        consoleTableSpy.mockRestore();
        consoleGroupEndSpy.mockRestore();
    });

    it('does not re-record route once completed', () => {
        vi.useFakeTimers();
        localStorage.setItem('PERF_DIAGNOSTICS', '1');
        const consoleGroupSpy = vi.spyOn(console, 'group').mockImplementation(() => {});

        startRoutePerfSession('Dashboard (/)');
        vi.advanceTimersByTime(2000);
        expect(consoleGroupSpy).toHaveBeenCalledTimes(1);

        // Second visit should be ignored
        startRoutePerfSession('Dashboard (/)');
        vi.advanceTimersByTime(2000);
        expect(consoleGroupSpy).toHaveBeenCalledTimes(1);

        consoleGroupSpy.mockRestore();
    });

    it('handles rejected API responses gracefully', async () => {
        vi.useFakeTimers();
        localStorage.setItem('PERF_DIAGNOSTICS', '1');
        setupApiPerfInterceptor(mockAxios);

        startRoutePerfSession('ErrorRoute');
        const req = requestInterceptor({ url: '/api/v1/fail', method: 'get' });
        await expect(
            responseErrorInterceptor({
                config: req,
                response: { status: 500 },
            })
        ).rejects.toBeDefined();

        vi.advanceTimersByTime(2000);
    });
});
