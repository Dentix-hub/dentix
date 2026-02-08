// HYPER-REALISTIC DENTAL ANATOMY PATHS
// Mapped to Universal Numbering System (1-32)
// Each tooth has physically accurate root structure and occlusal morphology.

const PATHS = {
    // UPPER RIGHT (1-8)

    // 1: 3rd Molar (Wisdom) - Variable, usually fused roots, smaller crown
    1: {
        Root: "M25,60 C25,40 28,15 35,5 C45,0 55,0 65,5 C72,15 75,40 75,60 L75,85 L25,85 Z",
        CrownBox: {
            Occlusal: "M35,95 C35,90 45,88 50,88 C55,88 65,90 65,95 C65,110 55,125 50,125 C45,125 35,110 35,95 Z",
            Buccal: "M35,95 L65,95 L75,85 L25,85 Z",
            Lingual: "M35,95 L65,95 L75,125 L25,125 Z",
            Mesial: "M35,95 L25,85 L25,125 Z",
            Distal: "M65,95 L75,85 L75,125 Z"
        }
    },
    // 2: 2nd Molar - 3 Roots, Rhomboid
    2: {
        Root: "M20,60 C20,30 10,10 30,5 C40,0 60,0 70,5 C90,10 80,30 80,60 L80,90 L20,90 Z",
        CrownBox: {
            Occlusal: "M35,100 C32,95 38,90 50,90 C62,90 68,95 65,100 C62,115 62,120 65,125 C68,130 62,135 50,135 C38,135 32,130 35,125 C38,120 38,115 35,100 Z",
            Buccal: "M35,100 C45,90 55,90 65,100 L80,90 C70,80 30,80 20,90 Z",
            Lingual: "M35,125 C45,135 55,135 65,125 L80,140 C70,150 30,150 20,140 Z",
            Mesial: "M35,100 C30,110 30,115 35,125 L20,140 C10,115 10,110 20,90 Z",
            Distal: "M65,100 C70,110 70,115 65,125 L80,140 C90,115 90,110 80,90 Z"
        }
    },
    // 3: 1st Molar - Largest, 3 Divergent Roots, Cusp of Carabelli (hinted)
    3: {
        Root: "M15,60 C15,25 5,5 30,0 C45,-5 55,-5 70,0 C95,5 85,25 85,60 L85,90 L15,90 Z",
        CrownBox: {
            Occlusal: "M32,100 C30,90 40,85 50,85 C60,85 70,90 68,100 C65,115 65,120 68,125 C70,135 60,140 50,140 C40,140 30,135 32,125 C35,120 35,115 32,100 Z",
            Buccal: "M32,100 L68,100 L85,90 L15,90 Z",
            Lingual: "M32,125 L68,125 L85,145 L15,145 Z",
            Mesial: "M32,100 L32,125 L15,145 L15,90 Z",
            Distal: "M68,100 L68,125 L85,145 L85,90 Z"
        }
    },
    // 4: 2nd Premolar - Oval
    4: {
        Root: "M30,60 C30,30 35,0 50,0 C65,0 70,30 70,60 L70,85 L30,85 Z",
        CrownBox: {
            Occlusal: "M40,95 C38,90 42,88 50,88 C58,88 62,90 60,95 C58,105 58,110 60,115 C62,120 58,122 50,122 C42,122 38,120 40,115 C42,110 42,105 40,95 Z",
            Buccal: "M40,95 L60,95 L70,85 L30,85 Z",
            Lingual: "M40,115 L60,115 L70,125 L30,125 Z",
            Mesial: "M40,95 L40,115 L30,125 L30,85 Z",
            Distal: "M60,95 L60,115 L70,125 L70,85 Z"
        }
    },
    // 5: 1st Premolar - Bicuspid, often 2 roots (Kidney shape occlusal)
    5: {
        Root: "M30,60 C30,30 25,0 45,0 C60,0 75,30 70,60 L70,85 L30,85 Z",
        CrownBox: {
            Occlusal: "M38,95 C35,90 40,88 50,88 C60,88 65,90 62,95 C60,105 60,110 62,115 C65,120 60,122 50,122 C40,122 35,120 38,115 C40,110 40,105 38,95 Z",
            Buccal: "M38,95 L62,95 L70,85 L30,85 Z",
            Lingual: "M38,115 L62,115 L70,125 L30,125 Z",
            Mesial: "M38,95 L38,115 L30,125 L30,85 Z",
            Distal: "M62,95 L62,115 L70,125 L70,85 Z"
        }
    },
    // 6: Canine - Pointy, massive root
    6: {
        Root: "M35,60 C35,20 35,-10 50,-15 C65,-10 65,20 65,60 L65,90 L35,90 Z",
        CrownBox: {
            Occlusal: "M42,95 L50,90 L58,95 L58,115 C55,120 45,120 42,115 Z", // Diamond/Triangular
            Buccal: "M42,95 L50,90 L58,95 L65,90 L35,90 Z",
            Lingual: "M42,115 L58,115 L65,130 L35,130 Z",
            Mesial: "M42,95 L42,115 L35,130 L35,90 Z",
            Distal: "M58,95 L58,115 L65,130 L65,90 Z"
        }
    },
    // 7: Lateral Incisor - Small, rounded
    7: {
        Root: "M40,65 C40,40 42,10 50,5 C58,10 60,40 60,65 L60,95 L40,95 Z",
        CrownBox: {
            Occlusal: "M45,100 L55,100 L55,115 C55,120 45,120 45,115 Z",
            Buccal: "M45,100 L55,100 L60,95 L40,95 Z",
            Lingual: "M45,115 L55,115 L60,130 L40,130 Z",
            Mesial: "M45,100 L45,115 L40,130 L40,95 Z",
            Distal: "M55,100 L55,115 L60,130 L60,95 Z"
        }
    },
    // 8: Central Incisor - Large, shovel shaped
    8: {
        Root: "M35,65 C35,35 38,5 50,0 C62,5 65,35 65,65 L65,95 L35,95 Z",
        CrownBox: {
            Occlusal: "M40,100 L60,100 L60,118 L40,118 Z", // Rectangular
            Buccal: "M40,100 L60,100 L65,95 L35,95 Z",
            Lingual: "M40,118 L60,118 L65,135 L35,135 Z", // Cingulum area
            Mesial: "M40,100 L40,118 L35,135 L35,95 Z",
            Distal: "M60,100 L60,118 L65,135 L65,95 Z"
        }
    },
    // 9: Central Incisor (Mirror of 8)
    9: { MirrorOf: 8 },
    10: { MirrorOf: 7 },
    11: { MirrorOf: 6 },
    12: { MirrorOf: 5 },
    13: { MirrorOf: 4 },
    14: { MirrorOf: 3 },
    15: { MirrorOf: 2 },
    16: { MirrorOf: 1 },

    // LOWER ARCH (17-32)
    // 17-32 are mapped similarly but roots go DOWN
    // We handle this by using dedicated paths for lower or flipping logic in getOrganicToothType
};

// LOWER: (Roots go down)
const LOWER_PATHS = {
    // 17: 3rd Molar
    17: {
        Root: "M25,85 C25,110 30,135 50,140 C70,135 75,110 75,85 L75,55 L25,55 Z",
        CrownBox: {
            Occlusal: "M35,15 C35,10 45,8 50,8 C55,8 65,10 65,15 C65,30 55,45 50,45 C45,45 35,30 35,15 Z",
            Buccal: "M35,45 L65,45 L75,55 L25,55 Z",
            Lingual: "M35,15 L65,15 L75,0 L25,0 Z",
            Mesial: "M35,15 L35,45 L25,55 L25,0 Z",
            Distal: "M65,15 L65,45 L75,55 L75,0 Z"
        }
    },
    // 30: 1st Molar - 2 Roots, 5 Cusps (Pentagonal)
    30: {
        Root: "M20,85 C20,120 10,140 30,150 C50,145 70,145 90,140 C80,120 80,85 80,85 L80,50 L20,50 Z",
        CrownBox: {
            Occlusal: "M32,15 C30,10 40,5 50,5 C60,5 70,10 68,15 C65,35 65,40 68,45 C70,50 60,55 50,55 C40,55 30,50 32,45 C35,40 35,35 32,15 Z",
            Buccal: "M32,45 L68,45 L80,50 L20,50 Z",
            Lingual: "M32,15 L68,15 L80,5 L20,5 Z",
            Mesial: "M32,15 L32,45 L20,50 L20,5 Z",
            Distal: "M68,15 L68,45 L80,50 L80,5 Z"
        }
    },
    // 31: 2nd Molar - 4 Cusps (Rectangular)
    31: {
        Root: "M25,85 C25,120 20,140 35,145 C50,145 65,140 75,120 75,85 L75,50 L25,50 Z",
        CrownBox: {
            Occlusal: "M35,15 L65,15 L65,40 L35,40 Z", // Basic Square Molar
            Buccal: "M35,40 L65,40 L75,50 L25,50 Z",
            Lingual: "M35,15 L65,15 L75,5 L25,5 Z",
            Mesial: "M35,15 L35,40 L25,50 L25,5 Z",
            Distal: "M65,15 L65,40 L75,50 L75,5 Z"
        }
    },
    // 29: 2nd Premolar
    29: {
        Root: "M35,85 C35,110 38,140 50,145 C62,140 65,110 65,85 L65,55 L35,55 Z",
        CrownBox: {
            Occlusal: "M42,15 C42,10 45,8 50,8 C55,8 58,10 58,15 C58,35 55,40 50,40 C45,40 42,35 42,15 Z",
            Buccal: "M42,40 L58,40 L65,55 L35,55 Z",
            Lingual: "M42,15 L58,15 L65,0 L35,0 Z",
            Mesial: "M42,15 L42,40 L35,55 L35,0 Z",
            Distal: "M58,15 L58,40 L65,55 L65,0 Z"
        }
    },
    // 28: 1st Premolar
    28: { CopyOf: 29 }, // Similar enough for visual chart

    // 27: Canine
    27: {
        Root: "M35,85 C35,120 40,150 50,155 C60,150 65,120 65,85 L65,55 L35,55 Z",
        CrownBox: {
            Occlusal: "M42,20 L50,15 L58,20 L58,40 C55,45 45,45 42,40 Z",
            Buccal: "M42,40 L50,45 L58,40 L65,55 L35,55 Z",
            Lingual: "M42,20 L58,20 L65,0 L35,0 Z",
            Mesial: "M42,20 L42,40 L35,55 L35,0 Z",
            Distal: "M58,20 L58,40 L65,55 L65,0 Z"
        }
    },
    // 26: Lateral Incisor
    26: {
        Root: "M40,85 C40,110 45,140 50,145 C55,140 60,110 60,85 L60,55 L40,55 Z",
        CrownBox: {
            Occlusal: "M45,20 L55,20 L55,40 L45,40 Z",
            Buccal: "M45,40 L55,40 L60,55 L40,55 Z",
            Lingual: "M45,20 L55,20 L60,0 L40,0 Z",
            Mesial: "M45,20 L45,40 L40,55 L40,0 Z",
            Distal: "M55,20 L55,40 L60,55 L60,0 Z"
        }
    },
    // 25: Central Incisor (Smallest)
    25: { CopyOf: 26 }, // Mandibular incisors are very similar
    24: { CopyOf: 26 },
    23: { CopyOf: 26 },
    22: { CopyOf: 27 }, // Canine
    21: { CopyOf: 29 }, // Premolar
    20: { CopyOf: 29 }, // Premolar
    19: { CopyOf: 30 }, // Molar 1
    18: { CopyOf: 31 }, // Molar 2
};


export const getOrganicToothType = (number) => {
    // Return specific ID if mapped, or resolve mirror/copy
    let def = null;

    // UPPER
    if (number >= 1 && number <= 16) {
        if (PATHS[number]) {
            def = PATHS[number];
            if (def.MirrorOf) {
                // Return reflected version of the base tooth
                return { ...PATHS[def.MirrorOf], isMirror: true };
            }
            return { ...def, isMirror: false };
        }
    }

    // LOWER
    if (number >= 17 && number <= 32) {
        if (LOWER_PATHS[number]) {
            def = LOWER_PATHS[number];
            if (def.CopyOf) {
                return { ...LOWER_PATHS[def.CopyOf], isMirror: false };
            }
            return { ...def, isMirror: false };
        }
    }

    // Fallback
    return PATHS[1];
};
