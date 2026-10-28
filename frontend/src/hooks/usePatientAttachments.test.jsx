import { renderHook, act } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import {
    usePatientAttachments,
    ATTACHMENT_POLL_INTERVAL_MS,
    MAX_ATTACHMENT_POLL_DURATION_MS,
} from './usePatientDetails';
import * as api from '@/api';

vi.mock('@/api', () => ({
    getAttachments: vi.fn(),
}));

function createWrapper() {
    const queryClient = new QueryClient({
        defaultOptions: {
            queries: {
                retry: false,
            },
        },
    });
    const Wrapper = ({ children }) => (
        <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>
    );
    Wrapper.displayName = 'TestQueryClientWrapper';
    return Wrapper;
}

describe('usePatientAttachments - bounded polling', () => {
    beforeEach(() => {
        vi.useFakeTimers();
        vi.clearAllMocks();
    });

    afterEach(() => {
        vi.useRealTimers();
    });

    it('polls at finite intervals while pending and stalls when budget is exhausted', async () => {
        api.getAttachments.mockResolvedValue({
            data: [{ id: 101, filename: 'xray.png', storage_status: 'pending' }],
        });

        const { result } = renderHook(() => usePatientAttachments(42), {
            wrapper: createWrapper(),
        });

        // Initial fetch
        await act(async () => {
            await vi.advanceTimersByTimeAsync(0);
        });

        expect(api.getAttachments).toHaveBeenCalledTimes(1);
        expect(result.current.isPollingStalled).toBe(false);

        // Advance through all polling intervals until max duration
        const intervals = MAX_ATTACHMENT_POLL_DURATION_MS / ATTACHMENT_POLL_INTERVAL_MS;
        for (let i = 1; i <= intervals; i++) {
            await act(async () => {
                await vi.advanceTimersByTimeAsync(ATTACHMENT_POLL_INTERVAL_MS);
            });
            expect(api.getAttachments).toHaveBeenCalledTimes(i + 1);
        }

        // Budget reached: polling must stop and stall state must be set
        await act(async () => {
            await vi.advanceTimersByTimeAsync(0);
        });
        expect(result.current.isPollingStalled).toBe(true);

        const callCount = api.getAttachments.mock.calls.length;

        // Advance further time: no more polling calls should occur
        await act(async () => {
            await vi.advanceTimersByTimeAsync(ATTACHMENT_POLL_INTERVAL_MS * 5);
        });
        expect(api.getAttachments).toHaveBeenCalledTimes(callCount);

        // Deliberate manual retry resets the budget and starts polling again
        await act(async () => {
            result.current.manualRetry();
            await vi.advanceTimersByTimeAsync(0);
        });

        expect(result.current.isPollingStalled).toBe(false);
        expect(api.getAttachments).toHaveBeenCalledTimes(callCount + 1);
    });

    it('stops polling and clears stall when attachment transitions to ready', async () => {
        api.getAttachments.mockResolvedValueOnce({
            data: [{ id: 102, filename: 'scan.png', storage_status: 'pending' }],
        });

        const { result } = renderHook(() => usePatientAttachments(42), {
            wrapper: createWrapper(),
        });

        await act(async () => {
            await vi.advanceTimersByTimeAsync(0);
        });
        expect(api.getAttachments).toHaveBeenCalledTimes(1);

        // Next poll returns ready
        api.getAttachments.mockResolvedValueOnce({
            data: [{ id: 102, filename: 'scan.png', storage_status: 'ready' }],
        });

        await act(async () => {
            await vi.advanceTimersByTimeAsync(ATTACHMENT_POLL_INTERVAL_MS);
        });

        expect(api.getAttachments).toHaveBeenCalledTimes(2);
        expect(result.current.isPollingStalled).toBe(false);

        // Further time advances do not poll
        await act(async () => {
            await vi.advanceTimersByTimeAsync(ATTACHMENT_POLL_INTERVAL_MS * 3);
        });
        expect(api.getAttachments).toHaveBeenCalledTimes(2);
    });

    it('resets polling budget when a newly queued attachment appears', async () => {
        api.getAttachments.mockResolvedValueOnce({
            data: [{ id: 103, filename: 'doc1.png', storage_status: 'pending' }],
        });

        const { result } = renderHook(() => usePatientAttachments(42), {
            wrapper: createWrapper(),
        });

        await act(async () => {
            await vi.advanceTimersByTimeAsync(0);
        });

        // Run several polls
        for (let i = 0; i < 5; i++) {
            await act(async () => {
                await vi.advanceTimersByTimeAsync(ATTACHMENT_POLL_INTERVAL_MS);
            });
        }
        expect(api.getAttachments).toHaveBeenCalledTimes(6);

        // Newly queued operation arrives (e.g. user uploaded doc2.png)
        api.getAttachments.mockResolvedValue({
            data: [
                { id: 103, filename: 'doc1.png', storage_status: 'pending' },
                { id: 104, filename: 'doc2.png', storage_status: 'pending' },
            ],
        });

        await act(async () => {
            await vi.advanceTimersByTimeAsync(ATTACHMENT_POLL_INTERVAL_MS);
        });

        // The budget has been reset, so polling can continue and is not stalled
        expect(result.current.isPollingStalled).toBe(false);
    });
});
