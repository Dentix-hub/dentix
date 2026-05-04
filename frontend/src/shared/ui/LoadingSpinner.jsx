/**
 * LoadingSpinner — Branded dental-themed loading animation.
 * Variants: 'page' (full page), 'inline' (small inline), 'shimmer' (content placeholder)
 */
export default function LoadingSpinner({ variant = 'page', className = '' }) {
    if (variant === 'shimmer') {
        return (
            <div className={`space-y-4 ${className}`}>
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded-full w-3/4 animate-shimmer" />
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded-full w-1/2 animate-shimmer" style={{ animationDelay: '0.15s' }} />
                <div className="h-4 bg-slate-200 dark:bg-slate-700 rounded-full w-5/6 animate-shimmer" style={{ animationDelay: '0.3s' }} />
            </div>
        );
    }

    if (variant === 'inline') {
        return (
            <div className={`inline-flex items-center justify-center ${className}`}>
                <div className="relative w-5 h-5">
                    <div className="absolute inset-0 rounded-full border-2 border-primary/20" />
                    <div className="absolute inset-0 rounded-full border-2 border-transparent border-t-primary animate-spin" />
                </div>
            </div>
        );
    }

    // Default: 'page' — branded tooth pulse animation
    return (
        <div className={`flex flex-col items-center justify-center min-h-[200px] gap-4 ${className}`}>
            <div className="relative">
                {/* Outer glow ring */}
                <div className="absolute inset-0 rounded-full bg-primary/10 animate-ping" style={{ animationDuration: '2s' }} />
                {/* Tooth icon container */}
                <div className="relative w-14 h-14 bg-gradient-to-br from-primary/10 to-primary/5 dark:from-primary/20 dark:to-primary/10 rounded-2xl flex items-center justify-center shadow-lg shadow-primary/10">
                    {/* Animated tooth SVG */}
                    <svg
                        viewBox="0 0 24 24"
                        fill="none"
                        className="w-7 h-7 text-primary animate-pulse"
                        style={{ animationDuration: '1.5s' }}
                    >
                        <path
                            d="M12 2C9.5 2 7.5 3.5 7 5.5C6.5 7.5 5 8 4 9.5C3 11 3.5 13 4.5 14.5C5.5 16 6 18 6.5 19.5C7 21 8 22 9 22C10 22 10.5 21 11 19.5C11.3 18.5 11.6 17.5 12 17.5C12.4 17.5 12.7 18.5 13 19.5C13.5 21 14 22 15 22C16 22 17 21 17.5 19.5C18 18 18.5 16 19.5 14.5C20.5 13 21 11 20 9.5C19 8 17.5 7.5 17 5.5C16.5 3.5 14.5 2 12 2Z"
                            fill="currentColor"
                            fillOpacity="0.15"
                            stroke="currentColor"
                            strokeWidth="1.5"
                            strokeLinecap="round"
                            strokeLinejoin="round"
                        />
                    </svg>
                </div>
            </div>
            {/* Loading dots */}
            <div className="flex gap-1.5">
                {[0, 1, 2].map((i) => (
                    <div
                        key={i}
                        className="w-1.5 h-1.5 rounded-full bg-primary/60"
                        style={{
                            animation: 'pulse 1.2s ease-in-out infinite',
                            animationDelay: `${i * 0.15}s`,
                        }}
                    />
                ))}
            </div>
        </div>
    );
}
