import { getDentalAnatomy, TOOTH_TYPES } from '@/features/clinical-chart/domain/dentalAnatomyRegistry';

/**
 * Canal anatomy definition mapping roots and default canals for any FDI tooth key.
 * Used in Chairside RCT Structured UI (G10-M09, G10-M10).
 */

export const REFERENCE_POINTS = [
    'MB cusp',
    'ML cusp',
    'DB cusp',
    'DL cusp',
    'Buccal cusp',
    'Palatal cusp',
    'Incisal edge',
    'Cingulum',
];

export const MAF_SIZES = [
    '#20 / .04',
    '#25 / .04',
    '#25 / .06',
    '#30 / .04',
    '#30 / .06',
    '#35 / .04',
    '#35 / .06',
    '#40 / .04',
    '#45 / .04',
    '#50 / .04',
];

/**
 * Get canal presets by tooth key.
 * @param {string|number} toothKey FDI tooth key (e.g. '46', '16', '11')
 * @returns {Array<{ rootId: string, rootLabel: string, defaultCanals: string[] }>}
 */
export function getCanalAnatomyForTooth(toothKey) {
    const key = String(toothKey);
    const anatomy = getDentalAnatomy(key);

    if (!anatomy) {
        return [
            {
                rootId: 'single',
                rootLabel: 'Single Root',
                defaultCanals: ['Canal 1'],
            },
        ];
    }

    const { arch, toothType, position } = {
        arch: anatomy.arch,
        toothType: anatomy.toothType,
        position: Number(key[1] || 1),
    };

    if (toothType === TOOTH_TYPES.MOLAR) {
        if (arch === 'maxillary') {
            return [
                {
                    rootId: 'mesiobuccal',
                    rootLabel: 'Mesiobuccal (MB)',
                    defaultCanals: ['MB1', 'MB2'],
                },
                {
                    rootId: 'distobuccal',
                    rootLabel: 'Distobuccal (DB)',
                    defaultCanals: ['DB'],
                },
                {
                    rootId: 'palatal',
                    rootLabel: 'Palatal (P)',
                    defaultCanals: ['P'],
                },
            ];
        }
        // Mandibular molars (e.g. 46, 36)
        return [
            {
                rootId: 'mesial',
                rootLabel: 'Mesial (M)',
                defaultCanals: ['MB', 'ML'],
            },
            {
                rootId: 'distal',
                rootLabel: 'Distal (D)',
                defaultCanals: ['D', 'DB', 'DL'],
            },
        ];
    }

    if (toothType === TOOTH_TYPES.PREMOLAR) {
        if (arch === 'maxillary' && position === 4) {
            return [
                {
                    rootId: 'buccal',
                    rootLabel: 'Buccal (B)',
                    defaultCanals: ['B'],
                },
                {
                    rootId: 'palatal',
                    rootLabel: 'Palatal (P)',
                    defaultCanals: ['P'],
                },
            ];
        }
        return [
            {
                rootId: 'single',
                rootLabel: 'Root',
                defaultCanals: ['B', 'L'],
            },
        ];
    }

    // Incisors and canines
    return [
        {
            rootId: 'single',
            rootLabel: 'Single Root',
            defaultCanals: ['Main'],
        },
    ];
}
