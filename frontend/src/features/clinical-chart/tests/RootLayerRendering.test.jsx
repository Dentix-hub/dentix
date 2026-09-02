import { render } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import DentalChartSVG from '@/features/dental/DentalChartSVG';
import ClinicalChartWorkspace from '../ClinicalChartWorkspace';

describe('Phase A10 — Root Layer Rendering', () => {
    describe('A10-M01: Add root layer renderer', () => {
        it('renders roots as a dedicated background layer under the crown for all 32 permanent teeth', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            const rootLayers = container.querySelectorAll('svg[data-layer="roots"]');
            const crownLayers = container.querySelectorAll('svg[data-layer="crown"]');

            expect(rootLayers).toHaveLength(32);
            expect(crownLayers).toHaveLength(32);

            rootLayers.forEach((rootSvg) => {
                expect(rootSvg).toHaveAttribute('viewBox', '0 0 50 48');
                expect(rootSvg).toHaveAttribute('width', '50');
                expect(rootSvg).toHaveAttribute('height', '48');
                expect(rootSvg.className.baseVal).toContain('pointer-events-none');
                expect(rootSvg.className.baseVal).toContain('absolute');
            });
        });

        it('mounts the root layer seamlessly inside the ClinicalChartWorkspace', () => {
            const { container } = render(<ClinicalChartWorkspace />);
            const rootLayers = container.querySelectorAll('svg[data-layer="roots"]');

            expect(rootLayers).toHaveLength(32);
            rootLayers.forEach((rootSvg) => {
                expect(rootSvg.querySelector('[data-layer-role="base-anatomy"]')).toBeInTheDocument();
            });
        });
    });

    describe('A10-M02: Handle single-root teeth (incisors and canines)', () => {
        const permanentSingleRootTeeth = [
            '11', '12', '13', '21', '22', '23', // Maxillary
            '31', '32', '33', '41', '42', '43', // Mandibular
        ];

        it.each(permanentSingleRootTeeth)('renders exactly 1 root for FDI %s', (toothKey) => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);

            expect(rootSvg).toBeInTheDocument();
            expect(rootSvg).toHaveAttribute('data-root-count', '1');
            expect(rootSvg.querySelectorAll('[data-layer-role="base-anatomy"] path')).toHaveLength(1);
        });

        it('orients maxillary single roots apically upward and mandibular roots downward', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            const upperRoot = container.querySelector('svg[data-layer="roots"][data-tooth-key="11"] [data-root-orientation]');
            const lowerRoot = container.querySelector('svg[data-layer="roots"][data-tooth-key="41"] [data-root-orientation]');

            expect(upperRoot).toHaveAttribute('transform', 'rotate(180 25 24)');
            expect(lowerRoot).not.toHaveAttribute('transform');
        });
    });

    describe('A10-M03: Handle premolars', () => {
        it('renders canonical 2 roots (buccal & palatal) for maxillary first premolars (14, 24)', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            ['14', '24'].forEach((toothKey) => {
                const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);
                expect(rootSvg).toHaveAttribute('data-root-count', '2');
                expect(rootSvg.querySelectorAll('[data-layer-role="base-anatomy"] path')).toHaveLength(2);
            });
        });

        it('renders 1 root for maxillary second premolars (15, 25)', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            ['15', '25'].forEach((toothKey) => {
                const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);
                expect(rootSvg).toHaveAttribute('data-root-count', '1');
                expect(rootSvg.querySelectorAll('[data-layer-role="base-anatomy"] path')).toHaveLength(1);
            });
        });

        it('renders 1 root for all mandibular premolars (34, 35, 44, 45)', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            ['34', '35', '44', '45'].forEach((toothKey) => {
                const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);
                expect(rootSvg).toHaveAttribute('data-root-count', '1');
                expect(rootSvg.querySelectorAll('[data-layer-role="base-anatomy"] path')).toHaveLength(1);
            });
        });
    });

    describe('A10-M04: Handle molars', () => {
        it('renders 3 roots (MB, DB, Palatal) for all permanent maxillary molars (16-18, 26-28)', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            ['16', '17', '18', '26', '27', '28'].forEach((toothKey) => {
                const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);
                expect(rootSvg).toHaveAttribute('data-root-count', '3');
                expect(rootSvg.querySelectorAll('[data-layer-role="base-anatomy"] path')).toHaveLength(3);
            });
        });

        it('renders 2 roots (Mesial, Distal) for all permanent mandibular molars (36-38, 46-48)', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            ['36', '37', '38', '46', '47', '48'].forEach((toothKey) => {
                const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);
                expect(rootSvg).toHaveAttribute('data-root-count', '2');
                expect(rootSvg.querySelectorAll('[data-layer-role="base-anatomy"] path')).toHaveLength(2);
            });
        });
    });

    describe('A10-M05: Handle primary teeth', () => {
        it('renders the complete 20 primary root set with correct anatomy', () => {
            const { container } = render(
                <DentalChartSVG isPediatric showRoots teethStatus={{}} />,
            );
            const rootLayers = container.querySelectorAll('svg[data-layer="roots"]');

            expect(rootLayers).toHaveLength(20);

            // Primary incisors and canines (51-53, 61-63, 71-73, 81-83) have 1 root
            ['51', '52', '53', '61', '62', '63', '71', '72', '73', '81', '82', '83'].forEach((toothKey) => {
                const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);
                expect(rootSvg).toHaveAttribute('data-root-count', '1');
            });

            // Primary maxillary molars (54, 55, 64, 65) have 3 divergent roots
            ['54', '55', '64', '65'].forEach((toothKey) => {
                const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);
                expect(rootSvg).toHaveAttribute('data-root-count', '3');
            });

            // Primary mandibular molars (74, 75, 84, 85) have 2 divergent roots
            ['74', '75', '84', '85'].forEach((toothKey) => {
                const rootSvg = container.querySelector(`svg[data-layer="roots"][data-tooth-key="${toothKey}"]`);
                expect(rootSvg).toHaveAttribute('data-root-count', '2');
            });
        });
    });

    describe('A10-M06: Prevent root overlap artifacts', () => {
        it('ensures all root paths are non-empty and bounded within the SVG viewBox', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            const rootPaths = container.querySelectorAll('svg[data-layer="roots"] [data-layer-role="base-anatomy"] path');

            rootPaths.forEach((path) => {
                const d = path.getAttribute('d');
                expect(d).toBeTruthy();
                expect(d).toMatch(/^M\d+/);
                expect(d).toMatch(/Z$/);
                expect(d).not.toContain('NaN');
                expect(d).not.toContain('undefined');
            });
        });

        it('renders roots behind crowns so crowns smoothly mask the cervical root boundaries', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            const toothSpans = container.querySelectorAll('span.relative.block');

            toothSpans.forEach((span) => {
                const children = Array.from(span.children);
                const rootIndex = children.findIndex((el) => el.getAttribute('data-layer') === 'roots');
                const crownIndex = children.findIndex((el) => el.getAttribute('data-layer') === 'crown');

                expect(rootIndex).toBe(0);
                expect(crownIndex).toBe(1);
                expect(rootIndex).toBeLessThan(crownIndex);
            });
        });

        it('keeps root layers non-interactive (pointer-events-none) so clicks pass through cleanly', () => {
            const { container } = render(
                <DentalChartSVG isPediatric={false} showRoots teethStatus={{}} />,
            );
            const rootLayers = container.querySelectorAll('svg[data-layer="roots"]');

            rootLayers.forEach((rootSvg) => {
                expect(rootSvg.classList.contains('pointer-events-none')).toBe(true);
            });
        });
    });
});
