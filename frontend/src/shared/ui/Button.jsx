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
    const baseStyles = 'inline-flex items-center justify-center rounded-control font-bold transition-colors duration-fast disabled:opacity-50 disabled:cursor-not-allowed';

    const variants = {
        primary: 'bg-primary text-white hover:bg-primary-600 shadow-low',
        secondary: 'bg-surface-subtle text-text-primary hover:bg-surface-hover border border-border',
        outline: 'border border-primary text-primary hover:bg-primary/5',
        ghost: 'text-text-secondary hover:text-primary hover:bg-primary/5',
        danger: 'bg-danger text-white hover:bg-red-600 shadow-low',
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
