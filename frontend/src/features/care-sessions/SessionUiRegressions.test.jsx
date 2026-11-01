import { it, expect, vi } from 'vitest';
import { render, screen, fireEvent, within } from '@testing-library/react';
import { createInstance } from 'i18next';
import { I18nextProvider, initReactI18next } from 'react-i18next';
import HistoricalCareSessionModal from './HistoricalCareSessionModal';
import ClinicalChartInspector from '@/features/clinical-chart/components/ClinicalChartInspector';
import ar from '@/locales/ar/translation.json';

it('uses Arabic labels, prefills the selected tooth, and explains an empty measurement add', async () => {
    const i18n = createInstance();
    await i18n.use(initReactI18next).init({ lng: 'ar', resources: { ar: { translation: ar } }, interpolation: { escapeValue: false } });
    render(<I18nextProvider i18n={i18n}><HistoricalCareSessionModal isOpen onClose={vi.fn()} patientId={1} patientWorkItems={[{ id: 10, code: 'ENDO_RCT', targets: [{ tooth_key: '46' }] }, { id: 20, code: 'ENDO_RCT', tooth_number: '36' }]} /></I18nextProvider>);
    expect(screen.getByText('تسجيل زيارة سابقة')).toBeInTheDocument();
    expect(screen.getByTestId('input-historical-obs-tooth')).toHaveValue('46');
    fireEvent.click(screen.getByTestId('canal-chip-MB'));
    expect(screen.getByText(ar.care_session.maf_taper)).toBeInTheDocument();
    expect(within(screen.getByTestId('canal-target-selector')).getByText(ar.care_session.roots.mesial, { selector: 'span' })).toBeInTheDocument();
    expect(within(screen.getByTestId('select-ref-MB')).getByRole('option', { name: ar.care_session.reference_points.mb_cusp })).toHaveValue('MB cusp');
    fireEvent.change(screen.getByTestId('select-historical-obs-code'), { target: { value: 'measurement' } });
    fireEvent.click(screen.getByTestId('btn-add-historical-obs'));
    expect(screen.getByText(ar.care_session.observation_value_required)).toBeInTheDocument();
    fireEvent.click(screen.getByTestId('checkbox-proc-20').querySelector('input'));
    fireEvent.change(screen.getByTestId('historical-entry-procedure'), { target: { value: '20' } });
    expect(screen.getByTestId('input-historical-obs-tooth')).toHaveValue('36');
    fireEvent.change(screen.getByTestId('select-historical-obs-code'), { target: { value: 'measurement' } });
    fireEvent.change(screen.getByTestId('input-historical-obs-value'), { target: { value: 'A2' } });
    fireEvent.click(screen.getByTestId('btn-add-historical-obs'));
    expect(screen.getByTestId('historical-obs-item-0')).toHaveTextContent('A2');
});

it('renders one procedure across native, linked legacy and visual representations', () => {
    render(<ClinicalChartInspector copy={{}} title="Tooth" selection={{ toothKey: '46' }} workItems={[{ id: 10, kind: 'procedure', code: 'ENDO_RCT', status: 'planned', targets: [{ tooth_key: '46' }] }]} treatments={[{ id: 50, work_item_id: 10, tooth_number: '46', procedure: 'RCT' }]} toothState={{ procedures: [{ visualId: 've-wi-10', code: 'ENDO_RCT' }, { visualId: 've-legacy-wi-50', code: 'ENDO_RCT' }] }} />);
    expect(within(screen.getByTestId('inspector-items-list')).getAllByRole('listitem')).toHaveLength(1);
});

it('preserves independent procedures even if a legacy row ID equals a native ID', () => {
    render(<ClinicalChartInspector copy={{}} title="Tooth" selection={{ toothKey: '46' }} workItems={[{ id: 10, kind: 'procedure', code: 'ENDO_RCT', status: 'planned', targets: [{ tooth_key: '46' }] }]} treatments={[{ id: 10, tooth_number: '46', procedure: 'RCT' }]} toothState={{ procedures: [] }} />);
    expect(within(screen.getByTestId('inspector-items-list')).getAllByRole('listitem')).toHaveLength(2);
});
