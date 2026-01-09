import { forwardRef, type SelectHTMLAttributes, type ReactNode } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '../../lib/utils';

interface SelectProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  error?: string;
  options?: { value: string; label: string }[];
  children?: ReactNode;
}

export const Select = forwardRef<HTMLSelectElement, SelectProps>(
  ({ className, label, error, options, children, id, ...props }, ref) => {
    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={id}
            className="block text-sm font-medium text-text-secondary mb-1.5"
          >
            {label}
          </label>
        )}
        <div className="relative">
          <select
            ref={ref}
            id={id}
            className={cn(
              'w-full appearance-none bg-bg-tertiary border rounded-lg',
              'px-4 py-2.5 pr-10 text-text-primary',
              'focus:ring-1 transition-all duration-200 outline-none cursor-pointer',
              error
                ? 'border-status-error focus:border-status-error focus:ring-status-error/30'
                : 'border-border-default focus:border-accent-primary focus:ring-accent-primary/30',
              className
            )}
            {...props}
          >
            {options
              ? options.map((option) => (
                  <option key={option.value} value={option.value}>
                    {option.label}
                  </option>
                ))
              : children}
          </select>
          <ChevronDown className="absolute right-3 top-1/2 -translate-y-1/2 w-5 h-5 text-text-muted pointer-events-none" />
        </div>
        {error && <p className="mt-1.5 text-sm text-status-error">{error}</p>}
      </div>
    );
  }
);

Select.displayName = 'Select';
