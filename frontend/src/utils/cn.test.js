import { describe, it, expect } from 'vitest';
import { cn } from './cn';

describe('cn utility', () => {
    it('combines ordinary non-conflicting class names', () => {
        expect(cn('btn', 'btn-primary', 'text-sm')).toBe('btn btn-primary text-sm');
        expect(cn('flex items-center justify-between')).toBe('flex items-center justify-between');
    });

    it('ignores falsy conditional inputs such as false, null, and undefined', () => {
        expect(cn('base-class', false, null, undefined, '')).toBe('base-class');
        expect(cn(false && 'hidden', null, undefined, 'active')).toBe('active');
        expect(cn(true && 'visible', false && 'hidden')).toBe('visible');
    });

    it('supports array and object inputs accepted by clsx', () => {
        expect(cn(['btn', 'btn-large'])).toBe('btn btn-large');
        expect(cn({ active: true, disabled: false, highlighted: true })).toBe('active highlighted');
        expect(cn(['p-4', { 'bg-red-500': true, 'text-white': false }], 'shadow-md')).toBe('p-4 bg-red-500 shadow-md');
    });

    it('resolves conflicting Tailwind classes with the later class winning', () => {
        expect(cn('px-2', 'px-4')).toBe('px-4');
        expect(cn('p-2 p-4', 'p-6')).toBe('p-6');
        expect(cn('text-red-500', 'text-blue-500')).toBe('text-blue-500');
        expect(cn('w-full', 'w-auto')).toBe('w-auto');
    });

    it('resolves variant conflicts independently, such as conflicting hover classes', () => {
        expect(cn('hover:bg-red-500', 'hover:bg-blue-500')).toBe('hover:bg-blue-500');
        expect(cn('focus:ring-1', 'focus:ring-2')).toBe('focus:ring-2');
    });

    it('preserves unrelated responsive and state variants', () => {
        expect(cn('p-2', 'md:p-4', 'lg:p-6')).toBe('p-2 md:p-4 lg:p-6');
        expect(cn('hover:text-red-500', 'focus:text-red-500', 'text-black')).toBe('hover:text-red-500 focus:text-red-500 text-black');
        expect(cn('text-sm', 'md:text-base', 'text-lg')).toBe('md:text-base text-lg');
    });
});
