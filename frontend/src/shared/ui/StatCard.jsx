
const StatCard = ({ icon: Icon, title, value, subtext, label, color = "indigo", onClick }) => (
    <div
        onClick={(e) => {
            if (onClick) {
                onClick(e);
            }
        }}
        className={`relative overflow-hidden bg-surface dark:bg-surface/50 p-6 rounded-[2rem] border border-border shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 group ${onClick ? 'cursor-pointer active:scale-95' : ''}`}
    >
        <div className={`absolute top-0 right-0 w-32 h-32 bg-${color}-50 dark:bg-${color}-900/20 rounded-bl-[100px] transition-all group-hover:scale-110 pointer-events-none`} />
        <div className="relative z-10 flex justify-between items-start">
            <div>
                <h3 className="text-slate-500 dark:text-slate-400 text-sm font-semibold mb-1">{title || label}</h3>
                <p className={`text-3xl font-black text-slate-800 dark:text-white mb-2`}>{value}</p>
                {subtext && <p className={`text-xs font-medium px-2 py-1 rounded-full bg-${color}-50 dark:bg-${color}-900/30 text-${color}-600 dark:text-${color}-400 inline-block`}>{subtext}</p>}
            </div>
            <div className={`p-3 bg-${color}-100 dark:bg-${color}-900/50 rounded-2xl text-${color}-600 dark:text-${color}-400 group-hover:rotate-12 transition-transform`}>
                <Icon size={28} strokeWidth={2} />
            </div>
        </div>
    </div>
);

export default StatCard;