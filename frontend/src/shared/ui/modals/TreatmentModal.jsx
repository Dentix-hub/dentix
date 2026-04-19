import { useState, useEffect } from 'react';
import { X, Package, Plus, Trash2, Clock, FileText } from 'lucide-react';
import { getMaterials, getProcedureWeights, getActiveSessions } from '@/api/inventory';
import TrackSessionModal from '@/features/inventory/components/TrackSessionModal';
import { EnhancedMaterialConsumption } from '@/features/inventory/components/EnhancedMaterialConsumption';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { addTreatmentSession } from '@/api';
import { MultiSessionPanel } from '../components/MultiSessionPanel';
export default function TreatmentModal({
    isOpen,
    onClose,
    onSave,
    initialData,
    isEditing = false,
    procedures = [],
    selectedToothCondition,
    setSelectedToothCondition
}) {
    const [treatment, setTreatment] = useState(initialData);
    const [showAdvanced, setShowAdvanced] = useState(false);
    const [isManualProcedure, setIsManualProcedure] = useState(false);
    // Modal Tabs
    const [toothModalTab, setToothModalTab] = useState('Status');
    const [selectedPathologies, setSelectedPathologies] = useState([]);
    const [selectedRestorations, setSelectedRestorations] = useState([]);
    // Inventory State
    const [availableMaterials, setAvailableMaterials] = useState([]);
    const [consumedMaterials, setConsumedMaterials] = useState([]); // [{ material_id, quantity }]
    const [showInventory, setShowInventory] = useState(false);
    const [isSmartConsumptionOpen, setIsSmartConsumptionOpen] = useState(false);
    const [smartConsumptionMode, setSmartConsumptionMode] = useState('smart');
    // Fetch Active Sessions to show status
    const { data: activeSessionsRes, refetch: refetchSessions } = useQuery({
        queryKey: ['active-sessions'],
        queryFn: getActiveSessions,
        enabled: isOpen
    });
    const activeSessions = activeSessionsRes?.data || [];
    // Session Tracking State
    const [isTrackSessionOpen, setIsTrackSessionOpen] = useState(false);
    const [trackSessionMode, setTrackSessionMode] = useState('OPEN');
    const [trackSessionMaterial, setTrackSessionMaterial] = useState(null);
    const [trackSessionData, setTrackSessionData] = useState(null);
    // Fetch Materials on Mount
    useEffect(() => {
        if (isOpen) {
            getMaterials().then(res => setAvailableMaterials(res.data)).catch(err => console.error("Failed to load materials", err));
        }
    }, [isOpen]);
    useEffect(() => {
        if (isOpen) {
            setTreatment(initialData);
            // FIX: Initialize consumed materials from initialData when editing
            if (isEditing && initialData.consumedMaterials) {
                console.log("[TreatmentModal] Loading existing materials:", initialData.consumedMaterials);
                setConsumedMaterials(initialData.consumedMaterials);
                if (initialData.consumedMaterials.length > 0) {
                    setShowInventory(true);
                }
            } else if (!isEditing) {
                // Reset for new entry
                setConsumedMaterials([]);
                setShowInventory(false);
            }
            // Reset tabs logic when opening new (or editing if needed, but usually keep existing)
            if (!isEditing) {
                setToothModalTab('Status');
                setSelectedPathologies([]);
                setSelectedRestorations([]);
            }
        }
    }, [isOpen, initialData, isEditing]);
    const queryClient = useQueryClient();

    const addSessionMutation = useMutation({
        mutationFn: (data) => addTreatmentSession(treatment.id, data),
        onSuccess: () => {
            queryClient.invalidateQueries(['patient-details', treatment.patient_id]);
            // Also update local state to show the new session without a full refetch if possible
            setTreatment(prev => ({
                ...prev,
                treatment_sessions: [...(prev.treatment_sessions || []), { 
                    ...prev.last_added_session, // mock or wait for refresh
                    created_at: new Date().toISOString() 
                }]
            }));
        }
    });

    const handleAddSession = async (sessionData) => {
        try {
            await addSessionMutation.mutateAsync({
                ...sessionData,
                treatment_id: treatment.id,
                tenant_id: treatment.tenant_id
            });
            return true;
        } catch (error) {
            console.error("Failed to add session:", error);
            return false;
        }
    };
    if (!isOpen) return null;
    const handleSave = async (e) => {
        if (e) e.preventDefault();
        // 0. Smart Inventory Pre-Check (Client Side Optimization)
        const payload = {
            ...treatment,
            tooth_number: treatment.tooth_number,
            cost: treatment.cost ? parseFloat(treatment.cost) : 0,
            discount: treatment.discount ? parseFloat(treatment.discount) : 0,
            canal_count: treatment.canal_count ? parseInt(treatment.canal_count, 10) : null,
            diagnosis: treatment.diagnosis,
            selectedPathologies,
            selectedRestorations,
            consumedMaterials
        };
        try {
            await onSave(payload);
        } catch (error) {
            // Handle 409 Conflict (Structured Data)
            // Backend now returns detailed logic in `error.details`
            const errorData = error.response?.data?.error;
            const errorDetails = errorData?.details;
            if (error.response?.status === 409) {
                // Check structured details first
                if (errorDetails?.code === "CONFIRM_OPEN_REQUIRED") {
                    const stockId = errorDetails.stock_item_id;
                    const matName = errorDetails.material_info;
                    setConfirmOpenMaterial({
                        stockItemId: stockId,
                        name: matName
                    });
                    // Set mode for TrackSessionModal
                    setTrackSessionMaterial({ name: matName, id: stockId });
                    setTrackSessionMode('OPEN');
                    setIsTrackSessionOpen(true);
                    return;
                }
            }
            // Fallback / Legacy String Parsing
            const res = error?.response?.data;
            const errorMsg = res?.error?.message || res?.detail || res?.message || "";
            if (typeof errorMsg === 'string' && errorMsg.includes("CONFIRM_OPEN_REQUIRED")) {
                const parts = errorMsg.split('CONFIRM_OPEN_REQUIRED:');
                if (parts.length > 1) {
                    const infoParts = parts[1].split(':');
                    if (infoParts.length >= 1) {
                        const stockId = infoParts[0];
                        const matName = infoParts.slice(1).join(':') || "Unknown Material";
                        setConfirmOpenMaterial({
                            stockItemId: stockId,
                            name: matName
                        });
                        setTrackSessionMaterial({ name: matName, id: stockId });
                        setTrackSessionMode('OPEN');
                        setIsTrackSessionOpen(true);
                        return;
                    }
                }
            }
            // Re-throw if not ours
            throw error;
        }
    };
    return (
        <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 backdrop-blur-sm">
            <div className="bg-white w-full max-w-md rounded-2xl p-6 shadow-2xl max-h-[90vh] overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h3 className="text-xl font-bold">
                        {isEditing ? 'تعديل بيانات العلاج' : (treatment.tooth_number ? `تفاصيل السن رقم #${treatment.tooth_number}` : 'تسجيل علاج جديد')}
                    </h3>
                    <button onClick={onClose} className="p-1 hover:bg-slate-100 rounded-full"><X size={20} /></button>
                </div>
                <div className="space-y-4">
                    {treatment.tooth_number && (
                        <div className="bg-white rounded-2xl border border-slate-100 p-4 shadow-sm mb-4">
                            {/* Segmented Control */}
                            <div className="flex p-1 bg-slate-100 rounded-xl mb-6 relative">
                                {['Status', 'Pathology', 'Restorations'].map((tab) => (
                                    <button
                                        key={tab}
                                        onClick={() => setToothModalTab(tab)}
                                        className={`flex-1 py-2 text-sm font-bold rounded-lg transition-all duration-300 relative z-10 ${toothModalTab === tab ? 'bg-white text-slate-900 shadow-sm scale-100' : 'text-slate-500 hover:text-slate-700'}`}
                                    >
                                        {tab === 'Status' && 'العامة'}
                                        {tab === 'Pathology' && 'الأمراض'}
                                        {tab === 'Restorations' && 'التركيبات'}
                                    </button>
                                ))}
                            </div>
                            {/* Tab Content */}
                            <div className="min-h-[100px]">
                                {/* Tab 1: Status (Single Select) */}
                                {toothModalTab === 'Status' && (
                                    <div className="animate-in fade-in zoom-in-95 duration-200">
                                        <div className="flex flex-wrap gap-2">
                                            {['Healthy', 'Missing', 'Impacted', 'Unerupted', 'Retained Root'].map(status => (
                                                <button
                                                    key={status}
                                                    onClick={() => {
                                                        setSelectedToothCondition(status);
                                                        // Auto-fill logic
                                                        const foundProc = procedures.find(p => p.name.toLowerCase() === status.toLowerCase());
                                                        setTreatment(prev => ({
                                                            ...prev,
                                                            diagnosis: status,
                                                            procedure: foundProc ? foundProc.name : prev.procedure,
                                                            cost: foundProc ? foundProc.price : prev.cost
                                                        }));
                                                    }}
                                                    className={`px-4 py-2 rounded-full text-sm font-bold transition-all border ${selectedToothCondition === status
                                                        ? 'bg-slate-800 text-white border-slate-800 shadow-md transform scale-105'
                                                        : 'bg-white text-slate-600 border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                                                        }`}
                                                >
                                                    {status}
                                                </button>
                                            ))}
                                        </div>
                                    </div>
                                )}
                                {/* Tab 2: Pathology (Multi Select) */}
                                {toothModalTab === 'Pathology' && (
                                    <div className="animate-in fade-in zoom-in-95 duration-200">
                                        <div className="flex flex-wrap gap-2">
                                            {['Decayed', 'Fractured', 'Abscess', 'Mobility', 'Pain'].map(item => {
                                                const isSelected = selectedPathologies.includes(item);
                                                return (
                                                    <button
                                                        key={item}
                                                        onClick={() => {
                                                            const newSel = isSelected
                                                                ? selectedPathologies.filter(i => i !== item)
                                                                : [...selectedPathologies, item];
                                                            setSelectedPathologies(newSel);
                                                            // Update diagnosis with all selected
                                                            const diagnosis = [...newSel, ...selectedRestorations].join(', ');
                                                            setTreatment(prev => ({ ...prev, diagnosis: diagnosis || prev.diagnosis }));
                                                            // If Decayed is selected, update chart color
                                                            if (!isSelected && item === 'Decayed') setSelectedToothCondition('Decayed');
                                                        }}
                                                        className={`px-4 py-2 rounded-full text-sm font-bold transition-all border ${isSelected
                                                            ? 'bg-red-50 text-red-600 border-red-200 shadow-sm ring-1 ring-red-100'
                                                            : 'bg-white text-slate-600 border-slate-200 hover:border-red-200 hover:text-red-500'
                                                            }`}
                                                    >
                                                        {item}
                                                    </button>
                                                )
                                            })}
                                        </div>
                                    </div>
                                )}
                                {/* Tab 3: Restorations (Multi Select) */}
                                {toothModalTab === 'Restorations' && (
                                    <div className="animate-in fade-in zoom-in-95 duration-200">
                                        <div className="flex flex-wrap gap-2">
                                            {['Filled', 'Root Canal', 'Crown', 'Bridge', 'Implant'].map(item => {
                                                const isSelected = selectedRestorations.includes(item);
                                                return (
                                                    <button
                                                        key={item}
                                                        onClick={() => {
                                                            const newSel = isSelected
                                                                ? selectedRestorations.filter(i => i !== item)
                                                                : [...selectedRestorations, item];
                                                            setSelectedRestorations(newSel);
                                                            const diagnosis = [...selectedPathologies, ...newSel].join(', ');
                                                            setTreatment(prev => ({ ...prev, diagnosis: diagnosis || prev.diagnosis }));
                                                            const chartMap = { 'Filled': 'Filled', 'Root Canal': 'RootCanal', 'Crown': 'Crown', 'Bridge': 'Crown', 'Implant': 'Crown' };
                                                            if (!isSelected && chartMap[item]) {
                                                                setSelectedToothCondition(chartMap[item]);
                                                            }
                                                        }}
                                                        className={`px-4 py-2 rounded-full text-sm font-bold transition-all border ${isSelected
                                                            ? 'bg-blue-50 text-blue-600 border-blue-200 shadow-sm ring-1 ring-blue-100'
                                                            : 'bg-white text-slate-600 border-slate-200 hover:border-blue-200 hover:text-blue-500'
                                                            }`}
                                                    >
                                                        {item}
                                                    </button>
                                                )
                                            })}
                                        </div>
                                    </div>
                                )}
                            </div>
                        </div>
                    )}
                    <input value={treatment.diagnosis} onChange={e => setTreatment({ ...treatment, diagnosis: e.target.value })} placeholder="التشخيص" className="w-full p-3 bg-slate-50 rounded-xl outline-none" />
                    {/* Procedure Selection & Price Calculation */}
                    <div className="bg-slate-50 p-4 rounded-xl space-y-4">
                        {/* Price List Selection (Optional Override) */}
                        <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
                            <span>قائمة الأسعار:</span>
                            {/* In a real app, this could be a dropdown. For now, we just show the active one or allow toggle if needed */}
                        </div>
                        {isManualProcedure ? (
                            <div className="flex gap-2 animate-in fade-in zoom-in-95 duration-200">
                                <input
                                    value={treatment.procedure}
                                    onChange={e => setTreatment({ ...treatment, procedure: e.target.value })}
                                    placeholder="أدخل اسم الإجراء يدوياً..."
                                    className="flex-1 p-3 bg-blue-50/50 border border-blue-100 rounded-xl outline-none text-blue-900 placeholder-blue-300 font-bold"
                                    autoFocus
                                />
                                <button
                                    onClick={() => {
                                        setIsManualProcedure(false);
                                        setTreatment({ ...treatment, procedure: '' });
                                    }}
                                    className="px-4 bg-slate-100 hover:bg-slate-200 text-slate-600 rounded-xl font-medium transition-colors"
                                >
                                    قائمة
                                </button>
                            </div>
                        ) : (
                            <div className="relative">
                                <select
                                    value={treatment.procedure}
                                    onChange={async e => {
                                        const val = e.target.value;
                                        if (val === 'MANUAL_ENTRY_OPTION') {
                                            setIsManualProcedure(true);
                                            setTreatment({ ...treatment, procedure: '', cost: '', price_list_id: null });
                                            return;
                                        }
                                        // Find generic procedure info
                                        const foundProc = procedures.find(p => p.name === val);
                                        const baseProcedurePrice = foundProc?.price || 0; // Fallback value
                                        let calculatedPrice = baseProcedurePrice;
                                        let activePriceListId = treatment.price_list_id;
                                        console.log('[PRICE_DEBUG] Found Procedure:', foundProc?.name, 'Base Price:', baseProcedurePrice);
                                        console.log('[PRICE_DEBUG] Default Price List ID:', initialData?.default_price_list_id);
                                        // If we have a patient default price list, try to fetch specific price
                                        if (foundProc && initialData?.default_price_list_id) {
                                            try {
                                                // Dynamic import to avoid circular dependency
                                                const { getProcedurePrices } = await import('@/api');
                                                const pricesData = await getProcedurePrices(foundProc.id);
                                                console.log('[PRICE_DEBUG] Prices Data:', pricesData?.data);
                                                // Check if there's a price for the patient's list
                                                const specificPrice = pricesData.data?.price_lists?.find(pl =>
                                                    // Loose comparison for ID safety
                                                    String(pl.price_list_id) === String(initialData.default_price_list_id)
                                                );
                                                console.log('[PRICE_DEBUG] Specific Price Found:', specificPrice);
                                                if (specificPrice && specificPrice.final_price > 0) {
                                                    // Use price list price ONLY if it's greater than 0
                                                    calculatedPrice = specificPrice.final_price;
                                                    activePriceListId = initialData.default_price_list_id;
                                                } else if (specificPrice && specificPrice.final_price === 0) {
                                                    // Price list has 0 - fallback to base procedure price
                                                    console.log('[PRICE_DEBUG] Price list price is 0, using base procedure price:', baseProcedurePrice);
                                                    calculatedPrice = baseProcedurePrice;
                                                }
                                            } catch (err) {
                                                console.error("Failed to fetch custom prices", err);
                                            }
                                        }
                                        console.log('[PRICE_DEBUG] Final Calculated Price:', calculatedPrice);
                                        // NEW: Auto-load consumed materials (BOM)
                                        if (foundProc) {
                                            try {
                                                const weightsRes = await getProcedureWeights({ procedure_id: foundProc.id });
                                                if (weightsRes.data && weightsRes.data.length > 0) {
                                                    const autoMaterials = weightsRes.data.map(w => ({
                                                        material_id: w.material_id,
                                                        quantity: parseFloat(w.weight) || 1
                                                    }));
                                                    console.log("Auto-loaded materials:", autoMaterials);
                                                    setConsumedMaterials(autoMaterials);
                                                    setShowInventory(true); // Auto-expand to show user
                                                }
                                            } catch (err) {
                                                console.error("Failed to load procedure materials", err);
                                            }
                                        }
                                        setTreatment({
                                            ...treatment,
                                            procedure: val,
                                            cost: calculatedPrice,
                                            price_list_id: activePriceListId
                                        });
                                    }}
                                    className="w-full p-3 bg-white border border-slate-200 rounded-xl outline-none appearance-none cursor-pointer font-bold text-slate-700 focus:border-primary focus:ring-1 focus:ring-primary/20 transition-all"
                                >
                                    <option value="">اختر الإجراء العلاجي...</option>
                                    <option value="MANUAL_ENTRY_OPTION" className="font-bold text-primary bg-blue-50">✍️ كتابة إجراء يدوي (غير مضاف)</option>
                                    {procedures.map(p => (
                                        <option key={p.id} value={p.name}>{p.name}</option>
                                    ))}
                                </select>
                                <div className="absolute left-3 top-1/2 transform -translate-y-1/2 pointer-events-none">
                                    <svg className="w-5 h-5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                                    </svg>
                                </div>
                            </div>
                        )}
                        {/* Price Display / Override */}
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="text-xs font-bold text-slate-400 block mb-1">التكلفة</label>
                                <input
                                    value={treatment.cost}
                                    onChange={e => setTreatment({ ...treatment, cost: e.target.value })}
                                    placeholder="0.00"
                                    type="number"
                                    className="w-full p-3 bg-white border border-slate-200 rounded-xl outline-none font-bold"
                                />
                            </div>
                            <div>
                                <label className="text-xs font-bold text-slate-400 block mb-1">الخصم</label>
                                <input
                                    value={treatment.discount}
                                    onChange={e => setTreatment({ ...treatment, discount: e.target.value })}
                                    placeholder="0.00"
                                    type="number"
                                    className="w-full p-3 bg-white border border-slate-200 border-dashed rounded-xl outline-none"
                                />
                            </div>
                        </div>
                    </div>
                    <input value={treatment.tooth_number} onChange={e => setTreatment({ ...treatment, tooth_number: e.target.value })} placeholder="رقم السن" className="w-full p-3 bg-slate-50 rounded-xl outline-none" />
                    {/* Advanced Toggle */}
                    <button
                        onClick={() => setShowAdvanced(!showAdvanced)}
                        className="w-full py-2 text-sm text-primary font-bold border border-primary/20 rounded-xl hover:bg-primary/5 transition-colors"
                    >
                        {showAdvanced ? '- إخفاء التفاصيل' : '+ إضافة تفاصيل (عصب، قنوات)'}
                    </button>
                    {showAdvanced && (
                        <div className="space-y-4 p-4 bg-primary/5 rounded-2xl border border-primary/10 animate-in slide-in-from-top-2 duration-200">
                            {/* Simplified Advanced Fields for Brevity - Keeping core functionality */}
                            <div>
                                <label className="block text-xs font-bold text-slate-500 mb-1">عدد القنوات</label>
                                <input type="number" value={treatment.canal_count} onChange={e => setTreatment({ ...treatment, canal_count: e.target.value })} className="w-full p-3 bg-white rounded-xl border border-slate-100" placeholder="e.g 3" />
                            </div>
                            <div>
                                <label className="block text-xs font-bold text-slate-500 mb-1">تفاصيل القنوات</label>
                                {treatment.canals.map((canal, idx) => (
                                    <div key={idx} className="flex gap-2 mb-2">
                                        <input value={canal.name} onChange={e => {
                                            const newCanals = treatment.canals.map((c, i) => i === idx ? { ...c, name: e.target.value } : c);
                                            setTreatment({ ...treatment, canals: newCanals });
                                        }} placeholder="الاسم" className="flex-1 p-2 bg-white rounded-lg border border-slate-100" />
                                        <input value={canal.length} onChange={e => {
                                            const newCanals = treatment.canals.map((c, i) => i === idx ? { ...c, length: e.target.value } : c);
                                            setTreatment({ ...treatment, canals: newCanals });
                                        }} placeholder="مم" className="w-20 p-2 bg-white rounded-lg border border-slate-100" />
                                    </div>
                                ))}
                                <button onClick={() => setTreatment({ ...treatment, canals: [...treatment.canals, { name: '', length: '' }] })} className="text-xs text-primary">+ إضافة قناة</button>
                            </div>
                            <textarea value={treatment.sessions} onChange={e => setTreatment({ ...treatment, sessions: e.target.value })} placeholder="جلسات" className="w-full p-3 bg-white rounded-xl border border-slate-100 h-20" />
                            <textarea value={treatment.complications} onChange={e => setTreatment({ ...treatment, complications: e.target.value })} placeholder="المضاعفات" className="w-full p-3 bg-white rounded-xl border border-red-100 text-red-600 h-20" />
                        </div>
                    )}
                    {/* Inventory Consumption Section */}
                    <div className="border border-slate-200 rounded-xl overflow-hidden">
                        <div className="p-3 bg-slate-50 flex items-center justify-between">
                            <h4 className="font-bold text-slate-700 flex items-center gap-2">
                                <Package size={18} />
                                المواد المستهلكة
                            </h4>
                            <button
                                onClick={() => {
                                    setSmartConsumptionMode('manual');
                                    setIsSmartConsumptionOpen(true);
                                }}
                                className="text-xs font-bold bg-primary text-white px-3 py-1.5 rounded-lg hover:bg-primary-600 transition-colors flex items-center gap-1 shadow-sm shadow-primary/20"
                            >
                                <Plus size={14} /> إضافة
                            </button>
                        </div>
                        {consumedMaterials.length > 0 ? (
                            <div className="p-3 bg-white space-y-2">
                                {consumedMaterials.map((item, idx) => {
                                    const matInfo = availableMaterials.find(m => m.id === parseInt(item.material_id));
                                    const matName = matInfo?.name || 'Unknown Material';
                                    // Check if divisible based on unit or material type
                                    const isDivisible = ['g', 'ml', 'cm'].includes(item.unit?.toLowerCase()) ||
                                        matInfo?.type === 'DIVISIBLE' ||
                                        matInfo?.material_type === 'DIVISIBLE';
                                    return (
                                        <div key={idx} className="flex justify-between items-center text-sm p-2 bg-slate-50 rounded-lg border border-slate-100">
                                            <span className="font-medium text-slate-700">{matName}</span>
                                            <div className="flex items-center gap-2">
                                                <span className="bg-white px-2 py-0.5 rounded border text-slate-600 font-mono font-bold text-xs">
                                                    {item.quantity} {isDivisible ? '× وزن نسبي' : (item.unit ? item.unit : 'وحدة')}
                                                </span>
                                                <button
                                                    onClick={() => {
                                                        const newMats = [...consumedMaterials];
                                                        newMats.splice(idx, 1);
                                                        setConsumedMaterials(newMats);
                                                    }}
                                                    className="text-red-400 hover:text-red-500"
                                                >
                                                    <Trash2 size={14} />
                                                </button>
                                            </div>
                                        </div>
                                    );
                                })}
                            </div>
                        ) : (
                            <div className="p-4 text-center text-xs text-slate-400 bg-slate-50/50">
                                لم يتم تسجيل أي مواد لهذا الإجراء
                            </div>
                        )}
                    </div>
                    <textarea value={treatment.notes} onChange={e => setTreatment({ ...treatment, notes: e.target.value })} placeholder="ملاحظات عامة" className="w-full p-3 bg-slate-50 rounded-xl outline-none" />
                    <div className="flex justify-end gap-3 text-lg font-bold">
                        <button onClick={onClose} className="px-4 py-2 hover:bg-slate-100 rounded-lg">إلغاء</button>
                        <button onClick={handleSave} className="px-6 py-2 bg-primary text-white rounded-lg">حفظ</button>
                    </div>
                </div>
            </div>
            {/* Smart Inventory Modal */}
            <EnhancedMaterialConsumption
                isOpen={isSmartConsumptionOpen}
                onClose={() => setIsSmartConsumptionOpen(false)}
                procedure={procedures.find(p => p.name === treatment.procedure)}
                patientAge={null} // Add logic if needed
                availableMaterials={availableMaterials}
                initialMaterials={consumedMaterials} // Pass existing materials
                mode={smartConsumptionMode} // Pass mode
                onSave={(newMaterials) => {
                    // Map generic format to specific format needed by backend
                    // Backend expects: { material_id, quantity, batch_id? }
                    // Enhanced returns: { materialId, quantity, ... }
                    const mapped = newMaterials.map(m => ({
                        material_id: m.materialId,
                        quantity: m.quantity,
                        unit: m.unit // purely for display
                    }));
                    setConsumedMaterials(mapped);
                }}
            />
            {/* Session Tracking Modal */}
            <TrackSessionModal
                isOpen={isTrackSessionOpen}
                onClose={() => {
                    setIsTrackSessionOpen(false);
                    refetchSessions(); // Refresh status after close
                }}
                mode={trackSessionMode}
                material={trackSessionMaterial}
                session={trackSessionData}
                onSuccess={() => {
                    // Auto-retry save after opening session
                    if (trackSessionMode === 'OPEN') {
                        setTimeout(() => handleSave(), 100);
                    }
                }}
            />
        </div>
    );
}

