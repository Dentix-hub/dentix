// HIGH FIDELITY ORGANIC TOOTH PATHS
// Designed to look like clinical dental charts (Curved "Flower" style for Molars, Smooth Ovals for others)

export const ORGANIC_PATHS = {
    // UPPER MOLAR (1, 2, 3, 14, 15, 16) - 3 Roots, "Flower" Occlusal
    UPPER_MOLAR: {
        Root: "M25,65 C25,40 10,20 20,5 C30,-5 45,10 50,15 C55,10 70,-5 80,5 C90,20 75,40 75,65 L75,85 L25,85 Z",
        CrownBox: {
            // Central Occlusal (Rounded Square/Circle)
            Occlusal: "M38,100 C38,95 45,90 50,90 C55,90 62,95 62,100 C62,108 62,118 62,125 C62,130 55,135 50,135 C45,135 38,130 38,125 Z",

            // Top (Buccal) - Curved trapezoid
            Buccal: "M38,100 C45,90 55,90 62,100 L75,85 C65,75 35,75 25,85 Z",

            // Bottom (Lingual or Palatal)
            Lingual: "M38,125 C45,135 55,135 62,125 L75,140 C65,150 35,150 25,140 Z",

            // Left (Mesial)
            Mesial: "M38,100 C32,110 32,115 38,125 L25,140 C10,125 10,100 25,85 Z",

            // Right (Distal)
            Distal: "M62,100 C68,110 68,115 62,125 L75,140 C90,125 90,100 75,85 Z"
        }
    },

    // UPPER PREMOLAR (4, 5, 12, 13) - 2 Roots, Oval Occlusal
    UPPER_PREMOLAR: {
        Root: "M35,65 C35,40 30,15 40,5 C45,0 55,0 60,5 C70,15 65,40 65,65 L65,85 L35,85 Z",
        CrownBox: {
            Occlusal: "M42,100 C42,95 45,92 50,92 C55,92 58,95 58,100 L58,125 C58,130 55,133 50,133 C45,133 42,130 42,125 Z",
            Buccal: "M42,100 C45,92 55,92 58,100 L65,85 C55,80 45,80 35,85 Z",
            Lingual: "M42,125 C45,133 55,133 58,125 L65,140 C55,145 45,145 35,140 Z",
            Mesial: "M42,100 L42,125 L35,140 C28,125 28,100 35,85 Z",
            Distal: "M58,100 L58,125 L65,140 C72,125 72,100 65,85 Z"
        }
    },

    // UPPER ANTERIOR (6-11) - Single Root, Rectangular Edge
    UPPER_ANTERIOR: {
        Root: "M40,65 C40,40 42,10 50,5 C58,10 60,40 60,65 L60,85 L40,85 Z",
        CrownBox: {
            // Incisal Edge is narrow
            Occlusal: "M45,100 L55,100 L55,125 L45,125 Z", // Just a strip
            Buccal: "M45,100 L55,100 L60,85 L40,85 Z",    // Facial
            Lingual: "M45,125 L55,125 L60,140 L40,140 Z",  // Lingual
            Mesial: "M45,100 L45,125 L40,140 L40,85 Z",
            Distal: "M55,100 L55,125 L60,140 L60,85 Z"
        }
    },

    // LOWER MOLAR (17-19, 30-32) - 2 Roots (Wide, Curved)
    LOWER_MOLAR: {
        Root: "M25,85 C25,110 15,135 30,145 C40,150 60,150 70,145 C85,135 75,110 75,85 L75,55 L25,55 Z",
        CrownBox: {
            // Inverted logic for lower? No, Crown is Crown.
            Occlusal: "M38,15 C38,10 45,5 50,5 C55,5 62,10 62,15 C62,28 62,35 62,40 C62,45 55,50 50,50 C45,50 38,45 38,40 Z",

            Buccal: "M38,40 C45,50 55,50 62,40 L75,55 C65,65 35,65 25,55 Z", // Bottom on SVG (Outer)
            Lingual: "M38,15 C45,5 55,5 62,15 L75,0 C65,-10 35,-10 25,0 Z",   // Top on SVG (Inner)
            Mesial: "M38,15 C32,20 32,35 38,40 L25,55 C10,35 10,10 25,0 Z",
            Distal: "M62,15 C68,20 68,35 62,40 L75,55 C90,35 90,10 75,0 Z"
        }
    },

    // LOWER PREMOLAR (20, 21, 28, 29)
    LOWER_PREMOLAR: {
        Root: "M35,85 C35,110 38,140 50,145 C62,140 65,110 65,85 L65,55 L35,55 Z",
        CrownBox: {
            Occlusal: "M42,15 C42,10 45,8 50,8 C55,8 58,10 58,15 L58,40 C58,45 55,48 50,48 C45,48 42,45 42,40 Z",
            Buccal: "M42,40 C45,48 55,48 58,40 L65,55 C55,60 45,60 35,55 Z",
            Lingual: "M42,15 C45,8 55,8 58,15 L65,0 C55,-5 45,-5 35,0 Z",
            Mesial: "M42,15 L42,40 L35,55 C28,40 28,15 35,0 Z",
            Distal: "M58,15 L58,40 L65,55 C72,40 72,15 65,0 Z"
        }
    },

    // LOWER ANTERIOR (22-27) - Very narrow
    LOWER_ANTERIOR: {
        Root: "M40,85 C40,110 45,140 50,145 C55,140 60,110 60,85 L60,55 L40,55 Z",
        CrownBox: {
            Occlusal: "M45,20 L55,20 L55,40 L45,40 Z",
            Buccal: "M45,40 L55,40 L60,55 L40,55 Z",
            Lingual: "M45,20 L55,20 L60,0 L40,0 Z",
            Mesial: "M45,20 L45,40 L40,55 L40,0 Z",
            Distal: "M55,20 L55,40 L60,55 L60,0 Z"
        }
    }
};

export const getOrganicToothType = (number) => {
    // Universal numbering maps to types
    if ([1, 2, 3, 14, 15, 16].includes(number)) return 'UPPER_MOLAR';
    if ([4, 5, 12, 13].includes(number)) return 'UPPER_PREMOLAR';
    if ([6, 7, 8, 9, 10, 11].includes(number)) return 'UPPER_ANTERIOR';

    if ([17, 18, 19, 30, 31, 32].includes(number)) return 'LOWER_MOLAR';
    if ([20, 21, 28, 29].includes(number)) return 'LOWER_PREMOLAR';
    if ([22, 23, 24, 25, 26, 27].includes(number)) return 'LOWER_ANTERIOR';

    return 'UPPER_MOLAR';
};
