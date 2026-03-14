"use client";

import { useState, useEffect, useCallback } from "react";
import { apiFetch } from "@/lib/api";

// ── Types ─────────────────────────────────────────────────────────────────────

interface ScheduledReport {
  id: number;
  name: string;
  domain_id: string;
  format: "pdf" | "excel" | "html";
  sections: string[];
  report_title: string | null;
  interval_minutes: number;
  recipient_emails: string[];
  is_active: boolean;
  last_run_at: string | null;
  next_run_at: string | null;
  last_status: string;
  last_error: string | null;
  total_sent: number;
  created_at: string | null;
}

interface Domain { id: string; name: string; }
interface Section { id: string; label: string; }

const FORMAT_LABELS: Record<string, string> = {
  pdf: "PDF",
  excel: "Excel",
  html: "HTML",
};

const FORMAT_COLORS: Record<string, string> = {
  pdf:   "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
  excel: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  html:  "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
};

const STATUS_COLORS: Record<string, string> = {
  pending: "bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400",
  running: "bg-blue-100 text-blue-700 dark:bg-blue-900/30 dark:text-blue-400",
  success: "bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400",
  error:   "bg-red-100 text-red-700 dark:bg-red-900/30 dark:text-red-400",
};

function intervalLabel(minutes: number): string {
  if (minutes < 120) return `${minutes} min`;
  if (minutes < 1440) return `${Math.round(minutes / 60)}h`;
  if (minutes === 1440) return "Daily";
  if (minutes === 10080) return "Weekly";
  return `${Math.round(minutes / 1440)}d`;
}

function fmtDate(iso: string | null): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: "medium", timeStyle: "short",
  });
}

// ── Empty form state ──────────────────────────────────────────────────────────

const EMPTY_FORM = {
  name: "",
  domain_id: "default",
  format: "pdf" as "pdf" | "excel" | "html",
  sections: [] as string[],
  report_title: "",
  interval_minutes: 1440,
  recipient_emails: "",
};

// ── Main component ────────────────────────────────────────────────────────────

export default function ScheduledReportsPage() {
  const [reports, setReports]     = useState<ScheduledReport[]>([]);
  const [domains, setDomains]     = useState<Domain[]>([]);
  const [sections, setSections]   = useState<Section[]>([]);
  const [loading, setLoading]     = useState(true);
  const [showForm, setShowForm]   = useState(false);
  const [editId, setEditId]       = useState<number | null>(null);
  const [form, setForm]           = useState({ ...EMPTY_FORM });
  const [saving, setSaving]       = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [triggering, setTriggering] = useState<number | null>(null);
  const [expandedError, setExpandedError] = useState<number | null>(null);

  // ── Data loading ────────────────────────────────────────────────────────────

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [rRes, dRes, sRes] = await Promise.all([
        apiFetch("/scheduled-reports"),
        apiFetch("/domains"),
        apiFetch("/reports/sections"),
      ]);
      if (rRes.ok) setReports(await rRes.json());
      if (dRes.ok) setDomains(await dRes.json());
      if (sRes.ok) setSections(await sRes.json());
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // ── Form helpers ────────────────────────────────────────────────────────────

  function openCreate() {
    setEditId(null);
    setForm({ ...EMPTY_FORM });
    setError(null);
    setShowForm(true);
  }

  function openEdit(r: ScheduledReport) {
    setEditId(r.id);
    setForm({
      name:             r.name,
      domain_id:        r.domain_id,
      format:           r.format,
      sections:         r.sections,
      report_title:     r.report_title ?? "",
      interval_minutes: r.interval_minutes,
      recipient_emails: r.recipient_emails.join(", "),
    });
    setError(null);
    setShowForm(true);
  }

  function toggleSection(id: string) {
    setForm((f) => ({
      ...f,
      sections: f.sections.includes(id)
        ? f.sections.filter((s) => s !== id)
        : [...f.sections, id],
    }));
  }

  async function handleSave() {
    setError(null);
    setSaving(true);
    const emails = form.recipient_emails
      .split(/[,\n]+/)
      .map((e) => e.trim())
      .filter(Boolean);

    const body = {
      name:             form.name.trim(),
      domain_id:        form.domain_id,
      format:           form.format,
      sections:         form.sections,
      report_title:     form.report_title.trim() || null,
      interval_minutes: form.interval_minutes,
      recipient_emails: emails,
    };
    try {
      const res = editId !== null
        ? await apiFetch(`/scheduled-reports/${editId}`, { method: "PUT", body: JSON.stringify(body) })
        : await apiFetch("/scheduled-reports", { method: "POST", body: JSON.stringify(body) });
      if (!res.ok) {
        const data = await res.json().catch(() => ({}));
        setError(data.detail ?? `Error ${res.status}`);
        return;
      }
      setShowForm(false);
      await load();
    } catch {
      setError("Network error");
    } finally {
      setSaving(false);
    }
  }

  async function handleDelete(id: number) {
    if (!confirm("Delete this scheduled report?")) return;
    await apiFetch(`/scheduled-reports/${id}`, { method: "DELETE" });
    await load();
  }

  async function handleToggleActive(r: ScheduledReport) {
    await apiFetch(`/scheduled-reports/${r.id}`, {
      method: "PUT",
      body: JSON.stringify({ is_active: !r.is_active }),
    });
    await load();
  }

  async function handleTrigger(id: number) {
    setTriggering(id);
    try {
      const res = await apiFetch(`/scheduled-reports/${id}/trigger`, { method: "POST" });
      const data = await res.json().catch(() => ({}));
      if (!res.ok || !data.success) {
        alert(`Trigger failed: ${data.error ?? data.detail ?? "Unknown error"}`);
      } else {
        alert(`Report sent to ${data.recipients} recipient(s).`);
      }
      await load();
    } finally {
      setTriggering(null);
    }
  }

  // ── Render ──────────────────────────────────────────────────────────────────

  return (
    <div className="space-y-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
            Scheduled Reports
          </h2>
          <p className="mt-0.5 text-sm text-gray-500 dark:text-gray-400">
            Automatically generate and email reports on a recurring schedule.
          </p>
        </div>
        <button
          onClick={openCreate}
          className="flex items-center gap-2 rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700"
        >
          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
          </svg>
          New Schedule
        </button>
      </div>

      {/* SMTP notice */}
      <div className="flex items-start gap-3 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 dark:border-amber-800/50 dark:bg-amber-900/20">
        <svg className="mt-0.5 h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
        </svg>
        <p className="text-sm text-amber-700 dark:text-amber-300">
          Reports are sent via SMTP. Configure your mail server in{" "}
          <a href="/settings/notifications" className="font-medium underline">
            Settings → Notifications
          </a>
          .
        </p>
      </div>

      {/* Table */}
      {loading ? (
        <div className="space-y-3">
          {[1, 2, 3].map((i) => (
            <div key={i} className="h-16 animate-pulse rounded-lg bg-gray-100 dark:bg-gray-800" />
          ))}
        </div>
      ) : reports.length === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-200 py-16 text-center dark:border-gray-700">
          <svg className="mx-auto mb-3 h-10 w-10 text-gray-300 dark:text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm text-gray-500 dark:text-gray-400">No scheduled reports yet.</p>
          <button onClick={openCreate} className="mt-3 text-sm font-medium text-blue-600 hover:underline dark:text-blue-400">
            Create your first schedule →
          </button>
        </div>
      ) : (
        <div className="overflow-hidden rounded-xl border border-gray-200 dark:border-gray-700">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/60">
              <tr>
                {["Name", "Domain", "Format", "Interval", "Recipients", "Next Run", "Last Status", "Sent", ""].map((h) => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-semibold uppercase tracking-wide text-gray-500 dark:text-gray-400">
                    {h}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {reports.map((r) => (
                <>
                  <tr key={r.id} className={`transition-colors hover:bg-gray-50 dark:hover:bg-gray-800/40 ${!r.is_active ? "opacity-50" : ""}`}>
                    <td className="px-4 py-3">
                      <p className="font-medium text-gray-900 dark:text-white">{r.name}</p>
                      {r.report_title && (
                        <p className="text-xs text-gray-400">{r.report_title}</p>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{r.domain_id}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${FORMAT_COLORS[r.format] ?? ""}`}>
                        {FORMAT_LABELS[r.format] ?? r.format}
                      </span>
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{intervalLabel(r.interval_minutes)}</td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">
                      {r.recipient_emails.length === 0
                        ? <span className="text-gray-400">none</span>
                        : r.recipient_emails.length === 1
                          ? r.recipient_emails[0]
                          : `${r.recipient_emails[0]} +${r.recipient_emails.length - 1}`
                      }
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{fmtDate(r.next_run_at)}</td>
                    <td className="px-4 py-3">
                      <span className={`rounded-md px-2 py-0.5 text-xs font-semibold ${STATUS_COLORS[r.last_status] ?? ""}`}>
                        {r.last_status}
                      </span>
                      {r.last_status === "error" && r.last_error && (
                        <button
                          onClick={() => setExpandedError(expandedError === r.id ? null : r.id)}
                          className="ml-1 text-xs text-red-500 hover:underline"
                        >
                          {expandedError === r.id ? "hide" : "details"}
                        </button>
                      )}
                    </td>
                    <td className="px-4 py-3 text-gray-600 dark:text-gray-300">{r.total_sent}</td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1.5">
                        {/* Active toggle */}
                        <button
                          onClick={() => handleToggleActive(r)}
                          title={r.is_active ? "Pause" : "Resume"}
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-700 dark:hover:text-gray-200"
                        >
                          {r.is_active ? (
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 9v6m4-6v6m7-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          ) : (
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14.752 11.168l-3.197-2.132A1 1 0 0010 9.87v4.263a1 1 0 001.555.832l3.197-2.132a1 1 0 000-1.664z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                            </svg>
                          )}
                        </button>
                        {/* Trigger now */}
                        <button
                          onClick={() => handleTrigger(r.id)}
                          disabled={triggering === r.id}
                          title="Send now"
                          className="rounded p-1 text-blue-500 hover:bg-blue-50 hover:text-blue-700 disabled:opacity-40 dark:hover:bg-blue-900/20"
                        >
                          {triggering === r.id ? (
                            <svg className="h-4 w-4 animate-spin" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                            </svg>
                          ) : (
                            <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 19l9 2-9-18-9 18 9-2zm0 0v-8" />
                            </svg>
                          )}
                        </button>
                        {/* Edit */}
                        <button
                          onClick={() => openEdit(r)}
                          title="Edit"
                          className="rounded p-1 text-gray-400 hover:bg-gray-100 hover:text-gray-700 dark:hover:bg-gray-700 dark:hover:text-gray-200"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                          </svg>
                        </button>
                        {/* Delete */}
                        <button
                          onClick={() => handleDelete(r.id)}
                          title="Delete"
                          className="rounded p-1 text-red-400 hover:bg-red-50 hover:text-red-600 dark:hover:bg-red-900/20"
                        >
                          <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                          </svg>
                        </button>
                      </div>
                    </td>
                  </tr>
                  {expandedError === r.id && r.last_error && (
                    <tr key={`err-${r.id}`}>
                      <td colSpan={9} className="bg-red-50 px-4 py-2 dark:bg-red-900/10">
                        <p className="font-mono text-xs text-red-700 dark:text-red-400">{r.last_error}</p>
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Create / Edit slide-over form */}
      {showForm && (
        <div className="fixed inset-0 z-50 flex">
          <div className="fixed inset-0 bg-black/40" onClick={() => setShowForm(false)} />
          <div className="relative ml-auto flex h-full w-full max-w-lg flex-col bg-white shadow-xl dark:bg-gray-900">
            <div className="flex items-center justify-between border-b border-gray-200 px-6 py-4 dark:border-gray-700">
              <h3 className="text-base font-semibold text-gray-900 dark:text-white">
                {editId !== null ? "Edit Schedule" : "New Scheduled Report"}
              </h3>
              <button
                onClick={() => setShowForm(false)}
                className="rounded p-1 text-gray-400 hover:text-gray-600 dark:hover:text-gray-200"
              >
                <svg className="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                </svg>
              </button>
            </div>

            <div className="flex-1 overflow-y-auto px-6 py-5 space-y-5">
              {error && (
                <div className="rounded-lg bg-red-50 p-3 text-sm text-red-700 dark:bg-red-900/20 dark:text-red-400">
                  {error}
                </div>
              )}

              {/* Name */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Schedule Name <span className="text-red-500">*</span>
                </label>
                <input
                  value={form.name}
                  onChange={(e) => setForm((f) => ({ ...f, name: e.target.value }))}
                  placeholder="e.g. Weekly Executive Summary"
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                />
              </div>

              {/* Domain + Format */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Domain</label>
                  <select
                    value={form.domain_id}
                    onChange={(e) => setForm((f) => ({ ...f, domain_id: e.target.value }))}
                    className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                  >
                    {domains.map((d) => (
                      <option key={d.id} value={d.id}>{d.name}</option>
                    ))}
                  </select>
                </div>
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Format</label>
                  <select
                    value={form.format}
                    onChange={(e) => setForm((f) => ({ ...f, format: e.target.value as "pdf" | "excel" | "html" }))}
                    className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                  >
                    <option value="pdf">PDF</option>
                    <option value="excel">Excel</option>
                    <option value="html">HTML</option>
                  </select>
                </div>
              </div>

              {/* Report title */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Report Title (optional)</label>
                <input
                  value={form.report_title}
                  onChange={(e) => setForm((f) => ({ ...f, report_title: e.target.value }))}
                  placeholder="Defaults to schedule name"
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                />
              </div>

              {/* Interval */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">Frequency</label>
                <select
                  value={form.interval_minutes}
                  onChange={(e) => setForm((f) => ({ ...f, interval_minutes: Number(e.target.value) }))}
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                >
                  <option value={60}>Every hour</option>
                  <option value={360}>Every 6 hours</option>
                  <option value={720}>Every 12 hours</option>
                  <option value={1440}>Daily</option>
                  <option value={10080}>Weekly</option>
                </select>
              </div>

              {/* Sections */}
              {sections.length > 0 && (
                <div>
                  <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                    Sections <span className="text-gray-400 font-normal">(leave empty = all)</span>
                  </label>
                  <div className="flex flex-wrap gap-2">
                    {sections.map((s) => (
                      <button
                        key={s.id}
                        type="button"
                        onClick={() => toggleSection(s.id)}
                        className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                          form.sections.includes(s.id)
                            ? "border-blue-500 bg-blue-500 text-white"
                            : "border-gray-200 bg-white text-gray-600 hover:border-blue-300 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-300"
                        }`}
                      >
                        {s.label}
                      </button>
                    ))}
                  </div>
                </div>
              )}

              {/* Recipients */}
              <div>
                <label className="mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300">
                  Recipient Emails <span className="text-red-500">*</span>
                </label>
                <textarea
                  value={form.recipient_emails}
                  onChange={(e) => setForm((f) => ({ ...f, recipient_emails: e.target.value }))}
                  rows={3}
                  placeholder="one@example.com, two@example.com"
                  className="w-full rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm text-gray-800 outline-none focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-200"
                />
                <p className="mt-1 text-xs text-gray-400">Separate multiple addresses with commas.</p>
              </div>
            </div>

            <div className="flex items-center justify-end gap-3 border-t border-gray-200 px-6 py-4 dark:border-gray-700">
              <button
                onClick={() => setShowForm(false)}
                className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                disabled={saving || !form.name.trim()}
                className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Saving…" : editId !== null ? "Save Changes" : "Create Schedule"}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
