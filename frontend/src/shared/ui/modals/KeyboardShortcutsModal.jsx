import Modal from '../Modal';
import { useTranslation } from 'react-i18next';
import { ArrowUp, ArrowDown } from 'lucide-react';

const ShortcutItem = ({ keys, description }) => (
    <div className="flex items-center justify-between py-3 border-b border-border/50 last:border-0">
        <span className="text-sm font-bold text-slate-600 dark:text-slate-400">{description}</span>
        <div className="flex gap-1.5">
            {keys.map((key, i) => (
                <kbd key={i} className="px-2 py-1 bg-slate-100 dark:bg-slate-800 border border-slate-200 dark:border-white/10 rounded-lg text-[10px] font-black shadow-sm text-slate-700 dark:text-slate-200 uppercase tracking-widest min-w-[24px] text-center">
                    {key}
                </kbd>
            ))}
        </div>
    </div>
);

const KeyboardShortcutsModal = ({ isOpen, onClose }) => {
    const { t } = useTranslation();

    const shortcuts = [
        {
            title: t('shortcuts.global', 'Global'),
            items: [
                { keys: ['Ctrl', 'K'], description: t('shortcuts.open_command_palette', 'Open Command Palette') },
                { keys: ['?'], description: t('shortcuts.show_shortcuts', 'Show Keyboard Shortcuts') },
                { keys: ['ESC'], description: t('shortcuts.close_modal', 'Close Modal / Cancel') }
            ]
        },
        {
            title: t('shortcuts.navigation', 'Navigation'),
            items: [
                { keys: [<ArrowUp key="up" size={12} />, <ArrowDown key="down" size={12} />], description: t('shortcuts.navigate_results', 'Navigate Results') },
                { keys: ['↵'], description: t('shortcuts.select_item', 'Select Item') }
            ]
        }
    ];

    return (
        <Modal 
            isOpen={isOpen} 
            onClose={onClose} 
            title={t('shortcuts.title', 'Keyboard Shortcuts')}
            size="md"
        >
            <div className="space-y-8">
                {shortcuts.map((group, i) => (
                    <div key={i}>
                        <h4 className="text-[10px] font-extrabold text-primary uppercase tracking-[0.2em] mb-4">{group.title}</h4>
                        <div className="bg-slate-50/50 dark:bg-white/5 rounded-2xl px-4 border border-border/50">
                            {group.items.map((item, j) => (
                                <ShortcutItem key={j} {...item} />
                            ))}
                        </div>
                    </div>
                ))}
            </div>
        </Modal>
    );
};

export default KeyboardShortcutsModal;
