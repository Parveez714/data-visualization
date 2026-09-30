import React, { useState, useEffect } from 'react';
import Header from './components/Header';
import ConstellationBackground from './components/ConstellationBackground';
import VisualizationStudio from './components/VisualizationStudio';
import DataExplorer from './components/DataExplorer';
import ApiSettingsModal from './components/ApiSettingsModal';
import { API_BASE_URL } from './config';

export default function App() {
  const [activeTab, setActiveTab] = useState('studio'); // 'studio' | 'explorer'
  const [datasets, setDatasets] = useState([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState(null);
  const [backendStatus, setBackendStatus] = useState('checking');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);

  // Local storage for API settings
  const [apiSettings, setApiSettings] = useState(() => {
    try {
      const saved = localStorage.getItem('antigravity_viz_settings');
      if (saved) return JSON.parse(saved);
    } catch (e) {
      // ignore
    }
    return {
      geminiApiKey: '',
      togetherApiKey: '',
      e2bApiKey: '',
      modelName: 'gemini-2.5-flash'
    };
  });

  const handleSaveSettings = (newSettings) => {
    setApiSettings(newSettings);
    try {
      localStorage.setItem('antigravity_viz_settings', JSON.stringify(newSettings));
    } catch (e) {
      console.error(e);
    }
  };

  // Check backend health & fetch datasets
  const fetchDatasets = async () => {
    try {
      const res = await fetch(`${API_BASE_URL}/api/datasets`);
      if (res.ok) {
        const data = await res.json();
        const loadedDatasets = data.datasets || [];
        setDatasets(loadedDatasets);
        setSelectedDatasetId((prev) => {
          if (prev && loadedDatasets.some((d) => d.id === prev)) {
            return prev;
          }
          return loadedDatasets.length > 0 ? loadedDatasets[0].id : null;
        });
        setBackendStatus('online');
      } else {
        setBackendStatus('offline');
      }
    } catch (e) {
      setBackendStatus('offline');
    }
  };

  useEffect(() => {
    fetchDatasets();
    const interval = setInterval(fetchDatasets, 10000);
    return () => clearInterval(interval);
  }, []);

  // Handle CSV / Excel file upload
  const handleUploadCsv = async (file) => {
    const formData = new FormData();
    formData.append('file', file);
    if (apiSettings.geminiApiKey) formData.append('geminiApiKey', apiSettings.geminiApiKey);
    if (apiSettings.togetherApiKey) formData.append('togetherApiKey', apiSettings.togetherApiKey);
    if (apiSettings.modelName) formData.append('modelName', apiSettings.modelName);

    try {
      const res = await fetch(`${API_BASE_URL}/api/upload`, {
        method: 'POST',
        body: formData
      });

      if (!res.ok) {
        const err = await res.json().catch(() => ({}));
        throw new Error(err.detail || 'Upload failed');
      }

      const data = await res.json();
      await fetchDatasets();
      setSelectedDatasetId(data.datasetId);
      alert(`File "${data.name}" uploaded successfully with ${data.rowCount} rows! Smart prompt suggestions have been generated for your data.`);
    } catch (e) {
      alert(`Upload error: ${e.message}`);
    }
  };

  return (
    <div className="min-h-screen relative flex flex-col font-sans bg-[#FAFAFA] text-[#09090B]">
      
      {/* Background Layers: Grayscale Constellation Network */}
      <ConstellationBackground />

      {/* Header: Pure Black Header */}
      <Header
        activeTab={activeTab}
        setActiveTab={setActiveTab}
        onOpenSettings={() => setIsSettingsOpen(true)}
        selectedModel={apiSettings.modelName}
        backendStatus={backendStatus}
        hasApiKeys={Boolean(apiSettings.geminiApiKey || apiSettings.togetherApiKey || apiSettings.e2bApiKey)}
      />

      {/* Main Content Area */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 relative z-10">
        
        {/* Visual studio view */}
        {activeTab === 'studio' && (
          <VisualizationStudio
            datasets={datasets}
            selectedDatasetId={selectedDatasetId}
            onSelectDataset={setSelectedDatasetId}
            onUploadCsv={handleUploadCsv}
            apiSettings={apiSettings}
            onOpenSettings={() => setIsSettingsOpen(true)}
          />
        )}

        {/* Dataset Schema & Explorer */}
        {activeTab === 'explorer' && (
          <DataExplorer
            selectedDatasetId={selectedDatasetId}
          />
        )}

      </main>

      {/* Settings Modal */}
      <ApiSettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
        settings={apiSettings}
        onSave={handleSaveSettings}
      />

      {/* Footer */}
      <footer className="w-full border-t border-[#E4E4E7] py-6 relative z-10 bg-white/80 backdrop-blur-sm text-xs text-[#71717A]">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-heading font-extrabold text-[#09090B]">Antigravity Viz</span>
            <span>•</span>
            <span>Google Gemini + Python Data Visualization Engine</span>
          </div>
          <div className="flex items-center gap-4 text-[#A1A1AA]">
            <span>Monochrome UI</span>
            <span>Data Visualization Agent</span>
            <span className="font-mono text-[11px] text-[#09090B] font-semibold">Port 8005 / 5173</span>
          </div>
        </div>
      </footer>

    </div>
  );
}
