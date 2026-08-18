import React from 'react';
import * as TooltipPrimitive from '@radix-ui/react-tooltip';

const TooltipContent = React.forwardRef(({ className = '', sideOffset = 6, ...props }, ref) => (
  <TooltipPrimitive.Portal>
    <TooltipPrimitive.Content
      ref={ref}
      sideOffset={sideOffset}
      className={`z-popover overflow-hidden rounded-control border border-border bg-surface-elevated px-3 py-1.5 text-xs font-semibold text-text-primary shadow-medium ${className}`}
      {...props}
    />
  </TooltipPrimitive.Portal>
));
TooltipContent.displayName = TooltipPrimitive.Content.displayName;

const Tooltip = ({ children, content, side = 'top', align = 'center', ...props }) => (
  <TooltipPrimitive.Provider delayDuration={300} skipDelayDuration={100}>
    <TooltipPrimitive.Root>
      <TooltipPrimitive.Trigger asChild>{children}</TooltipPrimitive.Trigger>
      <TooltipContent side={side} align={align} {...props}>
        {content}
        <TooltipPrimitive.Arrow className="fill-surface-elevated" />
      </TooltipContent>
    </TooltipPrimitive.Root>
  </TooltipPrimitive.Provider>
);

export default Tooltip;
export { Tooltip as DentixTooltip };
