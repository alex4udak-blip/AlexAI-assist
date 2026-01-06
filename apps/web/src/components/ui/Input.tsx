import { forwardRef, type InputHTMLAttributes } from 'react';
import { cn } from '../../lib/utils';

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  error?: string;
  label?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className, error, label, id, ...props }, ref) => {
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
        <input
          ref={ref}
          id={id}
          className={cn(
            'w-full bg-bg-tertiary border rounded-lg',
            'px-4 py-2.5 text-text-primary placeholder:text-text-muted',
            'focus:ring-1 transition-all duration-200 outline-none',
            error
              ? 'border-status-error focus:border-status-error focus:ring-status-error/30'
              : 'border-border-default focus:border-accent-primary focus:ring-accent-primary/30',
            className
          )}
          {...props}
        />
        {error && (
          <p className="mt-1.5 text-sm text-status-error">{error}</p>
        )}
      </div>
    );
  }
);

Input.displayName = 'Input';

export const Textarea = forwardRef<
  HTMLTextAreaElement,
  React.TextareaHTMLAttributes<HTMLTextAreaElement> & {
    error?: string;
    label?: string;
  }
>(({ className, error, label, id, ...props }, ref) => {
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
      <textarea
        ref={ref}
        id={id}
        className={cn(
          'w-full bg-bg-tertiary border rounded-lg',
          'px-4 py-2.5 text-text-primary placeholder:text-text-muted',
          'focus:ring-1 transition-all duration-200 outline-none resize-none',
          error
            ? 'border-status-error focus:border-status-error focus:ring-status-error/30'
            : 'border-border-default focus:border-accent-primary focus:ring-accent-primary/30',
          className
        )}
        {...props}
      />
      {error && <p className="mt-1.5 text-sm text-status-error">{error}</p>}
    </div>
  );
});

Textarea.displayName = 'Textarea';
