// TemporaryPasswordDialog - shows a generated password once, with a copy button

import { useState } from "react";
import { Button, Dialog } from "@/components/ui";

interface Props {
  password: string | null;
  email: string;
  onClose: () => void;
}

export function TemporaryPasswordDialog({ password, email, onClose }: Props) {
  const [copied, setCopied] = useState(false);

  const copy = async () => {
    if (!password) return;
    await navigator.clipboard.writeText(password);
    setCopied(true);
  };

  return (
    <Dialog
      open={Boolean(password)}
      title="Temporary password"
      onClose={onClose}
      actions={
        <>
          <Button variant="secondary" onClick={copy}>
            {copied ? "Copied" : "Copy"}
          </Button>
          <Button onClick={onClose}>Done</Button>
        </>
      }
    >
      <p>
        Give this password to <strong>{email}</strong>. It is shown only once; the user can change it
        after signing in.
      </p>
      <p className="mt-4 rounded-input border border-line bg-neutral-50 px-4 py-3 text-center font-mono text-base font-semibold tracking-wide">
        {password}
      </p>
    </Dialog>
  );
}
