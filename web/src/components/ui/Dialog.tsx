// Dialog - modal for confirmations and one-time information (native <dialog> element)

import { useEffect, useId, useRef, type ReactNode } from "react";

interface DialogProps {
  open: boolean;
  title: string;
  onClose: () => void;
  children: ReactNode;
  actions?: ReactNode;
}

export function Dialog({ open, title, onClose, children, actions }: DialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) dialog.showModal();
    if (!open && dialog.open) dialog.close();
  }, [open]);

  return (
    <dialog
      ref={ref}
      onClose={onClose}
      onCancel={onClose}
      aria-labelledby={titleId}
      className="m-auto w-[min(92vw,440px)] rounded-card border border-line bg-white p-0 text-ink shadow-xl backdrop:bg-neutral-900/40"
    >
      <div className="p-6">
        <h2 id={titleId} className="text-lg font-semibold">
          {title}
        </h2>
        <div className="mt-3 text-sm text-neutral-700">{children}</div>
      </div>
      {actions && (
        <div className="flex justify-end gap-2 border-t border-line bg-neutral-50 px-6 py-4">
          {actions}
        </div>
      )}
    </dialog>
  );
}
