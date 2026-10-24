import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import MedicalAlertBadge from './MedicalAlertBadge';
import PatientTable from '../PatientTable';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, options) => {
            const map = {
                'patients.medical_alert_generic': 'تنبيه طبي',
                'patients.medical_conditions.pregnancy': 'حمل/رضاعة',
                'patients.medical_conditions.diabetes': 'سكري',
                'patients.medical_conditions.hypertension': 'ضغط دم',
                'patients.medical_conditions.allergy': 'حساسية',
                'patients.medical_conditions.other': 'أخرى',
            };
            if (map[key]) return map[key];
            if (typeof options === 'string') return options;
            if (options && options.age) return `${options.age} سنة`;
            return key;
        },
    }),
}));

vi.mock('@/auth/useAuth', () => ({
    useAuth: () => ({
        user: { id: 1, role: 'admin' },
    }),
}));

describe('MedicalAlertBadge', () => {
    it('renders nothing when alert is null, has_alert is false, or kinds is empty', () => {
        const { container: c1 } = render(<MedicalAlertBadge alert={null} />);
        expect(c1.firstChild).toBeNull();

        const { container: c2 } = render(<MedicalAlertBadge alert={{ has_alert: false, kinds: [] }} />);
        expect(c2.firstChild).toBeNull();

        const { container: c3 } = render(<MedicalAlertBadge alert={{ has_alert: true, kinds: [] }} />);
        expect(c3.firstChild).toBeNull();
    });

    it('renders warning badge for general medical conditions with generic tooltip', () => {
        render(<MedicalAlertBadge alert={{ has_alert: true, kinds: ['diabetes', 'hypertension'] }} />);
        const warning = screen.getByTestId('medical-alert-warning');
        expect(warning).toBeInTheDocument();
        expect(screen.queryByTestId('medical-alert-pregnancy')).toBeNull();
        expect(warning.getAttribute('title')).toBe('تنبيه طبي');
    });

    it('renders nothing when patient has only smoking', () => {
        const { container: c1 } = render(<MedicalAlertBadge alert={{ has_alert: false, kinds: ['smoking'] }} />);
        expect(c1.firstChild).toBeNull();

        const { container: c2 } = render(<MedicalAlertBadge alert={{ has_alert: true, kinds: ['smoking'] }} />);
        expect(c2.firstChild).toBeNull();
    });

    it('renders distinct badge for pregnancy condition', () => {
        render(<MedicalAlertBadge alert={{ has_alert: true, kinds: ['pregnancy'] }} />);
        const pregnancy = screen.getByTestId('medical-alert-pregnancy');
        expect(pregnancy).toBeInTheDocument();
        expect(screen.queryByTestId('medical-alert-warning')).toBeNull();
        expect(pregnancy.getAttribute('title')).toBe('حمل/رضاعة');
    });

    it('renders both badges when patient has both pregnancy and general conditions', () => {
        render(<MedicalAlertBadge alert={{ has_alert: true, kinds: ['pregnancy', 'diabetes'] }} />);
        expect(screen.getByTestId('medical-alert-pregnancy')).toBeInTheDocument();
        expect(screen.getByTestId('medical-alert-warning')).toBeInTheDocument();
    });
});

describe('PatientTable with Medical Alerts', () => {
    it('renders appropriate alert badges in table rows and cards', () => {
        const patients = [
            {
                id: 1,
                name: 'Fatima',
                age: 28,
                medical_alert: { has_alert: true, kinds: ['pregnancy'] },
            },
            {
                id: 2,
                name: 'Omar',
                age: 50,
                medical_alert: { has_alert: true, kinds: ['diabetes'] },
            },
            {
                id: 3,
                name: 'Zaid',
                age: 22,
                medical_alert: { has_alert: false, kinds: [] },
            },
        ];

        render(
            <MemoryRouter>
                <PatientTable patients={patients} isLoading={false} />
            </MemoryRouter>
        );

        // Fatima should have pregnancy badge (in desktop table and mobile card)
        const pregnancyBadges = screen.getAllByTestId('medical-alert-pregnancy');
        expect(pregnancyBadges.length).toBe(2);

        // Omar should have warning badge (in desktop table and mobile card)
        const warningBadges = screen.getAllByTestId('medical-alert-warning');
        expect(warningBadges.length).toBe(2);
    });
});
