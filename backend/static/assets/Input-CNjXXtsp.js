import{j as e}from"./vendor-ui-Cdn1MXMw.js";import{r as l}from"./vendor-react--W3J6lTe.js";const p=({label:s,error:t,icon:r,type:i="text",className:o="",containerClassName:a="",...n})=>e.jsxs("div",{className:`space-y-1.5 ${a}`,children:[s&&e.jsx("label",{className:"block text-sm font-bold text-text-secondary",children:s}),e.jsxs("div",{className:"relative group",children:[r&&e.jsx("div",{className:"absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none text-slate-400 group-focus-within:text-primary transition-colors",children:l.isValidElement(r)?r:e.jsx(r,{size:18})}),e.jsx("input",{type:i,className:`
                        w-full rounded-xl border bg-input text-text-primary outline-none transition-all duration-200
                        placeholder:text-slate-400
                        ${r?"pr-10 pl-3":"px-3"}
                        ${t?"border-red-500 focus:border-red-500 focus:ring-1 focus:ring-red-500":"border-border focus:border-primary focus:ring-1 focus:ring-primary hover:border-slate-300 dark:hover:border-slate-600"}
                        py-2.5
                        ${o}
                    `,...n})]}),t&&e.jsx("p",{className:"text-xs text-red-500 font-medium animate-in slide-in-from-top-1",children:t})]});export{p as I};
