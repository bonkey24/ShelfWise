import React, { useRef, useState, useCallback } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import {
  UploadCloud,
  CheckCircle2,
  AlertTriangle,
  FileSpreadsheet,
  X,
  Search,
  Loader2,
  Clock,
  Database,
} from 'lucide-react';
import api from '../api/client';

export interface DatasetItem {
  id: number;
  name: string;
  file: string;
  rows_imported: number;
  status: 'pending' | 'processing' | 'done' | 'failed';
  error: string;
  created_at: string;
}

export interface UploadSuccessResponse {
  id: number;
  name: string;
  file: string;
  rows_imported: number;
  status: 'done' | 'failed' | 'processing' | 'pending';
  error: string;
  created_at: string;
}

export const UploadPage: React.FC = () => {
  const queryClient = useQueryClient();
  const fileInputRef = useRef<HTMLInputElement>(null);

  // Upload Form State
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [datasetName, setDatasetName] = useState('');
  const [isDragging, setIsDragging] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  // Success / Error notification state
  const [successData, setSuccessData] = useState<UploadSuccessResponse | null>(null);
  const [validationErrors, setValidationErrors] = useState<string[] | null>(null);

  // TanStack Query: fetch recent uploads list
  const {
    data: datasets,
    isLoading: isDatasetsLoading,
    isFetching: isDatasetsFetching,
  } = useQuery<DatasetItem[]>({
    queryKey: ['datasets'],
    queryFn: async () => {
      const res = await api.get<DatasetItem[]>('/datasets/');
      return res.data;
    },
  });

  // TanStack Mutation: POST /datasets/upload/
  const uploadMutation = useMutation({
    mutationFn: async ({ file, name }: { file: File; name: string }) => {
      const formData = new FormData();
      formData.append('file', file);
      if (name.trim()) {
        formData.append('name', name.trim());
      }

      const res = await api.post<UploadSuccessResponse>('/datasets/upload/', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
      });
      return res.data;
    },
    onSuccess: (data) => {
      setSuccessData(data);
      setValidationErrors(null);
      setSelectedFile(null);
      setDatasetName('');
      if (fileInputRef.current) {
        fileInputRef.current.value = '';
      }
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
    onError: (err: any) => {
      setSuccessData(null);
      const resData = err.response?.data;
      if (resData?.errors && Array.isArray(resData.errors)) {
        setValidationErrors(resData.errors);
      } else if (resData?.detail) {
        setValidationErrors([String(resData.detail)]);
      } else if (err.message) {
        setValidationErrors([err.message]);
      } else {
        setValidationErrors(['An unexpected error occurred during upload.']);
      }
      queryClient.invalidateQueries({ queryKey: ['datasets'] });
    },
  });

  // Drag and drop handlers
  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragging(false);

    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      const file = e.dataTransfer.files[0];
      if (file.name.endsWith('.csv') || file.name.endsWith('.tsv') || file.type.includes('csv')) {
        setSelectedFile(file);
        setValidationErrors(null);
        setSuccessData(null);
        if (!datasetName) {
          setDatasetName(file.name.replace(/\.[^/.]+$/, ''));
        }
      } else {
        setValidationErrors(['Only CSV files (.csv) are currently supported.']);
      }
    }
  }, [datasetName]);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files.length > 0) {
      const file = e.target.files[0];
      setSelectedFile(file);
      setValidationErrors(null);
      setSuccessData(null);
      if (!datasetName) {
        setDatasetName(file.name.replace(/\.[^/.]+$/, ''));
      }
    }
  };

  const handleClearSelected = () => {
    setSelectedFile(null);
    setDatasetName('');
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || uploadMutation.isPending) return;

    setValidationErrors(null);
    setSuccessData(null);
    uploadMutation.mutate({
      file: selectedFile,
      name: datasetName,
    });
  };

  // Filter datasets by search query
  const filteredDatasets = (datasets || []).filter((d) =>
    (d.name || d.file || '').toLowerCase().includes(searchQuery.toLowerCase())
  );

  const requiredColumns = ['store', 'sku', 'date', 'units_sold', 'price', 'on_promo'];

  return (
    <div className="space-y-6 max-w-6xl mx-auto">
      {/* 1. Header Banner */}
      <section className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 tracking-tight">Upload Data</h1>
          <p className="text-sm text-slate-500 mt-1 max-w-2xl">
            Import daily historical sales or point-of-sale data to train predictive demand models
            and refresh inventory cover projections.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <div className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-white border border-slate-200 text-xs text-slate-600 shadow-xs">
            <Database className="w-3.5 h-3.5 text-blue-600" />
            <span>Format: CSV (UTF-8)</span>
          </div>
        </div>
      </section>

      {/* 2. Success Card */}
      {successData && (
        <section className="bg-emerald-50 border border-emerald-200 rounded-xl p-5 shadow-xs transition-all">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-6 h-6" />
              </div>
              <div>
                <h3 className="text-sm font-semibold text-emerald-900">
                  Dataset successfully uploaded &amp; ingested!
                </h3>
                <p className="text-xs text-emerald-700 mt-1">
                  Imported <strong className="font-bold">{successData.rows_imported.toLocaleString()}</strong> valid
                  sales records from <span className="font-medium underline">{successData.name}</span> into the database.
                </p>
                <div className="mt-3 flex items-center gap-2">
                  <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-200/60 text-emerald-800">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                    Status: {successData.status}
                  </span>
                  <span className="text-xs text-emerald-600">
                    Dataset ID #{successData.id}
                  </span>
                </div>
              </div>
            </div>
            <button
              onClick={() => setSuccessData(null)}
              className="p-1 rounded-md text-emerald-700 hover:bg-emerald-100 transition-colors cursor-pointer"
              title="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </section>
      )}

      {/* 3. Validation Error Card */}
      {validationErrors && validationErrors.length > 0 && (
        <section className="bg-red-50 border border-red-200 rounded-xl p-5 shadow-xs transition-all">
          <div className="flex items-start justify-between gap-3">
            <div className="flex items-start gap-3.5">
              <div className="w-10 h-10 rounded-lg bg-red-100 text-red-700 flex items-center justify-center shrink-0">
                <AlertTriangle className="w-6 h-6" />
              </div>
              <div className="space-y-2">
                <h3 className="text-sm font-semibold text-red-900">
                  Upload validation failed ({validationErrors.length} {validationErrors.length === 1 ? 'error' : 'errors'})
                </h3>
                <p className="text-xs text-red-700">
                  The uploaded file could not be parsed or failed Pandera schema validation. Please review the errors below:
                </p>
                <div className="bg-white/80 border border-red-200 rounded-lg p-3 max-h-48 overflow-y-auto">
                  <ul className="space-y-1.5 text-xs text-red-800 font-mono">
                    {validationErrors.map((err, idx) => (
                      <li key={idx} className="flex items-start gap-2">
                        <span className="text-red-500 font-bold">•</span>
                        <span>{err}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>
            <button
              onClick={() => setValidationErrors(null)}
              className="p-1 rounded-md text-red-700 hover:bg-red-100 transition-colors cursor-pointer"
              title="Dismiss"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </section>
      )}

      {/* 4. Upload Form with Drag and Drop */}
      <section className="bg-white rounded-xl border border-slate-200 p-6 shadow-xs">
        <form onSubmit={handleUploadSubmit} className="space-y-5">
          {/* Dropzone Container */}
          <div
            onDragOver={handleDragOver}
            onDragLeave={handleDragLeave}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer relative ${
              isDragging
                ? 'border-blue-600 bg-blue-50/50 scale-[0.99]'
                : selectedFile
                ? 'border-blue-400 bg-blue-50/20'
                : 'border-slate-300 hover:border-blue-400 hover:bg-slate-50/50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={handleFileChange}
              className="hidden"
              id="csv-file-input"
            />

            {!selectedFile ? (
              <label
                htmlFor="csv-file-input"
                className="cursor-pointer flex flex-col items-center justify-center space-y-3"
              >
                <div className="w-14 h-14 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center transition-transform group-hover:scale-105">
                  <UploadCloud className="w-7 h-7" />
                </div>
                <div>
                  <h3 className="text-sm font-semibold text-slate-800">
                    Drop your sales CSV here or browse
                  </h3>
                  <p className="text-xs text-slate-500 mt-1">
                    Select a comma-delimited .csv file from your computer.
                  </p>
                </div>
                <span className="inline-flex items-center px-3.5 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-medium shadow-xs transition-colors">
                  Browse Files
                </span>
              </label>
            ) : (
              <div className="flex flex-col items-center justify-center space-y-3">
                <div className="w-12 h-12 rounded-full bg-emerald-50 text-emerald-600 flex items-center justify-center">
                  <FileSpreadsheet className="w-6 h-6" />
                </div>
                <div>
                  <p className="text-sm font-semibold text-slate-900">{selectedFile.name}</p>
                  <p className="text-xs text-slate-500 mt-0.5">
                    {(selectedFile.size / (1024 * 1024)).toFixed(2)} MB &middot; Ready for upload
                  </p>
                </div>
                <div className="flex items-center gap-2 pt-1">
                  <button
                    type="button"
                    onClick={handleClearSelected}
                    className="inline-flex items-center gap-1 px-3 py-1 text-xs text-red-600 hover:bg-red-50 rounded-md transition-colors cursor-pointer"
                  >
                    <X className="w-3.5 h-3.5" />
                    <span>Choose another file</span>
                  </button>
                </div>
              </div>
            )}

            {/* Required Schema Column Pills */}
            <div className="mt-6 pt-5 border-t border-slate-200/80">
              <span className="text-[11px] font-semibold text-slate-400 uppercase tracking-wider block mb-2">
                Required columns in your CSV header:
              </span>
              <div className="flex flex-wrap items-center justify-center gap-2">
                {requiredColumns.map((col) => (
                  <span
                    key={col}
                    className="px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 font-mono text-xs font-medium border border-slate-200"
                  >
                    {col}
                  </span>
                ))}
              </div>
            </div>
          </div>

          {/* Dataset Name Input & Upload Action */}
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-3">
            <div className="flex-1">
              <label htmlFor="dataset-name" className="sr-only">
                Dataset Name
              </label>
              <input
                id="dataset-name"
                type="text"
                value={datasetName}
                onChange={(e) => setDatasetName(e.target.value)}
                placeholder="Dataset display name (e.g., Flagship Stores Q3 Sales)"
                className="w-full px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent bg-white shadow-xs"
              />
            </div>
            <button
              type="submit"
              disabled={!selectedFile || uploadMutation.isPending}
              className="px-6 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white font-medium text-sm flex items-center justify-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shadow-xs"
            >
              {uploadMutation.isPending ? (
                <>
                  <Loader2 className="w-4 h-4 animate-spin" />
                  <span>Importing &amp; Validating...</span>
                </>
              ) : (
                <>
                  <UploadCloud className="w-4 h-4" />
                  <span>Upload &amp; Import</span>
                </>
              )}
            </button>
          </div>

          {/* Upload progress state indicator */}
          {uploadMutation.isPending && (
            <div className="p-3.5 rounded-lg bg-blue-50 border border-blue-200 flex items-center gap-3 text-xs text-blue-700">
              <Loader2 className="w-4 h-4 animate-spin shrink-0 text-blue-600" />
              <span>
                Sending CSV to server and validating schema with Pandera. Database insertion in progress...
              </span>
            </div>
          )}
        </form>
      </section>

      {/* 5. Recent Uploads Table */}
      <section className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {/* Table Header with Search */}
        <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2">
              <h2 className="text-base font-semibold text-slate-900">Recent uploads</h2>
              {isDatasetsFetching && !isDatasetsLoading && (
                <span className="text-[11px] text-blue-600 animate-pulse">Syncing...</span>
              )}
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Audit trail of point-of-sale datasets ingested into your forecasting engine.
            </p>
          </div>
          <div className="relative w-full sm:w-64">
            <Search className="w-4 h-4 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search uploads..."
              className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-300 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent bg-white shadow-xs"
            />
          </div>
        </div>

        {/* Table Body */}
        {isDatasetsLoading ? (
          <div className="p-12 text-center text-sm text-slate-500 flex flex-col items-center justify-center gap-2">
            <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
            <span>Loading uploaded datasets...</span>
          </div>
        ) : filteredDatasets.length === 0 ? (
          <div className="p-12 text-center text-sm text-slate-500">
            {searchQuery
              ? 'No datasets match your search query.'
              : 'No datasets uploaded yet. Upload your first sales CSV above.'}
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-5 py-3">Dataset Name</th>
                  <th className="px-5 py-3 text-right">Rows Imported</th>
                  <th className="px-5 py-3 text-center">Status</th>
                  <th className="px-5 py-3">Date Uploaded</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {filteredDatasets.map((d) => (
                  <tr key={d.id} className="hover:bg-slate-50/80 transition-colors">
                    {/* Dataset Name & File */}
                    <td className="px-5 py-3.5 font-medium text-slate-800">
                      <div className="flex items-center gap-2.5">
                        <div className="w-7 h-7 rounded-md bg-blue-50 text-blue-600 flex items-center justify-center shrink-0">
                          <FileSpreadsheet className="w-4 h-4" />
                        </div>
                        <div className="truncate max-w-xs sm:max-w-md">
                          <p className="font-semibold text-slate-900 truncate">
                            {d.name || 'Unnamed Dataset'}
                          </p>
                          {d.error && (
                            <p className="text-[11px] text-red-600 truncate mt-0.5" title={d.error}>
                              Error: {d.error}
                            </p>
                          )}
                        </div>
                      </div>
                    </td>

                    {/* Rows */}
                    <td className="px-5 py-3.5 text-right font-mono text-slate-700 font-medium">
                      {(d.rows_imported ?? 0).toLocaleString()}
                    </td>

                    {/* Status Badge */}
                    <td className="px-5 py-3.5 text-center">
                      {d.status === 'done' ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-600" />
                          done
                        </span>
                      ) : d.status === 'failed' ? (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-red-50 text-red-700 border border-red-200">
                          <span className="w-1.5 h-1.5 rounded-full bg-red-600" />
                          failed
                        </span>
                      ) : (
                        <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-[11px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                          <span className="w-1.5 h-1.5 rounded-full bg-blue-600 animate-ping" />
                          {d.status || 'processing'}
                        </span>
                      )}
                    </td>

                    {/* Date */}
                    <td className="px-5 py-3.5 text-slate-500 flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                      <span>
                        {d.created_at
                          ? new Date(d.created_at).toLocaleString(undefined, {
                              year: 'numeric',
                              month: 'short',
                              day: 'numeric',
                              hour: '2-digit',
                              minute: '2-digit',
                            })
                          : '—'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  );
};

export default UploadPage;
