// FailForm - "Mark as undelivered" (D-08): reason, notes and an optional next delivery date.
// With a date the order is rescheduled; without one it goes back to the hub (BR17).

import { useState } from "react";
import { Alert, Button, SelectField, TextAreaField, TextField } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { businessDate } from "@/lib/format";
import { FAILURE_REASON, options } from "@/lib/labels";
import type { FailureReason } from "@/types";

export type FailValues = { reason: FailureReason; note: string | null; proposed_date: string | null };

type Props = {
  submitting: boolean;
  error: unknown;
  onSubmit: (values: FailValues) => void;
  onCancel?: () => void;
};

export function FailForm({ submitting, error, onSubmit, onCancel }: Props) {
  const [reason, setReason] = useState<FailureReason | "">("");
  const [note, setNote] = useState("");
  const [date, setDate] = useState("");

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        if (!reason) return;
        onSubmit({ reason, note: note.trim() || null, proposed_date: date || null });
      }}
    >
      <SelectField
        label="Reason"
        placeholder="Choose a reason"
        options={options(FAILURE_REASON)}
        value={reason}
        onChange={(event) => setReason(event.target.value as FailureReason)}
        required
      />
      <TextAreaField
        label="Add notes"
        placeholder="e.g. Customer asked to deliver after 18:00"
        value={note}
        onChange={(event) => setNote(event.target.value)}
        maxLength={500}
      />
      <TextField
        type="date"
        label="Select next delivery date"
        hint="Leave empty to bring the parcel back to the hub."
        min={businessDate(1)}
        max={businessDate(7)}
        value={date}
        onChange={(event) => setDate(event.target.value)}
      />
      {Boolean(error) && <Alert tone="danger">{errorMessage(error)}</Alert>}
      <div className="flex justify-end gap-2">
        {onCancel && (
          <Button variant="secondary" size="lg" onClick={onCancel}>
            Cancel
          </Button>
        )}
        <Button type="submit" size="lg" loading={submitting} disabled={!reason} className="flex-1">
          Confirm
        </Button>
      </div>
    </form>
  );
}
