import React from 'react';
import { 
  BarChart3, 
  Table2, 
  Settings, 
  Sparkles, 
  Activity, 
  Database,
  Cpu
} from 'lucide-react';

export default function Header({ 
  activeTab, 
  setActiveTab, 
  onOpenSettings, 
  selectedModel, 
  backendStatus, 
  hasApiKeys 
}) {
  const tabs = [
    { id: 'studio', label: 'AI Visualization Studio', icon: BarChart3, badge: 'AI Agent' },
    { id: 'explorer', label: 'Dataset Explorer', icon: Table2, badge: 'Schema & Stats' },
  ];

  return (
    <header className="sticky top-0 z-40 w-full bg-[#000000] border-b border-zinc-800">
      {/* Top Banner / Brand Bar */}
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16 border-b border-zinc-800">
          
          {/* Logo & Title */}
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-white text-black shadow-md border border-zinc-200">
              <Sparkles className="w-5 h-5 text-black" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="font-heading font-extrabold text-lg tracking-tight text-white">
                  Antigravity Data Viz
                </span>
                <span className="px-2 py-0.5 text-[10px] font-mono font-bold tracking-wider uppercase rounded bg-zinc-800 text-zinc-200 border border-zinc-700">
                  v2.0
                </span>
              </div>
              <p className="text-xs text-zinc-400 -mt-0.5 hidden sm:block">
                AI-Powered Data Visualization & Analytics Agent
              </p>
            </div>
          </div>

          {/* Right Action Items: Model Pill & Settings */}
          <div className="flex items-center gap-3">
            {/* Backend Status */}
            <div className="hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full bg-zinc-900 border border-zinc-700 text-xs">
              <span className={`w-2 h-2 rounded-full ${backendStatus === 'online' ? 'bg-white animate-pulse' : 'bg-zinc-500'}`} />
              <span className="text-zinc-300 font-mono text-[11px]">
                {backendStatus === 'online' ? 'Live' : 'Connecting...'}
              </span>
            </div>

            {/* Model Badge */}
            <button
              onClick={onOpenSettings}
              className="hidden sm:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-xs text-zinc-200 transition-colors"
              title="Configure AI Model & Keys"
            >
              <Cpu className="w-3.5 h-3.5 text-zinc-300" />
              <span className="font-medium truncate max-w-[130px]">
                {selectedModel.split('/')[1] || selectedModel}
              </span>
              {hasApiKeys && (
                <span className="w-1.5 h-1.5 rounded-full bg-white" />
              )}
            </button>

            {/* Settings Button */}
            <button
              onClick={onOpenSettings}
              className="p-2 rounded-lg bg-zinc-900 hover:bg-zinc-800 border border-zinc-700 text-zinc-300 hover:text-white transition-colors"
              aria-label="API Settings"
            >
              <Settings className="w-4 h-4" />
            </button>
          </div>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center space-x-1 overflow-x-auto py-2 scrollbar-none">
          {tabs.map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all whitespace-nowrap ${
                  isActive
                    ? 'bg-white text-black shadow-sm font-bold'
                    : 'text-zinc-400 hover:text-white hover:bg-zinc-900'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-black' : 'text-zinc-400'}`} />
                <span>{tab.label}</span>
                {tab.badge && (
                  <span
                    className={`text-[10px] px-1.5 py-0.2 rounded font-mono ${
                      isActive
                        ? 'bg-black text-white font-bold'
                        : 'bg-zinc-800 text-zinc-400'
                    }`}
                  >
                    {tab.badge}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      </div>
    </header>
  );
}
