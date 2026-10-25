// ShiftsPage - D-05 (UC-01): register or cancel shifts for the next 7 days

import { Alert, Badge, Button, Card, Loading } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDay, formatTime } from "@/lib/format";
import type { ShiftSlot } from "@/types";
import { useCancelRegistration, useRegisterShift, useShiftDays } from "../hooks";

const STATUS_LABEL: Record<ShiftSlot["status"], { label: string; tone: "success" | "neutral" | "warning" | "danger" | "primary" }> = {
  AVAILABLE: { label: "Available", tone: "primary" },
  REGISTERED: { label: "Registered", tone: "success" },
  FULL: { label: "Full", tone: "danger" },
  CLOSED: { label: "Closed", tone: "neutral" },
  CONFLICT: { label: "Overlaps", tone: "warning" },
};

export function ShiftsPage() {
  const days = useShiftDays();
  const register = useRegisterShift();
  const cancel = useCancelRegistration();
  const busy = register.isPending || cancel.isPending;

  if (days.isPending) return <Loading />;
  if (days.isError) return <Alert tone="danger">{errorMessage(days.error)}</Alert>;

  return (
    <div className="flex flex-col gap-4">
      <div>
        <h1 className="text-lg font-bold">My shifts</h1>
        <p className="text-sm text-neutral-600">
          Register before 06:00 on the day. Only drivers in a shift receive orders.
        </p>
      </div>
      {days.data.map((day) => (
        <Card key={day.work_date} title={formatDay(day.work_date)} className="p-4">
          <ul className="flex flex-col divide-y divide-line">
            {day.slots.map((slot) => {
              const status = STATUS_LABEL[slot.status];
              return (
                <li key={slot.shift_id} className="flex items-center justify-between gap-3 py-3">
                  <div>
                    <p className="font-medium">{slot.name}</p>
                    <p className="text-xs text-neutral-600">
                      {formatTime(slot.start_time)} - {formatTime(slot.end_time)}, {slot.taken}/
                      {slot.capacity} drivers
                    </p>
                  </div>
                  <div className="flex items-center gap-2">
                    <Badge tone={status.tone}>{status.label}</Badge>
                    {slot.status === "AVAILABLE" && (
                      <Button
                        size="sm"
                        disabled={busy}
                        onClick={() => register.mutate({ shiftId: slot.shift_id, workDate: day.work_date })}
                      >
                        Register
                      </Button>
                    )}
                    {slot.status === "REGISTERED" && slot.registration_id && (
                      <Button
                        size="sm"
                        variant="secondary"
                        disabled={busy}
                        onClick={() => cancel.mutate(slot.registration_id as string)}
                      >
                        Cancel
                      </Button>
                    )}
                  </div>
                </li>
              );
            })}
          </ul>
        </Card>
      ))}
    </div>
  );
}
