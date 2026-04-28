import { useState } from "react";

const data = {
  scores: [
    { label: "Design Consistency", score: 58, max: 100, color: "#f59e0b" },
    { label: "RTL / Arabic Support", score: 70, max: 100, color: "#10b981" },
    { label: "Information Density", score: 45, max: 100, color: "#ef4444" },
    { label: "Accessibility (a11y)", score: 40, max: 100, color: "#ef4444" },
    { label: "Component Polish", score: 65, max: 100, color: "#f59e0b" },
    { label: "Navigation UX", score: 72, max: 100, color: "#10b981" },
    { label: "Mobile Experience", score: 55, max: 100, color: "#f59e0b" },
    { label: "Medical SaaS Standards", score: 50, max: 100, color: "#f59e0b" },
  ],
  competitors: [
    { name: "Jane App", region: "🇨🇦", strengths: ["Appointment UX", "Clean modals", "Consistent radii", "Keyboard nav"], color: "#6366f1" },
    { name: "Carepatron", region: "🇳🇿", strengths: ["Modern design system", "Patient timeline", "Mobile-first", "Empty states"], color: "#8b5cf6" },
    { name: "Dental Intel", region: "🇺🇸", strengths: ["KPI density", "Procedure analytics", "Print workflows", "Drill-down"], color: "#3b82f6" },
    { name: "Medifusion", region: "🇸🇦", strengths: ["Arabic-first RTL", "Clinic branding", "MENA-aware flows"], color: "#14b8a6" },
  ],
  issues: [
    {
      id: "I-01", severity: "critical", category: "Design System",
      title: "لا يوجد نظام border-radius موحّد",
      file: "Layout.jsx, GradientCard, Card, Button",
      detail: "GradientCard: rounded-[2.5rem] (40px) — Card: rounded-2xl (16px) — Button: rounded-xl (12px) — Nav links: rounded-2xl. أربع قيم مختلفة في نفس الـ Layout. المنتجات الاحترافية زي Jane App بتلتزم بـ radius واحد طول البرنامج.",
      fix: "حدّد radius واحد للـ component tier: small=rounded-lg (8px)، medium=rounded-xl (12px)، card=rounded-2xl (16px). احذف rounded-[2.5rem] تماماً.",
      before: "rounded-[2.5rem] p-6 text-white",
      after: "rounded-2xl p-6 text-white",
    },
    {
      id: "I-02", severity: "critical", category: "RTL Bug",
      title: "icon margin في Button معكوس في العربي",
      file: "src/shared/ui/Button.jsx — السطر 33",
      detail: 'الكود بيستخدم className=\"mr-2\" على الـ icon. في RTL (العربي) المسافة المفروض تكون على اليسار مش اليمين. يعني الأيقونة بتكون ملصوقة بالنص من الجهة الغلط.',
      fix: "استبدل mr-2 بـ me-2 (margin-inline-end) اللي بتشتغل صح في LTR و RTL أوتوماتيك.",
      before: '<Icon className={`mr-2 h-4 w-4`} />',
      after: '<Icon className={`me-2 h-4 w-4`} />',
    },
    {
      id: "I-03", severity: "critical", category: "Color Inconsistency",
      title: "صفحة Analytics بتستخدم indigo مش primary",
      file: "src/features/analytics/SmartDashboard.jsx",
      detail: "كل البرنامج بيستخدم primary color (#0891B2 - cyan). لكن SmartDashboard بيستخدم hardcoded indigo-600 في الـ tabs والـ period selector. يعني المستخدم شايف لونين مختلفين للـ active state في نفس البرنامج.",
      fix: "استبدل bg-indigo-600 بـ bg-primary و border-indigo-600 بـ border-primary في كل ملف SmartDashboard.",
      before: "bg-indigo-600 text-white shadow-md shadow-indigo-200",
      after: "bg-primary text-white shadow-md shadow-primary/20",
    },
    {
      id: "I-04", severity: "critical", category: "Anti-pattern",
      title: "PatientTable بيلوّن الكروت بشكل عشوائي بـ index",
      file: "src/features/patients/PatientTable.jsx — CARD_COLORS",
      detail: "كل كارت مريض بياخد لون بناءً على index % 5. يعني نفس المريض بياخد لون مختلف لو اتصفّح في ترتيب تاني. لا يوجد أي معنى طبي أو بياني لهذا اللون. المنتجات المحترفة بتستخدم لون neutral واحد مع تمييز بالـ status فقط.",
      fix: "احذف CARD_COLORS. استخدم كارت neutral موحّد (bg-surface border-border) مع أيقونة avatar دائرية بلون واحد.",
      before: "const colorTheme = CARD_COLORS[index % CARD_COLORS.length]",
      after: "// لون ثابت، التمييز من خلال status badge فقط",
    },
    {
      id: "I-05", severity: "critical", category: "UX Pattern",
      title: "window.confirm لحذف المواعيد",
      file: "src/pages/Appointments.jsx — handleDelete",
      detail: 'if (!window.confirm(...)) return; — ده browser native dialog. بيبان قديم جداً، مش متناسق مع الـ design system، ومش بيدي الـ loading state بعد الموافقة. كل SaaS محترف زي Carepatron بيستخدم custom confirmation modal.',
      fix: "استخدم ConfirmDialog الموجود أصلاً في src/shared/ui/ConfirmDialog.jsx بدل window.confirm.",
      before: "if (!window.confirm(t('appointments.confirm_delete'))) return;",
      after: "setConfirmDelete({ open: true, appointmentId: id }); // ثم <ConfirmDialog />",
    },
    {
      id: "I-06", severity: "high", category: "Performance / UX",
      title: "Logo بـ CSS scale hack في الـ sidebar",
      file: "src/layouts/Layout.jsx — className على img",
      detail: 'className="h-full w-full object-contain drop-shadow-md scale-[2.5] translate-x-4" — ده يعني اللوجو بيتكبّر بـ CSS transform بدل ما يكون الصورة الأصلية بالحجم المناسب. بيسبب blurry render على شاشات الـ HiDPI وبيأثر على الـ layout.',
      fix: "أوفّر نسخة SVG أو PNG بالأبعاد الصح. احذف scale و translate. خلّي الـ img بـ max-h-16 w-auto.",
      before: 'className="h-full w-full object-contain scale-[2.5] translate-x-4"',
      after: 'className="max-h-16 w-auto object-contain"',
    },
    {
      id: "I-07", severity: "high", category: "Information Architecture",
      title: "Sidebar 288px بياكل مساحة كبيرة على شاشات 1366px",
      file: "src/layouts/Layout.jsx — w-72",
      detail: "w-72 = 288px. شاشات الـ 1366px (الأكثر انتشاراً في مصر) تفضل 1078px للمحتوى بس. Jane App و Dental Intel بيستخدموا collapsed sidebar بـ 64px + expanded بـ 240px. ده بيدي المحتوى مساحة أكبر بـ 224px.",
      fix: "ضيف collapsible sidebar: icon-only mode (w-16) + expanded mode (w-60). استخدم Zustand store الموجود في ui.store.js.",
      before: "w-72 (288px دايماً)",
      after: "w-16 collapsed / w-60 expanded — toggle من المحتوى",
    },
    {
      id: "I-08", severity: "high", category: "Medical UX",
      title: "PatientInfoCard مفيش تاريخ الميلاد أو حساب العمر أوتوماتيك",
      file: "src/features/patients/PatientInfoCard.jsx",
      detail: "patient.age بيتعرض كـ static number. لو المريض اتسجّل من سنتين والعمر 30 سنة، دلوقتي هيبقى 32 لكن البرنامج لسه بيقول 30. Jane App و Carepatron بيخزّنوا date_of_birth ويحسبوا العمر الحالي أوتوماتيك.",
      fix: "احسب العمر من date_of_birth في الـ display: const age = dob ? differenceInYears(new Date(), new Date(dob)) : patient.age",
      before: "patient.age ? `${patient.age} سنة` : 'غير معروف'",
      after: "calcAge(patient.date_of_birth) || patient.age + ' سنة'",
    },
    {
      id: "I-09", severity: "high", category: "Medical UX",
      title: "Kanban الـ 5 أعمدة بيحتاج scroll أفقي",
      file: "src/pages/Appointments.jsx — columns array",
      detail: "5 columns (Scheduled, Waiting, In-Chair, Completed, Cancelled) على شاشة 1366px بـ sidebar 288px = 155px لكل عمود. ده ضيق جداً وبيسبب text truncation. Dental Intel و Curve Dental بيستخدموا max 3-4 columns أو timeline view.",
      fix: "احذف عمود Cancelled من الـ Kanban واعمله filter منفصل. أو اعمل drag-and-drop مع vertical layout على المحمول.",
      before: "5 columns في نفس الوقت",
      after: "4 columns + Cancelled كـ collapsed section أو filter",
    },
    {
      id: "I-10", severity: "high", category: "Accessibility",
      title: "مفيش aria-labels على الأزرار icon-only",
      file: "Layout.jsx — Globe و Moon/Sun buttons",
      detail: 'أزرار تغيير اللغة والـ dark mode ليس فيها text مرئي ولا aria-label. قارئات الشاشة مش هتعرف تقول للمستخدم إيه اللي بيعمله الزرار. ده يخالف WCAG 2.1 AA.',
      fix: 'أضف aria-label على كل زرار icon-only: <button aria-label="تغيير اللغة">',
      before: '<button title={t("common.language")}><Globe /></button>',
      after: '<button aria-label={t("common.language")} title={t("common.language")}><Globe /></button>',
    },
    {
      id: "I-11", severity: "medium", category: "Missing Feature",
      title: "مفيش Breadcrumb في صفحة تفاصيل المريض",
      file: "src/pages/PatientDetails.jsx",
      detail: "لو المستخدم دخل على مريض من نتيجة بحث أو من صفحة تانية، مش عارف إنه في إيه. Jane App و Carepatron عندهم breadcrumb: المرضى › اسم المريض › التفاصيل. بيساعد في الـ navigation وبيحسن الـ context.",
      fix: "أضف Breadcrumb component بسيط في أول الصفحة: Patients > {patient.name}",
      before: "// لا يوجد breadcrumb",
      after: "<Breadcrumb items={[{ label: 'المرضى', to: '/patients' }, { label: patient.name }]} />",
    },
    {
      id: "I-12", severity: "medium", category: "Anti-pattern",
      title: "PriceListBadge بتعمل dynamic import داخل useEffect",
      file: "src/features/patients/PatientInfoCard.jsx — PriceListBadge",
      detail: "import('../../api').then(({ getPriceList }) => { getPriceList(...) }) — ده بيعمل API call لكل مريض تفتح صفحته لجلب اسم قائمة الأسعار. لو في 20 مريض بتفتحهم = 20 API call. الأصح إن الـ price lists تتجيب مرة واحدة وتتخزن في context أو React Query.",
      fix: "استخدم usePriceLists() hook مع React Query لجلب كل القوائم مرة واحدة وفلتر بالـ id.",
      before: "import('../../api').then(({ getPriceList }) => getPriceList(priceListId))",
      after: "const { data: priceLists } = usePriceLists(); // cached once globally",
    },
    {
      id: "I-13", severity: "medium", category: "UX Pattern",
      title: "مفيش skeleton loading في Kanban columns",
      file: "src/pages/Appointments.jsx",
      detail: "لما الـ appointments بتتحمّل بيظهر اللا شيء أو الـ columns فاضية. Jane App بتعرض skeleton cards جوه كل column أثناء التحميل. بيحسن الـ perceived performance بشكل كبير.",
      fix: "أضف SkeletonBox داخل كل column لما loading=true بدل ما تعرض column فاضي.",
      before: "// columns تبقى فاضية أثناء التحميل",
      after: "[...Array(2)].map(i => <SkeletonBox key={i} height='80px' className='rounded-xl' />)",
    },
    {
      id: "I-14", severity: "medium", category: "Typography",
      title: "خلط بين font-black و font-bold و font-semibold بدون hierarchy",
      file: "Dashboard.jsx, Patients.jsx, SmartDashboard.jsx",
      detail: "بتلاقي font-black على عناوين الكروت، font-bold على اسم المريض، font-semibold على نص تاني. مش فيه type scale واضح. Dental Intel مثلاً: H1=32 semibold، H2=24 semibold، body=14 regular، caption=12 medium.",
      fix: "حدد type scale: heading-xl=text-2xl font-bold، heading-lg=text-xl font-semibold، heading-md=text-base font-semibold، body=text-sm font-normal، caption=text-xs font-medium. طبّقه everywhere.",
      before: "text-3xl font-black + text-2xl font-bold + text-lg font-semibold (نفس المستوى)",
      after: "type scale واضح: 3 levels بس",
    },
    {
      id: "I-15", severity: "low", category: "Missing Feature",
      title: "مفيش keyboard shortcuts",
      file: "Layout.jsx, Patients.jsx, Appointments.jsx",
      detail: "كل منتجات dental management زي Dentrix و Curve Dental عندها shortcuts: N = مريض جديد، / = بحث، Esc = غلق modal. الـ dentist بيشتغل بسرعة ومحتاج keyboard navigation.",
      fix: "استخدم useHotkeys من react-hotkeys-hook. على الأقل: Ctrl+K للبحث، N لإضافة جديد، Esc لغلق.",
      before: "// لا يوجد shortcuts",
      after: "useHotkeys('ctrl+k', () => searchRef.current?.focus())",
    },
  ],
  quickWins: [
    { icon: "🎯", title: "استبدل window.confirm بـ ConfirmDialog", time: "30 دقيقة", impact: "high" },
    { icon: "↔️", title: "صلّح mr-2 إلى me-2 في Button.jsx", time: "5 دقائق", impact: "high" },
    { icon: "🎨", title: "استبدل indigo-600 بـ primary في SmartDashboard", time: "15 دقيقة", impact: "high" },
    { icon: "📦", title: "احذف CARD_COLORS العشوائية من PatientTable", time: "20 دقيقة", impact: "medium" },
    { icon: "🏷️", title: "أضف aria-label على أزرار اللغة والـ dark mode", time: "10 دقائق", impact: "medium" },
    { icon: "🔗", title: "أضف Breadcrumb في PatientDetails", time: "45 دقيقة", impact: "medium" },
    { icon: "📐", title: "وحّد border-radius على rounded-xl فقط", time: "60 دقيقة", impact: "high" },
  ]
};

const SEVERITY_CONFIG = {
  critical: { label: "حرج", color: "#ef4444", bg: "rgba(239,68,68,0.1)", border: "rgba(239,68,68,0.3)" },
  high: { label: "عالي", color: "#f59e0b", bg: "rgba(245,158,11,0.1)", border: "rgba(245,158,11,0.3)" },
  medium: { label: "متوسط", color: "#3b82f6", bg: "rgba(59,130,246,0.1)", border: "rgba(59,130,246,0.3)" },
  low: { label: "منخفض", color: "#10b981", bg: "rgba(16,185,129,0.1)", border: "rgba(16,185,129,0.3)" },
};

function ScoreBar({ label, score, color }) {
  return (
    <div style={{ marginBottom: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 6, alignItems: "center" }}>
        <span style={{ fontSize: 13, color: "#cbd5e1", fontFamily: "Cairo, sans-serif" }}>{label}</span>
        <span style={{ fontFamily: "monospace", fontSize: 13, fontWeight: 700, color }}>{score}/100</span>
      </div>
      <div style={{ height: 6, background: "#1e293b", borderRadius: 3, overflow: "hidden" }}>
        <div style={{
          height: "100%", width: `${score}%`, background: color, borderRadius: 3,
          transition: "width 1s cubic-bezier(.4,0,.2,1)"
        }} />
      </div>
    </div>
  );
}

function IssueCard({ issue, isOpen, onToggle }) {
  const cfg = SEVERITY_CONFIG[issue.severity];
  return (
    <div style={{
      border: `1px solid ${isOpen ? cfg.border : "#1e293b"}`,
      borderRadius: 12, overflow: "hidden", marginBottom: 8,
      background: isOpen ? cfg.bg : "#0f172a",
      transition: "all 0.2s"
    }}>
      <button
        onClick={onToggle}
        style={{
          width: "100%", padding: "14px 18px", display: "flex",
          alignItems: "center", gap: 12, background: "none", border: "none",
          cursor: "pointer", textAlign: "right", direction: "rtl"
        }}
      >
        <span style={{
          fontSize: 10, fontWeight: 700, padding: "3px 8px", borderRadius: 4,
          background: cfg.bg, color: cfg.color, border: `1px solid ${cfg.border}`,
          whiteSpace: "nowrap", flexShrink: 0
        }}>{cfg.label}</span>
        <span style={{
          fontSize: 10, color: "#475569", fontFamily: "monospace",
          background: "#1e293b", padding: "2px 6px", borderRadius: 3, flexShrink: 0
        }}>{issue.id}</span>
        <span style={{ flex: 1, fontSize: 14, fontWeight: 600, color: "#e2e8f0", fontFamily: "Cairo, sans-serif", textAlign: "right" }}>
          {issue.title}
        </span>
        <span style={{ color: "#475569", fontSize: 11, flexShrink: 0 }}>{issue.category}</span>
        <span style={{ color: "#475569", fontSize: 16, flexShrink: 0 }}>{isOpen ? "▲" : "▼"}</span>
      </button>

      {isOpen && (
        <div style={{ padding: "0 18px 18px", direction: "rtl" }}>
          <div style={{
            fontSize: 11, color: "#64748b", fontFamily: "monospace",
            background: "#0a0f1a", padding: "4px 8px", borderRadius: 4,
            marginBottom: 12, display: "inline-block"
          }}>📁 {issue.file}</div>

          <p style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.8, marginBottom: 14, fontFamily: "Cairo, sans-serif" }}>
            {issue.detail}
          </p>

          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10, marginBottom: 14 }}>
            {[
              { label: "❌ قبل", code: issue.before, bg: "rgba(239,68,68,0.08)", border: "rgba(239,68,68,0.2)" },
              { label: "✅ بعد", code: issue.after, bg: "rgba(16,185,129,0.08)", border: "rgba(16,185,129,0.2)" },
            ].map(item => (
              <div key={item.label} style={{ background: item.bg, border: `1px solid ${item.border}`, borderRadius: 8, padding: "10px 12px" }}>
                <div style={{ fontSize: 11, fontWeight: 700, color: "#64748b", marginBottom: 6 }}>{item.label}</div>
                <code style={{ fontSize: 11, color: "#e2e8f0", fontFamily: "monospace", lineHeight: 1.6, display: "block", wordBreak: "break-all" }}>
                  {item.code}
                </code>
              </div>
            ))}
          </div>

          <div style={{
            fontSize: 12, color: "#38bdf8", background: "rgba(56,189,248,0.08)",
            border: "1px solid rgba(56,189,248,0.2)", borderRadius: 8, padding: "10px 14px",
            fontFamily: "Cairo, sans-serif"
          }}>
            🔧 <strong>الحل:</strong> {issue.fix}
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [openIssue, setOpenIssue] = useState("I-01");
  const [filterSeverity, setFilterSeverity] = useState("all");
  const [activeTab, setActiveTab] = useState("overview");

  const filtered = filterSeverity === "all"
    ? data.issues
    : data.issues.filter(i => i.severity === filterSeverity);

  const totalScore = Math.round(data.scores.reduce((s, i) => s + i.score, 0) / data.scores.length);
  const criticalCount = data.issues.filter(i => i.severity === "critical").length;
  const highCount = data.issues.filter(i => i.severity === "high").length;

  return (
    <div style={{
      minHeight: "100vh", background: "#070c16",
      fontFamily: "Cairo, sans-serif", color: "#e2e8f0",
      direction: "rtl"
    }}>
      <style>{`
        @import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;500;600;700;900&display=swap');
        * { box-sizing: border-box; margin: 0; padding: 0; }
        ::-webkit-scrollbar { width: 4px; }
        ::-webkit-scrollbar-track { background: #0a0f1a; }
        ::-webkit-scrollbar-thumb { background: #1e3a5f; border-radius: 2px; }
        button { font-family: Cairo, sans-serif; }
      `}</style>

      {/* Header */}
      <div style={{
        borderBottom: "1px solid #1e293b", padding: "20px 32px",
        display: "flex", alignItems: "center", justifyContent: "space-between",
        background: "rgba(7,12,22,0.95)", position: "sticky", top: 0, zIndex: 100
      }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 4 }}>
            <div style={{
              width: 32, height: 32, borderRadius: 8,
              background: "linear-gradient(135deg, #0891B2, #6366f1)",
              display: "flex", alignItems: "center", justifyContent: "center", fontSize: 16
            }}>⬡</div>
            <span style={{ fontSize: 18, fontWeight: 900, color: "#f0f9ff" }}>DENTIX — تقرير مراجعة UI/UX</span>
          </div>
          <span style={{ fontSize: 12, color: "#475569" }}>مقارنة بـ Jane App · Carepatron · Dental Intel · Medifusion</span>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div style={{
            width: 64, height: 64, borderRadius: "50%",
            background: `conic-gradient(${totalScore >= 70 ? "#10b981" : totalScore >= 50 ? "#f59e0b" : "#ef4444"} ${totalScore * 3.6}deg, #1e293b 0deg)`,
            display: "flex", alignItems: "center", justifyContent: "center",
            position: "relative"
          }}>
            <div style={{
              width: 50, height: 50, borderRadius: "50%", background: "#070c16",
              display: "flex", alignItems: "center", justifyContent: "center",
              fontSize: 16, fontWeight: 900, color: "#f59e0b"
            }}>{totalScore}</div>
          </div>
          <div>
            <div style={{ fontSize: 12, color: "#64748b" }}>النتيجة الكلية</div>
            <div style={{ fontSize: 13, fontWeight: 700, color: "#f59e0b" }}>من 100 نقطة</div>
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ borderBottom: "1px solid #1e293b", padding: "0 32px", display: "flex", gap: 4 }}>
        {[
          { id: "overview", label: "📊 نظرة عامة" },
          { id: "issues", label: `🐛 المشاكل (${data.issues.length})` },
          { id: "competitors", label: "🏆 مقارنة بالمنافسين" },
          { id: "quickwins", label: "⚡ Quick Wins" },
        ].map(tab => (
          <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
            padding: "14px 18px", border: "none", background: "none", cursor: "pointer",
            fontSize: 13, fontWeight: 600,
            color: activeTab === tab.id ? "#38bdf8" : "#64748b",
            borderBottom: activeTab === tab.id ? "2px solid #38bdf8" : "2px solid transparent",
            transition: "all 0.2s"
          }}>{tab.label}</button>
        ))}
      </div>

      <div style={{ maxWidth: 960, margin: "0 auto", padding: "28px 24px" }}>

        {/* OVERVIEW TAB */}
        {activeTab === "overview" && (
          <div>
            {/* Summary Cards */}
            <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: 12, marginBottom: 28 }}>
              {[
                { label: "مشاكل حرجة", value: criticalCount, color: "#ef4444", icon: "🔴" },
                { label: "أولوية عالية", value: highCount, color: "#f59e0b", icon: "🟡" },
                { label: "إجمالي المشاكل", value: data.issues.length, color: "#94a3b8", icon: "📋" },
                { label: "Quick Wins متاحة", value: data.quickWins.length, color: "#10b981", icon: "⚡" },
              ].map(item => (
                <div key={item.label} style={{
                  background: "#0f172a", border: "1px solid #1e293b",
                  borderRadius: 12, padding: "16px", textAlign: "center"
                }}>
                  <div style={{ fontSize: 24, marginBottom: 6 }}>{item.icon}</div>
                  <div style={{ fontFamily: "monospace", fontSize: 28, fontWeight: 900, color: item.color, marginBottom: 4 }}>{item.value}</div>
                  <div style={{ fontSize: 12, color: "#64748b" }}>{item.label}</div>
                </div>
              ))}
            </div>

            {/* Score Bars */}
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 24 }}>
              <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 14, padding: "20px 24px" }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#94a3b8", marginBottom: 18, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                  تقييم المحاور
                </div>
                {data.scores.map(s => <ScoreBar key={s.label} {...s} />)}
              </div>

              <div>
                {/* Key Finding */}
                <div style={{
                  background: "linear-gradient(135deg, rgba(239,68,68,0.1), rgba(245,158,11,0.05))",
                  border: "1px solid rgba(239,68,68,0.25)",
                  borderRadius: 14, padding: "20px 24px", marginBottom: 14
                }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#ef4444", marginBottom: 10 }}>⚠️ أهم 3 مشاكل الآن</div>
                  {data.issues.filter(i => i.severity === "critical").slice(0, 3).map(issue => (
                    <div key={issue.id} style={{
                      display: "flex", alignItems: "flex-start", gap: 10,
                      padding: "8px 0", borderBottom: "1px solid rgba(255,255,255,0.05)"
                    }}>
                      <span style={{ fontFamily: "monospace", fontSize: 10, color: "#ef4444", flexShrink: 0, marginTop: 2 }}>{issue.id}</span>
                      <span style={{ fontSize: 13, color: "#cbd5e1" }}>{issue.title}</span>
                    </div>
                  ))}
                </div>

                <div style={{
                  background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)",
                  borderRadius: 14, padding: "20px 24px"
                }}>
                  <div style={{ fontSize: 13, fontWeight: 700, color: "#10b981", marginBottom: 10 }}>✅ إيه الكويس الموجود</div>
                  {[
                    "Prefetching on hover — فكرة احترافية نادرة",
                    "RTL + i18n infrastructure — أساس صح",
                    "React Query caching — performance صح",
                    "Skeleton loading states موجودة",
                    "Dark mode مع Zustand — clean implementation",
                  ].map((item, i) => (
                    <div key={i} style={{ fontSize: 12, color: "#94a3b8", padding: "5px 0", borderBottom: "1px solid rgba(255,255,255,0.05)" }}>
                      ✓ {item}
                    </div>
                  ))}
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ISSUES TAB */}
        {activeTab === "issues" && (
          <div>
            <div style={{ display: "flex", gap: 8, marginBottom: 20, flexWrap: "wrap" }}>
              {[
                { id: "all", label: "الكل", count: data.issues.length },
                { id: "critical", label: "حرج", count: data.issues.filter(i => i.severity === "critical").length },
                { id: "high", label: "عالي", count: data.issues.filter(i => i.severity === "high").length },
                { id: "medium", label: "متوسط", count: data.issues.filter(i => i.severity === "medium").length },
                { id: "low", label: "منخفض", count: data.issues.filter(i => i.severity === "low").length },
              ].map(f => (
                <button key={f.id} onClick={() => setFilterSeverity(f.id)} style={{
                  padding: "6px 14px", borderRadius: 8, border: "1px solid",
                  borderColor: filterSeverity === f.id ? "#38bdf8" : "#1e293b",
                  background: filterSeverity === f.id ? "rgba(56,189,248,0.12)" : "#0f172a",
                  color: filterSeverity === f.id ? "#38bdf8" : "#64748b",
                  fontSize: 13, fontWeight: 600, cursor: "pointer", transition: "all 0.2s"
                }}>
                  {f.label} ({f.count})
                </button>
              ))}
            </div>

            {filtered.map(issue => (
              <IssueCard
                key={issue.id}
                issue={issue}
                isOpen={openIssue === issue.id}
                onToggle={() => setOpenIssue(openIssue === issue.id ? null : issue.id)}
              />
            ))}
          </div>
        )}

        {/* COMPETITORS TAB */}
        {activeTab === "competitors" && (
          <div>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, marginBottom: 24 }}>
              {data.competitors.map(comp => (
                <div key={comp.name} style={{
                  background: "#0f172a", border: `1px solid ${comp.color}33`,
                  borderRadius: 14, padding: "20px 24px"
                }}>
                  <div style={{ display: "flex", alignItems: "center", gap: 10, marginBottom: 16 }}>
                    <span style={{
                      width: 36, height: 36, borderRadius: 8,
                      background: `${comp.color}22`, color: comp.color,
                      display: "flex", alignItems: "center", justifyContent: "center",
                      fontSize: 18
                    }}>{comp.region}</span>
                    <div>
                      <div style={{ fontSize: 16, fontWeight: 700, color: "#f0f9ff" }}>{comp.name}</div>
                    </div>
                  </div>
                  <div style={{ fontSize: 12, color: "#64748b", marginBottom: 10, textTransform: "uppercase", letterSpacing: "0.06em" }}>
                    بيتميز بـ
                  </div>
                  {comp.strengths.map((s, i) => (
                    <div key={i} style={{
                      display: "flex", alignItems: "center", gap: 8,
                      padding: "6px 0", borderBottom: "1px solid #1e293b",
                      fontSize: 13, color: "#94a3b8"
                    }}>
                      <span style={{ color: comp.color, fontSize: 10 }}>▶</span>
                      {s}
                    </div>
                  ))}
                </div>
              ))}
            </div>

            {/* Comparison Table */}
            <div style={{ background: "#0f172a", border: "1px solid #1e293b", borderRadius: 14, overflow: "hidden" }}>
              <div style={{ padding: "16px 24px", borderBottom: "1px solid #1e293b" }}>
                <div style={{ fontSize: 14, fontWeight: 700, color: "#94a3b8" }}>مقارنة الميزات مع المنافسين</div>
              </div>
              <div style={{ overflowX: "auto" }}>
                <table style={{ width: "100%", borderCollapse: "collapse" }}>
                  <thead>
                    <tr style={{ background: "#0a0f1a" }}>
                      {["الميزة", "DENTIX الحالي", "Jane App", "Carepatron", "Dental Intel"].map(h => (
                        <th key={h} style={{
                          padding: "12px 16px", textAlign: "right", fontSize: 12,
                          fontWeight: 700, color: "#64748b", textTransform: "uppercase",
                          letterSpacing: "0.05em", borderBottom: "1px solid #1e293b"
                        }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {[
                      ["Kanban مواعيد", "✅ 5 أعمدة", "✅ 4 + drag", "✅ Timeline", "✅ 3 أعمدة"],
                      ["Breadcrumb", "❌ غير موجود", "✅", "✅", "✅"],
                      ["Keyboard Shortcuts", "❌ غير موجود", "✅ N, /, Esc", "✅", "✅ موسّع"],
                      ["Confirm Dialog Custom", "❌ window.confirm", "✅", "✅", "✅"],
                      ["Sidebar Collapsible", "❌ ثابت 288px", "✅ icon mode", "✅", "✅"],
                      ["Patient Photo", "❌ حرف واحد", "✅ صورة حقيقية", "✅", "❌"],
                      ["Date of Birth → Age", "❌ manual age", "✅ auto-calc", "✅", "✅"],
                      ["RTL Native", "⚠️ جزئي", "❌", "❌", "❌"],
                      ["Prefetch on Hover", "✅ نادر!", "❌", "❌", "❌"],
                      ["Print Workflows", "✅ موجود", "✅", "✅", "✅ متطوّر"],
                    ].map(([feature, ...vals], ri) => (
                      <tr key={feature} style={{ background: ri % 2 === 0 ? "transparent" : "#0a0f1a" }}>
                        <td style={{ padding: "12px 16px", fontSize: 13, color: "#94a3b8", borderBottom: "1px solid #1e293b" }}>{feature}</td>
                        {vals.map((v, vi) => (
                          <td key={vi} style={{
                            padding: "12px 16px", fontSize: 13, borderBottom: "1px solid #1e293b",
                            color: v.startsWith("✅") ? "#10b981" : v.startsWith("❌") ? "#ef4444" : "#f59e0b",
                            textAlign: "right"
                          }}>{v}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* QUICK WINS TAB */}
        {activeTab === "quickwins" && (
          <div>
            <div style={{
              background: "rgba(16,185,129,0.08)", border: "1px solid rgba(16,185,129,0.2)",
              borderRadius: 12, padding: "16px 20px", marginBottom: 24,
              fontSize: 13, color: "#6ee7b7", fontWeight: 600
            }}>
              ⚡ الـ Quick Wins دي تقدر تخلص منها في يوم واحد وتأثيرها كبير على UX
            </div>

            {data.quickWins.map((win, i) => (
              <div key={i} style={{
                display: "flex", alignItems: "center", gap: 16,
                background: "#0f172a", border: "1px solid #1e293b",
                borderRadius: 12, padding: "16px 20px", marginBottom: 10,
                transition: "border-color 0.2s"
              }}
                onMouseEnter={e => e.currentTarget.style.borderColor = "#1e3a5f"}
                onMouseLeave={e => e.currentTarget.style.borderColor = "#1e293b"}
              >
                <span style={{ fontSize: 24, flexShrink: 0 }}>{win.icon}</span>
                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: 14, fontWeight: 600, color: "#e2e8f0", marginBottom: 4 }}>{win.title}</div>
                  <div style={{ display: "flex", gap: 10 }}>
                    <span style={{ fontSize: 11, color: "#64748b", fontFamily: "monospace" }}>⏱ {win.time}</span>
                  </div>
                </div>
                <span style={{
                  fontSize: 11, fontWeight: 700, padding: "4px 10px", borderRadius: 6,
                  background: win.impact === "high" ? "rgba(239,68,68,0.1)" : "rgba(245,158,11,0.1)",
                  color: win.impact === "high" ? "#ef4444" : "#f59e0b",
                  border: `1px solid ${win.impact === "high" ? "rgba(239,68,68,0.3)" : "rgba(245,158,11,0.3)"}`,
                  flexShrink: 0
                }}>
                  {win.impact === "high" ? "تأثير عالي" : "تأثير متوسط"}
                </span>
              </div>
            ))}

            <div style={{
              marginTop: 24, background: "#0f172a", border: "1px solid #1e3a5f",
              borderRadius: 14, padding: "20px 24px"
            }}>
              <div style={{ fontSize: 14, fontWeight: 700, color: "#38bdf8", marginBottom: 16 }}>
                🗺️ الخطة المقترحة بالترتيب
              </div>
              {[
                { phase: "اليوم 1", items: ["I-02: صلّح mr-2", "I-03: indigo → primary", "I-05: window.confirm", "I-10: aria-labels"], color: "#ef4444" },
                { phase: "اليوم 2-3", items: ["I-01: وحّد border-radius", "I-04: احذف CARD_COLORS", "I-11: Breadcrumb", "I-06: صلّح Logo"], color: "#f59e0b" },
                { phase: "الأسبوع القادم", items: ["I-07: Collapsible Sidebar", "I-08: DOB → Auto Age", "I-09: 4 Kanban columns", "I-15: Keyboard shortcuts"], color: "#10b981" },
              ].map(phase => (
                <div key={phase.phase} style={{ marginBottom: 16 }}>
                  <div style={{
                    fontSize: 12, fontWeight: 700, color: phase.color,
                    marginBottom: 8, display: "flex", alignItems: "center", gap: 8
                  }}>
                    <div style={{ width: 8, height: 8, borderRadius: "50%", background: phase.color }} />
                    {phase.phase}
                  </div>
                  <div style={{ display: "flex", gap: 8, flexWrap: "wrap", paddingRight: 16 }}>
                    {phase.items.map(item => (
                      <span key={item} style={{
                        fontSize: 12, color: "#94a3b8",
                        background: "#1e293b", padding: "4px 10px", borderRadius: 6
                      }}>{item}</span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
