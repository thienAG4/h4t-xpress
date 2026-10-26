// ShiftsPage - A-05: shift times and capacity per hub, with today's registrations

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Alert, Button, Loading, SelectField, Switch, Table, Td, TextField, Th } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatTime } from "@/lib/format";
import { toast } from "@/lib/toast";
import type { AdminShift } from "@/types";
import { listAdminHubs, listShifts, updateShift } from "../api";

function ShiftRow({ shift }: { shift: AdminShift }) {
  const queryClient = useQueryClient();
  const [start, setStart] = useState(formatTime(shift.start_time));
  const [end, setEnd] = useState(formatTime(shift.end_time));
  const [capacity, setCapacity] = useState(shift.capacity);
  const save = useMutation({
    mutationFn: (active: boolean) =>
      updateShift(shift.id, { start_time: `${start}:00`, end_time: `${end}:00`, capacity, is_active: active }),
    onSuccess: (saved) => {
      toast.success(`${saved.hub_name}: ${saved.name} shift saved.`);
      void queryClient.invalidateQueries({ queryKey: ["admin", "shifts"] });
    },
    onError: (error) => toast.error(errorMessage(error)),
  });
  const dirty =
    start !== formatTime(shift.start_time) || end !== formatTime(shift.end_time) || capacity !== shift.capacity;

  return (
    <tr>
      <Td>
        <p className="font-semibold">{shift.name}</p>
        <p className="text-xs text-neutral-600">{shift.hub_name}</p>
      </Td>
      <Td className="w-32">
        <TextField compact type="time" aria-label="Start" value={start} onChange={(e) => setStart(e.target.value)} />
      </Td>
      <Td className="w-32">
        <TextField compact type="time" aria-label="End" value={end} onChange={(e) => setEnd(e.target.value)} />
      </Td>
      <Td className="w-28">
        <TextField
          compact
          type="number"
          min={1}
          aria-label="Capacity"
          value={capacity}
          onChange={(e) => setCapacity(Number(e.target.value))}
        />
      </Td>
      <Td className="tabular-nums">
        {shift.registered_today} / {shift.capacity}
      </Td>
      <Td>
        <Switch label={`${shift.name} active`} checked={shift.is_active} disabled={save.isPending} onChange={(active) => save.mutate(active)} />
      </Td>
      <Td className="text-right">
        <Button size="sm" disabled={!dirty} loading={save.isPending} onClick={() => save.mutate(shift.is_active)}>
          Save
        </Button>
      </Td>
    </tr>
  );
}

export function ShiftsPage() {
  const [hubId, setHubId] = useState("");
  const hubs = useQuery({ queryKey: ["admin", "hubs"], queryFn: listAdminHubs });
  const shifts = useQuery({ queryKey: ["admin", "shifts", hubId], queryFn: () => listShifts(hubId || undefined) });

  return (
    <>
      <PageHeader
        title="Shifts"
        description="Drivers register for these shifts (UC-01). Capacity limits how many can register per day."
        actions={
          <div className="w-56">
            <SelectField
              compact
              aria-label="Hub"
              placeholder="All hubs"
              options={(hubs.data ?? []).map((hub) => ({ value: hub.id, label: hub.name }))}
              value={hubId}
              onChange={(event) => setHubId(event.target.value)}
            />
          </div>
        }
      />
      {shifts.isPending && <Loading />}
      {shifts.isError && <Alert tone="danger">{errorMessage(shifts.error)}</Alert>}
      {shifts.data && (
        <Table>
          <thead>
            <tr>
              <Th>Shift</Th>
              <Th>Start</Th>
              <Th>End</Th>
              <Th>Capacity</Th>
              <Th>Today</Th>
              <Th>Active</Th>
              <Th className="text-right">Actions</Th>
            </tr>
          </thead>
          <tbody>
            {shifts.data.map((shift) => (
              // Keyed by the saved values so a successful save resets the row.
              <ShiftRow key={`${shift.id}-${shift.start_time}-${shift.end_time}-${shift.capacity}`} shift={shift} />
            ))}
          </tbody>
        </Table>
      )}
    </>
  );
}
