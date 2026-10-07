import React, { useState } from 'react';
import { 
  X, 
  Key, 
  Sparkles, 
  Cpu, 
  ExternalLink, 
  ShieldCheck, 
  Check 
} from 'lucide-react';

export default function ApiSettingsModal({
  isOpen,
  onClose,
  settings,
  onSave
}) {
  const [geminiKey, setGeminiKey] = useState(settings.geminiApiKey || '');
  const [togetherKey, setTogetherKey] = useState(settings.togetherApiKey || '');
  const [model, setModel] = useState(settings.modelName || 'gemini-2.5-flash');
  const [showKeys, setShowKeys] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);

  if (!isOpen) return null;

  const modelOptions = [
    {
      id: 'gemini-2.5-flash',
      name: 'Google Gemini 2.5 Flash',
      provider: 'Google Gemini',
      desc: 'State-of-the-art fast & highly intelligent model for Python code generation and deep analytics.',
      tag: 'Recommended'
    },
    {
      id: 'gemini-1.5-pro',
      name: 'Google Gemini 1.5 Pro',
      provider: 'Google Gemini',
      desc: 'Top-tier complex analytical reasoning, multi-turn reasoning, and in-depth dataset deductions.',
      tag: 'Deep Reasoning'
    },
    {
      id: 'gemini-1.5-flash',
      name: 'Google Gemini 1.5 Flash',
      provider: 'Google Gemini',
      desc: 'Ultra-fast lightweight model for rapid iterations and quick chart plotting.',
      tag: 'Fast & Lean'
    },
    {
      id: 'meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo',
      name: 'Meta-Llama 3.1 405B',
      provider: 'Together AI',
      desc: 'Open source titan for complex statistical modeling and intricate plotting.',
      tag: 'Together AI'
    },
    {
      id: 'deepseek-ai/DeepSeek-V3',
      name: 'DeepSeek V3',
      provider: 'Together AI',
      desc: 'Exceptional reasoning and deep analytical code generation.',
      tag: 'Together AI'
    }
  ];

  const handleSave = (e) => {
    e.preventDefault();
    onSave({
      geminiApiKey: geminiKey.trim(),
      togetherApiKey: togetherKey.trim(),
      modelName: model
    });
    setSavedSuccess(true);
    setTimeout(() => {
      setSavedSuccess(false);
      onClose();
    }, 800);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-black/70 backdrop-blur-sm animate-fadeIn">
      <div 
        className="w-full max-w-xl rounded-xl shadow-2xl border border-zinc-300 overflow-hidden transition-all relative z-10 bg-white"
      >
        {/* Modal Header */}
        <div className="px-6 py-4 border-b border-zinc-800 bg-black flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-zinc-800 border border-zinc-700 flex items-center justify-center text-white">
              <Key className="w-4 h-4 text-white" />
            </div>
            <div>
              <h3 className="font-heading font-extrabold text-white text-base">
                API & Model Settings
              </h3>
              <p className="text-xs text-zinc-400">
                Configure Google Gemini & Cloud LLM endpoints
              </p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="text-zinc-400 hover:text-white p-1 rounded-md transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body */}
        <form onSubmit={handleSave} className="p-6 space-y-5 max-h-[80vh] overflow-y-auto">
          
          {/* Smart Local Fallback Callout */}
          <div className="p-3.5 rounded-lg border border-[#E4E4E7] bg-zinc-50 flex items-start gap-3">
            <ShieldCheck className="w-5 h-5 text-black shrink-0 mt-0.5" />
            <div className="text-xs text-[#52525B] leading-relaxed">
              <strong className="text-[#09090B]">Automatic .env Key Detection:</strong> The backend automatically reads <code className="bg-zinc-200 px-1 py-0.5 rounded text-[#09090B] font-mono">GEMINI_API_KEY</code> from your project's <code className="bg-zinc-200 px-1 py-0.5 rounded text-[#09090B] font-mono">.env</code> file. You can also override it below.
            </div>
          </div>

          {/* Google Gemini API Key */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-[#09090B] uppercase tracking-wider flex items-center gap-1.5">
                <Sparkles className="w-3.5 h-3.5 text-black" />
                Google Gemini API Key
              </label>
              <a
                href="https://aistudio.google.com/app/apikey"
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-black font-semibold hover:underline flex items-center gap-1"
              >
                Get Free Gemini Key <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <input
              type={showKeys ? 'text' : 'password'}
              value={geminiKey}
              onChange={(e) => setGeminiKey(e.target.value)}
              placeholder="Loaded from .env (or enter AIzaSy...)"
              className="w-full px-3.5 py-2.5 rounded-lg border border-[#E4E4E7] text-xs font-mono text-[#09090B] placeholder-zinc-400 focus:outline-none focus:border-black focus:ring-1 focus:ring-black bg-white"
            />
          </div>

          {/* Model Selection */}
          <div>
            <label className="block text-xs font-bold text-[#09090B] uppercase tracking-wider mb-2 flex items-center gap-1.5">
              <Cpu className="w-3.5 h-3.5 text-black" />
              Select AI Model
            </label>
            <div className="space-y-2">
              {modelOptions.map((opt) => (
                <label
                  key={opt.id}
                  onClick={() => setModel(opt.id)}
                  className={`flex items-start p-3 rounded-lg border cursor-pointer transition-all ${
                    model === opt.id
                      ? 'border-black bg-zinc-50 ring-1 ring-black'
                      : 'border-[#E4E4E7] hover:border-zinc-400 bg-white'
                  }`}
                >
                  <input
                    type="radio"
                    name="model"
                    checked={model === opt.id}
                    onChange={() => setModel(opt.id)}
                    className="mt-1 text-black focus:ring-black accent-black"
                  />
                  <div className="ml-3 flex-1">
                    <div className="flex items-center justify-between">
                      <span className="text-xs font-bold text-[#09090B]">{opt.name}</span>
                      <span className={`text-[10px] font-mono px-2 py-0.5 rounded font-bold ${model === opt.id ? 'bg-black text-white' : 'bg-zinc-100 text-zinc-800'}`}>
                        {opt.tag}
                      </span>
                    </div>
                    <p className="text-[11px] text-[#71717A] mt-0.5">{opt.desc}</p>
                  </div>
                </label>
              ))}
            </div>
          </div>

          {/* Together AI Key (Optional) */}
          <div>
            <div className="flex items-center justify-between mb-1.5">
              <label className="text-xs font-bold text-[#09090B] uppercase tracking-wider">
                Together AI API Key (Optional)
              </label>
              <a
                href="https://api.together.ai/signin"
                target="_blank"
                rel="noreferrer"
                className="text-[11px] text-black font-semibold hover:underline flex items-center gap-1"
              >
                Get Together AI Key <ExternalLink className="w-3 h-3" />
              </a>
            </div>
            <input
              type={showKeys ? 'text' : 'password'}
              value={togetherKey}
              onChange={(e) => setTogetherKey(e.target.value)}
              placeholder="e.g. tog_1234567890abcdef..."
              className="w-full px-3.5 py-2.5 rounded-lg border border-[#E4E4E7] text-xs font-mono text-[#09090B] placeholder-zinc-400 focus:outline-none focus:border-black focus:ring-1 focus:ring-black bg-white"
            />
          </div>

          {/* Toggle Key Visibility */}
          <div className="flex items-center justify-between pt-1">
            <label className="flex items-center gap-2 cursor-pointer text-xs text-[#52525B]">
              <input
                type="checkbox"
                checked={showKeys}
                onChange={(e) => setShowKeys(e.target.checked)}
                className="rounded border-[#E4E4E7] text-black focus:ring-black accent-black"
              />
              Show API key values
            </label>

            {(geminiKey || togetherKey) && (
              <button
                type="button"
                onClick={() => {
                  setGeminiKey('');
                  setTogetherKey('');
                  setE2bKey('');
                }}
                className="text-xs text-black font-semibold hover:underline"
              >
                Clear Keys
              </button>
            )}
          </div>

          {/* Modal Actions */}
          <div className="pt-4 border-t border-[#E4E4E7] flex items-center justify-end gap-3">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg border border-[#E4E4E7] text-xs font-bold text-[#09090B] hover:bg-zinc-100 transition-colors"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="btn-accent px-5 py-2 rounded-lg text-xs font-bold flex items-center gap-1.5"
            >
              {savedSuccess ? (
                <>
                  <Check className="w-4 h-4 text-white" />
                  Saved!
                </>
              ) : (
                'Save Preferences'
              )}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
