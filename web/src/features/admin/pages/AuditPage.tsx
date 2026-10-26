// AuditPage - A-07: who changed what and when (admin actions, settings, reports, hubs)

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { Fragment, useState } from "react";
import { PageHeader } from "@/components/PageHeader";
import { Alert, Button, EmptyState, Loading, Pagination, SelectField, Table, Td, Th } from "@/components/ui";
import { errorMessage } from "@/lib/errors";
import { formatDateTime } from "@/lib/format";
import { listAuditLogs, type AuditFilters } from "../api";

const ACTIONS = [
  { value: "user.", label: "User accounts" },
  { value: "role.", label: "Roles and permissions" },
  { value: "setting.", label: "Settings" },
  { value: "hub.", label: "Hubs" },
  { value: "area.", label: "Areas" },
  { value: "shift.", label: "Shifts" },
  { value: "report.", label: "Report exports" },
];

export function AuditPage() {
  const [filters, setFilters] = useState<AuditFilters>({ page: 1, page_size: 20 });
  const [open, setOpen] = useState<string | null>(null);
  const logs = useQuery({
    queryKey: ["admin", "audit", filters],
    queryFn: () => listAuditLogs(filters),
    placeholderData: keepPreviousData,
  });

  return (
    <>
      <PageHeader
        title="Audit log"
        description="Every change made by administrators and hub managers, newest first."
        actions={
          <div className="w-56">
            <SelectField
              compact
              aria-label="Action"
              placeholder="All actions"
              options={ACTIONS}
              value={filters.action ?? ""}
              onChange={(event) => setFilters({ ...filters, page: 1, action: event.target.value || undefined })}
            />
          </div>
        }
      />
      {logs.isPending && <Loading />}
      {logs.isError && <Alert tone="danger">{errorMessage(logs.error)}</Alert>}
      {logs.data?.items.length === 0 && <EmptyState title="Nothing recorded yet" />}
      {logs.data && logs.data.items.length > 0 && (
        <>
          <Table>
            <thead>
              <tr>
                <Th>When</Th>
                <Th>Who</Th>
                <Th>Action</Th>
                <Th>Target</Th>
                <Th>IP</Th>
                <Th className="text-right">Details</Th>
              </tr>
            </thead>
            <tbody>
              {logs.data.items.map((entry) => (
                <Fragment key={entry.id}>
                  <tr>
                    <Td className="whitespace-nowrap">{formatDateTime(entry.created_at)}</Td>
                    <Td>{entry.actor_name ?? "System"}</Td>
                    <Td className="font-mono text-xs">{entry.action}</Td>
                    <Td className="text-xs">
                      {entry.entity_type}
                      {entry.entity_id && <span className="block text-neutral-500">{entry.entity_id}</span>}
                    </Td>
                    <Td className="text-xs">{entry.ip ?? "-"}</Td>
                    <Td className="text-right">
                      <Button size="sm" variant="ghost" onClick={() => setOpen(open === entry.id ? null : entry.id)}>
                        {open === entry.id ? "Hide" : "Show"}
                      </Button>
                    </Td>
                  </tr>
                  {open === entry.id && (
                    <tr>
                      <Td colSpan={6} className="bg-neutral-50">
                        <div className="grid gap-4 md:grid-cols-2">
                          <div>
                            <p className="text-xs font-semibold text-neutral-600">Before</p>
                            <pre className="mt-1 overflow-x-auto text-xs">{JSON.stringify(entry.before, null, 2) ?? "-"}</pre>
                          </div>
                          <div>
                            <p className="text-xs font-semibold text-neutral-600">After</p>
                            <pre className="mt-1 overflow-x-auto text-xs">{JSON.stringify(entry.after, null, 2) ?? "-"}</pre>
                          </div>
                        </div>
                      </Td>
                    </tr>
                  )}
                </Fragment>
              ))}
            </tbody>
          </Table>
          <Pagination
            page={filters.page}
            pageSize={filters.page_size}
            total={logs.data.total}
            onChange={(page) => setFilters({ ...filters, page })}
          />
        </>
      )}
    </>
  );
}
