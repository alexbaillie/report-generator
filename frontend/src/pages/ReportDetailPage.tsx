import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
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

export default function ReportDetailPage() {
  const { id } = useParams();
  const [report, setReport] = useState<Report | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        <div className="flex items-center justify-between">
          <h1 className="text-2xl text-white font-semibold">{report.title}</h1>
          <Link to="/reports" className="text-blue-400 underline">Back to reports</Link>
        </div>
        <div className="text-sm text-gray-400">
          <div>Patient: {report.patient_name}</div>
          <div>Type: {report.report_type}</div>
          <div>Created: {new Date(report.created_at).toLocaleString()}</div>
        </div>
        <div className="prose prose-invert max-w-none whitespace-pre-wrap text-gray-200 bg-dark-800 p-6 rounded border border-dark-700">
          {report.content}
        </div>
      </div>
    </div>
  );
}
