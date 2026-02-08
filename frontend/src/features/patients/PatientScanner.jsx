import React, { useState, useRef, useEffect } from 'react';
import { Camera, X, RefreshCw, Check, Loader2, Info, Scan } from 'lucide-react';
import { performOCR } from '@/api';

export default function PatientScanner({ onScanComplete, onClose }) {
    const [isReady, setIsReady] = useState(false);
    const [isProcessing, setIsProcessing] = useState(false);
    const [stream, setStream] = useState(null);
    const [capturedImage, setCapturedImage] = useState(null);
    const [ocrStatus, setOcrStatus] = useState('');
    const [isReviewing, setIsReviewing] = useState(false);
    const [rawOcrText, setRawOcrText] = useState('');
    const [showRaw, setShowRaw] = useState(false);
    const [extractedData, setExtractedData] = useState({ name: '', age: '', address: '', phone: '' });
    const [errorHeader, setErrorHeader] = useState('');
    const videoRef = useRef(null);
    const canvasRef = useRef(null);
    const fileInputRef = useRef(null);

    useEffect(() => {
        startCamera();
        return () => stopCamera();
    }, []);

    const startCamera = async () => {
        if (!window.isSecureContext && window.location.hostname !== 'localhost') {
            setErrorHeader('الكاميرا تتطلب رابط آمن (HTTPS).');
            return;
        }

        if (!navigator.mediaDevices?.getUserMedia) {
            setErrorHeader('متصفحك لا يدعم فتح الكاميرا.');
            return;
        }

        try {
            const constraints = {
                video: {
                    facingMode: 'environment',
                    width: { ideal: 1920 },
                    height: { ideal: 1080 }
                }
            };
            const mediaStream = await navigator.mediaDevices.getUserMedia(constraints);
            setStream(mediaStream);
            if (videoRef.current) {
                videoRef.current.srcObject = mediaStream;
                setIsReady(true);
            }
        } catch (err) {
            console.error("Camera error:", err);
            setErrorHeader('حدث خطأ في الكاميرا. يمكنك رفع الصورة بدلاً من ذلك.');
        }
    };

    const stopCamera = () => {
        if (stream) stream.getTracks().forEach(t => t.stop());
        setIsReady(false);
    };

    const retake = () => {
        setCapturedImage(null);
        setIsReviewing(false);
        setErrorHeader('');
        startCamera();
    };

    const handleFileUpload = (e) => {
        const file = e.target.files[0];
        if (file) {
            const reader = new FileReader();
            reader.onload = (event) => {
                setCapturedImage(event.target.result);
                setErrorHeader('');
                stopCamera();
            };
            reader.readAsDataURL(file);
        }
    };

    const processOCR = async (useOriginal = false) => {
        setIsProcessing(true);
        setOcrStatus('جاري تحليل الكارت...');
        try {
            let imageToProcess = capturedImage;
            if (!useOriginal && canvasRef.current && videoRef.current) {
                const canvas = canvasRef.current;
                const video = videoRef.current;

                const MAX_SIZE = 1600;
                let width = video.videoWidth;
                let height = video.videoHeight;
                if (width > MAX_SIZE || height > MAX_SIZE) {
                    const ratio = Math.min(MAX_SIZE / width, MAX_SIZE / height);
                    width *= ratio;
                    height *= ratio;
                }

                canvas.width = width;
                canvas.height = height;
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0, width, height);

                // Grayscale + Contrast Adjustment (Softer than hard threshold)
                const imageData = ctx.getImageData(0, 0, width, height);
                const data = imageData.data;
                for (let i = 0; i < data.length; i += 4) {
                    const gray = 0.299 * data[i] + 0.587 * data[i + 1] + 0.114 * data[i + 2];
                    // Boost contrast: push darks darker and lights lighter without hard clipping
                    let pixel = gray;
                    if (pixel < 128) pixel = pixel * 0.8; // Darker
                    else pixel = Math.min(255, pixel * 1.2); // Brighter
                    data[i] = data[i + 1] = data[i + 2] = pixel;
                }
                ctx.putImageData(imageData, 0, 0);
                imageToProcess = canvas.toDataURL('image/jpeg', 0.80);
            }

            const response = await performOCR(imageToProcess);
            if (response.data.IsErroredOnProcessing) throw new Error(response.data.ErrorMessage[0]);

            const rawText = response.data.ParsedResults?.[0]?.ParsedText || "";
            const text = sanitizeText(rawText);
            setRawOcrText(text);
            const parsed = parseText(text);
            setExtractedData(parsed);
            setIsReviewing(true);
        } catch (err) {
            console.error("OCR Error:", err);
            let msg = "فشل الاتصال بمحرك القراءة.";
            if (err.code === 'ECONNABORTED') {
                msg = "انتهى وقت المحاولة (Timeout)";
            } else if (err.message) {
                msg = `خطأ: ${err.message}`;
            }
            alert(`${msg}\n\nيرجى المحاولة مرة أخرى أو اختيار صورة أوضح.`);
        } finally {
            setIsProcessing(false);
            setOcrStatus('');
        }
    };

    const sanitizeText = (text) => {
        if (!text) return '';
        return text.trim().replace(/\r\n/g, '\n');
    };

    const parseText = (text) => {
        const hindiToEn = (s) => s.replace(/[٠١٢٣٤٥٦٧٨٩]/g, d => "٠١٢٣٤٥٦٧٨٩".indexOf(d));
        const lines = text.split('\n').map(l => l.trim()).filter(l => l.length > 0);

        // Filter out clinic headers to reduce noise
        const cleanLines = lines.filter(l =>
            !l.includes('إسلام عمارة') &&
            !l.includes('Eslam Emara') &&
            !l.includes('عيادة') &&
            !l.includes('دكتور') &&
            !l.includes('مركز')
        );

        const data = { name: '', age: '', phone: '', address: '' };

        const phoneRegex = /(01[0125]\d{8})/;
        const ageRegex = /\b([1-9][0-9]?)\b/;

        // Keyword lists for fuzzy matching
        const nameKeywords = ['المريض', 'الاسم', 'اسم', 'مريض'];
        const ageKeywords = ['السن', 'السم', 'سنة', 'سنه', 'عمر', 'عام'];
        const phoneKeywords = ['تليفون', 'موبايل', 'هاتف', 'محمول', 'جوال', 'ت:', 'م:'];
        const addressKeywords = ['العنوان', 'عنوان', 'شارع', 'بجوار', 'حي', 'قرية', 'مركز'];

        cleanLines.forEach((line, index) => {
            const normalizedLine = hindiToEn(line);

            // Helper: Get value after label or from next line
            const extractValue = (lineContent, keywords) => {
                let val = '';
                const matchedKeyword = keywords.find(k => lineContent.includes(k));
                if (matchedKeyword) {
                    const parts = lineContent.split(matchedKeyword);
                    // Take what's after the keyword on the same line
                    val = parts[1] ? parts[1].replace(/[:\-]/g, '').trim() : '';

                    // If same line empty, check next line
                    if (!val && cleanLines[index + 1]) {
                        const nextLine = cleanLines[index + 1];
                        // Ensure next line isn't another label
                        const isNextLabel = [...nameKeywords, ...ageKeywords, ...phoneKeywords, ...addressKeywords]
                            .some(k => nextLine.includes(k));
                        if (!isNextLabel) val = nextLine;
                    }
                }
                return val;
            };

            // 1. Phone (Priority: High Regex Match)
            const phoneMatch = normalizedLine.match(phoneRegex);
            if (phoneMatch && !data.phone) data.phone = phoneMatch[0];

            // 2. Name
            if (!data.name) {
                const nameVal = extractValue(line, nameKeywords);
                if (nameVal && nameVal.length > 3) data.name = nameVal;
            }

            // 3. Age
            if (!data.age) {
                const ageMatch = normalizedLine.match(ageRegex);
                const hasAgeKeyword = ageKeywords.some(k => line.includes(k));
                if (hasAgeKeyword && ageMatch) {
                    data.age = ageMatch[0];
                }
            }

            // 4. Address
            if (!data.address) {
                const addrVal = extractValue(line, addressKeywords);
                if (addrVal && addrVal.length > 4) data.address = addrVal;
            }
        });

        // --- Final Fallbacks (If still empty) ---

        // Name Fallback: Usually the first line after doctor info
        if (!data.name && cleanLines.length > 0) {
            data.name = cleanLines.find(l => l.length > 5 && !l.match(/\d/) && !l.includes('شارع')) || '';
        }

        // Phone Fallback: Any 11-digit number starting with 01
        if (!data.phone) {
            const anyPhone = hindiToEn(text).match(phoneRegex);
            if (anyPhone) data.phone = anyPhone[0];
        }

        // Age Fallback: Any 2-digit number 5-95
        if (!data.age) {
            const possibleAges = hindiToEn(text).match(/\b\d{1,2}\b/g);
            if (possibleAges) {
                const age = possibleAges.find(n => parseInt(n) > 4 && parseInt(n) < 100);
                if (age) data.age = age;
            }
        }

        return data;
    };

    return (
        <div className="fixed inset-0 bg-slate-900/95 backdrop-blur-md z-[200] flex items-center justify-center p-4">
            <div className="bg-white dark:bg-slate-800 w-full max-w-xl rounded-[2.5rem] shadow-2xl overflow-hidden relative">

                <div className="p-6 flex justify-between items-center border-b dark:border-white/5">
                    <h3 className="font-bold text-xl flex items-center gap-2 dark:text-white">
                        <Scan className="text-primary" /> اسكان كارت المريض
                    </h3>
                    <button onClick={onClose} className="p-2 hover:bg-slate-100 dark:hover:bg-white/5 rounded-xl transition-colors">
                        <X className="dark:text-white" />
                    </button>
                </div>

                <div className="aspect-video bg-black relative overflow-hidden">
                    {errorHeader ? (
                        <div className="absolute inset-0 flex flex-col items-center justify-center p-8 text-center bg-slate-900">
                            <Info size={48} className="text-red-500 mb-4" />
                            <p className="text-white font-bold mb-6 text-lg">{errorHeader}</p>
                            <button onClick={() => fileInputRef.current?.click()} className="w-full bg-primary py-4 rounded-2xl text-white font-black">اختيار صورة من الجهاز</button>
                        </div>
                    ) : capturedImage && !isReviewing ? (
                        <div className="absolute inset-0 bg-slate-900 flex items-center justify-center p-4">
                            <img src={capturedImage} className="max-w-full max-h-full object-contain rounded-xl" alt="Preview" />
                        </div>
                    ) : !isReviewing ? (
                        <>
                            <video ref={videoRef} autoPlay playsInline muted className="w-full h-full object-cover" />
                            <div className="absolute inset-0 border-[40px] border-black/40 pointer-events-none">
                                <div className="w-full h-full border-2 border-dashed border-white/30 rounded-2xl flex items-center justify-center">
                                    <p className="text-white/50 text-xs font-bold bg-black/50 px-4 py-2 rounded-full">ضع بيانات الكارت داخل هذا الإطار</p>
                                </div>
                            </div>
                        </>
                    ) : (
                        <div className="absolute inset-0 bg-white dark:bg-slate-900 p-8 overflow-y-auto">
                            <div className="flex items-center justify-between mb-6">
                                <h4 className="text-xl font-black dark:text-white flex items-center gap-2">
                                    <Check className="text-green-500" /> مراجعة البيانات
                                </h4>
                                <button
                                    onClick={() => setShowRaw(!showRaw)}
                                    className="text-[10px] font-black uppercase tracking-wider text-primary hover:bg-primary/5 px-3 py-1.5 rounded-lg border border-primary/20 transition-colors"
                                >
                                    {showRaw ? 'إخفاء النص الأصلي' : 'عرض النص المستخرج'}
                                </button>
                            </div>

                            {showRaw && (
                                <div className="mb-6 p-4 bg-slate-50 dark:bg-slate-800 rounded-2xl border border-slate-200 dark:border-white/5 animate-in fade-in slide-in-from-top-2 duration-300">
                                    <label className="text-[10px] font-black text-slate-400 block mb-2">النص كما قرأه البرنامج (OCR):</label>
                                    <p className="text-xs text-slate-600 dark:text-slate-300 whitespace-pre-wrap leading-relaxed font-medium bg-white dark:bg-slate-900 p-3 rounded-xl border border-slate-100 dark:border-white/5 max-h-40 overflow-y-auto">
                                        {rawOcrText || 'لم يتم العثور على نص'}
                                    </p>
                                </div>
                            )}

                            <div className="space-y-4">
                                <div><label className="text-xs font-bold text-slate-400 block mb-1">الاسم</label>
                                    <input type="text" value={extractedData.name} onChange={e => setExtractedData({ ...extractedData, name: e.target.value })} className="w-full p-4 bg-slate-50 dark:bg-slate-800 border-none rounded-2xl font-bold dark:text-white focus:ring-2 focus:ring-primary/20 transition-all" /></div>
                                <div className="grid grid-cols-2 gap-4">
                                    <div><label className="text-xs font-bold text-slate-400 block mb-1">السن</label>
                                        <input type="text" value={extractedData.age} onChange={e => setExtractedData({ ...extractedData, age: e.target.value })} className="w-full p-4 bg-slate-50 dark:bg-slate-800 border-none rounded-2xl font-bold dark:text-white focus:ring-2 focus:ring-primary/20 transition-all" /></div>
                                    <div><label className="text-xs font-bold text-slate-400 block mb-1">رقم الهاتف</label>
                                        <input type="text" value={extractedData.phone} onChange={e => setExtractedData({ ...extractedData, phone: e.target.value })} className="w-full p-4 bg-slate-50 dark:bg-slate-800 border-none rounded-2xl font-bold dark:text-white text-left focus:ring-2 focus:ring-primary/20 transition-all" dir="ltr" /></div>
                                </div>
                                <div><label className="text-xs font-bold text-slate-400 block mb-1">العنوان</label>
                                    <input type="text" value={extractedData.address} onChange={e => setExtractedData({ ...extractedData, address: e.target.value })} className="w-full p-4 bg-slate-50 dark:bg-slate-800 border-none rounded-2xl font-bold dark:text-white focus:ring-2 focus:ring-primary/20 transition-all" /></div>
                            </div>
                        </div>
                    )}

                    {isProcessing && (
                        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm flex flex-col items-center justify-center text-white z-50">
                            <Loader2 className="animate-spin text-primary mb-4" size={48} />
                            <p className="font-black text-xl">{ocrStatus}</p>
                        </div>
                    )}
                </div>

                <div className="p-8 flex gap-4 bg-slate-50 dark:bg-slate-900/50">
                    {isReviewing ? (
                        <>
                            <button onClick={retake} className="flex-1 py-4 font-bold text-slate-500 hover:bg-slate-100 rounded-2xl transition-colors">إعادة تصوير</button>
                            <button onClick={() => { onScanComplete(extractedData); onClose(); }} className="flex-[2] py-4 bg-primary text-white font-black rounded-2xl shadow-xl shadow-primary/20 hover:scale-[1.02] transition-all">تأكيد وحفظ</button>
                        </>
                    ) : (
                        <div className="flex gap-4 w-full">
                            {capturedImage ? (
                                <>
                                    <button onClick={retake} className="flex-1 py-4 font-bold text-slate-500 bg-slate-200 rounded-2xl">إلغاء</button>
                                    <button onClick={() => processOCR(true)} className="flex-[2] py-4 bg-primary text-white font-black rounded-2xl shadow-lg">تحليل الصورة المرفوعة</button>
                                </>
                            ) : (
                                <button
                                    disabled={!isReady || isProcessing}
                                    onClick={() => {
                                        const canvas = canvasRef.current;
                                        const video = videoRef.current;
                                        if (video && canvas) {
                                            canvas.width = video.videoWidth;
                                            canvas.height = video.videoHeight;
                                            canvas.getContext('2d').drawImage(video, 0, 0);
                                            setCapturedImage(canvas.toDataURL('image/jpeg'));
                                            processOCR();
                                        }
                                    }}
                                    className="w-full py-5 bg-primary text-white font-black rounded-3xl flex items-center justify-center gap-3 shadow-2xl shadow-primary/30 hover:scale-[1.02] active:scale-95 transition-all disabled:opacity-50"
                                >
                                    <Camera size={24} />
                                    <span>التقاط صورة الكارت</span>
                                </button>
                            )}
                        </div>
                    )}
                </div>

                <canvas ref={canvasRef} className="hidden" />
                <input type="file" ref={fileInputRef} className="hidden" accept="image/*" onChange={handleFileUpload} />
            </div>
        </div>
    );
}
