// SettingsPage - A-06: business parameters grouped by area. Each value is edited with a
// control that fits its type and validated again by the server (SETTING_INVALID).

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Alert, Button, Card, Loading, Switch, TextField } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { toast } from "@/lib/toast";
import type { Setting } from "@/types";
import { listSettings, updateSetting } from "../api";

const GROUPS: Record<string, string> = {
  dispatch: "Dispatch (BR4-BR8)",
  eta: "ETA and traffic",
  sla: "Service level",
  delivery: "Delivery",
  shift: "Shifts",
  anomaly: "Anomaly detection (BR12)",
  sim: "Demo simulator",
};
const WEIGHT_KEYS = ["distance", "load", "performance", "time_fit"] as const;

type Rule = { from: string; to: string; factor: number };

function title(key: string): string {
  const name = key.split(".").slice(1).join(" ").replaceAll("_", " ");
  return name.charAt(0).toUpperCase() + name.slice(1);
}

function SettingEditor({ setting }: { setting: Setting }) {
  const queryClient = useQueryClient();
  const [draft, setDraft] = useState<unknown>(setting.value);
  const save = useMutation({
    mutationFn: (value: unknown) => updateSetting(setting.key, value),
    onSuccess: (saved) => {
      toast.success(`${title(saved.key)} saved.`);
      void queryClient.invalidateQueries({ queryKey: ["admin", "settings"] });
    },
  });
  const dirty = JSON.stringify(draft) !== JSON.stringify(setting.value);

  let control;
  if (typeof setting.value === "boolean") {
    control = <Switch label={title(setting.key)} checked={Boolean(draft)} onChange={(value) => save.mutate(value)} disabled={save.isPending} />;
  } else if (typeof setting.value === "number") {
    control = (
      <div className="w-36">
        <TextField compact type="number" step="any" aria-label={title(setting.key)} value={String(draft)} onChange={(e) => setDraft(Number(e.target.value))} />
      </div>
    );
  } else if (typeof setting.value === "string") {
    control = (
      <div className="w-36">
        <TextField compact aria-label={title(setting.key)} value={String(draft)} onChange={(e) => setDraft(e.target.value)} />
      </div>
    );
  } else if (setting.key === "dispatch.weights") {
    const weights = draft as Record<string, number>;
    const total = WEIGHT_KEYS.reduce((sum, key) => sum + (Number(weights[key]) || 0), 0);
    control = (
      <div className="flex flex-wrap items-end gap-2">
        {WEIGHT_KEYS.map((key) => (
          <div key={key} className="w-28">
            <TextField
              compact
              type="number"
              step="0.05"
              label={key.replace("_", " ")}
              value={String(weights[key])}
              onChange={(e) => setDraft({ ...weights, [key]: Number(e.target.value) })}
            />
          </div>
        ))}
        <p className={total === 1 ? "pb-2 text-xs text-neutral-600" : "pb-2 text-xs text-danger-700"}>Total {total.toFixed(2)} (must be 1)</p>
      </div>
    );
  } else if (setting.key === "eta.traffic_factors") {
    const rules = draft as Rule[];
    const set = (index: number, patch: Partial<Rule>) => setDraft(rules.map((rule, i) => (i === index ? { ...rule, ...patch } : rule)));
    control = (
      <div className="flex flex-col gap-2">
        {rules.map((rule, index) => (
          <div key={index} className="flex flex-wrap items-end gap-2">
            <div className="w-28">
              <TextField compact type="time" label="From" value={rule.from} onChange={(e) => set(index, { from: e.target.value })} />
            </div>
            <div className="w-28">
              <TextField compact type="time" label="To" value={rule.to} onChange={(e) => set(index, { to: e.target.value })} />
            </div>
            <div className="w-24">
              <TextField compact type="number" step="0.1" label="Factor" value={String(rule.factor)} onChange={(e) => set(index, { factor: Number(e.target.value) })} />
            </div>
            <Button size="sm" variant="ghost" onClick={() => setDraft(rules.filter((_, i) => i !== index))}>
              Remove
            </Button>
          </div>
        ))}
        <Button size="sm" variant="secondary" className="self-start" onClick={() => setDraft([...rules, { from: "11:00", to: "13:00", factor: 1.2 }])}>
          Add time window
        </Button>
      </div>
    );
  } else {
    control = <pre className="text-xs">{JSON.stringify(setting.value)}</pre>;
  }

  return (
    <li className="flex flex-col gap-3 border-t border-line py-4 first:border-t-0 first:pt-0 md:flex-row md:items-start md:justify-between">
      <div className="max-w-md">
        <p className="font-semibold">{title(setting.key)}</p>
        <p className="text-xs text-neutral-600">{setting.description}</p>
        <p className="mt-1 font-mono text-[11px] text-neutral-400">
          {setting.key}
          {setting.updated_at ? ` - saved ${formatDateTime(setting.updated_at)}` : ""}
        </p>
        {save.isError && <Alert tone="danger" className="mt-2">{errorMessage(save.error)}</Alert>}
      </div>
      <div className="flex flex-wrap items-end gap-2">
        {control}
        {typeof setting.value !== "boolean" && (
          <Button size="sm" disabled={!dirty} loading={save.isPending} onClick={() => save.mutate(draft)}>
            Save
          </Button>
        )}
      </div>
    </li>
  );
}

export function SettingsPage() {
  const settings = useQuery({ queryKey: ["admin", "settings"], queryFn: listSettings });
  // Business order (dispatch first), not alphabetical; unknown groups go last.
  const order = Object.keys(GROUPS);
  const rank = (group: string) => (order.includes(group) ? order.indexOf(group) : order.length);
  const groups = new Map<string, Setting[]>();
  for (const setting of [...(settings.data ?? [])].sort((a, b) => rank(a.group) - rank(b.group))) {
    groups.set(setting.group, [...(groups.get(setting.group) ?? []), setting]);
  }

  return (
    <>
      <PageHeader
        title="Settings"
        description="Changes apply to the next dispatch round or ETA refresh. Every change is recorded in the audit log."
      />
      {settings.isPending && <Loading />}
      {settings.isError && <Alert tone="danger">{errorMessage(settings.error)}</Alert>}
      <div className="flex flex-col gap-6">
        {[...groups.entries()].map(([group, rows]) => (
          <Card key={group} title={GROUPS[group] ?? group}>
            <ul>
              {rows.map((setting) => (
                // Keyed by the saved value so the draft resets after a save.
                <SettingEditor key={`${setting.key}-${JSON.stringify(setting.value)}`} setting={setting} />
              ))}
            </ul>
          </Card>
        ))}
      </div>
    </>
  );
}
