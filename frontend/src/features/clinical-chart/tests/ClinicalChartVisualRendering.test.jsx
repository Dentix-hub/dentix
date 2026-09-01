import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalChartWorkspace from '../ClinicalChartWorkspace';

const toothCrown = (container, toothKey) => (
    container.querySelector(`svg[data-layer="crown"][data-tooth-key="${toothKey}"]`)
);

const toothRoots = (container, toothKey) => (
    container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`)
);

describe('clinical chart visual rule rendering', () => {
    it('renders caries on the targeted crown surface and never on the root layer', () => {
        const { container } = render(<ClinicalChartWorkspace />);
        const crown = toothCrown(container, '46');
        const roots = toothRoots(container, '46');
        const caries = crown.querySelector('[data-effect="surface-caries"][data-target-surface="D"] path');

        expect(caries).toHaveAttribute('fill', '#b91c1c');
        expect(caries).toHaveAttribute('fill-opacity', '0.86');
        expect(roots.querySelector('[data-effect="surface-caries"]')).not.toBeInTheDocument();
    });

    it('renders completed composite restorations as prominent blue surface overlays', () => {
        const { container } = render(<ClinicalChartWorkspace />);
        const restorations = toothCrown(container, '44')
            .querySelectorAll('[data-effect="surface-restoration"]');

        expect(restorations).toHaveLength(3);
        expect(Array.from(restorations).map((restoration) => (
            restoration.querySelector('path').getAttribute('fill')
        ))).toEqual(['#2563eb', '#2563eb', '#2563eb']);
        expect(Array.from(restorations).map((restoration) => (
            restoration.getAttribute('data-target-surface')
        )).sort()).toEqual(['D', 'M', 'O']);
    });

    it('renders endodontic therapy inside the matching root and chamber', () => {
        const { container } = render(<ClinicalChartWorkspace />);
        const rootEffect = toothRoots(container, '11')
            .querySelector('[data-effect="endodontic-therapy"][data-target-root="single"] path');
        const crownEffect = toothCrown(container, '11')
            .querySelector('[data-effect="endodontic-therapy"] path');

        expect(rootEffect).toHaveAttribute('stroke', '#7c3aed');
        expect(rootEffect).toHaveAttribute('stroke-dasharray', '2.5 1.5');
        expect(crownEffect).toHaveAttribute('fill', '#ede9fe');
    });

    it('replaces natural roots with the implant fixture while retaining a distinct implant crown', () => {
        const { container } = render(<ClinicalChartWorkspace />);
        const roots = toothRoots(container, '23');
        const crown = toothCrown(container, '23');

        expect(roots.querySelector('[data-layer-role="base-anatomy"]')).toHaveAttribute('opacity', '0');
        expect(roots.querySelector('[data-effect="implant-fixture"] path')).toHaveAttribute('stroke', '#0f766e');
        expect(crown.querySelector('[data-effect="implant-crown"] path')).toHaveAttribute('fill', '#99f6e4');
    });

    it('distinguishes planned and completed extraction semantics', () => {
        const { container } = render(<ClinicalChartWorkspace />);
        const planned = toothCrown(container, '24').querySelector('[data-effect="surgical-extraction"] path');
        const completed = toothCrown(container, '25').querySelector('[data-effect="surgical-extraction"] path');

        expect(planned).toHaveAttribute('stroke', '#dc2626');
        expect(planned).toHaveAttribute('stroke-dasharray', '4 2');
        expect(completed).toHaveAttribute('stroke', '#64748b');
        expect(completed).not.toHaveAttribute('stroke-dasharray');
    });

    it('keeps read-only visual layer DOM order deterministic without selection controls', () => {
        const { container } = render(<ClinicalChartWorkspace />);
        const layerIndexes = Array.from(toothCrown(container, '44').querySelectorAll('[data-layer-index]'))
            .map((node) => Number(node.getAttribute('data-layer-index')));

        expect(layerIndexes).toEqual([...layerIndexes].sort((left, right) => left - right));
        expect(layerIndexes[0]).toBe(0);
        expect(layerIndexes.at(-1)).toBe(3);
    });
});
