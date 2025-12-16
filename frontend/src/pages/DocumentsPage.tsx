import { useState, useEffect } from 'react';
import { Upload, File, Trash2, FileText } from 'lucide-react';
import { api } from '../services/api';

interface Document {
  id: number;
  filename: string;
  file_type: string;
  content: string | null;
  uploaded_at: string;
}

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedDocument, setSelectedDocument] = useState<Document | null>(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    loadDocuments();
  }, []);

  const loadDocuments = async () => {
    try {
      const data = await api.getDocuments();
      setDocuments(data);
    } catch (error) {
      console.error('Failed to load documents:', error);
    }
  };

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    try {
      await api.uploadDocument(file);
      await loadDocuments();
      e.target.value = '';
    } catch (error) {
      alert('Failed to upload document');
      console.error('Error uploading document:', error);
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: number) => {
    if (!confirm('Are you sure you want to delete this document?')) return;

    try {
      await api.deleteDocument(id);
      setDocuments(documents.filter((d) => d.id !== id));
      if (selectedDocument?.id === id) {
        setSelectedDocument(null);
      }
    } catch (error) {
      alert('Failed to delete document');
      console.error('Error deleting document:', error);
    }
  };

  return (
    <div className="flex h-full">
      {/* Documents List */}
      <div className="w-96 border-r border-dark-700 flex flex-col">
        <div className="p-6 border-b border-dark-700">
          <h1 className="text-2xl font-bold text-white flex items-center">
            <FileText className="mr-3" size={28} />
            Documents
          </h1>
          <p className="text-gray-400 text-sm mt-1">
            {documents.length} document{documents.length !== 1 ? 's' : ''}
          </p>
        </div>

        <div className="p-4 border-b border-dark-700">
          <label className="btn btn-primary w-full flex items-center justify-center cursor-pointer">
            <Upload size={20} className="mr-2" />
            {uploading ? 'Uploading...' : 'Upload Document'}
            <input
              type="file"
              className="hidden"
              onChange={handleFileUpload}
              disabled={uploading}
              accept=".txt,.pdf,.doc,.docx"
            />
          </label>
        </div>

        <div className="flex-1 overflow-auto p-4">
          {documents.length === 0 ? (
            <p className="text-gray-400 text-center">No documents yet</p>
          ) : (
            <div className="space-y-2">
              {documents.map((doc) => (
                <div
                  key={doc.id}
                  className={`p-4 rounded-lg cursor-pointer transition-colors ${
                    selectedDocument?.id === doc.id
                      ? 'bg-primary-600'
                      : 'bg-dark-800 hover:bg-dark-700'
                  }`}
                  onClick={() => setSelectedDocument(doc)}
                >
                  <div className="flex items-start">
                    <File size={20} className="mr-3 mt-1 flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <h3 className="font-semibold text-white truncate">{doc.filename}</h3>
                      <p className="text-xs text-gray-400 mt-1">
                        {new Date(doc.uploaded_at).toLocaleDateString()}
                      </p>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Document Viewer */}
      <div className="flex-1 flex flex-col">
        {selectedDocument ? (
          <>
            <div className="p-6 border-b border-dark-700 flex items-center justify-between">
              <div>
                <h2 className="text-2xl font-bold text-white">{selectedDocument.filename}</h2>
                <p className="text-gray-400 mt-1">
                  Uploaded: {new Date(selectedDocument.uploaded_at).toLocaleDateString()}
                </p>
              </div>
              <button
                onClick={() => handleDelete(selectedDocument.id)}
                className="btn bg-red-600 hover:bg-red-700 text-white flex items-center"
              >
                <Trash2 size={18} className="mr-2" />
                Delete
              </button>
            </div>

            <div className="flex-1 overflow-auto p-8">
              <div className="max-w-4xl mx-auto">
                <div className="card">
                  {selectedDocument.content ? (
                    <pre className="whitespace-pre-wrap text-gray-300 font-sans">
                      {selectedDocument.content}
                    </pre>
                  ) : (
                    <p className="text-gray-500 italic">
                      Content preview not available for this file type
                    </p>
                  )}
                </div>
              </div>
            </div>
          </>
        ) : (
          <div className="flex-1 flex items-center justify-center">
            <div className="text-center text-gray-500">
              <File size={64} className="mx-auto mb-4 opacity-50" />
              <p>Select a document to view</p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
