import React, { useEffect, useRef, useState } from 'react';
import { documentsApi } from '@/services/api';
import type { Document } from '@/types';
import { formatDate } from '@/utils/formatters';
import { Upload, File, CheckCircle, XCircle, Clock, AlertCircle } from 'lucide-react';
import { cn } from '@/utils/cn';

const DOC_TYPES = [
  { value: 'passport', label: 'Passport' },
  { value: 'id_card', label: 'National ID Card' },
  { value: 'driver_license', label: "Driver's License" },
  { value: 'proof_of_address', label: 'Proof of Address' },
  { value: 'bank_statement', label: 'Bank Statement' },
];

const statusIcon: Record<string, React.ReactNode> = {
  approved: <CheckCircle className="h-4 w-4 text-emerald-500" />,
  rejected: <XCircle className="h-4 w-4 text-red-500" />,
  pending: <Clock className="h-4 w-4 text-amber-500" />,
  under_review: <AlertCircle className="h-4 w-4 text-blue-500" />,
};

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Document[]>([]);
  const [uploading, setUploading] = useState(false);
  const [docType, setDocType] = useState('passport');
  const [error, setError] = useState('');
  const [success, setSuccess] = useState('');
  const fileRef = useRef<HTMLInputElement>(null);

  const fetchDocs = () => {
    documentsApi.getMyDocuments().then(r => setDocs(r.data)).catch(() => {});
  };

  useEffect(() => { fetchDocs(); }, []);

  const handleUpload = async () => {
    const file = fileRef.current?.files?.[0];
    if (!file) { setError('Please select a file'); return; }
    const fd = new FormData();
    fd.append('document_type', docType);
    fd.append('file', file);
    setUploading(true);
    setError('');
    try {
      await documentsApi.upload(fd);
      setSuccess('Document uploaded successfully!');
      fetchDocs();
      if (fileRef.current) fileRef.current.value = '';
      setTimeout(() => setSuccess(''), 4000);
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Upload failed');
    } finally {
      setUploading(false);
    }
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 animate-fade-in">
      <h1 className="text-2xl font-bold text-gray-900">Document Upload</h1>

      {/* Upload card */}
      <div className="card p-6">
        <h2 className="font-semibold text-gray-900 mb-4">Upload New Document</h2>
        <div className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">Document Type</label>
            <select value={docType} onChange={e => setDocType(e.target.value)}
              className="mt-1 block w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none">
              {DOC_TYPES.map(t => <option key={t.value} value={t.value}>{t.label}</option>)}
            </select>
          </div>
          <div
            onClick={() => fileRef.current?.click()}
            className="flex flex-col items-center justify-center gap-2 rounded-xl border-2 border-dashed border-gray-300 bg-gray-50 p-10 cursor-pointer hover:border-primary hover:bg-blue-50 transition-colors"
          >
            <Upload className="h-8 w-8 text-gray-400" />
            <p className="text-sm font-medium text-gray-600">Click to select file</p>
            <p className="text-xs text-gray-400">PDF, JPG, or PNG — max 10MB</p>
            <input ref={fileRef} type="file" accept=".pdf,.jpg,.jpeg,.png" className="hidden" />
          </div>
          {error && (
            <div className="flex items-center gap-2 text-sm text-red-600">
              <AlertCircle className="h-4 w-4" /> {error}
            </div>
          )}
          {success && (
            <div className="flex items-center gap-2 text-sm text-emerald-600">
              <CheckCircle className="h-4 w-4" /> {success}
            </div>
          )}
          <button onClick={handleUpload} disabled={uploading}
            className="w-full rounded-lg bg-primary px-4 py-2.5 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50">
            {uploading ? 'Uploading...' : 'Upload Document'}
          </button>
        </div>
      </div>

      {/* Uploaded docs */}
      <div className="card overflow-hidden">
        <div className="border-b px-6 py-4">
          <h2 className="font-semibold text-gray-900">My Documents ({docs.length})</h2>
        </div>
        {docs.length === 0 ? (
          <div className="flex h-32 flex-col items-center justify-center text-gray-400">
            <File className="mb-2 h-8 w-8" />
            <p className="text-sm">No documents uploaded yet</p>
          </div>
        ) : (
          <ul className="divide-y divide-gray-100">
            {docs.map(doc => (
              <li key={doc.id} className="flex items-center gap-4 px-6 py-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-gray-100">
                  <File className="h-5 w-5 text-gray-500" />
                </div>
                <div className="flex-1 min-w-0">
                  <p className="truncate text-sm font-medium text-gray-900">{doc.original_filename}</p>
                  <p className="text-xs text-gray-500 capitalize">{doc.document_type.replace(/_/g, ' ')} · {formatDate(doc.created_at)}</p>
                </div>
                <div className="flex items-center gap-2">
                  {statusIcon[doc.status]}
                  <span className={cn('text-xs font-medium capitalize',
                    doc.status === 'approved' ? 'text-emerald-600' :
                    doc.status === 'rejected' ? 'text-red-600' : 'text-amber-600')}>
                    {doc.status.replace(/_/g, ' ')}
                  </span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}
