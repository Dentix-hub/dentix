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
    FILLING: { id: 'filling', label: 'Filling (Resin/Amalgam)', color: '#3b82f6', category: 'restorative', isSurface: true }, // Blue-500
    CROWN: { id: 'crown', label: 'Crown (Porcelain/Gold)', color: '#22c55e', category: 'restorative', isWholeTooth: true }, // Green-500
    VENEER: { id: 'veneer', label: 'Veneer', color: '#86efac', category: 'restorative', isWholeTooth: true }, // Green-300

    // Endodontic
    RCT: { id: 'rct', label: 'Root Canal Treatment', color: '#ef4444', category: 'endo', isRoot: true }, // Red-500
    APICO: { id: 'apico', label: 'Apicoectomy', color: '#fca5a5', category: 'endo', isRoot: true }, // Red-300

    // Surgical
    EXTRACTION: { id: 'extraction', label: 'Extraction', color: '#0f172a', category: 'surgery', isWholeTooth: true }, // Slate-900
    IMPLANT: { id: 'implant', label: 'Implant', color: '#6366f1', category: 'surgery', isRoot: true }, // Indigo-500

    // Diagnostic
    EXAM: { id: 'exam', label: 'Periodic Exam', color: '#94a3b8', category: 'diagnostic', isWholeTooth: true },
    XRAY: { id: 'xray', label: 'Periapical X-Ray', color: '#cbd5e1', category: 'diagnostic', isWholeTooth: true }
};

export const PROCEDURE_STATUS = {
    PLANNED: 'planned',
    COMPLETED: 'completed',
    EXISTING: 'existing', // Previous work done elsewhere
    FAILED: 'failed'
};

export const PROCEDURE_STATUS_COLORS = {
    [PROCEDURE_STATUS.PLANNED]: 'opacity-50 border-dashed',
    [PROCEDURE_STATUS.COMPLETED]: 'opacity-100',
    [PROCEDURE_STATUS.EXISTING]: 'opacity-80 grayscale',
    [PROCEDURE_STATUS.FAILED]: 'stroke-red-500 stroke-2'
};
