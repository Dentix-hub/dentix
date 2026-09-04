const healthyAssetModules = import.meta.glob(
    './assets/adult-fdi-clean/tooth-*-healthy.png',
    { eager: true, import: 'default' },
);

const dedicatedVariantModules = import.meta.glob(
    './assets/tooth-*-approval-v*/tooth-*-*-v*.png',
    { eager: true, import: 'default' },
);

function buildHealthyAssetRegistry() {
    const entries = Object.entries(healthyAssetModules).map(([path, src]) => {
        const match = path.match(/tooth-(\d{2})-healthy\.png$/);
        if (!match) throw new Error(`Invalid clinical tooth asset filename: ${path}`);
        return [Number(match[1]), src];
    });

    if (entries.length !== 32) {
        throw new Error(`Expected 32 adult FDI tooth assets, received ${entries.length}`);
    }

    return Object.freeze(Object.fromEntries(entries));
}

export const HEALTHY_ADULT_TOOTH_ASSETS = buildHealthyAssetRegistry();

export function getHealthyAdultToothAsset(fdi) {
    const src = HEALTHY_ADULT_TOOTH_ASSETS[Number(fdi)];
    if (!src) throw new Error(`Missing healthy adult tooth asset for FDI ${fdi}`);
    return src;
}

export function buildDedicatedVariantKey({ fdi, type, surfaces = [] }) {
    const normalizedSurfaces = [...new Set(surfaces.map((surface) => String(surface).toUpperCase()))]
        .sort()
        .join('-');
    return [Number(fdi), type, normalizedSurfaces || 'whole'].join(':');
}

const DEDICATED_VARIANT_MANIFEST = Object.freeze([
    { fdi: 46, type: 'caries', surfaces: ['O'], filename: 'tooth-46-caries-v1.png' },
    { fdi: 46, type: 'composite', surfaces: ['O'], filename: 'tooth-46-composite-v2.png' },
    { fdi: 46, type: 'amalgam', surfaces: ['O'], filename: 'tooth-46-amalgam-v1.png' },
    { fdi: 46, type: 'rct', filename: 'tooth-46-rct-v1.png' },
    { fdi: 46, type: 'crown', filename: 'tooth-46-crown-v1.png' },
    { fdi: 46, type: 'implant', filename: 'tooth-46-implant-v1.png' },
    { fdi: 46, type: 'missing', filename: 'tooth-46-missing-v1.png' },
    { fdi: 46, type: 'fracture', filename: 'tooth-46-fracture-v1.png' },
]);

function buildDedicatedVariantRegistry() {
    const entries = DEDICATED_VARIANT_MANIFEST.map((variant) => {
        const moduleEntry = Object.entries(dedicatedVariantModules)
            .find(([path]) => path.endsWith(`/${variant.filename}`));
        if (!moduleEntry) throw new Error(`Missing dedicated clinical tooth variant: ${variant.filename}`);
        return [buildDedicatedVariantKey(variant), moduleEntry[1]];
    });

    return Object.freeze(Object.fromEntries(entries));
}

export const DEDICATED_TOOTH_VARIANTS = buildDedicatedVariantRegistry();

export function getDedicatedToothVariant({ fdi, type, surfaces = [] }) {
    return DEDICATED_TOOTH_VARIANTS[buildDedicatedVariantKey({ fdi, type, surfaces })] || null;
}
