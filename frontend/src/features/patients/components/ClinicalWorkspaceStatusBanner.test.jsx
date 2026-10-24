import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import ClinicalWorkspaceStatusBanner from './ClinicalWorkspaceStatusBanner';
import { useAuthStore } from '@/store/auth.store';

describe('ClinicalWorkspaceStatusBanner role gating (D1)', () => {
    const mockT = (key, fallback, options) => {
        if (typeof fallback === 'object' && fallback !== null && !options) {
            options = fallback;
            fallback = undefined;
        }
        if (options?.count !== undefined && fallback?.includes('{{count}}')) {
            return fallback.replace('{{count}}', options.count);
        }
        return fallback || key;
    };

    const sampleChart = {
        coverage: { teeth: 'COMPLETE', periodontal: 'UNCOVERED' },
        isFallback: true,
        warnings: [
            { code: 'UNKNOWN_PROCEDURE_CODE', message: 'Legacy procedure code 999 unknown' },
            { code: 'UNKNOWN_TOOTH_STATUS_CONDITION', message: 'Condition Fractured on tooth 11 unknown' },
        ],
    };

    beforeEach(() => {
        useAuthStore.setState({ user: null });
    });

    it('non-admin sees only one Arabic warning count line and no coverage or technical codes', () => {
        useAuthStore.setState({ user: { id: 10, role: 'doctor' } });

        render(<ClinicalWorkspaceStatusBanner adaptedChart={sampleChart} t={mockT} />);

        // Must show the single short count line
        expect(screen.getByText(/2 سجلات قديمة تحتاج مراجعة/i)).toBeInTheDocument();

        // Must hide coverage chips and fallback banner from regular users
        expect(screen.queryByTestId('clinical-workspace-coverage')).not.toBeInTheDocument();
        expect(screen.queryByTestId('clinical-workspace-fallback-banner')).not.toBeInTheDocument();

        // Must hide raw technical codes
        expect(screen.queryByText(/\[UNKNOWN_PROCEDURE_CODE\]/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/\[UNKNOWN_TOOTH_STATUS_CONDITION\]/i)).not.toBeInTheDocument();
        expect(screen.queryByText(/التفاصيل التقنية/i)).not.toBeInTheDocument();
    });

    it('non-admin sees nothing when there are zero warnings and no empty workspace', () => {
        useAuthStore.setState({ user: { id: 10, role: 'doctor' } });

        const cleanChart = {
            coverage: { teeth: 'COMPLETE' },
            isFallback: false,
            warnings: [],
        };

        const { container } = render(<ClinicalWorkspaceStatusBanner adaptedChart={cleanChart} t={mockT} />);
        expect(container.textContent.trim()).toBe('');
    });

    it('admin sees coverage, fallback banner, count line, and collapsed technical details with codes', () => {
        useAuthStore.setState({ user: { id: 1, role: 'admin' } });

        render(<ClinicalWorkspaceStatusBanner adaptedChart={sampleChart} t={mockT} />);

        // Admin sees coverage chips
        expect(screen.getByTestId('clinical-workspace-coverage')).toBeInTheDocument();

        // Admin sees fallback notice
        expect(screen.getByTestId('clinical-workspace-fallback-banner')).toBeInTheDocument();

        // Admin sees the count line
        expect(screen.getByText(/2 سجلات قديمة تحتاج مراجعة/i)).toBeInTheDocument();

        // Admin has collapsed details
        const details = screen.getByTestId('clinical-workspace-technical-details');
        expect(details).toBeInTheDocument();
        expect(details).not.toHaveAttribute('open');

        // Codes are inside details
        expect(screen.getByText(/\[UNKNOWN_PROCEDURE_CODE\]/i)).toBeInTheDocument();
        expect(screen.getByText(/\[UNKNOWN_TOOTH_STATUS_CONDITION\]/i)).toBeInTheDocument();
    });
});
