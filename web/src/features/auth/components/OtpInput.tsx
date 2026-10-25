// OtpInput - six single-digit boxes; handles typing, paste and SMS autofill (Figma "Verify")

import { useRef, type ClipboardEvent, type KeyboardEvent } from "react";
import { cn } from "@/lib/cn";

interface OtpInputProps {
  value: string;
  onChange: (value: string) => void;
  length?: number;
  invalid?: boolean;
}

export function OtpInput({ value, onChange, length = 6, invalid }: OtpInputProps) {
  const inputs = useRef<(HTMLInputElement | null)[]>([]);
  const digits = Array.from({ length }, (_, index) => value[index] ?? "");

  const focus = (index: number) => inputs.current[Math.max(0, Math.min(index, length - 1))]?.focus();

  /** Write `typed` starting at `index`; several digits at once come from paste or autofill. */
  const fillFrom = (index: number, typed: string) => {
    const next = digits.slice();
    typed.split("").forEach((digit, offset) => {
      if (index + offset < length) next[index + offset] = digit;
    });
    onChange(next.join("").slice(0, length));
    focus(index + typed.length);
  };

  const handleChange = (index: number, raw: string) => {
    const typed = raw.replace(/\D/g, "");
    if (!typed) {
      const next = digits.slice();
      next[index] = "";
      onChange(next.join(""));
      return;
    }
    fillFrom(index, typed);
  };

  const handleKeyDown = (index: number, event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "Backspace" && !digits[index] && index > 0) {
      event.preventDefault();
      const next = digits.slice();
      next[index - 1] = "";
      onChange(next.join(""));
      focus(index - 1);
    }
  };

  const handlePaste = (index: number, event: ClipboardEvent<HTMLInputElement>) => {
    const pasted = event.clipboardData.getData("text").replace(/\D/g, "");
    if (pasted) {
      event.preventDefault();
      fillFrom(index, pasted);
    }
  };

  return (
    <div className="flex justify-between gap-2" role="group" aria-label="Verification code">
      {digits.map((digit, index) => (
        <input
          key={index}
          ref={(element) => {
            inputs.current[index] = element;
          }}
          inputMode="numeric"
          autoComplete={index === 0 ? "one-time-code" : "off"}
          value={digit}
          aria-label={`Digit ${index + 1}`}
          // Selecting on focus makes a new keystroke replace the digit instead of appending.
          onFocus={(event) => event.target.select()}
          onChange={(event) => handleChange(index, event.target.value)}
          onKeyDown={(event) => handleKeyDown(index, event)}
          onPaste={(event) => handlePaste(index, event)}
          className={cn(
            "h-12 w-11 rounded-input border text-center font-display text-lg font-semibold outline-none",
            "focus:border-primary-600",
            invalid ? "border-danger-500" : "border-line",
          )}
        />
      ))}
    </div>
  );
}
