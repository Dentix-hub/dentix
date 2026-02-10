import { memo } from 'react';
import { universalToPalmer, toothToNumber } from '@/utils/toothUtils';
// Tooth Shapes defined as SVG paths (Simplified realistic shapes)
const TOOTH_PATHS = {
    // Upper Molar Right (1, 2, 3)
    upperMolarRight: "M10,5 C15,0 35,0 40,5 C45,15 45,35 40,45 C35,50 15,50 10,45 C5,35 5,15 10,5 Z M15,15 L20,20 M30,15 L25,20 M25,25 L25,35",
    upperPremolarRight: "M12,8 C17,3 33,3 38,8 C42,15 42,30 38,40 C33,45 17,45 12,40 C8,30 8,15 12,8 Z M25,15 L25,30",
    upperCanineRight: "M15,10 C20,5 30,5 35,10 C40,20 35,40 25,48 C15,40 10,20 15,10 Z",
    upperIncisorRight: "M10,10 C15,8 35,8 40,10 C42,20 40,40 35,45 C30,48 20,48 15,45 C10,40 8,20 10,10 Z",
    // Upper Left
    upperIncisorLeft: "M10,10 C15,8 35,8 40,10 C42,20 40,40 35,45 C30,48 20,48 15,45 C10,40 8,20 10,10 Z",
    upperCanineLeft: "M15,10 C20,5 30,5 35,10 C40,20 35,40 25,48 C15,40 10,20 15,10 Z",
    upperPremolarLeft: "M12,8 C17,3 33,3 38,8 C42,15 42,30 38,40 C33,45 17,45 12,40 C8,30 8,15 12,8 Z M25,15 L25,30",
    upperMolarLeft: "M10,5 C15,0 35,0 40,5 C45,15 45,35 40,45 C35,50 15,50 10,45 C5,35 5,15 10,5 Z M15,15 L20,20 M30,15 L25,20 M25,25 L25,35",
    // Lower
    lowerMolar: "M10,5 C15,0 35,0 40,5 C45,15 45,35 40,45 C35,50 15,50 10,45 C5,35 5,15 10,5 Z M15,15 L20,20 M30,15 L25,20 M25,25 L25,35",
    lowerPremolar: "M12,8 C17,3 33,3 38,8 C42,15 42,30 38,40 C33,45 17,45 12,40 C8,30 8,15 12,8 Z M25,15 L25,30",
    lowerCanine: "M15,10 C20,5 30,5 35,10 C40,20 35,40 25,48 C15,40 10,20 15,10 Z",
    lowerIncisor: "M15,12 C18,10 32,10 35,12 C36,20 35,35 32,40 C28,42 22,42 18,40 C15,35 14,20 15,12 Z",
};
// --- Palmer Notation Helper ---
const getPalmerLabel = (id, isPediatric) => {
    return universalToPalmer(id, isPediatric);
};
const getToothPath = (id, isPediatric) => {
    if (isPediatric) {
        switch (id) {
            case 'A': return TOOTH_PATHS.upperMolarRight;
            case 'B': return TOOTH_PATHS.upperMolarRight;
            case 'C': return TOOTH_PATHS.upperCanineRight;
            case 'D': return TOOTH_PATHS.upperIncisorRight;
            case 'E': return TOOTH_PATHS.upperIncisorRight;
            case 'F': return TOOTH_PATHS.upperIncisorLeft;
            case 'G': return TOOTH_PATHS.upperIncisorLeft;
            case 'H': return TOOTH_PATHS.upperCanineLeft;
            case 'I': return TOOTH_PATHS.upperMolarLeft;
            case 'J': return TOOTH_PATHS.upperMolarLeft;
            case 'K': return TOOTH_PATHS.lowerMolar;
            case 'L': return TOOTH_PATHS.lowerMolar;
            case 'M': return TOOTH_PATHS.lowerCanine;
            case 'N': return TOOTH_PATHS.lowerIncisor;
            case 'O': return TOOTH_PATHS.lowerIncisor;
            case 'P': return TOOTH_PATHS.lowerIncisor;
            case 'Q': return TOOTH_PATHS.lowerIncisor;
            case 'R': return TOOTH_PATHS.lowerCanine;
            case 'S': return TOOTH_PATHS.lowerMolar;
            case 'T': return TOOTH_PATHS.lowerMolar;
            default: return TOOTH_PATHS.upperMolarRight;
        }
    }
    const n = parseInt(id);
    if (n >= 1 && n <= 3) return TOOTH_PATHS.upperMolarRight;
    if (n >= 4 && n <= 5) return TOOTH_PATHS.upperPremolarRight;
    if (n === 6) return TOOTH_PATHS.upperCanineRight;
    if (n >= 7 && n <= 8) return TOOTH_PATHS.upperIncisorRight;
    if (n >= 9 && n <= 10) return TOOTH_PATHS.upperIncisorLeft;
    if (n === 11) return TOOTH_PATHS.upperCanineLeft;
    if (n >= 12 && n <= 13) return TOOTH_PATHS.upperPremolarLeft;
    if (n >= 14 && n <= 16) return TOOTH_PATHS.upperMolarLeft;
    if (n >= 17 && n <= 19) return TOOTH_PATHS.lowerMolar;
    if (n >= 20 && n <= 21) return TOOTH_PATHS.lowerPremolar;
    if (n === 22) return TOOTH_PATHS.lowerCanine;
    if (n >= 23 && n <= 26) return TOOTH_PATHS.lowerIncisor;
    if (n === 27) return TOOTH_PATHS.lowerCanine;
    if (n >= 28 && n <= 29) return TOOTH_PATHS.lowerPremolar;
    if (n >= 30 && n <= 32) return TOOTH_PATHS.lowerMolar;
    return TOOTH_PATHS.upperMolarRight;
};
const STATUS_STYLES = {
    Healthy: { fill: '#ffffff', stroke: '#94a3b8' },
    Decayed: { fill: '#fecaca', stroke: '#ef4444' },
    Filled: { fill: '#bfdbfe', stroke: '#3b82f6' },
    Missing: { fill: '#f1f5f9', stroke: '#e2e8f0', opacity: 0.3 },
    Crown: { fill: '#fef08a', stroke: '#eab308' },
    RootCanal: { fill: '#e9d5ff', stroke: '#a855f7' },
};
const SVGTooth = memo(function SVGTooth({ number, status, onClick, isPediatric }) {
    const path = getToothPath(number, isPediatric);
    const condition = status?.condition || 'Healthy';
    const style = STATUS_STYLES[condition];
    const palmerLabel = getPalmerLabel(number, isPediatric);
    return (
        <div
            className="flex flex-col items-center gap-1 cursor-pointer group relative"
            onClick={() => onClick(number)}
        >
            <svg width="50" height="60" viewBox="0 0 50 60" className="transition-transform transform group-hover:scale-110 duration-200">
                <path
                    d={path}
                    fill={style.fill}
                    stroke={style.stroke}
                    strokeWidth="2"
                    className="transition-colors duration-300"
                />
                {condition === 'Decayed' && <circle cx="25" cy="25" r="5" fill="#ef4444" />}
            </svg>
            <div className="flex flex-col items-center absolute -bottom-6">
                {/* Palmer Bracket Visual Aid - Optional but helpful */}
                <span className="text-sm font-bold text-slate-600 font-mono border-t border-slate-300 pt-1 w-full text-center">
                    {palmerLabel}
                </span>
            </div>
        </div>
    );
});
export default memo(function DentalChartSVG({ teethStatus, onToothClick, isPediatric }) {
    // Config - Universal IDs
    // (Updated below for visual layout)
    // VISUAL LAYOUT UPDATED:
    // Screen Left = Patient Left (Mirror View / User Request)
    // Screen Right = Patient Right
    // Row 1 (Upper): [Back Left...Front Left] | [Front Right...Back Right]
    // UL8...UL1 | UR1...UR8
    // Row 2 (Lower): [Back Left...Front Left] | [Front Right...Back Right]
    // LL8...LL1 | LR1...LR8
    // Arrays must be ordered to match the visual flow (Left -> Right)
    // Upper Left: 16 (Back) -> 9 (Front)
    const adultUpperLeft = [16, 15, 14, 13, 12, 11, 10, 9];
    // Upper Right: 8 (Front) -> 1 (Back)
    const adultUpperRight = [8, 7, 6, 5, 4, 3, 2, 1];
    // Lower Left: 17 (Back) -> 24 (Front)
    const adultLowerLeft = [17, 18, 19, 20, 21, 22, 23, 24];
    // Lower Right: 25 (Front) -> 32 (Back)
    const adultLowerRight = [25, 26, 27, 28, 29, 30, 31, 32];
    // Pediatric
    // UL: J (Back) -> F (Front)
    const childUpperLeft = ['J', 'I', 'H', 'G', 'F'];
    // UR: E (Front) -> A (Back)
    const childUpperRight = ['E', 'D', 'C', 'B', 'A'];
    // LL: K (Back) -> O (Front)
    const childLowerLeft = ['K', 'L', 'M', 'N', 'O'];
    // LR: P (Front) -> T (Back)
    const childLowerRight = ['P', 'Q', 'R', 'S', 'T'];
    const upperRight = isPediatric ? childUpperRight : adultUpperRight;
    const upperLeft = isPediatric ? childUpperLeft : adultUpperLeft;
    const lowerRight = isPediatric ? childLowerRight : adultLowerRight;
    const lowerLeft = isPediatric ? childLowerLeft : adultLowerLeft;
    return (
        <div className="bg-slate-50 p-8 rounded-3xl shadow-inner overflow-x-auto text-center">
            <h3 className="text-lg font-bold mb-8 text-slate-700">
                {isPediatric ? 'مخطط الأسنان (أطفال)' : 'مخطط الأسنان (بالغين)'}
                <span className="block text-xs text-slate-400 font-normal mt-1">Palmer Notation</span>
            </h3>
            <div className="inline-flex flex-col gap-16 min-w-[700px]">
                {/* Upper Arch */}
                <div className="flex justify-center gap-1 relative">
                    {/* Cross line for Palmer */}
                    <div className="absolute inset-y-0 left-1/2 w-0.5 bg-slate-300"></div>
                    <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-slate-300"></div>
                    {/* Left Slot: Patient Left (UL) */}
                    <div className="flex gap-1 px-4 pb-4">
                        {upperLeft.map(n => (
                            <SVGTooth key={n} number={n} status={teethStatus[toothToNumber(n)]} onClick={onToothClick} isPediatric={isPediatric} />
                        ))}
                    </div>
                    <div className="w-0.5"></div>
                    {/* Right Slot: Patient Right (UR) */}
                    <div className="flex gap-1 px-4 pb-4">
                        {upperRight.map(n => (
                            <SVGTooth key={n} number={n} status={teethStatus[toothToNumber(n)]} onClick={onToothClick} isPediatric={isPediatric} />
                        ))}
                    </div>
                </div>
                {/* Lower Arch */}
                <div className="flex justify-center gap-1 relative">
                    {/* Cross line for Palmer */}
                    <div className="absolute inset-y-0 left-1/2 w-0.5 bg-slate-300"></div>
                    <div className="absolute top-0 left-0 right-0 h-0.5 bg-slate-300"></div>
                    {/* Left Slot: Patient Left (LL) */}
                    <div className="flex gap-1 px-4 pt-4">
                        {lowerLeft.map(n => (
                            <SVGTooth key={n} number={n} status={teethStatus[toothToNumber(n)]} onClick={onToothClick} isPediatric={isPediatric} />
                        ))}
                    </div>
                    <div className="w-0.5"></div>
                    {/* Right Slot: Patient Right (LR) */}
                    <div className="flex gap-1 px-4 pt-4">
                        {lowerRight.map(n => (
                            <SVGTooth key={n} number={n} status={teethStatus[toothToNumber(n)]} onClick={onToothClick} isPediatric={isPediatric} />
                        ))}
                    </div>
                </div>
            </div>
            {/* Legend */}
            <div className="flex flex-wrap gap-6 mt-12 justify-center text-sm border-t border-slate-200 pt-6">
                {Object.entries(STATUS_STYLES).map(([status, style]) => (
                    <div key={status} className="flex items-center gap-2">
                        <div className="w-5 h-5 rounded-full border shadow-sm" style={{ backgroundColor: style.fill, borderColor: style.stroke, borderWidth: 2 }} />
                        <span className="font-medium text-slate-600">
                            {status === 'Healthy' ? 'سليم' :
                                status === 'Decayed' ? 'تسوس' :
                                    status === 'Filled' ? 'حشو' :
                                        status === 'Missing' ? 'مخلوع' :
                                            status === 'Crown' ? 'طربوش' : 'عصب'}
                        </span>
                    </div>
                ))}
            </div>
        </div>
    );
});
