import React, { useState, useEffect } from 'react';
import { 
  BarChart3, 
  Sparkles, 
  Play, 
  Download, 
  UploadCloud, 
  FileSpreadsheet, 
  RefreshCw, 
  AlertCircle, 
  Database, 
  ArrowRight,
  Lightbulb
} from 'lucide-react';
import { API_BASE_URL } from '../config';
import InteractiveChart from './InteractiveChart';

export default function VisualizationStudio({
  datasets,
  selectedDatasetId,
  onSelectDataset,
  onUploadCsv,
  apiSettings,
  onOpenSettings
}) {
  const currentDataset = datasets?.find((d) => d.id === selectedDatasetId);

  const [query, setQuery] = useState(
    'Show an overview visualization of key distributions and trends in this dataset.'
  );
  const [suggestions, setSuggestions] = useState([]);
  const [loadingSuggestions, setLoadingSuggestions] = useState(false);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState(null);
  const [error, setError] = useState(null);
  const [activeView, setActiveView] = useState('chart'); // 'chart' | 'explanation'

  // Update suggestions dynamically when active dataset changes
  useEffect(() => {
    if (!selectedDatasetId || !currentDataset) {
      setSuggestions([]);
      return;
    }

    if (currentDataset.suggestions && currentDataset.suggestions.length > 0) {
      setSuggestions(currentDataset.suggestions);
      return;
    }

    // If suggestions are not attached yet, fetch them from backend
    const fetchDatasetSuggestions = async () => {
      setLoadingSuggestions(true);
      try {
        const res = await fetch(`${API_BASE_URL}/api/dataset/${selectedDatasetId}/suggestions`);
        if (res.ok) {
          const data = await res.json();
          if (data.suggestions && data.suggestions.length > 0) {
            setSuggestions(data.suggestions);
            return;
          }
        }
      } catch (err) {
        console.error('Failed to fetch dataset suggestions:', err);
      } finally {
        setLoadingSuggestions(false);
      }

      // Fallback: Generate smart suggestions from column names if available
      if (currentDataset.columns && currentDataset.columns.length > 0) {
        const cols = currentDataset.columns;
        const fallbackSugs = [
          `What is the breakdown of records across ${cols[0]}?`,
          cols.length > 1 ? `Compare ${cols[cols.length - 1]} across ${cols[0]}` : `Analyze distribution of ${cols[0]}`,
          cols.length > 2 ? `Show correlation or relationship between ${cols[1]} and ${cols[2]}` : `Show overview statistics across all columns`,
          `Show distribution and summary histogram for key metrics in this dataset`
        ];
        setSuggestions(fallbackSugs);
      }
    };

    fetchDatasetSuggestions();
  }, [selectedDatasetId, currentDataset]);

  // Handler to refresh/regenerate smart suggestions via AI engine
  const handleRefreshSuggestions = async () => {
    if (!selectedDatasetId) return;
    setLoadingSuggestions(true);
    try {
      const payload = {
        geminiApiKey: apiSettings.geminiApiKey || null,
        togetherApiKey: apiSettings.togetherApiKey || null,
        modelName: apiSettings.modelName || 'gemini-2.5-flash'
      };

      const res = await fetch(`${API_BASE_URL}/api/dataset/${selectedDatasetId}/suggestions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (res.ok) {
        const data = await res.json();
        if (data.suggestions && data.suggestions.length > 0) {
          setSuggestions(data.suggestions);
        }
      }
    } catch (e) {
      console.error('Failed to regenerate suggestions:', e);
    } finally {
      setLoadingSuggestions(false);
    }
  };

  const handleRunAnalysis = async () => {
    if (!query.trim()) return;
    if (!selectedDatasetId) {
      setError('Please upload or select a dataset first.');
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const payload = {
        datasetId: selectedDatasetId,
        query: query.trim(),
        geminiApiKey: apiSettings.geminiApiKey || null,
        togetherApiKey: apiSettings.togetherApiKey || null,
        modelName: apiSettings.modelName || 'gemini-2.5-flash'
      };

      const response = await fetch(`${API_BASE_URL}/api/analyze`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });

      if (!response.ok) {
        const errData = await response.json().catch(() => ({}));
        throw new Error(errData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      setResult(data);
      setActiveView('chart');
    } catch (err) {
      setError(err.message || 'Failed to analyze dataset. Ensure backend server is running.');
    } finally {
      setLoading(false);
    }
  };

  const handleDownloadImage = (base64Data, index) => {
    const link = document.createElement('a');
    link.href = `data:image/png;base64,${base64Data}`;
    link.download = `visualization-${selectedDatasetId || 'chart'}-${index + 1}.png`;
    link.click();
  };

  // Determine active engine label
  const getEngineLabel = () => {
    if (apiSettings.modelName?.startsWith('gemini')) {
      return 'Google Gemini';
    }
    if (apiSettings.togetherApiKey) {
      return 'Together AI';
    }
    return 'Gemini / Local Engine';
  };

  // Format inline bold markdown
  const formatInlineMarkdown = (text) => {
    if (!text) return null;
    const parts = text.split(/(\*\*[^*]+\*\*)/g);
    return parts.map((part, i) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={i} className="font-bold text-[#09090B]">
            {part.slice(2, -2)}
          </strong>
        );
      }
      return part;
    });
  };

  return (
    <div className="space-y-6">
      
      {/* 1. Dataset Selector Bar */}
      <div className="card-shell p-5 bg-white border border-[#E4E4E7]">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 mb-4">
          <div>
            <h2 className="font-heading font-extrabold text-lg text-[#09090B] flex items-center gap-2">
              <Database className="w-5 h-5 text-black" />
              Active Dataset
            </h2>
            <p className="text-xs text-[#71717A]">
              Upload a CSV or Excel dataset to explore with Gemini AI.
            </p>
          </div>

          {/* Upload Button */}
          <label className="inline-flex items-center gap-2 px-4 py-2 rounded-lg border border-[#E4E4E7] hover:border-black bg-white hover:bg-zinc-100 text-xs font-bold text-[#09090B] cursor-pointer transition-all shrink-0 shadow-sm">
            <UploadCloud className="w-4 h-4 text-black" />
            Upload CSV / Excel File
            <input
              type="file"
              accept=".csv,.xlsx,.xls"
              className="hidden"
              onChange={(e) => {
                if (e.target.files?.[0]) {
                  onUploadCsv(e.target.files[0]);
                }
              }}
            />
          </label>
        </div>

        {/* Dataset Cards Grid / Empty State */}
        {datasets && datasets.length > 0 ? (
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {datasets.map((ds) => {
              const isSelected = ds.id === selectedDatasetId;
              return (
                <div
                  key={ds.id}
                  onClick={() => onSelectDataset(ds.id)}
                  className={`p-3.5 rounded-xl border text-left cursor-pointer transition-all ${
                    isSelected
                      ? 'border-black bg-zinc-50 ring-1 ring-black'
                      : 'border-[#E4E4E7] bg-white hover:border-zinc-400 hover:bg-zinc-50/60'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1.5">
                    <div className="flex items-center gap-2">
                      <FileSpreadsheet className={`w-4 h-4 ${isSelected ? 'text-black font-bold' : 'text-zinc-500'}`} />
                      <span className="font-heading font-bold text-xs text-[#09090B] truncate max-w-[170px]">
                        {ds.name}
                      </span>
                    </div>
                    <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${isSelected ? 'bg-black text-white' : 'bg-zinc-100 text-zinc-800'}`}>
                      {ds.rowCount} rows
                    </span>
                  </div>
                  <p className="text-[11px] text-[#71717A] line-clamp-2 leading-relaxed">
                    {ds.description || `${ds.columnCount} columns available for multi-dimensional plotting.`}
                  </p>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="border border-dashed border-[#E4E4E7] rounded-xl p-8 text-center bg-zinc-50/50">
            <UploadCloud className="w-8 h-8 text-zinc-400 mx-auto mb-2" />
            <h4 className="font-heading font-bold text-sm text-[#09090B] mb-1">
              No Datasets Loaded Yet
            </h4>
            <p className="text-xs text-[#71717A] max-w-md mx-auto mb-4">
              Upload your custom CSV or Excel dataset above to generate charts and analytical insights with Google Gemini.
            </p>
          </div>
        )}
      </div>

      {/* 2. Natural Language Query & AI Generation Panel */}
      <div className="card-shell p-6 bg-white border border-[#E4E4E7] space-y-4">
        <div className="flex items-center justify-between">
          <label className="font-heading font-bold text-sm text-[#09090B] flex items-center gap-2">
            <Sparkles className="w-4 h-4 text-black" />
            Ask Natural Language Question
          </label>

          <div className="flex items-center gap-2 text-xs">
            <span className="text-[#71717A] hidden sm:inline">Engine:</span>
            <button
              onClick={onOpenSettings}
              className="px-2.5 py-1 rounded-md bg-zinc-100 hover:bg-zinc-200 border border-zinc-300 text-[#09090B] font-mono text-[11px] flex items-center gap-1.5 transition-colors font-medium"
            >
              <span>{getEngineLabel()}</span>
              <span className="text-black font-bold">⚙️</span>
            </button>
          </div>
        </div>

        {/* Text Area */}
        <div className="relative">
          <textarea
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            rows={3}
            placeholder="e.g. Can you create a bar chart comparing performance metrics across categories?"
            className="w-full p-3.5 rounded-xl border border-[#E4E4E7] text-sm text-[#09090B] placeholder-zinc-400 focus:outline-none focus:border-black focus:ring-1 focus:ring-black bg-white transition-all resize-none font-sans"
          />
        </div>

        {/* Quick Suggestion Chips */}
        <div>
          <div className="flex items-center justify-between mb-2">
            <div className="text-[11px] font-bold text-[#52525B] uppercase tracking-wider flex items-center gap-1.5">
              <Lightbulb className="w-3.5 h-3.5 text-black" />
              <span>Prompt Suggestions</span>
              {currentDataset && (
                <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-100 text-zinc-800 border border-zinc-200 normal-case">
                  based on {currentDataset.name}
                </span>
              )}
            </div>

            {selectedDatasetId && (
              <button
                onClick={handleRefreshSuggestions}
                disabled={loadingSuggestions}
                title="Regenerate smart prompt suggestions using AI"
                className="text-[11px] font-semibold text-black hover:text-zinc-600 flex items-center gap-1 transition-colors px-2 py-0.5 rounded hover:bg-zinc-100 disabled:opacity-50"
              >
                <RefreshCw className={`w-3 h-3 ${loadingSuggestions ? 'animate-spin' : ''}`} />
                <span>{loadingSuggestions ? 'Analyzing schema...' : 'Regenerate'}</span>
              </button>
            )}
          </div>

          {suggestions && suggestions.length > 0 ? (
            <div className="flex flex-wrap gap-2">
              {suggestions.map((sug, idx) => (
                <button
                  key={idx}
                  onClick={() => setQuery(sug)}
                  className="text-xs px-3 py-1.5 rounded-lg border border-[#E4E4E7] bg-white hover:bg-zinc-50 hover:border-black text-[#09090B] text-left transition-all flex items-center gap-1.5 group shadow-sm"
                >
                  <span>{sug}</span>
                  <ArrowRight className="w-3 h-3 text-zinc-400 group-hover:text-black group-hover:translate-x-0.5 transition-all shrink-0" />
                </button>
              ))}
            </div>
          ) : (
            <div className="text-xs text-zinc-500 italic py-1 bg-zinc-50 p-3 rounded-lg border border-dashed border-[#E4E4E7]">
              {selectedDatasetId
                ? 'Generating data-specific suggestions for your uploaded file...'
                : 'Upload or select a CSV/Excel dataset above to get data-tailored prompt suggestions automatically.'}
            </div>
          )}
        </div>

        {/* Run Button */}
        <div className="flex items-center justify-between pt-2">
          <span className="text-xs text-[#71717A]">
            Powered by Google Gemini & Python Seaborn/Matplotlib.
          </span>

          <button
            onClick={handleRunAnalysis}
            disabled={loading || !query.trim() || !selectedDatasetId}
            className="btn-accent px-6 py-2.5 rounded-xl text-xs font-bold flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed shadow-md"
          >
            {loading ? (
              <>
                <RefreshCw className="w-4 h-4 animate-spin text-white" />
                <span>Synthesizing & Rendering...</span>
              </>
            ) : (
              <>
                <Play className="w-4 h-4 fill-white text-white" />
                <span>Run AI Analysis</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* 3. Error Alert */}
      {error && (
        <div className="p-4 rounded-xl border border-zinc-800 bg-zinc-900 text-white flex items-start gap-3">
          <AlertCircle className="w-5 h-5 text-zinc-300 shrink-0 mt-0.5" />
          <div className="text-xs">
            <strong className="font-bold">Analysis Error:</strong> {error}
          </div>
        </div>
      )}

      {/* 4. Results & Visualizations Canvas */}
      {result && (
        <div className="card-shell overflow-hidden bg-white shadow-lg border border-[#E4E4E7]">
          
          {/* Result Header & View Tabs */}
          <div className="px-6 py-3.5 border-b border-[#E4E4E7] bg-zinc-50 flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 rounded-full bg-black animate-pulse" />
              <h3 className="font-heading font-bold text-sm text-[#09090B]">
                Visualization & Agent Output
              </h3>
              <span className="text-[10px] font-mono px-2 py-0.5 rounded bg-zinc-200 text-zinc-800 font-bold border border-zinc-300">
                {result.modelUsed}
              </span>
            </div>

            {/* View Switcher: Chart & AI Insights */}
            <div className="flex items-center space-x-1 bg-zinc-200 p-1 rounded-lg">
              <button
                onClick={() => setActiveView('chart')}
                className={`px-3 py-1 rounded-md text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeView === 'chart'
                    ? 'bg-black text-white shadow-sm'
                    : 'text-zinc-600 hover:text-black'
                }`}
              >
                <BarChart3 className="w-3.5 h-3.5" />
                Chart Output ({result.images?.length || 0})
              </button>
              <button
                onClick={() => setActiveView('explanation')}
                className={`px-3 py-1 rounded-md text-xs font-bold transition-all flex items-center gap-1.5 ${
                  activeView === 'explanation'
                    ? 'bg-black text-white shadow-sm'
                    : 'text-zinc-600 hover:text-black'
                }`}
              >
                <Sparkles className="w-3.5 h-3.5" />
                AI Insights
              </button>
            </div>
          </div>

          {/* View Content */}
          <div className="p-6">
            
            {/* 1. Chart View */}
            {activeView === 'chart' && (
              <div className="space-y-6">
                {/* Dynamic MCP Chart or Legacy Static Image */}
                {result.chartSpec ? (
                  <div className="space-y-4">
                    <InteractiveChart spec={result.chartSpec} />

                    {/* Direct Analytical Insights under Chart */}
                    {result.explanation && (
                      <div className="p-4 rounded-xl border border-[#E4E4E7] bg-white text-xs text-[#09090B] leading-relaxed space-y-2">
                        <div className="flex items-center gap-1.5 font-bold text-black">
                          <Sparkles className="w-3.5 h-3.5 text-black" />
                          <span>Direct Analytical Insights</span>
                        </div>
                        <div className="space-y-2 pt-1">
                          {result.explanation.split('\n').filter(line => line.trim()).map((line, lIdx) => {
                            const cleanLine = line.replace(/^[•\-\*]\s*/, '').trim();
                            const boldMatch = cleanLine.match(/^\*\*([^*:]+)\*\*:\s*(.*)$/);
                            if (boldMatch) {
                              return (
                                <div key={lIdx} className="flex items-start gap-2.5">
                                  <span className="inline-block mt-0.5 px-2 py-0.5 rounded text-[10px] font-bold bg-black text-white whitespace-nowrap shrink-0">
                                    {boldMatch[1]}
                                  </span>
                                  <span className="text-[#09090B] leading-relaxed">
                                    {formatInlineMarkdown(boldMatch[2])}
                                  </span>
                                </div>
                              );
                            }
                            return (
                              <div key={lIdx} className="flex items-start gap-2 text-[#09090B]">
                                <span className="text-black font-bold">•</span>
                                <span>{formatInlineMarkdown(cleanLine)}</span>
                              </div>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                ) : result.images && result.images.length > 0 ? (
                  result.images.map((img, idx) => (
                    <div key={idx} className="space-y-3">
                      <div className="relative group rounded-xl overflow-hidden border border-[#E4E4E7] bg-zinc-50 p-3 flex items-center justify-center min-h-[380px]">
                        <img
                          src={`data:${img.type};base64,${img.base64}`}
                          alt={`Generated Visualization ${idx + 1}`}
                          className="max-h-[520px] w-auto object-contain rounded-lg shadow-sm"
                        />

                        {/* Floating actions */}
                        <div className="absolute top-4 right-4 flex items-center gap-2 opacity-90 group-hover:opacity-100 transition-opacity">
                          <button
                            onClick={() => handleDownloadImage(img.base64, idx)}
                            className="p-2 rounded-lg bg-white/95 hover:bg-black hover:text-white shadow-md border border-[#E4E4E7] text-black transition-colors"
                            title="Download High-Res PNG"
                          >
                            <Download className="w-4 h-4" />
                          </button>
                        </div>
                      </div>

                      {/* Direct Analytical Insights under Chart */}
                      {result.explanation && (
                        <div className="p-4 rounded-xl border border-[#E4E4E7] bg-white text-xs text-[#09090B] leading-relaxed space-y-2">
                          <div className="flex items-center gap-1.5 font-bold text-black">
                            <Sparkles className="w-3.5 h-3.5 text-black" />
                            <span>Direct Analytical Insights</span>
                          </div>
                          <div className="space-y-2 pt-1">
                            {result.explanation.split('\n').filter(line => line.trim()).map((line, lIdx) => {
                              const cleanLine = line.replace(/^[•\-\*]\s*/, '').trim();
                              const boldMatch = cleanLine.match(/^\*\*([^*:]+)\*\*:\s*(.*)$/);
                              if (boldMatch) {
                                return (
                                  <div key={lIdx} className="flex items-start gap-2.5">
                                    <span className="inline-block mt-0.5 px-2 py-0.5 rounded text-[10px] font-bold bg-black text-white whitespace-nowrap shrink-0">
                                      {boldMatch[1]}
                                    </span>
                                    <span className="text-[#09090B] leading-relaxed">
                                      {formatInlineMarkdown(boldMatch[2])}
                                    </span>
                                  </div>
                                );
                              }
                              return (
                                <div key={lIdx} className="flex items-start gap-2 text-[#09090B]">
                                  <span className="text-black font-bold">•</span>
                                  <span>{formatInlineMarkdown(cleanLine)}</span>
                                </div>
                              );
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  ))
                ) : (
                  <div className="p-12 text-center text-zinc-500 border border-dashed rounded-xl bg-zinc-50">
                    No visualization available.
                  </div>
                )}
              </div>
            )}

            {/* 2. AI Insights View */}
            {activeView === 'explanation' && (
              <div className="p-5 rounded-xl border border-[#E4E4E7] bg-zinc-50 space-y-4 text-xs leading-relaxed text-[#09090B]">
                <div className="flex items-center justify-between">
                  <h4 className="font-heading font-extrabold text-sm text-[#09090B] flex items-center gap-2">
                    <Sparkles className="w-4 h-4 text-black" />
                    Data Analysis & Statistical Findings
                  </h4>
                  <span className="text-[11px] font-mono font-bold px-2.5 py-0.5 rounded bg-black text-white">
                    Executive Summary
                  </span>
                </div>
                
                <div className="space-y-3 pt-1">
                  {result.explanation ? (
                    result.explanation.split('\n').filter(line => line.trim()).map((line, lIdx) => {
                      const cleanLine = line.replace(/^[•\-\*]\s*/, '').trim();
                      const boldMatch = cleanLine.match(/^\*\*([^*:]+)\*\*:\s*(.*)$/);
                      if (boldMatch) {
                        return (
                          <div key={lIdx} className="p-3.5 rounded-xl bg-white border border-[#E4E4E7] shadow-sm flex flex-col sm:flex-row sm:items-start gap-2.5 sm:gap-3.5 hover:border-black transition-all">
                            <span className="px-2.5 py-1 rounded-md text-[11px] font-bold bg-black text-white whitespace-nowrap self-start">
                              {boldMatch[1]}
                            </span>
                            <span className="text-[#09090B] font-medium leading-relaxed">
                              {formatInlineMarkdown(boldMatch[2])}
                            </span>
                          </div>
                        );
                      }
                      return (
                        <div key={lIdx} className="p-3.5 rounded-xl bg-white border border-[#E4E4E7] shadow-sm flex items-start gap-2.5 hover:border-black transition-all">
                          <span className="text-black font-bold mt-0.5">•</span>
                          <span className="text-[#09090B] font-medium leading-relaxed">{formatInlineMarkdown(cleanLine)}</span>
                        </div>
                      );
                    })
                  ) : (
                    <p className="text-zinc-500">No statistical explanation returned.</p>
                  )}
                </div>
              </div>
            )}

          </div>
        </div>
      )}

    </div>
  );
}
