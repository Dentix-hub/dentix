import { useMemo, useState } from 'react';
import { Badge, IconButton, Input } from '@/shared/ui';
import { X, Check } from 'lucide-react';
import { cn } from '@/utils/cn';
export function SmartMaterialRow({
    material,
    stockInfo,
    onChange,
    onRemove,
    patientId,
    onRefresh
}) {
    const [isDisposing, setIsDisposing] = useState(false);
    // Check if this is a divisible material based on unit
    const isDivisible = ['ml', 'g', 'cm'].includes(material.unit?.toLowerCase());
    // Generate quick amounts based on unit
    const quickAmounts = useMemo(() => {
        // For divisible materials, these are RELATIVE WEIGHTS (not actual grams)
        if (isDivisible) {
            return [
                { value: 0.1, label: '0.1' },
                { value: 0.25, label: '¼' },
                { value: 0.5, label: '½' },
                { value: 1, label: '1' }
            ];
        } else {
            return [
                { value: 1, label: '1' },
                { value: 2, label: '2' },
                { value: 3, label: '3' },
                { value: 5, label: '5' }
            ];
        }
    }, [isDivisible]);
    const [mode, setMode] = useState(() => {
        // Auto-detect mode: If quantity matches a quick amount, use 'quick', else 'custom'
        const isQuick = quickAmounts.some(q => q.value === material.quantity);
        return isQuick ? 'quick' : 'custom';
    });
    // Stock status - now uses has_active_session from backend
    const stockStatus = useMemo(() => {
        if (!stockInfo) return 'unknown';
        // Material has active session = virtual consumption, always OK
        if (stockInfo.has_active_session) return 'session_active';
        if (stockInfo.available === 0) return 'out';
        if (stockInfo.available < material.quantity) return 'insufficient';
        if (stockInfo.available < material.quantity * 2) return 'low';
        return 'ok';
    }, [stockInfo, material.quantity]);
    const StockStatusBadge = ({ status, stockInfo }) => {
        switch (status) {
            case 'session_active':
                return <Badge variant="success" className="bg-green-100 text-green-700">✓ جلسة مفتوحة</Badge>;
            case 'out':
                return (
                    <div className="flex flex-col gap-1">
                        <Badge variant="destructive">⚠️ غير متاح</Badge>
                        <span className="text-xs text-red-600 font-medium">
                            💡 يجب فتح جلسة من صفحة المخزون
                        </span>
                    </div>
                );
            case 'insufficient': return <Badge variant="warning">غير كافي</Badge>;
            case 'low': return <Badge variant="warning" className="bg-yellow-100 text-yellow-800">منخفض</Badge>;
            case 'ok': return <Badge variant="success">متوفر</Badge>;
            default: return <Badge variant="secondary">تحقق...</Badge>;
        }
    };
    return (
        <div className={cn(
            "bg-white border-2 rounded-xl p-4 transition-all",
            stockStatus === 'out' ? 'border-red-200 bg-red-50' :
                stockStatus === 'session_active' ? 'border-green-200 bg-green-50/30' :
                    'border-gray-200 hover:border-primary/30'
        )}>
            <div className="flex items-start gap-4">
                {/* Material Info */}
                <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                        <h4 className="font-bold text-lg truncate text-slate-800">
                            {material.material_name || material.name || material.materialName}
                        </h4>
                        {(!material.is_manual && !material.is_manual_override) && (
                            <Badge variant="primary" size="sm" className="bg-blue-100 text-blue-700 hover:bg-blue-200">
                                ✨ مقترح
                            </Badge>
                        )}
                    </div>
                    {/* Suggestion Reason */}
                    {material.reason && material.suggested && (
                        <p className="text-sm text-gray-500 mb-2 flex items-center gap-1">
                            💡 {material.reason}
                            {material.confidence && (
                                <span className="text-xs opacity-70">
                                    ({Math.round(material.confidence * 100)}%)
                                </span>
                            )}
                        </p>
                    )}
                    {/* Stock Status */}
                    <div className="flex items-center gap-3 flex-wrap mt-2">
                        <StockStatusBadge status={stockStatus} stockInfo={stockInfo} />
                        {stockInfo && stockStatus !== 'session_active' && (
                            <span className="text-sm text-gray-600">
                                المتوفر: <strong className="font-mono">{stockInfo.available} {isDivisible ? material.unit : 'وحدة'}</strong>
                            </span>
                        )}
                        {stockInfo && stockStatus === 'session_active' && (
                            <div className="flex flex-col gap-1">
                                <span className="text-sm text-green-700 font-bold flex items-center gap-1">
                                    استهلاك افتراضي (جلسة نشطة)
                                    {stockInfo.material_type === 'REUSABLE' && (
                                        <Badge variant="success" className="bg-green-600 text-white animate-pulse">
                                            استخدام: {stockInfo.current_uses + 1}
                                        </Badge>
                                    )}
                                </span>
                                {stockInfo.material_type === 'REUSABLE' && (
                                    <button 
                                        onClick={async () => {
                                            if (window.confirm('هل أنت متأكد من إتلاف هذه الأداة؟ سيتم حساب التكلفة النهائية.')) {
                                                setIsDisposing(true);
                                                try {
                                                    await api.post(`/api/v1/inventory/sessions/${stockInfo.session_id}/close`, {
                                                        reason: 'Manual Disposal during treatment'
                                                    });
                                                    toast.success("تم إتلاف الأداة بنجاح");
                                                    onRefresh?.();
                                                } catch (err) {
                                                    toast.error("فشل إتلاف الأداة");
                                                } finally {
                                                    setIsDisposing(false);
                                                }
                                            }
                                        }}
                                        disabled={isDisposing}
                                        className="text-[10px] text-red-600 font-bold hover:underline text-right"
                                    >
                                        {isDisposing ? 'جاري الإتلاف...' : '⚠️ إتلاف الأداة الآن (أصبحت غير صالحة)'}
                                    </button>
                                )}
                            </div>
                        )}
                    </div>
                </div>
                {/* Quantity Selector */}
                <div className="flex-shrink-0">
                    {mode === 'quick' ? (
                        <div className="space-y-2">
                            <div className="grid grid-cols-4 gap-1 min-w-[200px]">
                                {quickAmounts.map(({ value, label }) => (
                                    <button
                                        key={value}
                                        type="button"
                                        onClick={() => onChange({ ...material, quantity: value })}
                                        className={cn(
                                            'px-2 py-2 rounded-lg border font-bold transition-all text-sm',
                                            material.quantity === value
                                                ? 'border-primary bg-primary text-white shadow-md'
                                                : 'border-gray-200 hover:border-primary/50 hover:bg-primary/5 bg-white'
                                        )}
                                    >
                                        {label}
                                    </button>
                                ))}
                            </div>
                            <button
                                type="button"
                                onClick={() => setMode('custom')}
                                className="w-full text-xs text-primary hover:underline text-center mt-1"
                            >
                                ✏️ كمية مخصصة
                            </button>
                        </div>
                    ) : (
                        <div className="flex items-center gap-2 bg-gray-50 p-2 rounded-lg border border-gray-200">
                            <Input
                                type="number"
                                step="0.01"
                                min="0"
                                value={material.quantity || 0}
                                onChange={(e) => {
                                    const val = parseFloat(e.target.value);
                                    onChange({
                                        ...material,
                                        quantity: Number.isFinite(val) ? val : 0
                                    });
                                }}
                                className="w-20 text-center h-9"
                                autoFocus
                            />
                            <span className="text-sm text-gray-600 font-medium">
                                {isDivisible ? 'وزن نسبي' : material.unit}
                            </span>
                            <IconButton
                                icon={<Check size={16} />}
                                variant="ghost"
                                size="sm"
                                onClick={() => setMode('quick')}
                                className="hover:bg-green-100 hover:text-green-700"
                            />
                        </div>
                    )}
                </div>
                {/* Remove Button */}
                <button
                    onClick={onRemove}
                    className="text-gray-400 hover:text-red-500 hover:bg-red-50 p-2 rounded-full transition-colors"
                >
                    <X size={20} />
                </button>
            </div>
        </div>
    );
}

