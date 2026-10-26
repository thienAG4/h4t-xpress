// Reports API - E-01 data in one call, E-02 export as Excel or PDF

import { downloadFile, request, type Query } from "@/lib/http";
import type { Granularity, Report } from "@/types";

export type ReportFilters = {
  date_from: string;
  date_to: string;
  hub_ids: string[];
  granularity?: Granularity;
};

function query(filters: ReportFilters): Query {
  return {
    date_from: filters.date_from,
    date_to: filters.date_to,
    hub_ids: filters.hub_ids,
    granularity: filters.granularity,
  };
}

export function fetchReport(filters: ReportFilters): Promise<Report> {
  return request<Report>("/reports", { query: query(filters) });
}

export function exportReport(filters: ReportFilters, format: "xlsx" | "pdf"): Promise<void> {
  return downloadFile("/reports/export", { ...query(filters), format }, `h4t-report.${format}`);
}
