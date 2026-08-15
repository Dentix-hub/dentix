/**
 * Currency and Money formatting utility.
 * Centralizes Intl.NumberFormat usage across DENTIX Finance V2.
 */

export const formatMoney = (amount, options = {}) => {
    const {
        currency = 'EGP',
        locale = 'ar-EG',
        minimumFractionDigits = 0,
        maximumFractionDigits = 2,
        compact = false,
        showSymbol = true,
    } = options;

    const numericAmount = Number(amount) || 0;

    try {
        if (compact) {
            const formatter = new Intl.NumberFormat(locale, {
                notation: 'compact',
                compactDisplay: 'short',
                maximumFractionDigits: 1,
            });
            const formatted = formatter.format(numericAmount);
            return showSymbol ? `${formatted} ${currency}` : formatted;
        }

        const formatter = new Intl.NumberFormat(locale, {
            minimumFractionDigits,
            maximumFractionDigits,
        });

        const formatted = formatter.format(numericAmount);
        return showSymbol ? `${formatted} ${currency}` : formatted;
    } catch (e) {
        // Fallback formatting if Intl fails
        const rounded = numericAmount.toLocaleString();
        return showSymbol ? `${rounded} ${currency}` : rounded;
    }
};

export const getCurrencySymbol = (currency = 'EGP') => {
    switch (currency.toUpperCase()) {
        case 'EGP':
            return 'ج.م';
        case 'USD':
            return '$';
        case 'SAR':
            return 'ر.س';
        case 'AED':
            return 'د.إ';
        default:
            return currency;
    }
};
