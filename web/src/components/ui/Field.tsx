// Form fields - label, input/select/textarea, hint and error text (Figma auth inputs)

import {
  useId,
  useState,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
  type TextareaHTMLAttributes,
} from "react";
import { cn } from "@/lib/cn";

const CONTROL =
  "w-full rounded-input border bg-white px-4 text-sm text-ink placeholder:text-placeholder " +
  "outline-none transition-colors focus:border-primary-600 disabled:bg-neutral-100";

interface FieldShellProps {
  id: string;
  label?: string;
  hint?: string;
  error?: string;
  children: ReactNode;
}

function FieldShell({ id, label, hint, error, children }: FieldShellProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={id} className="text-xs text-ink">
          {label}
        </label>
      )}
      {children}
      {error ? (
        <p id={`${id}-error`} className="text-xs text-danger-500">
          {error}
        </p>
      ) : (
        hint && <p className="text-xs text-neutral-500">{hint}</p>
      )}
    </div>
  );
}

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
  prefix?: string;
  size?: never;
  compact?: boolean;
}

export function TextField({ label, hint, error, prefix, compact, className, id, ...props }: TextFieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  return (
    <FieldShell id={inputId} label={label} hint={hint} error={error}>
      <div className="relative">
        {prefix && (
          <span className="pointer-events-none absolute inset-y-0 left-4 flex items-center text-sm text-placeholder">
            {prefix}
          </span>
        )}
        <input
          id={inputId}
          aria-invalid={error ? true : undefined}
          aria-describedby={error ? `${inputId}-error` : undefined}
          className={cn(
            CONTROL,
            compact ? "h-10" : "h-[52px]",
            error ? "border-danger-500" : "border-line",
            prefix && "pl-14",
            className,
          )}
          {...props}
        />
      </div>
    </FieldShell>
  );
}

export function PasswordField(props: Omit<TextFieldProps, "type">) {
  const [visible, setVisible] = useState(false);
  return (
    <div className="relative">
      <TextField {...props} type={visible ? "text" : "password"} className="pr-16" />
      <button
        type="button"
        onClick={() => setVisible((value) => !value)}
        className={cn(
          "absolute right-3 text-xs font-semibold text-primary-600",
          props.label ? "top-[34px]" : "top-[17px]",
        )}
        aria-label={visible ? "Hide password" : "Show password"}
      >
        {visible ? "Hide" : "Show"}
      </button>
    </div>
  );
}

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  error?: string;
  compact?: boolean;
  options: { value: string; label: string }[];
  placeholder?: string;
}

export function SelectField({
  label,
  hint,
  error,
  compact,
  options,
  placeholder,
  className,
  id,
  ...props
}: SelectFieldProps) {
  const generatedId = useId();
  const selectId = id ?? generatedId;
  return (
    <FieldShell id={selectId} label={label} hint={hint} error={error}>
      <select
        id={selectId}
        aria-invalid={error ? true : undefined}
        className={cn(
          CONTROL,
          compact ? "h-10" : "h-[52px]",
          error ? "border-danger-500" : "border-line",
          className,
        )}
        {...props}
      >
        {placeholder !== undefined && <option value="">{placeholder}</option>}
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
    </FieldShell>
  );
}

interface TextAreaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export function TextAreaField({ label, hint, error, className, id, rows = 3, ...props }: TextAreaFieldProps) {
  const generatedId = useId();
  const areaId = id ?? generatedId;
  return (
    <FieldShell id={areaId} label={label} hint={hint} error={error}>
      <textarea
        id={areaId}
        rows={rows}
        aria-invalid={error ? true : undefined}
        aria-describedby={error ? `${areaId}-error` : undefined}
        className={cn(CONTROL, "py-3", error ? "border-danger-500" : "border-line", className)}
        {...props}
      />
    </FieldShell>
  );
}
