import { render, screen } from '@testing-library/react';
import { describe, it, expect, beforeEach } from 'vitest';
import ClinicalWorkspaceStatusBanner from './ClinicalWorkspaceStatusBanner';
import { useAuthStore } from '@/store/auth.store';

describe('ClinicalWorkspaceStatusBanner role gating & diagnostics', () => {
    const mockT = (key, fallback, options) => {
        if (typeof fallback === 'object' && fallback !== null && !options) {
            options = fallback;
            fallback = undefined;
        }
        let res = fallback || key;
        if (options?.count !== undefined && res.includes('{{count}}')) {
            res = res.replace('{{count}}', String(options.count));
        }
        if (options?.value !== undefined && res.includes('{{value}}')) {
            res = res.replace('{{value}}', String(options.value));
        }
        return res;
    };

    const sampleChartWithRealAndInfo = {
        coverage: { teeth: 'COMPLETE', periodontal: 'UNCOVERED' },
        isFallback: true,
        warnings: [
            {
                code: 'FALLBACK_DATA_ACTIVE',
                message: 'Clinical chart is displaying records using legacy fallback.',
            },
            {
                code: 'UNKNOWN_PROCEDURE_CODE',
                message: 'Legacy procedure code 999 unknown',
                raw_value: '999',
            },
        ],
    };

    const chartOnlyFallback = {
        coverage: { teeth: 'COMPLETE', periodontal: 'UNCOVERED' },
        isFallback: true,
        warnings: [
            {
                code: 'FALLBACK_DATA_ACTIVE',
                message: 'Clinical chart is displaying records using legacy fallback.',
            },
        ],
    };

    beforeEach(() => {
        useAuthStore.setState({ user: null });
    });

    it.each(['doctor', 'admin', 'manager'])(
        'non-super_admin role %s with only FALLBACK_DATA_ACTIVE renders nothing',
        (role) => {
            useAuthStore.setState({ user: { id: 10, role } });

            const { container } = render(
                <ClinicalWorkspaceStatusBanner adaptedChart={chartOnlyFallback} t={mockT} />
            );

            expect(container.textContent.trim()).toBe('');
            expect(screen.queryByTestId('clinical-workspace-status')).not.toBeInTheDocument();
            expect(screen.queryByTestId('clinical-workspace-coverage')).not.toBeInTheDocument();
            expect(screen.queryByTestId('clinical-workspace-fallback-banner')).not.toBeInTheDocument();
            expect(screen.queryByTestId('clinical-workspace-warnings')).not.toBeInTheDocument();
            expect(screen.queryByTestId('clinical-workspace-technical-details')).not.toBeInTheDocument();
        }
    );

    it.each(['doctor', 'admin', 'manager'])(
        'non-super_admin role %s with 1 real + 1 informational warning renders one Arabic line with count 1',
        (role) => {
            useAuthStore.setState({ user: { id: 10, role } });

            render(
                <ClinicalWorkspaceStatusBanner adaptedChart={sampleChartWithRealAndInfo} t={mockT} />
            );

            // Shows ONLY the single amber count line with count = 1 (ignoring informational warning)
            expect(screen.getByText(/1 سجلات قديمة تحتاج مراجعة/i)).toBeInTheDocument();

            // Coverage and fallback banner must NOT be visible
            expect(screen.queryByTestId('clinical-workspace-coverage')).not.toBeInTheDocument();
            expect(screen.queryByTestId('clinical-workspace-fallback-banner')).not.toBeInTheDocument();
            expect(screen.queryByTestId('clinical-workspace-status-notes')).not.toBeInTheDocument();
            expect(screen.queryByTestId('clinical-workspace-technical-details')).not.toBeInTheDocument();

            // No raw codes or English backend text in visible UI
            expect(screen.queryByText(/\[FALLBACK_DATA_ACTIVE\]/i)).not.toBeInTheDocument();
            expect(screen.queryByText(/\[UNKNOWN_PROCEDURE_CODE\]/i)).not.toBeInTheDocument();
            expect(screen.queryByText(/Clinical chart is displaying records/i)).not.toBeInTheDocument();
        }
    );

    it('non-super_admin sees nothing when there are zero warnings', () => {
        useAuthStore.setState({ user: { id: 10, role: 'doctor' } });

        const cleanChart = {
            coverage: { teeth: 'COMPLETE' },
            isFallback: false,
            warnings: [],
        };

        const { container } = render(
            <ClinicalWorkspaceStatusBanner adaptedChart={cleanChart} t={mockT} />
        );
        expect(container.textContent.trim()).toBe('');
    });

    it('super_admin sees coverage chips, fallback notice, friendly messages, and details without raw code or English text in visible UI', () => {
        useAuthStore.setState({ user: { id: 1, role: 'super_admin' } });

        const { container } = render(
            <ClinicalWorkspaceStatusBanner adaptedChart={sampleChartWithRealAndInfo} t={mockT} />
        );

        // Super Admin sees coverage chips
        expect(screen.getByTestId('clinical-workspace-coverage')).toBeInTheDocument();

        // Super Admin sees fallback notice
        expect(screen.getByTestId('clinical-workspace-fallback-banner')).toBeInTheDocument();

        // Amber review box count reflects ONLY real warnings (count = 1)
        const warningsBox = screen.getByTestId('clinical-workspace-warnings');
        expect(warningsBox).toBeInTheDocument();
        expect(screen.getByText(/1 سجلات قديمة تحتاج مراجعة/i)).toBeInTheDocument();

        // Informational warning rendered under status notes, NOT under legacy review
        const statusNotes = screen.getByTestId('clinical-workspace-status-notes');
        expect(statusNotes).toBeInTheDocument();
        expect(screen.getByTestId('clinical-status-note-0')).toBeInTheDocument();

        // Technical details element exists and is collapsed
        const details = screen.getByTestId('clinical-workspace-technical-details');
        expect(details).toBeInTheDocument();
        expect(details).not.toHaveAttribute('open');

        // Raw codes exist as data-code attributes on <li> elements, NOT in visible text
        const codeItemFallback = container.querySelector('[data-code="FALLBACK_DATA_ACTIVE"]');
        expect(codeItemFallback).toBeInTheDocument();
        const codeItemProcedure = container.querySelector('[data-code="UNKNOWN_PROCEDURE_CODE"]');
        expect(codeItemProcedure).toBeInTheDocument();

        // Visible text MUST NOT contain raw bracketed codes or English backend messages
        expect(container.textContent).not.toContain('[FALLBACK_DATA_ACTIVE]');
        expect(container.textContent).not.toContain('[UNKNOWN_PROCEDURE_CODE]');
        expect(container.textContent).not.toContain('Clinical chart is displaying records using legacy fallback.');
        expect(container.textContent).not.toContain('Legacy procedure code 999 unknown');
    });

    it('super_admin with only FALLBACK_DATA_ACTIVE sees coverage, fallback banner, status notes, and technical details without amber box', () => {
        useAuthStore.setState({ user: { id: 1, role: 'super_admin' } });

        const { container } = render(
            <ClinicalWorkspaceStatusBanner adaptedChart={chartOnlyFallback} t={mockT} />
        );

        expect(screen.getByTestId('clinical-workspace-coverage')).toBeInTheDocument();
        expect(screen.getByTestId('clinical-workspace-fallback-banner')).toBeInTheDocument();
        expect(screen.getByTestId('clinical-workspace-status-notes')).toBeInTheDocument();

        // Amber review box MUST NOT be rendered since there are zero real warnings
        expect(screen.queryByTestId('clinical-workspace-warnings')).not.toBeInTheDocument();
        expect(screen.queryByText(/سجلات قديمة تحتاج مراجعة/i)).not.toBeInTheDocument();

        // Details exists with data-code
        const details = screen.getByTestId('clinical-workspace-technical-details');
        expect(details).toBeInTheDocument();
        expect(container.querySelector('[data-code="FALLBACK_DATA_ACTIVE"]')).toBeInTheDocument();

        // No raw code or English text in visible text
        expect(container.textContent).not.toContain('[FALLBACK_DATA_ACTIVE]');
        expect(container.textContent).not.toContain('Clinical chart is displaying records using legacy fallback.');
    });
});
