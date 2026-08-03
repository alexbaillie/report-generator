import { useState, useEffect } from 'react';
import { FileText, Trash2, Eye, Download } from 'lucide-react';
import { api } from '../services/api';

interface Report {
  id: number;
  title: string;
  patient_name: string;
  report_type: string;
  content: string;
  created_at: string;
}

export default function ReportsPage() {
  const [reports, setReports] = useState<Report[]>([]);
  const [selectedReport, setSelectedReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [exportingReportId, setExportingReportId] = useState<number | null>(null);

  useEffect(() => {
    loadReports();
  }, []);

  const loadReports = async () => {
    try {
      const data = await api.getReports();
      setReports(data);
    } catch (error) {
      console.error('Failed to load reports:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this report?')) return;

    try {
      await api.deleteReport(id);
      setReports(reports.filter((r) => r.id !== id));
      if (selectedReport?.id === id) {
        setSelectedReport(null);
      }
    } catch (error) {
      alert('Failed to delete report');
      console.error('Error deleting report:', error);
    }
  };

  const downloadBlob = (blob: Blob, filename: string) => {
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const isAsdReport = (report: Report) => {
    const label = `${report.title} ${report.report_type}`.toLowerCase();
    return label.includes('asd') || label.includes('autism');
  };

  const handleExport = async (report: Report) => {
    if (isAsdReport(report)) {
      setExportingReportId(report.id);
      try {
        const response = await api.exportReportDocx(report.id);
        const disposition = String(response.headers['content-disposition'] || '');
        const filenameMatch = disposition.match(/filename="?([^";]+)"?/i);
        const filename = filenameMatch?.[1]
          || `${report.title.replace(/\s+/g, '_')}.docx`;
        downloadBlob(response.data, filename);
      } catch (error) {
        alert('Failed to export this report as a Word document.');
        console.error('DOCX export failed:', error);
      } finally {
        setExportingReportId(null);
      }
      return;
    }

    const blob = new Blob([report.content], { type: 'text/plain' });
    downloadBlob(blob, `${report.title.replace(/\s+/g, '_')}.txt`);
  };

  return (
    <div className="flex h-full">
      {/* Reports List */}
      <div className="w-96 border-r border-dark-700 flex flex-col">
        <div className="p-6 border-b border-dark-700">
          <h1 className="text-2xl font-bold text-white flex items-center">
            <FileText className="mr-3" size={28} />
            Reports
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            {reports.length} report{reports.length !== 1 ? 's' : ''}
          </p>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {loading ? (
            <p className="text-gray-400 text-center">Loading...</p>
          ) : reports.length === 0 ? (
            <p className="text-gray-400 text-center">No reports yet</p>
          ) : (
            <div className="space-y-2">
              {reports.map((report) => (
                <div
                  key={report.id}
                  className={`p-4 rounded-lg cursor-pointer transition-colors ${
                    selectedReport?.id === report.id
                      ? 'bg-primary-600'
                      : 'bg-dark-800 hover:bg-dark-700'
                  }`}
                  onClick={() => setSelectedReport(report)}
                >
                  <h3 className="font-semibold text-white">{report.title}</h3>
                  <p className="text-sm text-gray-400 mt-1">{report.patient_name}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-gray-500">
                      {new Date(report.created_at).toLocaleDateString()}
                    </span>
                    <span className="text-xs px-2 py-1 bg-dark-700 rounded text-gray-300">
                      {report.report_type}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Report Viewer */}
      <div className="flex-1 flex flex-col">
        {selectedReport ? (
          <>
            <div className="p-6 border-b border-dark-700 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">{selectedReport.title}</h2>
                <p className="text-gray-400 mt-1">
                  Patient: {selectedReport.patient_name} • Created:{' '}
                  {new Date(selectedReport.created_at).toLocaleDateString()}
                </p>
              </div>
              <div className="flex space-x-2">
                <button
                  onClick={() => handleExport(selectedReport)}
                  disabled={exportingReportId === selectedReport.id}
                  className="btn btn-secondary flex items-center"
                >
                  <Download size={18} className="mr-2" />
                  {exportingReportId === selectedReport.id
                    ? 'Exporting...'
                    : isAsdReport(selectedReport)
                      ? 'Export Word'
                      : 'Export'}
                </button>
                <button
                  onClick={() => handleDelete(selectedReport.id)}
                  className="btn bg-red-600 hover:bg-red-700 text-white flex items-center"
                >
                  <Trash2 size={18} className="mr-2" />
                  Delete
                </button>
              </div>
            </div>

            <div className="flex-1 overflow-auto p-8">
              <div className="max-w-4xl mx-auto">
                <div className="card">
                  <div className="prose prose-invert max-w-none">
                    <pre className="whitespace-pre-wrap text-gray-300 font-sans">
                      {selectedReport.content}
                    </pre>
                  </div>
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <Eye size={64} className="mx-auto mb-4 opacity-50" />
              <p>Select a report to view</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
