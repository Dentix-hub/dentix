import { useCallback, useRef } from 'react';

export function usePatientTouchScrollGuard() {
    const touchStartPosRef = useRef({ x: 0, y: 0, time: 0 });
    const isTouchScrollingRef = useRef(false);

    const handleTouchStart = useCallback((e) => {
        if (e.touches && e.touches.length > 0) {
            touchStartPosRef.current = {
                x: e.touches[0].clientX,
                y: e.touches[0].clientY,
                time: Date.now(),
            };
            isTouchScrollingRef.current = false;
        }
    }, []);

    const handleTouchMove = useCallback((e) => {
        if (e.touches && e.touches.length > 0) {
            const dx = e.touches[0].clientX - touchStartPosRef.current.x;
            const dy = e.touches[0].clientY - touchStartPosRef.current.y;
            if (Math.hypot(dx, dy) > 8) {
                isTouchScrollingRef.current = true;
            }
        }
    }, []);

    const handleTouchEnd = useCallback(() => {
        if (isTouchScrollingRef.current) {
            setTimeout(() => {
                isTouchScrollingRef.current = false;
            }, 250);
        }
    }, []);

    return {
        touchStartPosRef,
        isTouchScrollingRef,
        handleTouchStart,
        handleTouchMove,
        handleTouchEnd,
    };
}
