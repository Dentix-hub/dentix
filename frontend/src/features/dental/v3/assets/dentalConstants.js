// DENTAL CONSTANTS v3
// Strict medical standards for the Advanced Dental Chart

export const SEGMENTS = {
    OCCLUSAL: 'Occlusal',
    MESIAL: 'Mesial',
    DISTAL: 'Distal',
    BUCCAL: 'Buccal',
    LINGUAL: 'Lingual'
};

export const TOOTH_STATUS = {
    HEALTHY: 'Healthy',
    MISSING: 'Missing',
    IMPACTED: 'Impacted',
    EXTRACTED: 'Extracted'
};

export const PROCEDURE_TYPES = {
    // Restorative
    COMPOSITE:     { id: 'composite',     label: 'Composite Filling',   color: '#3B82F6', category: 'restorative', isSurface: true },
    AMALGAM:       { id: 'amalgam',       label: 'Amalgam Filling',     color: '#6B7280', category: 'restorative', isSurface: true },
    GLASS_IONOMER: { id: 'glass_ionomer', label: 'Glass Ionomer',       color: '#60A5FA', category: 'restorative', isSurface: true },
    INLAY:         { id: 'inlay',         label: 'Inlay / Onlay',       color: '#8B5CF6', category: 'restorative', isSurface: true },
    CROWN:         { id: 'crown',         label: 'Crown',               color: '#F59E0B', category: 'restorative', isWholeTooth: true },
    VENEER:        { id: 'veneer',        label: 'Veneer',              color: '#EC4899', category: 'restorative', isWholeTooth: true },
    BRIDGE:        { id: 'bridge',        label: 'Bridge',              color: '#D97706', category: 'restorative', isWholeTooth: true },

    // Endodontic
    PULP_CAPPING:  { id: 'pulp_capping',  label: 'Pulp Capping',        color: '#F97316', category: 'endo', isRoot: true },
    PULPOTOMY:     { id: 'pulpotomy',     label: 'Pulpotomy',           color: '#FB923C', category: 'endo', isRoot: true },
    RCT:           { id: 'rct',           label: 'Root Canal (RCT)',    color: '#EF4444', category: 'endo', isRoot: true },
    RCT_RETREAT:   { id: 'rct_retreatment', label: 'RCT Retreatment',  color: '#B91C1C', category: 'endo', isRoot: true },
    APICO:         { id: 'apico',         label: 'Apicoectomy',         color: '#7F1D1D', category: 'endo', isRoot: true },

    // Periodontics
    SCALING:       { id: 'scaling',       label: 'Scaling / Cleaning',  color: '#10B981', category: 'perio', isWholeTooth: true },
    DEEP_SCALING:  { id: 'deep_scaling',  label: 'Deep Scaling (SRP)',  color: '#059669', category: 'perio', isWholeTooth: true },

    // Surgery
    EXTRACTION:    { id: 'extraction',    label: 'Extraction',          color: '#DC2626', category: 'surgery', isWholeTooth: true },
    SURG_EXTRACT:  { id: 'surgical_extraction', label: 'Surgical Extraction', color: '#991B1B', category: 'surgery', isWholeTooth: true },
    IMPLANT:       { id: 'implant',       label: 'Implant',             color: '#1D4ED8', category: 'surgery', isRoot: true },

    // Diagnostic
    EXAM:          { id: 'exam',          label: 'Periodic Exam',       color: '#94a3b8', category: 'diagnostic', isWholeTooth: true },
    XRAY:          { id: 'xray',          label: 'Periapical X-Ray',   color: '#cbd5e1', category: 'diagnostic', isWholeTooth: true },

    // Prosthodontics & Orthodontics
    REMOVABLE:     { id: 'removable_partial', label: 'Removable Partial', color: '#7C3AED', category: 'prostho', isWholeTooth: true },
    BRACES:        { id: 'braces',        label: 'Fixed Braces',        color: '#0EA5E9', category: 'ortho', isWholeTooth: true },
    ALIGNER:       { id: 'aligner',       label: 'Clear Aligner',       color: '#38BDF8', category: 'ortho', isWholeTooth: true },

    // Pediatric & Cosmetic
    SSC:           { id: 'ssc',           label: 'Stainless Steel Crown', color: '#A3A3A3', category: 'pediatric', isWholeTooth: true },
    SEALANT:       { id: 'fissure_sealant', label: 'Fissure Sealant',  color: '#A7F3D0', category: 'restorative', isSurface: true },
    WHITENING:     { id: 'whitening',     label: 'Teeth Whitening',     color: '#FDE68A', category: 'cosmetic', isWholeTooth: true },
};

export const PROCEDURE_STATUS = {
    PLANNED: 'planned',
    COMPLETED: 'completed',
    EXISTING: 'existing', // Previous work done elsewhere
    FAILED: 'failed'
};

// Helper: build lookup map
export const PROCEDURE_MAP = Object.fromEntries(
    Object.entries(PROCEDURE_TYPES).map(([key, p]) => [p.id, { ...p, key }])
);

export function getProcedureColor(procedureId) {
    if (!procedureId) return '#E5E7EB';
    // Case-insensitive lookup match
    const entry = Object.values(PROCEDURE_TYPES).find(p => p.id.toLowerCase() === procedureId.toLowerCase());
    return entry?.color ?? '#E5E7EB';
}

export const PROCEDURE_STATUS_COLORS = {
    [PROCEDURE_STATUS.PLANNED]: 'opacity-50 border-dashed',
    [PROCEDURE_STATUS.COMPLETED]: 'opacity-100',
    [PROCEDURE_STATUS.EXISTING]: 'opacity-80 grayscale',
    [PROCEDURE_STATUS.FAILED]: 'stroke-red-500 stroke-2'
};
