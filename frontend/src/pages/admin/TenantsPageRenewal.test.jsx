import { webcrypto } from 'node:crypto';
import { expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import TenantsPage from './TenantsPage';
import { api } from '@/api';

vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: key => key, i18n: { language: 'en' } }) }));
vi.mock('react-router-dom', () => ({ useSearchParams: () => [new URLSearchParams(), vi.fn()] }));
vi.mock('@/api', () => ({ api: { get: vi.fn(), post: vi.fn() } }));
vi.mock('@/utils/logger', () => ({ default: { error: vi.fn() } }));
vi.mock('@/features/admin/SuperAdmin/TenantDetailPanel', () => ({ default: () => null }));
vi.mock('@/features/admin/SuperAdmin/TenantsManager', () => ({ default: ({ tenants, onManualRenew }) => tenants.map(tenant => <button key={tenant.id} onClick={() => onManualRenew(tenant)}>Open extension</button>) }));
vi.mock('@/shared/ui', async () => {
    const actual = await vi.importActual('@/shared/ui');
    return { ...actual, toast: { success: vi.fn(), error: vi.fn() } };
});
Object.defineProperty(globalThis.crypto, 'subtle', { value: webcrypto.subtle, configurable: true });

it('previews a free support extension and keeps its identity after a lost response and reload', async () => {
    sessionStorage.clear();
    api.get.mockImplementation(async url => ({ data: url.endsWith('/plans') ? [] : [{ id: 10, name: 'Synthetic support clinic' }] }));
    const commits = [];
    api.post.mockImplementation(async (url, payload, config) => {
        if (config?.params?.preview) return { data: { preview_marker: 'b'.repeat(64), preview_at: '2027-01-30T10:00:00', previous_end_date: '2027-01-31T10:00:00', subscription_end_date: '2027-02-03T10:00:00' } };
        commits.push(payload);
        if (commits.length === 1) throw new Error('Synthetic lost reply');
        return { data: { subscription_end_date: '2027-02-03T10:00:00' } };
    });
    let page = render(<TenantsPage />);
    const open = async () => {
        fireEvent.click(await screen.findByText('Open extension'));
        fireEvent.change(screen.getByRole('spinbutton'), { target: { value: '3' } });
        fireEvent.change(screen.getByRole('textbox'), { target: { value: 'Synthetic support correction' } });
        fireEvent.click(screen.getByText('super_admin.tenants.confirm_renewal'));
    };
    await open();
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/api/v1/admin/tenants/10/renew', expect.anything(), { params: { preview: true } }));
    expect(commits).toHaveLength(0);
    expect(await screen.findByText(/2027-02-03/)).toBeInTheDocument();
    fireEvent.click(screen.getByRole('button', { name: 'common.confirm' }));
    await waitFor(() => expect(commits).toHaveLength(1));
    page.unmount();
    page = render(<TenantsPage />);
    await open();
    fireEvent.click(await screen.findByRole('button', { name: 'common.confirm' }));
    await waitFor(() => expect(commits).toHaveLength(2));
    expect(commits[1].idempotency_key).toBe(commits[0].idempotency_key);
    expect(commits[1].preview_marker).toBe('b'.repeat(64));
    page.unmount();
});
