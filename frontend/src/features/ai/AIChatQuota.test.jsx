import { beforeEach, expect, it, vi } from 'vitest';
import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import AIChat from './AIChat';
import { sendAIQuery } from '@/api';
const fixture = vi.hoisted(() => ({ quota: { daily_limit: 2, remaining_quota: null }, refresh: vi.fn(), noop: vi.fn() }));
vi.mock('@/api', () => ({ sendAIQuery: vi.fn() }));
vi.mock('@/store/tenant.store', () => {
    const useTenantStore = () => ({ entitlements: { capacities: { ai: fixture.quota } } });
    useTenantStore.getState = () => ({ fetchTenant: fixture.refresh });
    return { useTenantStore };
});
vi.mock('@/hooks/useVoiceInput', () => ({ useVoiceInput: () => ({ isListening: false, stopListening: fixture.noop, startListening: fixture.noop, toggleListening: fixture.noop, speechSupported: false }) }));
vi.mock('@/hooks/useTextToSpeech', () => ({ useTextToSpeech: () => ({ ttsEnabled: false, setTtsEnabled: fixture.noop, speakText: fixture.noop }) }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key, options) => options?.defaultValue || key }) }));
beforeEach(() => { vi.clearAllMocks(); fixture.quota = { daily_limit: 2, remaining_quota: null }; Element.prototype.scrollIntoView = vi.fn(); });
function open() { render(<AIChat />); fireEvent.click(screen.getByRole('button', { name: /Toggle assistant/ })); }
it('shows unavailable rather than fabricating zero remaining', () => {
    open(); expect(screen.getByText(/Quota unavailable/)).toBeInTheDocument();
    expect(screen.queryByText('المتبقي اليوم: 0 من 2')).not.toBeInTheDocument();
});
it('keeps an already admitted confirmation usable when the daily quota is exhausted', async () => {
    fixture.quota = { daily_limit: 2, remaining_quota: 0 };
    sendAIQuery.mockResolvedValue({ data: { success: true, tool: 'response', message: 'Synthetic confirmed action' } });
    open(); fireEvent.click(screen.getByRole('button', { name: /Confirm pending action/ }));
    await waitFor(() => expect(sendAIQuery).toHaveBeenCalledWith('نعم', expect.any(Object)));
    await waitFor(() => expect(fixture.refresh).toHaveBeenCalled());
});
