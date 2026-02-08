import React from 'react';

const Card = ({ children, className = '', title, subtitle, actions }) => {
    return (
        <div className={`bg-surface backdrop-blur-xl border border-border shadow-sm rounded-2xl overflow-hidden ${className}`}>
            {(title || actions) && (
                <div className="px-6 py-5 border-b border-border/50 flex justify-between items-center bg-surface-hover/30">
                    <div>
                        {title && <h3 className="text-lg font-bold text-text-primary">{title}</h3>}
                        {subtitle && <p className="text-sm text-text-secondary mt-1">{subtitle}</p>}
                    </div>
                    {actions && <div className="flex items-center gap-2">{actions}</div>}
                </div>
            )}
            <div className="p-6">
                {children}
            </div>
        </div>
    );
};

export default Card;
