const RECENT_PATIENT_IDS_KEY = 'dentix_recent_patient_ids_v1';
const MAX_RECENT_PATIENTS = 8;

export function getRecentPatientIds() {
    if (typeof window === 'undefined') return [];
    try {
        const stored = JSON.parse(window.localStorage.getItem(RECENT_PATIENT_IDS_KEY) || '[]');
        if (!Array.isArray(stored)) return [];
        return stored
            .map((value) => Number.parseInt(value, 10))
            .filter((value) => Number.isInteger(value) && value > 0)
            .filter((value, index, array) => array.indexOf(value) === index)
            .slice(0, MAX_RECENT_PATIENTS);
    } catch {
        return [];
    }
}

export function rememberRecentPatientId(patientId) {
    if (typeof window === 'undefined') return;
    const id = Number.parseInt(patientId, 10);
    if (!Number.isInteger(id) || id <= 0) return;
    const recent = getRecentPatientIds().filter((existingId) => existingId !== id);
    window.localStorage.setItem(
        RECENT_PATIENT_IDS_KEY,
        JSON.stringify([id, ...recent].slice(0, MAX_RECENT_PATIENTS)),
    );
}
