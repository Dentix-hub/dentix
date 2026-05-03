import React from 'react';
import { ChevronDown } from 'lucide-react';

export default function Select({
    label,
    value,
    onChange,
    options = [],
    placeholder = 'Select an option',
    containerClassName = '',
    className = '',
    disabled = false,
    error,
    required = false,
    ...props
}) {
    return (
        <div className={`space-y-1.5 ${containerClassName}`}>
            {label && (
                <label className="block text-sm font-medium text-text-secondary">
                    {label}
                    {required && <span className="text-red-500 ml-1">*</span>}
                </label>
            )}
            <div className="relative">
                <select
                    value={value}
                    onChange={onChange}
                    disabled={disabled}
                    className={`w-full rounded-xl border ${error ? 'border-red-300 focus:border-red-500 focus:ring-red-500' : 'border-border focus:border-primary focus:ring-primary'} bg-input text-text-primary p-2.5 pr-10 outline-none focus:ring-1 transition-all disabled:opacity-50 disabled:cursor-not-allowed appearance-none ${className}`}
                    {...props}
                >
                    <option value="">{placeholder}</option>
                    {options.map((option) => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
                <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-secondary pointer-events-none" />
            </div>
            {error && <p className="text-sm text-red-500">{error}</p>}
        </div>
    );
}

