import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import ChartQuickActionLauncher from '../components/ChartQuickActionLauncher';
import ProceduresSettings from '@/features/settings/SettingsTabs/ProceduresSettings';
import { MiniToothPreview } from '@/features/settings/SettingsTabs/ProcedureChartAppearanceControl';
import {
    CHART_APPEARANCE_TEMPLATES,
    NEW_PROCEDURE_DEFAULT_CHART_STYLE,
    resolveEffectiveProcedureChartBehavior,
    suggestProcedureChartTemplate,
} from '../domain/procedureChartAppearance';
import * as api from '@/api';
import * as proceduresApi from '@/api/procedures';
import { useProcedures } from '@/shared/context/ProceduresContext';
import { useAuthStore } from '@/store/auth.store';

vi.mock('react-i18next', () => ({
    useTranslation: () => ({
        t: (key, fallback, options) => {
            if (options && options.count !== undefined && typeof fallback === 'string') {
                return fallback.replace('{{count}}', options.count);
            }
            return typeof fallback === 'string' ? fallback : key;
        },
        i18n: { language: 'ar' },
    }),
}));

vi.mock('@/shared/context/ProceduresContext', () => ({
    useProcedures: vi.fn(),
}));

vi.mock('@/api/procedures', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        getProcedureChartStyles: vi.fn(),
        upsertProcedureChartStyle: vi.fn(),
        deleteProcedureChartStyle: vi.fn(),
    };
});

vi.mock('@/api', async (importOriginal) => {
    const actual = await importOriginal();
    return {
        ...actual,
        createProcedure: vi.fn(),
        updateProcedure: vi.fn(),
        deleteProcedure: vi.fn(),
    };
});

describe('U4C: Domain — Template Options, Ordered Suggestions & Effective Launcher Behavior', () => {
    it('1. exposes the exact 9 chart appearance templates from Architecture A2 (excluding PROS_DENTURE)', () => {
        const templateKeys = CHART_APPEARANCE_TEMPLATES.map((t) => t.template);
        expect(templateKeys).toEqual([
            'REST_COMPOSITE',
            'ENDO_RCT',
            'PROS_CROWN',
            'PROS_BRIDGE',
            'IMPLANT_FIXTURE',
            'IMPLANT_CROWN',
            'SURG_EXTRACTION',
            'MARKER',
            'NONE',
        ]);
        expect(templateKeys).not.toContain('PROS_DENTURE');
        expect(NEW_PROCEDURE_DEFAULT_CHART_STYLE).toEqual({
            template: 'MARKER',
            color_key: null,
        });
    });

    it('2. suggests templates in strict specificity order so "حشو عصب" suggests ENDO_RCT before REST_COMPOSITE', () => {
        expect(suggestProcedureChartTemplate('حشو عصب')?.template).toBe('ENDO_RCT');
        expect(suggestProcedureChartTemplate('علاج قناة الجذر')?.template).toBe('ENDO_RCT');
        expect(suggestProcedureChartTemplate('Root Canal Retreatment')?.template).toBe('ENDO_RCT');

        expect(suggestProcedureChartTemplate('حشو كومبوزيت ضوئي')?.template).toBe('REST_COMPOSITE');
        expect(suggestProcedureChartTemplate('Composite Filling')?.template).toBe('REST_COMPOSITE');

        expect(suggestProcedureChartTemplate('تاج زرعة زيركون')?.template).toBe('IMPLANT_CROWN');
        expect(suggestProcedureChartTemplate('Implant Crown')?.template).toBe('IMPLANT_CROWN');

        expect(suggestProcedureChartTemplate('كراون زيركون')?.template).toBe('PROS_CROWN');
        expect(suggestProcedureChartTemplate('طربوش بورسلين')?.template).toBe('PROS_CROWN');

        expect(suggestProcedureChartTemplate('جسر خزفي')?.template).toBe('PROS_BRIDGE');
        expect(suggestProcedureChartTemplate('زرعة سويسرية')?.template).toBe('IMPLANT_FIXTURE');
        expect(suggestProcedureChartTemplate('خلع جراحي')?.template).toBe('SURG_EXTRACTION');

        // Already configured or allowlisted procedures do not get a suggestion
        expect(
            suggestProcedureChartTemplate({
                id: 1,
                name: 'حشو عصب',
                canonical_code: 'ENDO_RCT',
                chart_style: null,
            }),
        ).toBeNull();
        expect(
            suggestProcedureChartTemplate({
                id: 2,
                name: 'حشو عصب خاص',
                canonical_code: null,
                chart_style: { template: 'ENDO_RCT', color_key: 'red' },
            }),
        ).toBeNull();
    });

    it('3. computes effective launcher behavior from chart_style.template ?? allowlist canonical_code', () => {
        // Custom procedure with PROS_CROWN style -> requires_lab: true, prosthodontic category, no billing-only tag
        const customCrown = resolveEffectiveProcedureChartBehavior({
            id: 10,
            name: 'تاج إيماكس خاص',
            canonical_code: null,
            chart_style: { template: 'PROS_CROWN', color_key: 'amber' },
        });
        expect(customCrown.effectiveTemplate).toBe('PROS_CROWN');
        expect(customCrown.requires_lab).toBe(true);
        expect(customCrown.allowed_target_kinds).toEqual(['tooth']);
        expect(customCrown.category).toBe('prosthodontic');
        expect(customCrown.showBillingOnlyTag).toBe(false);
        expect(customCrown.hasChartMapping).toBe(true);
        expect(customCrown.paletteSwatch?.key).toBe('amber');

        // Custom procedure with MARKER style -> tooth + surface targets, default teal swatch, no billing-only tag
        const markerProc = resolveEffectiveProcedureChartBehavior({
            id: 11,
            name: 'تطبيق فلورايد موضعي',
            canonical_code: null,
            chart_style: { template: 'MARKER', color_key: null },
        });
        expect(markerProc.effectiveTemplate).toBe('MARKER');
        expect(markerProc.allowed_target_kinds).toEqual(['tooth', 'surface']);
        expect(markerProc.requires_lab).toBe(false);
        expect(markerProc.showBillingOnlyTag).toBe(false);
        expect(markerProc.paletteSwatch?.key).toBe('teal');

        // Custom procedure with NONE style and no allowlist code -> billing-only tag shown
        const billingOnlyProc = resolveEffectiveProcedureChartBehavior({
            id: 12,
            name: 'استشارة عامة',
            canonical_code: null,
            chart_style: { template: 'NONE', color_key: null },
        });
        expect(billingOnlyProc.effectiveTemplate).toBe('NONE');
        expect(billingOnlyProc.showBillingOnlyTag).toBe(true);
        expect(billingOnlyProc.hasChartMapping).toBe(false);
        expect(billingOnlyProc.paletteSwatch).toBeNull();
    });
});

describe('U4C: MiniToothPreview — Visual Template & Palette Preview', () => {
    it.each([
        ['REST_COMPOSITE', 'blue', 'surface'],
        ['ENDO_RCT', 'orange', 'root'],
        ['PROS_CROWN', 'amber', 'crown'],
        ['PROS_BRIDGE', 'purple', 'bridge'],
        ['IMPLANT_FIXTURE', 'teal', 'implant-fixture'],
        ['IMPLANT_CROWN', 'green', 'implant-crown'],
        ['SURG_EXTRACTION', 'slate', 'extraction'],
        ['MARKER', 'pink', 'marker'],
        ['NONE', null, 'none'],
    ])('renders MiniToothPreview for template=%s, colorKey=%s -> glyph=%s', (template, colorKey, expectedGlyph) => {
        const { unmount } = render(
            <MiniToothPreview
                template={template}
                colorKey={colorKey}
                testId={`preview-${template}`}
            />,
        );
        const preview = screen.getByTestId(`preview-${template}`);
        expect(preview).toHaveAttribute('data-preview-template', template);
        expect(preview).toHaveAttribute('data-preview-color-key', colorKey || 'default');
        expect(preview).toHaveAttribute('data-preview-glyph', expectedGlyph);
        unmount();
    });
});

describe('U4C: ProceduresSettings — Global & Tenant Rows, Suggestions, Save/Clear & Create Default', () => {
    const mockRefreshProcedures = vi.fn();
    const mockSetMessage = vi.fn();

    const sampleProcedures = [
        {
            id: 101,
            name: 'حشو عصب – Root Canal Treatment',
            price: 1500,
            tenant_id: null, // Global template (read-only name/price, editable chart style)
            canonical_code: 'ENDO_RCT',
            chart_style: null,
        },
        {
            id: 102,
            name: 'حشو عصب ميكروسكوبي',
            price: 2200,
            tenant_id: 5, // Tenant row without style or canonical_code -> should show ENDO_RCT suggestion
            canonical_code: null,
            chart_style: null,
        },
        {
            id: 103,
            name: 'جلسة ليزر للثة',
            price: 900,
            tenant_id: 5,
            canonical_code: null,
            chart_style: { template: 'MARKER', color_key: 'purple' },
        },
    ];

    beforeEach(() => {
        vi.clearAllMocks();
        useProcedures.mockReturnValue({
            procedures: sampleProcedures,
            loading: false,
            refresh: mockRefreshProcedures,
        });
        proceduresApi.getProcedureChartStyles.mockResolvedValue({
            data: [
                {
                    id: 77,
                    procedure_name: 'جلسة ليزر للثة',
                    template: 'MARKER',
                    color_key: 'purple',
                },
            ],
        });
        proceduresApi.upsertProcedureChartStyle.mockImplementation(async (payload) => ({
            data: { id: 88, ...payload },
        }));
        proceduresApi.deleteProcedureChartStyle.mockResolvedValue({ data: { ok: true } });
        api.createProcedure.mockImplementation(async (payload) => ({
            data: { id: 200, ...payload },
        }));
    });

    it('1. renders chart appearance control for BOTH global (tenant_id=null) and tenant rows while keeping global name/price read-only', async () => {
        const queryClient = new QueryClient();
        render(
            <QueryClientProvider client={queryClient}>
                <ProceduresSettings setMessage={mockSetMessage} />
            </QueryClientProvider>,
        );

        // Global row (101) has read-only badge and disabled edit/delete buttons
        expect(screen.getByTestId('global-procedure-badge-101')).toBeInTheDocument();
        expect(screen.getByTestId('edit-procedure-101')).toBeDisabled();
        expect(screen.getByTestId('delete-procedure-101')).toBeDisabled();

        // Yet its chart appearance control is interactive!
        const globalSelect = screen.getByTestId('chart-style-template-select-101');
        expect(globalSelect).not.toBeDisabled();
        expect(globalSelect).toHaveValue('ENDO_RCT');

        // Select a custom color on the global procedure row and save
        fireEvent.click(screen.getByTestId('chart-style-color-101-orange'));
        expect(screen.getByTestId('chart-style-mini-preview-101')).toHaveAttribute(
            'data-preview-color-key',
            'orange',
        );

        fireEvent.click(screen.getByTestId('save-chart-style-101'));

        await waitFor(() => {
            expect(proceduresApi.upsertProcedureChartStyle).toHaveBeenCalledWith({
                procedure_name: 'حشو عصب – Root Canal Treatment',
                template: 'ENDO_RCT',
                color_key: 'orange',
            });
        });
        expect(mockRefreshProcedures).toHaveBeenCalled();
    });

    it('2. shows suggestion chip without auto-applying on render, and applies + saves when clicked', async () => {
        const queryClient = new QueryClient();
        render(
            <QueryClientProvider client={queryClient}>
                <ProceduresSettings setMessage={mockSetMessage} />
            </QueryClientProvider>,
        );

        // Row 102 ("حشو عصب ميكروسكوبي") has no saved style and no canonical_code:
        // Select starts empty (NOT auto-applied!)
        const row102Select = screen.getByTestId('chart-style-template-select-102');
        expect(row102Select).toHaveValue('');

        // Suggestion chip is shown with ENDO_RCT (not REST_COMPOSITE)
        const suggestionChip = screen.getByTestId('chart-style-suggestion-102');
        expect(suggestionChip).toHaveTextContent(/علاج عصب/);

        // Clicking "Apply" updates the row draft template to ENDO_RCT
        fireEvent.click(screen.getByTestId('apply-chart-style-suggestion-102'));
        expect(row102Select).toHaveValue('ENDO_RCT');
        expect(screen.getByTestId('chart-style-mini-preview-102')).toHaveAttribute(
            'data-preview-template',
            'ENDO_RCT',
        );

        // Save persists via upsertProcedureChartStyle
        fireEvent.click(screen.getByTestId('save-chart-style-102'));
        await waitFor(() => {
            expect(proceduresApi.upsertProcedureChartStyle).toHaveBeenCalledWith({
                procedure_name: 'حشو عصب ميكروسكوبي',
                template: 'ENDO_RCT',
                color_key: null,
            });
        });
    });

    it('3. supports clearing/resetting a saved chart style and invalidating clinical queries', async () => {
        const queryClient = new QueryClient();
        const invalidateSpy = vi.spyOn(queryClient, 'invalidateQueries');

        render(
            <QueryClientProvider client={queryClient}>
                <ProceduresSettings setMessage={mockSetMessage} />
            </QueryClientProvider>,
        );

        await waitFor(() => {
            expect(proceduresApi.getProcedureChartStyles).toHaveBeenCalled();
        });

        // Row 103 has a saved style (id: 77, template: MARKER, color_key: purple)
        expect(screen.getByTestId('chart-style-mini-preview-103')).toHaveAttribute(
            'data-preview-template',
            'MARKER',
        );
        expect(screen.getByTestId('chart-style-mini-preview-103')).toHaveAttribute(
            'data-preview-color-key',
            'purple',
        );

        fireEvent.click(screen.getByTestId('clear-chart-style-103'));

        await waitFor(() => {
            expect(proceduresApi.deleteProcedureChartStyle).toHaveBeenCalledWith(77);
        });
        expect(mockRefreshProcedures).toHaveBeenCalled();
        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['procedure-chart-styles'] });
        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['procedures'] });
        expect(invalidateSpy).toHaveBeenCalledWith({ queryKey: ['patientPlanOverlay'] });
    });

    it('4. defaults new procedure modal to MARKER + null color with hint, and saves chart style on create', async () => {
        const queryClient = new QueryClient();
        render(
            <QueryClientProvider client={queryClient}>
                <ProceduresSettings setMessage={mockSetMessage} />
            </QueryClientProvider>,
        );

        // Open "إضافة" modal
        fireEvent.click(screen.getByRole('button', { name: /إضافة/i }));

        // Verify default hint and default MARKER + null color
        expect(screen.getByTestId('chart-style-default-hint-modal-new')).toBeInTheDocument();
        expect(screen.getByTestId('chart-style-template-select-modal-new')).toHaveValue('MARKER');
        expect(screen.getByTestId('chart-style-mini-preview-modal-new')).toHaveAttribute(
            'data-preview-template',
            'MARKER',
        );
        expect(screen.getByTestId('chart-style-mini-preview-modal-new')).toHaveAttribute(
            'data-preview-color-key',
            'default',
        );

        // Fill in new procedure name & price and submit without touching the appearance control
        fireEvent.change(screen.getByTestId('procedure-modal-name-input'), {
            target: { value: 'جلسة تلميع خاصة' },
        });
        fireEvent.change(screen.getByTestId('procedure-modal-price-input'), {
            target: { value: '450' },
        });

        fireEvent.click(screen.getByTestId('procedure-modal-submit-button'));

        await waitFor(() => {
            expect(api.createProcedure).toHaveBeenCalledWith({
                name: 'جلسة تلميع خاصة',
                price: 450,
            });
            expect(proceduresApi.upsertProcedureChartStyle).toHaveBeenCalledWith({
                procedure_name: 'جلسة تلميع خاصة',
                template: 'MARKER',
                color_key: null,
            });
        });
    });
});

describe('U4C: ChartQuickActionLauncher — Effective Chart Style & Swatch Integration', () => {
    beforeEach(() => {
        localStorage.clear();
        useAuthStore.setState({ user: { id: 42, tenant_id: 101, role: 'doctor' } });
    });

    it('uses chart_style.template for surface prompt, lab requirement, billing-only suppression, and renders palette swatch on cards', () => {
        const onAction = vi.fn();
        const styledProcedures = [
            {
                id: 50,
                name: 'حشوة تجميلية خاصة',
                canonical_code: null,
                price: 750,
                chart_style: { template: 'REST_COMPOSITE', color_key: 'green' },
            },
            {
                id: 51,
                name: 'علامة متابعة خاصة',
                canonical_code: null,
                price: 250,
                chart_style: { template: 'MARKER', color_key: 'pink' },
            },
            {
                id: 52,
                name: 'رسوم فتح ملف',
                canonical_code: null,
                price: 100,
                chart_style: { template: 'NONE', color_key: null },
            },
        ];

        render(
            <ChartQuickActionLauncher
                selectedTeeth={['16']}
                selectedSurfacesByTooth={{}}
                onAction={onAction}
                clinicProcedures={styledProcedures}
            />,
        );

        // 1. Custom REST_COMPOSITE procedure (id: 50):
        // - No billing-only tag even though canonical_code is null
        // - Renders green swatch
        // - Clicking it with tooth 16 selected opens surface prompt (because effective template is REST_COMPOSITE)
        expect(screen.queryByTestId('billing-only-tag-proc:50')).not.toBeInTheDocument();
        const swatch50 = screen.getByTestId('procedure-color-swatch-proc:50');
        expect(swatch50).toHaveAttribute('data-color-key', 'green');

        fireEvent.click(screen.getByTestId('chart-quick-action-item-proc:50'));
        expect(screen.getByTestId('surface-prompt-popover')).toBeInTheDocument();
        fireEvent.click(screen.getByTestId('confirm-action-button'));
        expect(onAction).toHaveBeenCalledWith(
            expect.objectContaining({
                item: expect.objectContaining({
                    key: 'proc:50',
                    effectiveTemplate: 'REST_COMPOSITE',
                    allowed_target_kinds: ['surface'],
                }),
                targetKind: 'surface',
                surfaces: ['O'],
            }),
        );

        // 2. MARKER procedure (id: 51):
        // - No billing-only tag
        // - Renders pink swatch
        // - Clicking it with tooth 16 selected (no preselected surfaces) applies immediately to whole tooth without forcing surface prompt
        expect(screen.queryByTestId('billing-only-tag-proc:51')).not.toBeInTheDocument();
        expect(screen.getByTestId('procedure-color-swatch-proc:51')).toHaveAttribute(
            'data-color-key',
            'pink',
        );

        onAction.mockClear();
        fireEvent.click(screen.getByTestId('chart-quick-action-item-proc:51'));
        expect(onAction).toHaveBeenCalledWith(
            expect.objectContaining({
                item: expect.objectContaining({
                    key: 'proc:51',
                    effectiveTemplate: 'MARKER',
                    allowed_target_kinds: ['tooth', 'surface'],
                }),
                targetKind: 'tooth',
                surfaces: [],
            }),
        );

        // 3. NONE procedure (id: 52) with canonical_code=null:
        // - Shows billing-only tag and no color swatch
        expect(screen.getByTestId('billing-only-tag-proc:52')).toBeInTheDocument();
        expect(screen.queryByTestId('procedure-color-swatch-proc:52')).not.toBeInTheDocument();
    });
});
