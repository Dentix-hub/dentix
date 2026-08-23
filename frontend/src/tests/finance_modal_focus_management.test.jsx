import { useState } from 'react';
import { describe, expect, it } from 'vitest';
import { fireEvent, render, screen } from '@testing-library/react';

import useModalFocusManagement from '../features/finance/hooks/useModalFocusManagement';

function Harness() {
    const [open, setOpen] = useState(false);
    const dialogRef = useModalFocusManagement(open, () => setOpen(false));

    return (
        <>
            <button type="button" onClick={() => setOpen(true)}>فتح</button>
            {open && (
                <div ref={dialogRef} tabIndex={-1} role="dialog" aria-modal="true" aria-label="اختبار">
                    <button type="button">الأول</button>
                    <button type="button">الأخير</button>
                </div>
            )}
        </>
    );
}

describe('Finance modal focus management', () => {
    it('moves focus inside, traps Tab, closes with Escape, and restores trigger focus', () => {
        render(<Harness />);

        const trigger = screen.getByRole('button', { name: 'فتح' });
        trigger.focus();
        fireEvent.click(trigger);

        const first = screen.getByRole('button', { name: 'الأول' });
        const last = screen.getByRole('button', { name: 'الأخير' });
        expect(document.activeElement).toBe(first);

        last.focus();
        fireEvent.keyDown(document, { key: 'Tab' });
        expect(document.activeElement).toBe(first);

        first.focus();
        fireEvent.keyDown(document, { key: 'Tab', shiftKey: true });
        expect(document.activeElement).toBe(last);

        fireEvent.keyDown(document, { key: 'Escape' });
        expect(screen.queryByRole('dialog')).toBeNull();
        expect(document.activeElement).toBe(trigger);
    });
});
