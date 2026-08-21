export function shouldLoadCommandPaletteData({ isOpen, isSuperAdmin }) {
    return Boolean(isOpen && !isSuperAdmin);
}
