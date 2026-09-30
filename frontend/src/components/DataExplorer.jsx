import React, { useState, useEffect, useMemo } from 'react';
import { 
  Table2, 
  Search, 
  Download, 
  Database,
  BarChart2,
  ChevronLeft, 
  ChevronRight
} from 'lucide-react';
import { API_BASE_URL } from '../config';

export default function DataExplorer({ selectedDatasetId }) {
  const [dataInfo, setDataInfo] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [activeTab, setActiveTab] = useState('preview'); // 'preview' | 'summary'
  const [currentPage, setCurrentPage] = useState(1);
  const pageSize = 12;

  useEffect(() => {
    let isMounted = true;
    if (!selectedDatasetId) {
      setDataInfo(null);
      setLoading(false);
      return;
    }
    setLoading(true);
    setError(null);

    fetch(`${API_BASE_URL}/api/dataset/${selectedDatasetId}?preview_limit=100`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP error ${res.status}`);
        return res.json();
      })
      .then((data) => {
        if (isMounted) {
          setDataInfo(data);
          setLoading(false);
          setCurrentPage(1);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.message);
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [selectedDatasetId]);

  // 0ms Instant Client-Side Search using useMemo
  const filteredRows = useMemo(() => {
    if (!dataInfo || !dataInfo.preview) return [];
    if (!searchTerm.trim()) return dataInfo.preview;

    const term = searchTerm.toLowerCase();
    return dataInfo.preview.filter((row) =>
      Object.values(row).some((val) =>
        String(val ?? '').toLowerCase().includes(term)
      )
    );
  }, [dataInfo, searchTerm]);

  // Pagination calculations
  const totalPages = Math.ceil(filteredRows.length / pageSize) || 1;
  const paginatedRows = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredRows.slice(start, start + pageSize);
  }, [filteredRows, currentPage, pageSize]);

  const handleExportCsv = () => {
    if (!dataInfo || !dataInfo.preview || dataInfo.preview.length === 0) return;
    const headers = dataInfo.columns.join(',');
    const rows = dataInfo.preview.map((row) =>
      dataInfo.columns.map((col) => `"${String(row[col] ?? '').replace(/"/g, '""')}"`).join(',')
    );
    const csvContent = [headers, ...rows].join('\n');
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `${dataInfo.name.replace(/\.[^/.]+$/, '')}_export.csv`;
    link.click();
  };

  if (loading) {
    return (
      <div className="card-shell p-12 text-center bg-white space-y-3 border border-[#E4E4E7]">
        <div className="w-8 h-8 rounded-full border-2 border-black border-t-transparent animate-spin mx-auto" />
        <p className="text-xs text-[#71717A]">Loading dataset schema and records...</p>
      </div>
    );
  }

  if (!selectedDatasetId) {
    return (
      <div className="card-shell p-12 text-center bg-white space-y-2 border border-[#E4E4E7]">
        <Database className="w-8 h-8 text-zinc-400 mx-auto mb-1" />
        <h4 className="font-heading font-bold text-sm text-[#09090B]">
          No Dataset Selected
        </h4>
        <p className="text-xs text-[#71717A]">
          Upload a CSV or Excel file from the Visualization Studio tab to explore data schema and summary statistics.
        </p>
      </div>
    );
  }

  if (error || !dataInfo) {
    return (
      <div className="card-shell p-8 text-center bg-white text-xs text-black border border-zinc-800">
        Failed to load dataset details: {error || 'Dataset not available'}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Top Metadata Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        <div className="card-shell p-4 bg-white border border-[#E4E4E7]">
          <span className="text-[11px] font-bold text-[#71717A] uppercase tracking-wider block mb-1">
            Total Rows
          </span>
          <div className="font-heading font-extrabold text-2xl text-[#09090B]">
            {dataInfo.rowCount.toLocaleString()}
          </div>
        </div>
        <div className="card-shell p-4 bg-white border border-[#E4E4E7]">
          <span className="text-[11px] font-bold text-[#71717A] uppercase tracking-wider block mb-1">
            Total Columns
          </span>
          <div className="font-heading font-extrabold text-2xl text-[#09090B]">
            {dataInfo.columnCount}
          </div>
        </div>
        <div className="card-shell p-4 bg-white border border-[#E4E4E7]">
          <span className="text-[11px] font-bold text-[#71717A] uppercase tracking-wider block mb-1">
            Cached Preview
          </span>
          <div className="font-heading font-extrabold text-2xl text-[#09090B]">
            {dataInfo.preview.length}
          </div>
        </div>
        <div className="card-shell p-4 bg-white border border-[#E4E4E7]">
          <span className="text-[11px] font-bold text-[#71717A] uppercase tracking-wider block mb-1">
            Filtering Latency
          </span>
          <div className="font-heading font-extrabold text-2xl text-black">
            0 ms
          </div>
        </div>
      </div>

      {/* Main Table Explorer Shell */}
      <div className="card-shell bg-white overflow-hidden shadow-md border border-[#E4E4E7]">
        
        {/* Controls Bar */}
        <div className="p-4 border-b border-[#E4E4E7] bg-zinc-50 flex flex-col md:flex-row md:items-center justify-between gap-3">
          {/* Tab buttons */}
          <div className="flex items-center space-x-1 bg-zinc-200 p-1 rounded-lg self-start">
            <button
              onClick={() => setActiveTab('preview')}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all flex items-center gap-1.5 ${
                activeTab === 'preview'
                  ? 'bg-black text-white shadow-sm'
                  : 'text-[#71717A] hover:text-[#09090B]'
              }`}
            >
              <Table2 className="w-3.5 h-3.5" />
              Preview Table
            </button>
            <button
              onClick={() => setActiveTab('summary')}
              className={`px-3 py-1.5 rounded-md text-xs font-bold transition-all flex items-center gap-1.5 ${
                activeTab === 'summary'
                  ? 'bg-black text-white shadow-sm'
                  : 'text-[#71717A] hover:text-[#09090B]'
              }`}
            >
              <BarChart2 className="w-3.5 h-3.5" />
              Statistical Summary
            </button>
          </div>

          {/* Search and Export */}
          <div className="flex items-center gap-2">
            {activeTab === 'preview' && (
              <div className="relative">
                <Search className="w-3.5 h-3.5 absolute left-3 top-1/2 -translate-y-1/2 text-zinc-400" />
                <input
                  type="text"
                  value={searchTerm}
                  onChange={(e) => {
                    setSearchTerm(e.target.value);
                    setCurrentPage(1);
                  }}
                  placeholder="Instant 0ms search..."
                  className="pl-8 pr-3 py-1.5 rounded-lg border border-[#E4E4E7] text-xs text-[#09090B] placeholder-zinc-400 bg-white focus:outline-none focus:border-black focus:ring-1 focus:ring-black w-48 sm:w-64 font-sans"
                />
              </div>
            )}

            <button
              onClick={handleExportCsv}
              className="px-3 py-1.5 rounded-lg border border-[#E4E4E7] hover:border-black bg-white text-xs font-bold text-[#09090B] hover:bg-zinc-100 transition-colors flex items-center gap-1.5 shadow-sm"
            >
              <Download className="w-3.5 h-3.5 text-black" />
              Export CSV
            </button>
          </div>
        </div>

        {/* Tab 1: Data Preview Table */}
        {activeTab === 'preview' && (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#E4E4E7] bg-zinc-100">
                  <th className="py-3 px-4 text-zinc-500 font-mono text-[10px] w-12 text-center">#</th>
                  {dataInfo.columns.map((col) => (
                    <th key={col} className="py-3 px-4 font-bold text-[#09090B] whitespace-nowrap">
                      <div className="flex items-center gap-1.5">
                        <span>{col}</span>
                        <span className="text-[9px] font-mono px-1.5 py-0.2 rounded bg-zinc-200 text-zinc-800 border border-zinc-300">
                          {dataInfo.columnTypes[col]?.replace('object', 'str') || 'any'}
                        </span>
                      </div>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E4E7]">
                {paginatedRows.length > 0 ? (
                  paginatedRows.map((row, idx) => (
                    <tr key={idx} className="hover:bg-zinc-50 transition-colors">
                      <td className="py-2.5 px-4 font-mono text-[10px] text-zinc-400 text-center">
                        {(currentPage - 1) * pageSize + idx + 1}
                      </td>
                      {dataInfo.columns.map((col) => (
                        <td key={col} className="py-2.5 px-4 text-[#09090B] whitespace-nowrap font-sans">
                          {String(row[col] ?? '—')}
                        </td>
                      ))}
                    </tr>
                  ))
                ) : (
                  <tr>
                    <td colSpan={dataInfo.columns.length + 1} className="py-8 text-center text-zinc-500">
                      No matching records found for "{searchTerm}".
                    </td>
                  </tr>
                )}
              </tbody>
            </table>

            {/* Pagination Controls */}
            <div className="p-3 border-t border-[#E4E4E7] bg-zinc-50 flex items-center justify-between text-xs text-zinc-600">
              <span>
                Showing {filteredRows.length > 0 ? (currentPage - 1) * pageSize + 1 : 0} to{' '}
                {Math.min(currentPage * pageSize, filteredRows.length)} of {filteredRows.length} records
              </span>
              <div className="flex items-center gap-2">
                <button
                  disabled={currentPage === 1}
                  onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                  className="p-1.5 rounded-lg border border-[#E4E4E7] disabled:opacity-30 hover:bg-white text-black transition-colors"
                >
                  <ChevronLeft className="w-4 h-4" />
                </button>
                <span className="font-mono text-[11px] px-2 font-semibold">
                  Page {currentPage} / {totalPages}
                </span>
                <button
                  disabled={currentPage >= totalPages}
                  onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                  className="p-1.5 rounded-lg border border-[#E4E4E7] disabled:opacity-30 hover:bg-white text-black transition-colors"
                >
                  <ChevronRight className="w-4 h-4" />
                </button>
              </div>
            </div>
          </div>
        )}

        {/* Tab 2: Statistical Summary */}
        {activeTab === 'summary' && (
          <div className="overflow-x-auto p-4">
            <table className="w-full text-left text-xs border-collapse">
              <thead>
                <tr className="border-b border-[#E4E4E7] bg-zinc-100">
                  <th className="py-2.5 px-4 font-bold text-[#09090B]">Statistic</th>
                  {Object.keys(dataInfo.summary).map((col) => (
                    <th key={col} className="py-2.5 px-4 font-bold text-[#09090B] whitespace-nowrap font-mono text-[11px]">
                      {col}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-[#E4E4E7]">
                {['count', 'mean', 'std', 'min', '25%', '50%', '75%', 'max'].map((stat) => (
                  <tr key={stat} className="hover:bg-zinc-50">
                    <td className="py-2 px-4 font-bold font-mono text-black uppercase text-[11px]">
                      {stat}
                    </td>
                    {Object.keys(dataInfo.summary).map((col) => {
                      const val = dataInfo.summary[col][stat];
                      const formatted = typeof val === 'number' ? val.toLocaleString(undefined, { maximumFractionDigits: 2 }) : (val ?? '—');
                      return (
                        <td key={col} className="py-2 px-4 text-[#09090B] font-mono text-[11px]">
                          {formatted}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

      </div>
    </div>
  );
}
