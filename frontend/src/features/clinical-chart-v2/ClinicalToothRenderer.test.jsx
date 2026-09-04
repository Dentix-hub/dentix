import { render, screen } from '@testing-library/react';
import { describe, expect, it } from 'vitest';
import ClinicalToothRenderer, { ClinicalBridgeRenderer } from './ClinicalToothRenderer';
import { CLINICAL_TOOTH_GEOMETRY, getClinicalToothGeometry } from './toothGeometry';
import {
    parseFdiTooth,
    PROCEDURE_LIFECYCLE,
    PROCEDURE_TYPE,
} from './toothTypes';

const procedure = (type, surfaces = [], lifecycle = PROCEDURE_LIFECYCLE.COMPLETED) => ({
    type,
    surfaces,
    lifecycle,
});

describe('clinical tooth domain', () => {
    it('parses FDI identity and selects the correct anatomical families', () => {
        expect(parseFdiTooth(11)).toMatchObject({
            arch: 'maxillary',
            kind: 'incisor',
            side: 'right',
            templateKey: 'maxillary-incisor',
        });
        expect(parseFdiTooth(36)).toMatchObject({
            arch: 'mandibular',
            kind: 'molar',
            side: 'left',
            templateKey: 'mandibular-molar',
        });
        expect(() => parseFdiTooth(49)).toThrow(/Invalid FDI/);
    });

    it('uses distinct upper and lower templates instead of flipping one generic tooth', () => {
        const upperIncisor = getClinicalToothGeometry(11);
        const lowerIncisor = getClinicalToothGeometry(31);
        const upperMolar = getClinicalToothGeometry(16);
        const lowerMolar = getClinicalToothGeometry(46);

        expect(upperIncisor.crown).not.toBe(lowerIncisor.crown);
        expect(upperIncisor.roots).not.toEqual(lowerIncisor.roots);
        expect(upperMolar.rootCount).toBe(3);
        expect(lowerMolar.rootCount).toBe(2);
        expect(upperMolar.canals).toHaveLength(3);
        expect(lowerMolar.canals).toHaveLength(3);
    });

    it('keeps lifecycle and clinical state out of raw anatomy geometry', () => {
        const geometryJson = JSON.stringify(CLINICAL_TOOTH_GEOMETRY);

        expect(geometryJson).not.toMatch(/lifecycle|in_progress|completed|planned|procedure|color/i);
    });
});

describe('ClinicalToothRenderer', () => {
    it('renders root canals along the selected tooth root anatomy', () => {
        render(
            <ClinicalToothRenderer
                fdi={46}
                state={{ procedures: [procedure(PROCEDURE_TYPE.RCT)] }}
            />
        );

        expect(screen.getByRole('img', { name: /Tooth 46: Root canal treatment/ })).toBeInTheDocument();
        expect(screen.getByTestId('rct-layer')).toHaveAttribute('data-lifecycle', 'completed');
    });

    it('renders an anatomical crown shell with planned lifecycle styling', () => {
        render(
            <ClinicalToothRenderer
                fdi={25}
                state={{
                    procedures: [procedure(
                        PROCEDURE_TYPE.CROWN,
                        [],
                        PROCEDURE_LIFECYCLE.PLANNED,
                    )],
                }}
            />
        );

        expect(screen.getByTestId('crown-layer')).toHaveAttribute('data-lifecycle', 'planned');
        expect(screen.getByTestId('crown-shell')).toHaveAttribute('stroke-dasharray', '5 3');
    });

    it('renders caries on each requested clinical surface', () => {
        render(
            <ClinicalToothRenderer
                fdi={16}
                state={{ procedures: [procedure(PROCEDURE_TYPE.CARIES, ['D', 'O'])] }}
            />
        );

        expect(screen.getByTestId('caries-surface-D')).toBeInTheDocument();
        expect(screen.getByTestId('caries-surface-O')).toBeInTheDocument();
    });

    it('replaces natural roots with implant fixture anatomy', () => {
        render(
            <ClinicalToothRenderer
                fdi={36}
                state={{ procedures: [procedure(PROCEDURE_TYPE.IMPLANT)] }}
            />
        );

        expect(screen.getByTestId('implant-layer')).toBeInTheDocument();
        expect(screen.queryByTestId('root-anatomy')).not.toBeInTheDocument();
    });

    it('renders a missing tooth as an absent ghost position', () => {
        render(
            <ClinicalToothRenderer
                fdi={15}
                state={{ procedures: [procedure(PROCEDURE_TYPE.MISSING)] }}
            />
        );

        expect(screen.getByRole('img', { name: /Tooth 15: Missing tooth/ })).toBeInTheDocument();
        expect(screen.getByTestId('missing-layer')).toBeInTheDocument();
    });

    it('renders a bridge with two abutments and a rootless pontic', () => {
        render(<ClinicalBridgeRenderer />);

        expect(screen.getByRole('group', { name: /Three-unit bridge/ })).toBeInTheDocument();
        const roles = screen.getAllByTestId('bridge-layer').map((layer) => layer.dataset.bridgeRole);
        expect(roles).toEqual(['abutment', 'pontic', 'abutment']);
    });
});

