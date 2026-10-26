// HubsPage - A-04: hubs with their area and staff, and the delivery areas used by dispatch

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Alert, Badge, Button, Dialog, Loading, SelectField, Table, Td, TextField, Th } from "@/components/ui";
import { ApiError } from "@/lib/http";
import { errorMessage } from "@/lib/errors";
import { toast } from "@/lib/toast";
import type { AdminArea, AdminHub, AreaInput, HubInput } from "@/types";
import { listAdminHubs, listAreas, saveArea, saveHub } from "../api";

type Editing<T> = { id?: string; value: T } | null;

const EMPTY_HUB: HubInput = { code: "", name: "", address: "", lat: 10.85, lng: 106.75, area_id: "", status: "ACTIVE" };
const EMPTY_AREA: AreaInput = { code: "", name: "", center_lat: 10.85, center_lng: 106.75, radius_km: 3 };

function numberField(value: number, onChange: (value: number) => void, label: string, step = "0.000001") {
  return (
    <TextField
      compact
      type="number"
      step={step}
      label={label}
      value={Number.isFinite(value) ? value : ""}
      onChange={(event) => onChange(Number(event.target.value))}
    />
  );
}

export function HubsPage() {
  const queryClient = useQueryClient();
  const hubs = useQuery({ queryKey: ["admin", "hubs"], queryFn: listAdminHubs });
  const areas = useQuery({ queryKey: ["admin", "areas"], queryFn: listAreas });
  const [hub, setHub] = useState<Editing<HubInput>>(null);
  const [area, setArea] = useState<Editing<AreaInput>>(null);

  const refresh = () => {
    void queryClient.invalidateQueries({ queryKey: ["admin", "hubs"] });
    void queryClient.invalidateQueries({ queryKey: ["admin", "areas"] });
    void queryClient.invalidateQueries({ queryKey: ["hubs"] });
  };
  const hubSave = useMutation({
    mutationFn: ({ id, value }: { id?: string; value: HubInput }) => saveHub(value, id),
    onSuccess: (saved) => {
      toast.success(`Hub ${saved.name} saved.`);
      setHub(null);
      refresh();
    },
  });
  const areaSave = useMutation({
    mutationFn: ({ id, value }: { id?: string; value: AreaInput }) => saveArea(value, id),
    onSuccess: (saved) => {
      toast.success(`Area ${saved.name} saved.`);
      setArea(null);
      refresh();
    },
  });

  const editHub = (row: AdminHub) =>
    setHub({
      id: row.id,
      value: { code: row.code, name: row.name, address: row.address, lat: row.lat, lng: row.lng, area_id: row.area_id, status: row.status },
    });
  const editArea = (row: AdminArea) =>
    setArea({
      id: row.id,
      value: { code: row.code, name: row.name, center_lat: row.center_lat, center_lng: row.center_lng, radius_km: row.radius_km },
    });

  return (
    <>
      <PageHeader
        title="Hubs & areas"
        description="Hubs are where parcels wait for drivers; areas decide which hub a new order belongs to."
        actions={
          <>
            <Button variant="secondary" onClick={() => setArea({ value: EMPTY_AREA })}>
              New area
            </Button>
            <Button onClick={() => setHub({ value: { ...EMPTY_HUB, area_id: areas.data?.[0]?.id ?? "" } })}>New hub</Button>
          </>
        }
      />
      {hubs.isPending && <Loading />}
      {hubs.isError && <Alert tone="danger">{errorMessage(hubs.error)}</Alert>}
      {hubs.data && (
        <Table>
          <thead>
            <tr>
              <Th>Hub</Th>
              <Th>Area</Th>
              <Th>Position</Th>
              <Th>Staff</Th>
              <Th>Status</Th>
              <Th className="text-right">Actions</Th>
            </tr>
          </thead>
          <tbody>
            {hubs.data.map((row) => (
              <tr key={row.id}>
                <Td>
                  <p className="font-semibold">{row.name}</p>
                  <p className="text-xs text-neutral-600">
                    {row.code} - {row.address}
                  </p>
                </Td>
                <Td>{row.area_name}</Td>
                <Td className="text-xs tabular-nums">
                  {row.lat.toFixed(5)}, {row.lng.toFixed(5)}
                </Td>
                <Td>
                  {row.drivers} drivers, {row.managers} manager{row.managers === 1 ? "" : "s"}
                </Td>
                <Td>
                  <Badge tone={row.status === "ACTIVE" ? "success" : "neutral"}>{row.status === "ACTIVE" ? "Active" : "Inactive"}</Badge>
                </Td>
                <Td className="text-right">
                  <Button size="sm" variant="secondary" onClick={() => editHub(row)}>
                    Edit
                  </Button>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <h2 className="mt-8 mb-3 text-base font-semibold">Delivery areas</h2>
      {areas.data && (
        <Table>
          <thead>
            <tr>
              <Th>Area</Th>
              <Th>Centre</Th>
              <Th>Radius</Th>
              <Th>Neighbours</Th>
              <Th className="text-right">Actions</Th>
            </tr>
          </thead>
          <tbody>
            {areas.data.map((row) => (
              <tr key={row.id}>
                <Td>
                  <p className="font-semibold">{row.name}</p>
                  <p className="text-xs text-neutral-600">{row.code}</p>
                </Td>
                <Td className="text-xs tabular-nums">
                  {row.center_lat.toFixed(4)}, {row.center_lng.toFixed(4)}
                </Td>
                <Td>{row.radius_km} km</Td>
                <Td className="text-xs">{row.neighbor_codes.join(", ") || "-"}</Td>
                <Td className="text-right">
                  <Button size="sm" variant="secondary" onClick={() => editArea(row)}>
                    Edit
                  </Button>
                </Td>
              </tr>
            ))}
          </tbody>
        </Table>
      )}

      <Dialog
        open={Boolean(hub)}
        title={hub?.id ? "Edit hub" : "New hub"}
        onClose={() => setHub(null)}
        actions={
          <>
            <Button variant="secondary" onClick={() => setHub(null)}>
              Cancel
            </Button>
            <Button loading={hubSave.isPending} onClick={() => hub && hubSave.mutate({ id: hub.id, value: hub.value })}>
              Save
            </Button>
          </>
        }
      >
        {hub && (
          <div className="grid gap-3 sm:grid-cols-2">
            <TextField compact label="Code" value={hub.value.code} onChange={(e) => setHub({ ...hub, value: { ...hub.value, code: e.target.value.toUpperCase() } })} />
            <TextField compact label="Name" value={hub.value.name} onChange={(e) => setHub({ ...hub, value: { ...hub.value, name: e.target.value } })} />
            <div className="sm:col-span-2">
              <TextField compact label="Address" value={hub.value.address} onChange={(e) => setHub({ ...hub, value: { ...hub.value, address: e.target.value } })} />
            </div>
            {numberField(hub.value.lat, (lat) => setHub({ ...hub, value: { ...hub.value, lat } }), "Latitude")}
            {numberField(hub.value.lng, (lng) => setHub({ ...hub, value: { ...hub.value, lng } }), "Longitude")}
            <SelectField
              compact
              label="Area"
              options={(areas.data ?? []).map((item) => ({ value: item.id, label: item.name }))}
              value={hub.value.area_id}
              onChange={(e) => setHub({ ...hub, value: { ...hub.value, area_id: e.target.value } })}
            />
            <SelectField
              compact
              label="Status"
              options={[
                { value: "ACTIVE", label: "Active" },
                { value: "INACTIVE", label: "Inactive" },
              ]}
              value={hub.value.status ?? "ACTIVE"}
              onChange={(e) => setHub({ ...hub, value: { ...hub.value, status: e.target.value as HubInput["status"] } })}
            />
            {hubSave.isError && (
              <Alert tone="danger" className="sm:col-span-2">
                {hubSave.error instanceof ApiError && hubSave.error.code === "HUB_CODE_TAKEN"
                  ? "This hub code is already used."
                  : errorMessage(hubSave.error)}
              </Alert>
            )}
          </div>
        )}
      </Dialog>

      <Dialog
        open={Boolean(area)}
        title={area?.id ? "Edit area" : "New area"}
        onClose={() => setArea(null)}
        actions={
          <>
            <Button variant="secondary" onClick={() => setArea(null)}>
              Cancel
            </Button>
            <Button loading={areaSave.isPending} onClick={() => area && areaSave.mutate({ id: area.id, value: area.value })}>
              Save
            </Button>
          </>
        }
      >
        {area && (
          <div className="grid gap-3 sm:grid-cols-2">
            <TextField compact label="Code" value={area.value.code} onChange={(e) => setArea({ ...area, value: { ...area.value, code: e.target.value.toUpperCase() } })} />
            <TextField compact label="Name" value={area.value.name} onChange={(e) => setArea({ ...area, value: { ...area.value, name: e.target.value } })} />
            {numberField(area.value.center_lat, (center_lat) => setArea({ ...area, value: { ...area.value, center_lat } }), "Centre latitude")}
            {numberField(area.value.center_lng, (center_lng) => setArea({ ...area, value: { ...area.value, center_lng } }), "Centre longitude")}
            {numberField(area.value.radius_km, (radius_km) => setArea({ ...area, value: { ...area.value, radius_km } }), "Radius (km)", "0.1")}
            {areaSave.isError && (
              <Alert tone="danger" className="sm:col-span-2">
                {errorMessage(areaSave.error)}
              </Alert>
            )}
          </div>
        )}
      </Dialog>
    </>
  );
}
