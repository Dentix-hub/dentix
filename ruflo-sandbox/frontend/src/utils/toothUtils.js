// Tooth Number Utilities

// Universal Pediatric Notation: A-T (Primary/Deciduous teeth)
// FDI Pediatric Notation: 51-85
const PEDIATRIC_LETTER_TO_NUMBER = {
    'A': 55, 'B': 54, 'C': 53, 'D': 52, 'E': 51,  // Upper Right
    'F': 61, 'G': 62, 'H': 63, 'I': 64, 'J': 65,  // Upper Left
    'K': 75, 'L': 74, 'M': 73, 'N': 72, 'O': 71,  // Lower Left
    'P': 81, 'Q': 82, 'R': 83, 'S': 84, 'T': 85   // Lower Right
};

const PEDIATRIC_NUMBER_TO_LETTER = Object.fromEntries(
    Object.entries(PEDIATRIC_LETTER_TO_NUMBER).map(([k, v]) => [v, k])
);

export const toothToNumber = (toothId) => {
    if (typeof toothId === 'string' && /^[A-T]$/.test(toothId)) {
        return PEDIATRIC_LETTER_TO_NUMBER[toothId];
    }
    const n = parseInt(toothId);
    // If it's 1-32 (Universal Adult), we should ideally convert to FDI (11-48)
    // Universal 1 = UR8 (FDI 18), 8 = UR1 (FDI 11), 9 = UL1 (FDI 21), 16 = UL8 (FDI 28)
    // 17 = LL8 (FDI 38), 24 = LL1 (FDI 31), 25 = LR1 (FDI 41), 32 = LR8 (FDI 48)
    if (n >= 1 && n <= 8) return 19 - n;
    if (n >= 9 && n <= 16) return 12 + n;
    if (n >= 17 && n <= 24) return 55 - n; // 24 -> 31, 17 -> 38
    if (n >= 25 && n <= 32) return 16 + n; // 25 -> 41, 32 -> 48

    return n;
};

export const universalToPalmer = (uId, isPediatric) => {
    if (!uId) return '';
    if (isPediatric) {
        const pedMap = {
            'A': 'UR E', 'B': 'UR D', 'C': 'UR C', 'D': 'UR B', 'E': 'UR A',
            'F': 'UL A', 'G': 'UL B', 'H': 'UL C', 'I': 'UL D', 'J': 'UL E',
            'K': 'LL E', 'L': 'LL D', 'M': 'LL C', 'N': 'LL B', 'O': 'LL A',
            'P': 'LR A', 'Q': 'LR B', 'R': 'LR C', 'S': 'LR D', 'T': 'LR E'
        };
        return pedMap[uId] || uId;
    }

    const n = parseInt(uId);
    if (n >= 1 && n <= 8) return `UR${9 - n}`;
    if (n >= 9 && n <= 16) return `UL${n - 8}`;
    if (n >= 17 && n <= 24) return `LL${25 - n}`;
    if (n >= 25 && n <= 32) return `LR${n - 24}`;

    return uId.toString();
};

export const fdiToPalmer = (fdi) => {
    if (!fdi) return '-';
    const n = parseInt(fdi);

    // Adult Teeth (11-48)
    if (n >= 11 && n <= 18) return `UR${n % 10}`;
    if (n >= 21 && n <= 28) return `UL${n % 10}`;
    if (n >= 31 && n <= 38) return `LL${n % 10}`;
    if (n >= 41 && n <= 48) return `LR${n % 10}`;

    // Pediatric mapping (51-85)
    const pedMap = {
        55: 'UR E', 54: 'UR D', 53: 'UR C', 52: 'UR B', 51: 'UR A',
        61: 'UL A', 62: 'UL B', 63: 'UL C', 64: 'UL D', 65: 'UL E',
        71: 'LL A', 72: 'LL B', 73: 'LL C', 74: 'LL D', 75: 'LL E',
        81: 'LR A', 82: 'LR B', 83: 'LR C', 84: 'LR D', 85: 'LR E'
    };

    return pedMap[n] || n.toString();
};

export const toothToDisplay = (toothNumber, isPediatric) => {
    // We now prefer Palmer notation for display as requested
    return fdiToPalmer(toothNumber);
};

export const palmerToFdi = (palmer) => {
    if (!palmer || typeof palmer !== 'string') return null;
    const clean = palmer.toUpperCase().replace(/\s/g, '');

    // Patterns: UR1, UL1, LL1, LR1 (Adult) or URA...URE (Pediatric)
    const match = clean.match(/^(UR|UL|LL|LR)([1-8]|[A-E])$/);
    if (!match) return parseInt(palmer) || null;

    const quad = match[1];
    const val = match[2];

    const isPed = /[A-E]/.test(val);

    if (!isPed) {
        const num = parseInt(val);
        if (quad === 'UR') return 10 + num;
        if (quad === 'UL') return 20 + num;
        if (quad === 'LL') return 30 + num;
        if (quad === 'LR') return 40 + num;
    } else {
        const pedMap = {
            'UR': { 'A': 51, 'B': 52, 'C': 53, 'D': 54, 'E': 55 },
            'UL': { 'A': 61, 'B': 62, 'C': 63, 'D': 64, 'E': 65 },
            'LL': { 'A': 71, 'B': 72, 'C': 73, 'D': 74, 'E': 75 },
            'LR': { 'A': 81, 'B': 82, 'C': 83, 'D': 84, 'E': 85 }
        };
        return pedMap[quad][val];
    }
    return null;
};

export const getTodayStr = () => {
    return new Date().toLocaleDateString('en-CA'); // YYYY-MM-DD
};

export const getTodayDateTimeStr = () => {
    const d = new Date();
    d.setMinutes(d.getMinutes() - d.getTimezoneOffset());
    return d.toISOString().slice(0, 16); // YYYY-MM-DDTHH:mm
};
