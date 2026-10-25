// CreateOrdersPanel - send random orders or one typed order to H4T through the partner API

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, type FormEvent } from "react";
import { Alert, Button, Card, SelectField, TextField } from "@/components/ui";
import { listHubs } from "@/features/auth/api";
import { isValidPhone, normalizePhone } from "@/features/auth/validation";
import { errorMessage } from "@/lib/errors";
import { toast } from "@/lib/toast";
import { createManualOrder, createRandomOrders } from "../api";

const SHOP_BUTTON = "bg-shop-600 hover:bg-shop-700";

export function CreateOrdersPanel() {
  const queryClient = useQueryClient();
  const hubs = useQuery({ queryKey: ["hubs"], queryFn: listHubs });
  const hubOptions = (hubs.data ?? []).map((hub) => ({ value: hub.code, label: hub.name }));
  const [hubCode, setHubCode] = useState("DIAN");
  const [count, setCount] = useState("5");
  const [manual, setManual] = useState({ name: "", phone: "", address: "", item: "", express: false });
  const [manualError, setManualError] = useState<string>();

  const refresh = () => queryClient.invalidateQueries({ queryKey: ["shopnow"] });

  const random = useMutation({
    mutationFn: () => createRandomOrders(hubCode, Number(count)),
    onSuccess: (orders) => {
      toast.success(`${orders.length} orders sent to H4T Xpress.`);
      void refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const single = useMutation({
    mutationFn: () =>
      createManualOrder({
        hub_code: hubCode,
        recipient_name: manual.name.trim(),
        recipient_phone: normalizePhone(manual.phone),
        delivery_address: manual.address.trim(),
        items: [{ name: manual.item.trim() || "Parcel", qty: 1 }],
        priority: manual.express ? "EXPRESS" : "NORMAL",
        promised_in_hours: manual.express ? 4 : 8,
      }),
    onSuccess: (order) => {
      toast.success(`Order ${order.waybill_code} sent to H4T Xpress.`);
      setManual({ name: "", phone: "", address: "", item: "", express: false });
      void refresh();
    },
    onError: (error) => toast.error(errorMessage(error)),
  });

  const submitRandom = (event: FormEvent) => {
    event.preventDefault();
    random.mutate();
  };

  const submitManual = (event: FormEvent) => {
    event.preventDefault();
    if (manual.name.trim().length < 2 || !isValidPhone(manual.phone) || manual.address.trim().length < 5) {
      setManualError("Fill in the recipient name, a valid phone number and the address.");
      return;
    }
    setManualError(undefined);
    single.mutate();
  };

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <Card title="Generate orders">
        <form className="grid gap-4 sm:grid-cols-[1fr_120px]" onSubmit={submitRandom}>
          <SelectField compact label="Last-mile hub" options={hubOptions} value={hubCode} onChange={(event) => setHubCode(event.target.value)} />
          <TextField compact label="How many" type="number" min={1} max={20} value={count} onChange={(event) => setCount(event.target.value)} />
          <p className="text-xs text-neutral-600 sm:col-span-2">
            Random recipients and parcels around the hub, about 15% express.
          </p>
          <Button type="submit" className={`${SHOP_BUTTON} sm:col-span-2`} loading={random.isPending}>
            Send to H4T Xpress
          </Button>
        </form>
      </Card>

      <Card title="Create one order">
        <form className="grid gap-4 sm:grid-cols-2" onSubmit={submitManual} noValidate>
          {manualError && (
            <Alert tone="danger" className="sm:col-span-2">
              {manualError}
            </Alert>
          )}
          <TextField compact label="Recipient" value={manual.name} onChange={(event) => setManual({ ...manual, name: event.target.value })} />
          <TextField compact label="Phone" inputMode="tel" value={manual.phone} onChange={(event) => setManual({ ...manual, phone: event.target.value })} />
          <div className="sm:col-span-2">
            <TextField compact label="Delivery address" value={manual.address} onChange={(event) => setManual({ ...manual, address: event.target.value })} />
          </div>
          <TextField compact label="Item" placeholder="Parcel" value={manual.item} onChange={(event) => setManual({ ...manual, item: event.target.value })} />
          <label className="flex items-end gap-2 pb-2 text-sm">
            <input type="checkbox" checked={manual.express} onChange={(event) => setManual({ ...manual, express: event.target.checked })} />
            Express delivery (4 hours)
          </label>
          <Button type="submit" className={`${SHOP_BUTTON} sm:col-span-2`} loading={single.isPending}>
            Place order
          </Button>
        </form>
      </Card>
    </div>
  );
}
