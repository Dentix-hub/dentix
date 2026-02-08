import React from 'react';

const Input = ({
    label,
    error,
    icon: Icon,
    type = 'text',
    className = '',
    containerClassName = '',
    ...props
}) => {
    return (
        <div className={`space-y-1.5 ${containerClassName}`}>
            {label && (
                <label className="block text-sm font-bold text-text-secondary">
                    {label}
                </label>
            )}

            <div className="relative group">
                {Icon && (
                    <div className="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-slate-400 group-focus-within:text-primary transition-colors">
                        <Icon size={18} />
                    </div>
                )}

                <input
                    type={type}
                    className={`
                        w-full rounded-xl border bg-input text-text-primary outline-none transition-all duration-200
                        placeholder:text-slate-400
                        ${Icon ? 'pr-10 pl-3' : 'px-3'}
                        ${error
                            ? 'border-red-500 focus:border-red-500 focus:ring-1 focus:ring-red-500'
                            : 'border-border focus:border-primary focus:ring-1 focus:ring-primary hover:border-slate-300 dark:hover:border-slate-600'
                        }
                        py-2.5
                        ${className}
                    `}
                    {...props}
                />
            </div>

            {error && (
                <p className="text-xs text-red-500 font-medium animate-in slide-in-from-top-1">
                    {error}
                </p>
            )}
        </div>
    );
};

export default Input;
