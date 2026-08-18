import { isValidElement, useId } from 'react';

const Input = ({
    label,
    help,
    error,
    icon: Icon,
    type = 'text',
    className = '',
    containerClassName = '',
    id,
    required = false,
    ...props
}) => {
    const generatedId = useId();
    const inputId = id || generatedId;
    const helpId = `${inputId}-help`;
    const errorId = `${inputId}-error`;
    const externalDescribedBy = props['aria-describedby'];
    const describedBy = [externalDescribedBy, help ? helpId : null, error ? errorId : null]
        .filter(Boolean)
        .join(' ') || undefined;

    return (
        <div className={`space-y-1.5 ${containerClassName}`}>
            {label && (
                <label htmlFor={inputId} className="block text-type-label text-text-secondary">
                    {label}
                    {required && <span className="ms-1 text-danger" aria-hidden="true">*</span>}
                </label>
            )}

            <div className="relative group">
                {Icon && (
                    <div className="absolute inset-y-0 end-0 pe-3 flex items-center pointer-events-none text-text-muted group-focus-within:text-primary transition-colors duration-fast" aria-hidden="true">
                        {isValidElement(Icon) ? Icon : <Icon size={18} />}
                    </div>
                )}

                <input
                    {...props}
                    id={inputId}
                    type={type}
                    required={required}
                    aria-invalid={error ? 'true' : props['aria-invalid']}
                    aria-describedby={describedBy}
                    className={`
                        w-full rounded-control border bg-input text-text-primary outline-none transition-colors duration-fast
                        placeholder:text-text-muted disabled:bg-disabled disabled:cursor-not-allowed
                        ${Icon ? 'pe-10 ps-3' : 'px-3'}
                        ${error
                            ? 'border-danger focus:border-danger focus:ring-1 focus:ring-danger'
                            : 'border-border hover:border-border-strong focus:border-focus focus:ring-1 focus:ring-focus'
                        }
                        py-2.5
                        ${className}
                    `}
                />
            </div>

            {help && !error && <p id={helpId} className="text-type-caption text-text-muted">{help}</p>}
            {error && <p id={errorId} role="alert" className="text-type-caption text-danger">{error}</p>}
        </div>
    );
};

export default Input;
