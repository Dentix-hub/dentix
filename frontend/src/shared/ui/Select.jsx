import { useId } from 'react';
import { ChevronDown } from 'lucide-react';

export default function Select({
    label,
    help,
    value,
    onChange,
    options = [],
    placeholder = 'Select an option',
    containerClassName = '',
    className = '',
    disabled = false,
    error,
    required = false,
    id,
    ...props
}) {
    const generatedId = useId();
    const selectId = id || generatedId;
    const helpId = `${selectId}-help`;
    const errorId = `${selectId}-error`;
    const externalDescribedBy = props['aria-describedby'];
    const describedBy = [externalDescribedBy, help ? helpId : null, error ? errorId : null]
        .filter(Boolean)
        .join(' ') || undefined;

    return (
        <div className={`space-y-1.5 ${containerClassName}`}>
            {label && (
                <label htmlFor={selectId} className="block text-type-label text-text-secondary">
                    {label}
                    {required && <span className="ms-1 text-danger" aria-hidden="true">*</span>}
                </label>
            )}
            <div className="relative">
                <select
                    {...props}
                    id={selectId}
                    value={value}
                    onChange={onChange}
                    disabled={disabled}
                    required={required}
                    aria-invalid={error ? 'true' : props['aria-invalid']}
                    aria-describedby={describedBy}
                    className={`w-full rounded-control border ${error ? 'border-danger focus:border-danger focus:ring-danger' : 'border-border hover:border-border-strong focus:border-focus focus:ring-focus'} bg-input text-text-primary p-2.5 pe-10 outline-none focus:ring-1 transition-colors duration-fast disabled:bg-disabled disabled:opacity-70 disabled:cursor-not-allowed appearance-none ${className}`}
                >
                    <option value="">{placeholder}</option>
                    {options.map((option) => (
                        <option key={option.value} value={option.value}>
                            {option.label}
                        </option>
                    ))}
                </select>
                <ChevronDown className="absolute end-3 top-1/2 -translate-y-1/2 w-4 h-4 text-text-muted pointer-events-none" aria-hidden="true" />
            </div>
            {help && !error && <p id={helpId} className="text-type-caption text-text-muted">{help}</p>}
            {error && <p id={errorId} role="alert" className="text-type-caption text-danger">{error}</p>}
        </div>
    );
}
