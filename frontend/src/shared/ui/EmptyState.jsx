import React from 'react';
import { motion } from 'framer-motion';
import { Ghost } from 'lucide-react';

const EmptyState = ({
    title,
    description,
    icon: Icon = Ghost,
    action,
    className = ''
}) => {
    return (
        <motion.div 
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            className={`flex flex-col items-center justify-center py-20 px-6 text-center bg-white/40 dark:bg-slate-900/40 backdrop-blur-md border border-dashed border-slate-200 dark:border-slate-800 rounded-[3rem] ${className}`}
        >
            <div className="relative mb-8">
                <div className="absolute inset-0 bg-primary/20 blur-3xl rounded-full animate-pulse" />
                <div className="relative bg-gradient-to-br from-slate-50 to-slate-200 dark:from-slate-800 dark:to-slate-900 p-8 rounded-[2rem] shadow-xl ring-1 ring-white/50 dark:ring-white/10">
                    <Icon size={48} className="text-primary/80" />
                </div>
            </div>
            
            <h3 className="text-2xl font-black text-slate-800 dark:text-slate-100 mb-3 tracking-tight">
                {title}
            </h3>
            
            <p className="text-slate-500 dark:text-slate-400 max-w-sm mb-8 text-base font-medium leading-relaxed">
                {description}
            </p>
            
            {action && (
                <motion.div 
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                >
                    {action}
                </motion.div>
            )}
        </motion.div>
    );
};

export default EmptyState;
