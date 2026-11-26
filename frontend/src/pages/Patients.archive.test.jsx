import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import Patients from './Patients';

const { archive, role, refetch } = vi.hoisted(() => ({
    archive: vi.fn(),
    role: { value: 'admin' },
    refetch: vi.fn(),
}));

const patients = [{ id: 42, name: 'Synthetic Patient', file_number: 'TEST-42' }];

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({ user: { role: role.value } }),
}));

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, options) => options?.name ? `${key}: ${options.name}` : key,
        i18n: { language: 'en', dir: () => 'ltr' },
    }),
}));

vi.mock('@/hooks/usePatients', () => ({
    useDeletePatient: () => ({ mutateAsync: archive }),
    usePatientDirectory: () => ({ data: { pages: [{ items: patients }] }, refetch }),
    useRecentPatients: (ids) => ({ data: patients.filter(({ id }) => ids.includes(id)), refetch }),
}));

vi.mock('@/features/patients/modals/PatientModal.jsx', () => ({ default: () => null }));

function openList(route = '/patients') {
    render(<MemoryRouter initialEntries={[route]}><Patients /></MemoryRouter>);
    return screen.getAllByRole('button', { name: 'patients.archive_patient' })[0];
}

function confirm() {
    return within(screen.getByRole('dialog')).getByRole('button', { name: 'common.confirm' });
}

describe('Patients directory archive confirmation', () => {
    beforeEach(() => {
        archive.mockReset();
        role.value = 'admin';
        localStorage.clear();
    });

    it('shows the selected patient and restores focus on cancel without writing', async () => {
        const trigger = openList();
        fireEvent.click(trigger);
        const dialog = screen.getByRole('dialog');
        expect(within(dialog).getByText('patients.archive_confirm: Synthetic Patient')).toBeVisible();
        fireEvent.click(within(dialog).getByRole('button', { name: 'common.cancel' }));
        expect(archive).not.toHaveBeenCalled();
        await waitFor(() => expect(trigger).toHaveFocus());
    });

    it('makes a single request and removes a recent patient only after success', async () => {
        localStorage.setItem('dentix_recent_patient_ids_v1', '[42]');
        let complete;
        archive.mockImplementation(() => new Promise(resolve => { complete = resolve; }));
        const trigger = openList('/patients?scope=recent');
        fireEvent.click(trigger);
        const button = confirm();
        act(() => {
            button.click();
            button.click();
        });
        fireEvent.click(trigger);
        expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
        expect(archive).toHaveBeenCalledExactlyOnceWith(42);
        expect(screen.getAllByRole('link', { name: 'Synthetic Patient' }).length).toBeGreaterThan(0);
        await act(async () => complete());
        expect(screen.queryByRole('link', { name: 'Synthetic Patient' })).not.toBeInTheDocument();
        expect(localStorage.getItem('dentix_recent_patient_ids_v1')).toBe('[]');
    });

    it('keeps the patient in the list after failure and allows a new confirmation', async () => {
        archive.mockRejectedValueOnce(new Error('unavailable')).mockResolvedValueOnce();
        const trigger = openList();
        fireEvent.click(trigger);
        await act(async () => fireEvent.click(confirm()));
        expect(screen.getAllByRole('link', { name: 'Synthetic Patient' }).length).toBeGreaterThan(0);
        fireEvent.click(trigger);
        await act(async () => fireEvent.click(confirm()));
        expect(archive.mock.calls).toEqual([[42], [42]]);
    });

    it('keeps archive unavailable to the doctor role', () => {
        role.value = 'doctor';
        render(<MemoryRouter><Patients /></MemoryRouter>);
        expect(screen.queryByRole('button', { name: 'patients.archive_patient' })).not.toBeInTheDocument();
        expect(archive).not.toHaveBeenCalled();
    });
});
