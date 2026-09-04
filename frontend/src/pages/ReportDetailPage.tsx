import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Download, Pencil, Save, X } from 'lucide-react';
import { api } from '../services/api';

interface Report {
  id: number;
  title: string;
  patient_name: string;
  report_type: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export function filenameFromDisposition(disposition: string | undefined, fallback: string): string {
  if (!disposition) return fallback;
  const match = disposition.match(/filename\*?=(?:UTF-8'')?"?([^";]+)"?/i);
  return match ? decodeURIComponent(match[1]) : fallback;
}

export default function ReportDetailPage() {
  const { id } = useParams();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);
  const [exportError, setExportError] = useState<string | null>(null);
  const [editing, setEditing] = useState(false);
  const [draftTitle, setDraftTitle] = useState('');
  const [draftPatient, setDraftPatient] = useState('');
  const [draftContent, setDraftContent] = useState('');
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  // Every report can export to Word now: ASD, Sunny Hill CDBC, and
  // Psycho-Educational reports use their clinic's branded template; anything
  // else falls back to a plain, cleanly-formatted export on the backend.
  const hasBrandedTemplate =
    !!report &&
    (/asd|autism|cdbc|sunny\s*hill|psycho-?educational|psyched/i.test(report.title) ||
      report.report_type === 'cdbc' ||
      report.report_type === 'psychoeducational');

  const startEditing = () => {
    if (!report) return;
    setDraftTitle(report.title);
    setDraftPatient(report.patient_name);
    setDraftContent(report.content);
    setSaveError(null);
    setEditing(true);
  };

  const cancelEditing = () => {
    setEditing(false);
    setSaveError(null);
  };

  const handleSave = async () => {
    if (!report) return;
    if (!draftContent.trim()) {
      setSaveError('Report content cannot be empty.');
      return;
    }
    setSaving(true);
    setSaveError(null);
    try {
      const updated = await api.updateReport(report.id, {
        title: draftTitle,
        patient_name: draftPatient,
        content: draftContent,
      });
      setReport(updated);
      setEditing(false);
    } catch (e: any) {
      setSaveError(e?.response?.data?.detail || 'Failed to save the report.');
    } finally {
      setSaving(false);
    }
  };

  const handleExport = async () => {
    if (!report) return;
    setExporting(true);
    setExportError(null);
    try {
      const response = await api.exportReportDocx(report.id);
      const filename = filenameFromDisposition(
        response.headers['content-disposition'],
        `${report.title || 'report'}.docx`
      );
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      link.remove();
      window.URL.revokeObjectURL(url);
    } catch (e: any) {
      // The blob error body needs to be read as text to surface the backend detail.
      let detail = 'Failed to export the report.';
      try {
        const blob = e?.response?.data;
        if (blob && typeof blob.text === 'function') {
          const parsed = JSON.parse(await blob.text());
          detail = parsed?.detail || detail;
        }
      } catch {
        // keep the default message
      }
      setExportError(detail);
    } finally {
      setExporting(false);
    }
  };

  useEffect(() => {
    const fetchReport = async () => {
      try {
        if (!id) return;
        const data = await api.getReport(Number(id));
        setReport(data);
      } catch (e: any) {
        setError(e?.message || 'Failed to load report');
      } finally {
        setLoading(false);
      }
    };
    fetchReport();
  }, [id]);

  if (loading) {
    return <div className="p-8 text-gray-200">Loading report...</div>;
  }

  if (error) {
    return (
      <div className="p-8 text-red-400">
        {error}
      </div>
    );
  }

  if (!report) {
    return (
      <div className="p-8 text-gray-200">
        Report not found. <Link to="/reports" className="text-blue-400 underline">Back to reports</Link>
      </div>
    );
  }

  return (
    <div className="p-8">
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="flex items-center justify-between gap-4">
          {editing ? (
            <input
              type="text"
              className="input text-xl font-semibold flex-1"
              value={draftTitle}
              onChange={(e) => setDraftTitle(e.target.value)}
              placeholder="Report title"
            />
          ) : (
            <h1 className="text-2xl text-white font-semibold">{report.title}</h1>
          )}
          <div className="flex items-center gap-4">
            {editing ? (
              <>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving}
                  className="btn btn-primary flex items-center gap-2 disabled:opacity-60"
                >
                  <Save size={18} />
                  {saving ? 'Saving...' : 'Save'}
                </button>
                <button
                  type="button"
                  onClick={cancelEditing}
                  disabled={saving}
                  className="text-gray-300 hover:text-white flex items-center gap-1"
                >
                  <X size={18} />
                  Cancel
                </button>
              </>
            ) : (
              <>
                <button
                  type="button"
                  onClick={startEditing}
                  className="btn btn-primary flex items-center gap-2"
                >
                  <Pencil size={18} />
                  Edit
                </button>
                <button
                  type="button"
                  onClick={handleExport}
                  disabled={exporting}
                  className="btn btn-primary flex items-center gap-2 disabled:opacity-60"
                >
                  <Download size={18} />
                  {exporting ? 'Exporting...' : 'Download Word'}
                </button>
                <Link to="/reports" className="text-blue-400 underline">Back to reports</Link>
              </>
            )}
          </div>
        </div>
        <div className="text-sm text-gray-400">
          <div className="flex items-center gap-2">
            <span>Patient:</span>
            {editing ? (
              <input
                type="text"
                className="input py-1"
                value={draftPatient}
                onChange={(e) => setDraftPatient(e.target.value)}
                placeholder="Patient name"
              />
            ) : (
              <span>{report.patient_name}</span>
            )}
          </div>
          <div>Type: {report.report_type}</div>
          <div>Created: {new Date(report.created_at).toLocaleString()}</div>
          <div>Last edited: {new Date(report.updated_at).toLocaleString()}</div>
          {!hasBrandedTemplate && !editing && (
            <div className="mt-1 text-gray-500">
              This report type has no clinic letterhead configured, so Word export uses a plain format.
            </div>
          )}
        </div>
        {exportError && (
          <div className="text-sm text-red-400">{exportError}</div>
        )}
        {saveError && (
          <div className="text-sm text-red-400">{saveError}</div>
        )}
        {editing ? (
          <textarea
            className="textarea w-full font-mono text-sm text-gray-100 bg-dark-800 p-6 rounded border border-dark-700"
            value={draftContent}
            onChange={(e) => setDraftContent(e.target.value)}
            rows={24}
          />
        ) : (
          <div className="prose prose-invert max-w-none whitespace-pre-wrap text-gray-200 bg-dark-800 p-6 rounded border border-dark-700">
            {report.content}
          </div>
        )}
      </div>
    </div>
  );
}
