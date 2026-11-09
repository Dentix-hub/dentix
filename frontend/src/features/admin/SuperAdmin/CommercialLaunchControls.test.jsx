import { beforeEach, expect, it, vi } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import CommercialLaunchControls from './CommercialLaunchControls';
import TenantCommercialOverrides from './TenantCommercialOverrides';
import { api } from '@/api';
vi.mock('@/api', () => ({ api: { get: vi.fn(), post: vi.fn(), put: vi.fn() } }));
vi.mock('react-i18next', () => ({ useTranslation: () => ({ t: (key) => key, i18n: { language: 'en' } }) }));
const trial = { trial_plan_name: 'professional', trial_plan_id: 2, trial_duration_days: 14, eligible_plans: [{ id: 2, name: 'professional' }] };
const inventory = { enforcement_mode: 'observe', catalog_plans: [{ id: 1, name: 'essential', price: 200, max_users: 2, ai_daily_limit: 2, is_active: true }], warnings: [] };
const preview = { unanchored_tenants: [{ tenant_id: 11, tenant_name: 'Synthetic clinic', current_raw_plan: 'starter', current_plan_id: null, policy_revision: 3 }] };
function mount(child) { return render(<QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false }, mutations: { retry: false } } })}>{child}</QueryClientProvider>); }
beforeEach(() => {
    vi.clearAllMocks();
    api.get.mockImplementation(async (url) => ({ data: url.endsWith('trial-policy') ? trial : url.endsWith('catalog-inventory') ? inventory : url.endsWith('reconciliation-preview') ? preview : url.endsWith('commercial-overrides') ? { policy_revision: 7, overrides: [], effective_capabilities: { ai_insights: true } } : { active_restrictions: [] } }));
    api.post.mockResolvedValue({ data: {} }); api.put.mockResolvedValue({ data: {} });
});
async function ready() { await screen.findByRole('heading', { name: 'Commercial controls' }); fireEvent.change(screen.getByLabelText('Reason for change'), { target: { value: 'Owner approved synthetic change' } }); }
async function confirm() { fireEvent.click(await screen.findByRole('button', { name: 'Confirm and save' })); }
it('shows actual mode/calendar unit; does not mutate on read', async () => {
    mount(<CommercialLaunchControls />); await ready();
    expect(screen.getByText(/Commercial enforcement is not enabled/)).toBeInTheDocument();
    expect(screen.getByText('Price / calendar month')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Preview selected mappings' })).toBeDisabled();
    expect(api.post).not.toHaveBeenCalled(); expect(api.put).not.toHaveBeenCalled();
});
it('previews trial changes and sends the observed policy/reason', async () => {
    mount(<CommercialLaunchControls />); await ready();
    fireEvent.change(screen.getByLabelText('Trial days'), { target: { value: 21 } });
    fireEvent.click(screen.getByRole('button', { name: 'Preview trial policy' }));
    expect(api.put).not.toHaveBeenCalled(); await confirm();
    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/api/v1/admin/subscriptions/trial-policy', expect.objectContaining({ trial_duration_days: 21, expected_trial_duration_days: 14, expected_trial_plan_id: 2 })));
    await waitFor(() => expect(api.get.mock.calls.filter(([url]) => url.endsWith('trial-policy')).length).toBeGreaterThan(1));
});
it('uses dedicated emergency API rather than a rollout toggle', async () => {
    mount(<CommercialLaunchControls />); await ready();
    fireEvent.click(screen.getByRole('button', { name: 'Preview emergency restriction' })); await confirm();
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/api/v1/admin/features/emergency-restrictions', expect.objectContaining({ capability_key: 'ai_insights', is_restricted: true, expected_restricted: false })));
});
it('submits only explicit mappings with original revision and anchor', async () => {
    mount(<CommercialLaunchControls />); await ready();
    fireEvent.change(screen.getByLabelText(/Synthetic clinic/), { target: { value: '1' } });
    fireEvent.click(screen.getByRole('button', { name: 'Preview selected mappings' }));
    expect(api.post).not.toHaveBeenCalled(); await confirm();
    await waitFor(() => expect(api.post).toHaveBeenCalledWith('/api/v1/admin/subscriptions/reconcile-tenants', { reason: 'Owner approved synthetic change', mappings: [{ tenant_id: 11, plan_id: 1, expected_revision: 3, expected_plan_id: null }] }));
});
async function openOverride(onSaved) {
    mount(<TenantCommercialOverrides tenantId={11} onSaved={onSaved} />);
    fireEvent.click(screen.getByRole('button', { name: 'Clinic commercial overrides' }));
    await screen.findByLabelText('Override reason');
    fireEvent.change(screen.getByLabelText('Override reason'), { target: { value: 'Reset synthetic clinic to plan' } });
    fireEvent.click(screen.getByRole('button', { name: 'Preview override' })); await confirm();
}
it('resets to inheritance with revision and refetches effective access', async () => {
    const saved = vi.fn(); await openOverride(saved);
    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/api/v1/admin/tenants/11/commercial-overrides', { expected_revision: 7, reason: 'Reset synthetic clinic to plan', overrides: [{ capability_key: 'ai_insights', override_value: 'inherit', expires_at: null }] }));
    await waitFor(() => expect(saved).toHaveBeenCalledOnce());
});
it('reports stale revision without claiming a successful change', async () => {
    api.put.mockRejectedValue({ response: { data: { detail: 'Revision conflict' } } });
    const saved = vi.fn(); await openOverride(saved);
    expect(await screen.findByRole('alert')).toHaveTextContent('Revision conflict'); expect(saved).not.toHaveBeenCalled();
});

it('edits an explicit per-plan tool list instead of inventing a feature grant', async () => {
    const { default: PlanAIToolPolicy } = await import('./PlanAIToolPolicy');
    api.get.mockResolvedValue({ data: [{ name: 'search_patients', description: 'Search visible patients' }] });
    const changed = vi.fn();
    mount(<PlanAIToolPolicy value="[]" onChange={changed} />);
    fireEvent.click(screen.getByRole('button', { name: 'Allowed AI tools for this plan' }));
    fireEvent.click(await screen.findByLabelText('Search visible patients'));
    expect(changed).toHaveBeenCalledWith('["search_patients"]');
});

it('can repair a missing trial reference by explicitly selecting an eligible Professional alias', async () => {
    api.get.mockImplementation(async (url) => ({ data: url.endsWith('trial-policy') ? { ...trial, trial_plan_id: null, eligible_plans: [{ id: 3, name: 'pro' }] } : url.endsWith('catalog-inventory') ? inventory : url.endsWith('reconciliation-preview') ? preview : { active_restrictions: [] } }));
    mount(<CommercialLaunchControls />); await ready();
    fireEvent.change(screen.getByLabelText('Trial plan'), { target: { value: 'pro' } });
    expect(screen.getByRole('button', { name: 'Preview trial policy' })).not.toBeDisabled();
    fireEvent.click(screen.getByRole('button', { name: 'Preview trial policy' })); await confirm();
    await waitFor(() => expect(api.put).toHaveBeenCalledWith('/api/v1/admin/subscriptions/trial-policy', expect.objectContaining({ trial_plan_name: 'pro', expected_trial_plan_id: null })));
});
