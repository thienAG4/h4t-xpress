// ScanDialog - D-09: confirm the parcel in hand by its waybill code (BR8).
// The web app has no barcode reader, so the driver types the code printed under the barcode.

import { useState } from "react";
import { Button, Dialog, TextField } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import type { DriverOrder } from "@/types";
import { useScanOrder } from "../hooks";

type Props = {
  order: DriverOrder | null;
  onClose: () => void;
};

export function ScanDialog({ order, onClose }: Props) {
  return (
    <Dialog open={Boolean(order)} title="Scan parcel" onClose={onClose}>
      {/* Keyed so each parcel starts with an empty field. */}
      {order && <ScanForm key={order.id} order={order} onDone={onClose} />}
    </Dialog>
  );
}

function ScanForm({ order, onDone }: { order: DriverOrder; onDone: () => void }) {
  const scan = useScanOrder();
  const [code, setCode] = useState("");

  return (
    <form
      className="flex flex-col gap-4"
      onSubmit={(event) => {
        event.preventDefault();
        scan.mutate({ orderId: order.id, waybillCode: code.trim() }, { onSuccess: onDone });
      }}
    >
      <p>
        Type the waybill code printed under the barcode of parcel{" "}
        <span className="font-semibold">{order.waybill_code}</span>
        {order.handover_from ? `, handed over by ${order.handover_from}` : ""}.
      </p>
      <TextField
        label="Waybill code"
        autoFocus
        autoCapitalize="characters"
        placeholder="e.g. H4T00012345"
        value={code}
        onChange={(event) => setCode(event.target.value.toUpperCase())}
        error={scan.isError ? errorMessage(scan.error) : undefined}
      />
      <div className="flex justify-end gap-2">
        <Button variant="secondary" onClick={onDone}>
          Cancel
        </Button>
        <Button type="submit" loading={scan.isPending} disabled={code.trim().length < 4}>
          Confirm
        </Button>
      </div>
    </form>
  );
}
