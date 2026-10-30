/**
 * Fixed 12-color palette for procedure chart appearance (Decision D2 / Architecture A3).
 *
 * Stored and transmitted as a palette `key` (never raw hex).
 * Red is deliberately excluded from this palette because red hues (`#b91c1c`, `#dc2626`)
 * are reserved for clinical findings (caries, fracture, pain).
 */

export const CARIES_FINDING_FILL = '#b91c1c';
export const DEFAULT_MARKER_COLOR_KEY = 'teal';

const freezeSwatch = (swatch) => Object.freeze({ ...swatch });

export const PROCEDURE_CHART_PALETTE = Object.freeze({
    blue: freezeSwatch({
        key: 'blue',
        fill: '#2563eb',
        stroke: '#1d4ed8',
        labelAr: 'أزرق',
        labelEn: 'Blue',
    }),
    teal: freezeSwatch({
        key: 'teal',
        fill: '#0d9488',
        stroke: '#0f766e',
        labelAr: 'تركواز',
        labelEn: 'Teal',
    }),
    green: freezeSwatch({
        key: 'green',
        fill: '#16a34a',
        stroke: '#15803d',
        labelAr: 'أخضر',
        labelEn: 'Green',
    }),
    lime: freezeSwatch({
        key: 'lime',
        fill: '#65a30d',
        stroke: '#4d7c0f',
        labelAr: 'ليموني',
        labelEn: 'Lime',
    }),
    amber: freezeSwatch({
        key: 'amber',
        fill: '#d97706',
        stroke: '#b45309',
        labelAr: 'عنبري',
        labelEn: 'Amber',
    }),
    orange: freezeSwatch({
        key: 'orange',
        fill: '#ea580c',
        stroke: '#c2410c',
        labelAr: 'برتقالي',
        labelEn: 'Orange',
    }),
    purple: freezeSwatch({
        key: 'purple',
        fill: '#7c3aed',
        stroke: '#6d28d9',
        labelAr: 'بنفسجي',
        labelEn: 'Purple',
    }),
    indigo: freezeSwatch({
        key: 'indigo',
        fill: '#4f46e5',
        stroke: '#4338ca',
        labelAr: 'نيلي',
        labelEn: 'Indigo',
    }),
    pink: freezeSwatch({
        key: 'pink',
        fill: '#db2777',
        stroke: '#be185d',
        labelAr: 'وردي',
        labelEn: 'Pink',
    }),
    cyan: freezeSwatch({
        key: 'cyan',
        fill: '#0891b2',
        stroke: '#0e7490',
        labelAr: 'سماوي',
        labelEn: 'Cyan',
    }),
    slate: freezeSwatch({
        key: 'slate',
        fill: '#475569',
        stroke: '#334155',
        labelAr: 'رمادي',
        labelEn: 'Slate',
    }),
    brown: freezeSwatch({
        key: 'brown',
        fill: '#92400e',
        stroke: '#78350f',
        labelAr: 'بني',
        labelEn: 'Brown',
    }),
});

export const PROCEDURE_CHART_PALETTE_KEYS = Object.freeze(
    Object.keys(PROCEDURE_CHART_PALETTE),
);

export const PROCEDURE_CHART_PALETTE_LIST = Object.freeze(
    PROCEDURE_CHART_PALETTE_KEYS.map((key) => PROCEDURE_CHART_PALETTE[key]),
);

/**
 * Resolves a palette entry by key. Returns `null` for null, undefined, empty,
 * non-string, or unknown keys. Never throws.
 *
 * @param {unknown} key
 * @returns {Readonly<{key: string, fill: string, stroke: string, labelAr: string, labelEn: string}> | null}
 */
export const resolvePaletteColor = (key) => {
    if (typeof key !== 'string') return null;
    const normalized = key.trim().toLowerCase();
    if (!normalized) return null;
    return Object.prototype.hasOwnProperty.call(PROCEDURE_CHART_PALETTE, normalized)
        ? PROCEDURE_CHART_PALETTE[normalized]
        : null;
};

/**
 * Resolves a palette entry for a tooth marker, falling back to `teal` when the
 * marker has `colorKey = null` or an unrecognised key.
 *
 * @param {unknown} key
 * @returns {Readonly<{key: string, fill: string, stroke: string, labelAr: string, labelEn: string}>}
 */
export const resolveMarkerPaletteColor = (key) => (
    resolvePaletteColor(key) ?? PROCEDURE_CHART_PALETTE[DEFAULT_MARKER_COLOR_KEY]
);

/**
 * Parses a 6-digit `#rrggbb` hex string into `{ r, g, b }` in `[0..255]`.
 */
export const parseHexRgb = (hex) => {
    const clean = String(hex || '').trim().replace(/^#/, '');
    if (!/^[0-9a-fA-F]{6}$/.test(clean)) {
        throw new RangeError(`Invalid 6-digit hex color: ${hex}`);
    }
    return {
        r: parseInt(clean.slice(0, 2), 16),
        g: parseInt(clean.slice(2, 4), 16),
        b: parseInt(clean.slice(4, 6), 16),
    };
};

/**
 * WCAG 2.1 relative luminance for a `#rrggbb` color.
 */
export const computeRelativeLuminance = (hex) => {
    const { r, g, b } = parseHexRgb(hex);
    const toLinear = (channel) => {
        const srgb = channel / 255;
        return srgb <= 0.03928 ? srgb / 12.92 : ((srgb + 0.055) / 1.055) ** 2.4;
    };
    return 0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
};

/**
 * WCAG 2.1 contrast ratio between two `#rrggbb` colors (`>= 1`).
 */
export const computeContrastRatio = (hexA, hexB = '#ffffff') => {
    const lumA = computeRelativeLuminance(hexA);
    const lumB = computeRelativeLuminance(hexB);
    const lighter = Math.max(lumA, lumB);
    const darker = Math.min(lumA, lumB);
    return Number(((lighter + 0.05) / (darker + 0.05)).toFixed(2));
};

/**
 * Euclidean RGB distance (`0..441.67`) between a hex color and the CARIES finding fill (`#b91c1c`).
 */
export const computeColorDistanceFromCaries = (hex, cariesHex = CARIES_FINDING_FILL) => {
    const a = parseHexRgb(hex);
    const b = parseHexRgb(cariesHex);
    const distance = Math.hypot(a.r - b.r, a.g - b.g, a.b - b.b);
    return Number(distance.toFixed(2));
};
