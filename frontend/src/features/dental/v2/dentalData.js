// Comprehensive Dental Data Configuration
// Categories map to ADA Code Ranges roughly or logical grouping for UI

export const TOOTH_STATUS_OPTIONS = [
    { id: 'Sound', label: 'سليم (Sound)', color: 'bg-green-500', code: 'SOUND' },
    { id: 'Missing', label: 'مفقود (Missing)', color: 'bg-slate-400', code: 'MISSING' },
    { id: 'Impacted', label: 'مدفون (Impacted)', color: 'bg-red-400', code: 'IMPACTED' },
    { id: 'Carry', label: 'تسوس (Decayed)', color: 'bg-orange-500', code: 'DECAY' },
    { id: 'RCT', label: 'علاج جذور (RCT)', color: 'bg-red-600', code: 'RCT_DONE' },
    { id: 'Crown', label: 'طربوش (Crown)', color: 'bg-yellow-400', code: 'CROWN' },
    { id: 'Bridge', label: 'جسر (Bridge)', color: 'bg-yellow-600', code: 'BRIDGE' },
    { id: 'Implant', label: 'زرعة (Implant)', color: 'bg-indigo-500', code: 'IMPLANT' },
    { id: 'Unerupted', label: 'لم يبزغ (Unerupted)', color: 'bg-slate-300', code: 'UNERUPTED' },
];

export const PROCEDURE_CATEGORIES = [
    {
        id: 'diagnostic',
        label: 'تشخيصي (Diagnostic)',
        icon: '🔍',
        items: [
            { id: 'D0120', label: 'فحص دوري (Periodic Exam)', price: 100 },
            { id: 'D0140', label: 'فحص طارئ (Limited Exam)', price: 150 },
            { id: 'D0210', label: 'أشعة كاملة (Full Mouth X-Ray)', price: 400 },
            { id: 'D0330', label: 'بانوراما (Panoramic)', price: 250 },
        ]
    },
    {
        id: 'preventive',
        label: 'وقائي (Preventive)',
        icon: '🛡️',
        items: [
            { id: 'D1110', label: 'تنوع (Cleaning - Adult)', price: 300 },
            { id: 'D1120', label: 'تنوع أطفال (Cleaning - Child)', price: 200 },
            { id: 'D1206', label: 'فلورايد (Fluoride)', price: 150 },
            { id: 'D1351', label: 'سيلانت (Sealant)', price: 200, requiresSegments: true }, // Needs Surface
        ]
    },
    {
        id: 'restorative',
        label: 'حشوات (Restorative)',
        icon: '🦷',
        items: [
            { id: 'D2140', label: 'حشو بلاتين 1 سطح (Amalgam 1 Surf)', price: 300, requiresSegments: true },
            { id: 'D2330', label: 'حشو كمبوزيت أمامي (Composite Ant)', price: 400, requiresSegments: true },
            { id: 'D2391', label: 'حشو كمبوزيت خلفي (Composite Post)', price: 450, requiresSegments: true },
            { id: 'D2335', label: 'حشو تجميلي (Cosmetic Filling)', price: 600, requiresSegments: true },
        ]
    },
    {
        id: 'endo',
        label: 'علاج جذور (Endodontic)',
        icon: '⚡',
        items: [
            { id: 'D3310', label: 'حشو عصب أمامي (RCT Anterior)', price: 800, isWholeTooth: true },
            { id: 'D3320', label: 'حشو عصب ضاحك (RCT Premolar)', price: 1000, isWholeTooth: true },
            { id: 'D3330', label: 'حشو عصب خلفي (RCT Molar)', price: 1500, isWholeTooth: true },
            { id: 'D3346', label: 'إعادة حشو عصب (Retreatment)', price: 1800, isWholeTooth: true },
        ]
    },
    {
        id: 'perio',
        label: 'لثة (Periodontic)',
        icon: '🩸',
        items: [
            { id: 'D4341', label: 'تنظيف جيري عميق (Scaling & Root Planing)', price: 500 },
            { id: 'D4910', label: 'متابعة لثة (Perio Maintenance)', price: 250 },
        ]
    },
    {
        id: 'prostho',
        label: 'تركيبات (Prosthodontics)',
        icon: '👑',
        items: [
            { id: 'D2740', label: 'طربوش بورسلين (Crown Porcelain)', price: 1500, isWholeTooth: true },
            { id: 'D2750', label: 'طربوش بورسلين/معدن (PFM)', price: 1200, isWholeTooth: true },
            { id: 'D2790', label: 'طربوش زيركون (Zirconia Crown)', price: 2000, isWholeTooth: true },
            { id: 'D2950', label: 'بناء كور (Core Buildup)', price: 400 },
            { id: 'D6010', label: 'غرسة زراعة (Implant Fixture)', price: 5000, isWholeTooth: true },
        ]
    },
    {
        id: 'surgery',
        label: 'جراحة (Surgery)',
        icon: '💉',
        items: [
            { id: 'D7140', label: 'خلع بسيط (Simple Extraction)', price: 300, isWholeTooth: true },
            { id: 'D7210', label: 'خلع جراحي (Surgical Extraction)', price: 800, isWholeTooth: true },
            { id: 'D7240', label: 'خلع ضرس عقل مدفون (Impaction)', price: 1200, isWholeTooth: true },
        ]
    }
];
