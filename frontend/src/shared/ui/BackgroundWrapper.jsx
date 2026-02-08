import React from 'react';

const BackgroundWrapper = () => {
    return (
        <div className="fixed inset-0 w-full h-full -z-50 pointer-events-none bg-slate-50 dark:bg-[#0b1121] overflow-hidden">
            {/* 
                CALM & COMFORT PALETTE (Eye-Resting Colors)
                Focus: Serenity, Trust, Cleanliness.
                Colors: Sky Blue (Tailwind Sky-100/200), Sage/Teal (Tailwind Teal-100/200), Slate (Neutral).
                No Pink, Purple, or high-saturation hues.
            */}

            {/* Top Left: Gentle Sky Blue (Trust & Calm) */}
            <div
                className="absolute top-[-10%] left-[-10%] w-[70%] h-[70%] rounded-full bg-sky-200/40 dark:bg-sky-900/10 blur-[120px]"
            />

            {/* Bottom Right: Soft Sage/Teal (Nature & Balance) */}
            <div
                className="absolute bottom-[-10%] right-[-10%] w-[70%] h-[70%] rounded-full bg-teal-100/40 dark:bg-teal-900/10 blur-[120px]"
            />

            {/* Top Right Accent: Very Light Slate/Grey (Neutrality) */}
            <div
                className="absolute top-[20%] right-[10%] w-[40%] h-[40%] rounded-full bg-slate-200/30 dark:bg-slate-800/20 blur-[100px]"
            />

            {/* Center Wash - Ensures text readability remains perfect */}
            <div className="absolute inset-0 bg-white/40 dark:bg-black/20 backdrop-blur-[1px]" />
        </div>
    );
};

export default BackgroundWrapper;
