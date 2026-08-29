import { memo, useMemo } from 'react';
import DentalChartSVG from '@/features/dental/DentalChartSVG';
import { createClinicalChartRendererAdapter } from '../rendering/ClinicalChartRendererAdapter';

/**
 * Stateless rendering boundary for the clinical chart. Persistence and domain
 * workflows stay with the parent that supplies the renderer input contract.
 */
export default memo(function ClinicalChartRenderer({ input }) {
    const adapter = useMemo(() => createClinicalChartRendererAdapter(input), [input]);

    return <DentalChartSVG {...adapter.chartProps} />;
});
