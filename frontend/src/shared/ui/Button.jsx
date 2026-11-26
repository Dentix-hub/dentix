import { isValidElement } from 'react';
import { Loader2 } from 'lucide-react';

const Button = ({
    children,
    variant = 'primary',
    size = 'md',
    isLoading = false,
    disabled = false,
    icon: Icon,
    className = '',
    onClick,
    type = 'button',
    ...props
}) => {
    const baseStyles = 'inline-flex items-center justify-center rounded-control font-bold transition-colors duration-fast focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-offset-2 focus-visible:ring-offset-surface disabled:opacity-50 disabled:cursor-not-allowed';

    const variants = {
        primary: 'bg-primary-700 text-white hover:bg-primary-800 focus-visible:ring-primary-700 dark:focus-visible:ring-primary-400 shadow-low',
        secondary: 'bg-surface-subtle text-text-primary hover:bg-surface-hover border border-border focus-visible:ring-primary-700 dark:focus-visible:ring-primary-400',
        outline: 'border border-primary-700 text-primary-700 hover:bg-primary-50 hover:text-primary-800 dark:border-primary-400 dark:text-primary-300 dark:hover:bg-primary-950 dark:hover:text-primary-200 focus-visible:ring-primary-700 dark:focus-visible:ring-primary-400',
        ghost: 'text-text-secondary hover:text-primary-700 hover:bg-primary-50 dark:hover:text-primary-300 dark:hover:bg-primary-950 focus-visible:ring-primary-700 dark:focus-visible:ring-primary-400',
        danger: 'bg-red-700 text-white hover:bg-red-800 focus-visible:ring-red-700 dark:focus-visible:ring-red-400 shadow-low',
    };

    const sizes = {
        sm: 'px-3 py-1.5 text-xs',
        md: 'px-5 py-2.5 text-sm',
        lg: 'px-6 py-3.5 text-base',
    };

    return (
        <button
            type={type}
            className={`${baseStyles} ${variants[variant] || variants.primary} ${sizes[size] || sizes.md} ${className}`}
            onClick={onClick}
            disabled={disabled || isLoading}
            aria-busy={isLoading || undefined}
            {...props}
        >
            {isLoading ? (
                <Loader2 className="me-2 h-4 w-4 animate-spin motion-reduce:animate-none" aria-hidden="true" />
            ) : Icon ? (
                isValidElement(Icon) ? (
                    <span className="me-2" aria-hidden="true">{Icon}</span>
                ) : (
                    <Icon className={`me-2 ${size === 'sm' ? 'h-3 w-3' : 'h-4 w-4'}`} aria-hidden="true" />
                )
            ) : null}
            {children}
        </button>
    );
};

export default Button;
