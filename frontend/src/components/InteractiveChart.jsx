import React, { useRef } from 'react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import { Bar, Line, Pie, Doughnut, Scatter } from 'react-chartjs-2';
import { Download, BarChart2 } from 'lucide-react';

ChartJS.register(
  CategoryScale,
  LinearScale,
  BarElement,
  PointElement,
  LineElement,
  ArcElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function InteractiveChart({ spec }) {
  const chartRef = useRef(null);

  if (!spec || !spec.labels || !spec.datasets) {
    return (
      <div className="p-8 text-center text-zinc-500 border border-dashed rounded-xl bg-zinc-50">
        No structured chart data available.
      </div>
    );
  }

  const { chart_type = 'bar', title, labels, datasets, xAxisLabel, yAxisLabel } = spec;

  const data = {
    labels,
    datasets: datasets.map((ds) => ({
      label: ds.label || 'Data',
      data: ds.data,
      backgroundColor: ds.backgroundColor || '#18181B',
      borderColor: ds.borderColor || (chart_type === 'line' ? '#18181B' : undefined),
      borderWidth: chart_type === 'line' ? 2.5 : 1,
      fill: chart_type === 'line' ? false : (ds.fill !== false),
      tension: chart_type === 'line' ? 0.3 : 0,
      borderRadius: chart_type === 'bar' ? 4 : 0,
    }))
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: {
        position: 'top',
        labels: {
          font: { family: 'sans-serif', size: 12, weight: 'bold' },
          color: '#18181B',
          boxWidth: 14,
          padding: 16
        }
      },
      title: {
        display: Boolean(title),
        text: title,
        font: { family: 'sans-serif', size: 15, weight: 'bold' },
        color: '#09090B',
        padding: { top: 10, bottom: 20 }
      },
      tooltip: {
        backgroundColor: '#18181B',
        titleFont: { size: 13, weight: 'bold' },
        bodyFont: { size: 12 },
        padding: 10,
        cornerRadius: 8,
        displayColors: true
      }
    },
    scales: ['pie', 'doughnut'].includes(chart_type) ? undefined : {
      x: {
        title: {
          display: Boolean(xAxisLabel),
          text: xAxisLabel,
          font: { weight: 'bold', size: 12 },
          color: '#71717A'
        },
        grid: { color: 'rgba(228, 228, 231, 0.6)' },
        ticks: { color: '#09090B', font: { size: 11 } }
      },
      y: {
        title: {
          display: Boolean(yAxisLabel),
          text: yAxisLabel,
          font: { weight: 'bold', size: 12 },
          color: '#71717A'
        },
        grid: { color: 'rgba(228, 228, 231, 0.6)' },
        ticks: { color: '#09090B', font: { size: 11 } }
      }
    }
  };

  const handleDownload = () => {
    if (chartRef.current) {
      const url = chartRef.current.toBase64Image();
      const link = document.createElement('a');
      link.download = `${title || 'chart'}.png`;
      link.href = url;
      link.click();
    }
  };

  return (
    <div className="space-y-4">
      <div className="relative group rounded-xl border border-[#E4E4E7] bg-white p-5 shadow-sm">
        {/* Floating Download Button */}
        <div className="absolute top-4 right-4 z-10 flex items-center gap-2">
          <button
            onClick={handleDownload}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-zinc-100 hover:bg-black hover:text-white border border-[#E4E4E7] text-xs font-bold text-black transition-all shadow-sm"
            title="Download PNG"
          >
            <Download className="w-3.5 h-3.5" />
            <span>Export PNG</span>
          </button>
        </div>

        {/* Dynamic Chart Container */}
        <div className="h-[440px] w-full pt-4">
          {chart_type === 'line' && <Line ref={chartRef} data={data} options={options} />}
          {chart_type === 'pie' && <Pie ref={chartRef} data={data} options={options} />}
          {chart_type === 'doughnut' && <Doughnut ref={chartRef} data={data} options={options} />}
          {chart_type === 'scatter' && <Scatter ref={chartRef} data={data} options={options} />}
          {(!['line', 'pie', 'doughnut', 'scatter'].includes(chart_type)) && (
            <Bar ref={chartRef} data={data} options={options} />
          )}
        </div>
      </div>
    </div>
  );
}
