import { PROJECTION_VISUAL_PHASES } from '../domain/clinicalChartProjection';

export const getBaseAnatomyOpacity = (toothVisual) => {
    const opacityValues = toothVisual?.instructions
        ?.map((instruction) => instruction.presentation.baseOpacity)
        .filter((opacity) => typeof opacity === 'number') ?? [];
    return opacityValues.length > 0 ? Math.min(...opacityValues) : 1;
};

export const shouldHideNaturalRoots = (toothVisual) => toothVisual?.instructions?.some((instruction) => (
    instruction.effect === 'implant-fixture'
    && [PROJECTION_VISUAL_PHASES.EXISTING, PROJECTION_VISUAL_PHASES.COMPLETED].includes(instruction.phase)
)) ?? false;
