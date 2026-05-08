import{j as e,X as m}from"./vendor-ui-Cdn1MXMw.js";import{r as c}from"./vendor-react--W3J6lTe.js";function f({isOpen:s,onClose:a,title:d,children:r,maxWidth:l="max-w-md",scrollable:i=!0,className:n=""}){return c.useEffect(()=>{const t=o=>{o.key==="Escape"&&a()};return s&&(document.addEventListener("keydown",t),document.body.style.overflow="hidden"),()=>{document.removeEventListener("keydown",t),document.body.style.overflow="auto"}},[s,a]),s?e.jsx("div",{className:"fixed inset-0 bg-black/50 z-50 flex items-end md:items-center justify-center backdrop-blur-sm transition-opacity duration-300",onClick:t=>t.target===t.currentTarget&&a(),children:e.jsxs("div",{className:`
                bg-white dark:bg-slate-900 w-full ${l} 
                rounded-t-3xl md:rounded-3xl p-4 md:p-6 shadow-2xl 
                max-h-[95vh] md:max-h-[90vh] 
                ${i?"overflow-y-auto":"overflow-hidden flex flex-col"} 
                transition-all duration-300 
                animate-slide-up md:animate-in md:fade-in md:zoom-in-95 
                safe-bottom md:pb-6
                ${n}
            `,children:[e.jsxs("div",{className:"flex justify-between items-center mb-6 sticky top-0 bg-white dark:bg-slate-900 z-10 py-2 -mt-2",children:[e.jsx("div",{className:"w-12 h-1.5 bg-slate-200 rounded-full mx-auto md:hidden absolute -top-4 left-1/2 -translate-x-1/2 mb-4"}),e.jsx("h3",{className:"text-xl font-black text-slate-800 dark:text-white tracking-tight",children:d}),e.jsx("button",{onClick:a,className:"p-2 hover:bg-slate-100 rounded-xl text-slate-400 hover:text-slate-600 transition-colors",children:e.jsx(m,{size:20})})]}),e.jsx("div",{className:"relative",children:r})]})}):null}export{f as M};
