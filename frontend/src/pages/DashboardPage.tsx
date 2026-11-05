import React, { useMemo } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Link } from 'react-router-dom';
import {
  AlertCircle,
  AlertTriangle,
  Layers,
  ArrowRight,
  CheckCircle2,
  Loader2,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import api from '../api/client';

export interface InventorySummary {
  run_id: number;
  counts: {
    stockout_risk: number;
    reorder_now: number;
    overstock: number;
    ok: number;
  };
  total_suggested_order_units: number;
  estimated_overstock_units: number;
}

export interface ForecastRunData {
  id: number;
  status: string;
  horizon_days: number;
  metrics: {
    Naive?: { WAPE?: number; Bias?: number; RMSSE?: number };
    'Seasonal Naive (28d)'?: { WAPE?: number; Bias?: number; RMSSE?: number };
    LightGBM?: { WAPE?: number; Bias?: number; RMSSE?: number };
    [key: string]: any;
  } | null;
}

export interface ForecastOverview {
  run_id: number;
  status: string;
  metrics: any;
  first_future_date: string | null;
  total_daily: Array<{
    date: string;
    forecast: number;
    actual: number | null;
  }>;
  dates: string[];
}

export interface InventoryAlertItem {
  stock_id?: number;
  store: string;
  sku: string;
  on_hand: number;
  days_of_cover: number;
  status: 'stockout_risk' | 'reorder_now' | 'overstock' | 'ok';
  suggested_order_qty: number;
}

export const DashboardPage: React.FC = () => {
  // 1. Fetch Inventory Summary counts
  const { data: summary, isLoading: summaryLoading } = useQuery<InventorySummary>({
    queryKey: ['inventory-summary'],
    queryFn: async () => {
      const res = await api.get<InventorySummary>('/inventory/summary/');
      return res.data;
    },
  });

  // 2. Fetch Forecast Runs to find the latest done run ID
  const { data: runs, isLoading: runsLoading } = useQuery<ForecastRunData[]>({
    queryKey: ['forecast-runs'],
    queryFn: async () => {
      const res = await api.get<ForecastRunData[]>('/forecasts/');
      return res.data;
    },
  });

  const latestDoneRun = useMemo(() => {
    if (!runs || runs.length === 0) return null;
    return runs.find((r) => r.status === 'done') || runs[0];
  }, [runs]);

  // 3. Fetch Overview aggregated daily actuals & forecast from /api/forecasts/{id}/overview/
  const {
    data: overview,
    isLoading: overviewLoading,
  } = useQuery<ForecastOverview>({
    queryKey: ['forecast-overview', latestDoneRun?.id],
    queryFn: async () => {
      if (!latestDoneRun?.id) return null as any;
      const res = await api.get<ForecastOverview>(`/forecasts/${latestDoneRun.id}/overview/`);
      return res.data;
    },
    enabled: !!latestDoneRun?.id,
  });

  // 4. Fetch top 8 urgent items from /api/inventory/alerts/?limit=8
  const { data: urgentItems, isLoading: urgentLoading } = useQuery<InventoryAlertItem[]>({
    queryKey: ['inventory-alerts-urgent'],
    queryFn: async () => {
      const res = await api.get<InventoryAlertItem[]>('/inventory/alerts/?limit=8');
      return res.data;
    },
  });

  // Calculate metrics for cards and comparison bars
  const metrics = overview?.metrics || latestDoneRun?.metrics || {};
  const lgbmMetrics = metrics['LightGBM'];
  const naiveMetrics = metrics['Naive'];
  const sNaiveMetrics = metrics['Seasonal Naive (28d)'];

  // Accuracy calculation specifically from LightGBM: 100 minus (WAPE * 100)
  const lgbmWape =
    typeof lgbmMetrics?.WAPE === 'number'
      ? lgbmMetrics.WAPE
      : typeof latestDoneRun?.metrics?.LightGBM?.WAPE === 'number'
      ? latestDoneRun.metrics.LightGBM.WAPE
      : null;
  const accuracyPct =
    lgbmWape !== null ? Math.max(0, 100 - lgbmWape * 100).toFixed(1) : '—';
  const wapeFormatted =
    lgbmWape !== null ? `${(lgbmWape * 100).toFixed(1)}%` : '—';

  // Format chart data
  const chartData = useMemo(() => {
    if (!overview?.total_daily) return [];
    return overview.total_daily.map((pt) => ({
      date: pt.date,
      actual: pt.actual !== null ? Math.round(pt.actual) : null,
      forecast: Math.round(pt.forecast),
    }));
  }, [overview]);

  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'stockout_risk':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-red-50 text-status-stockout border border-red-200">
            <span className="w-1.5 h-1.5 rounded-full bg-status-stockout animate-pulse" />
            Stockout risk
          </span>
        );
      case 'reorder_now':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-orange-50 text-status-reorder border border-orange-200">
            <span className="w-1.5 h-1.5 rounded-full bg-status-reorder" />
            Reorder now
          </span>
        );
      case 'overstock':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-purple-50 text-status-overstock border border-purple-200">
            <span className="w-1.5 h-1.5 rounded-full bg-status-overstock" />
            Overstock
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-status-ok border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-status-ok" />
            OK
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Subtitle & Context Banner (No duplicate page title) */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-1">
        <div>
          <p className="text-sm text-slate-500">
            Portfolio demand trajectories, automated risk triggers, and model benchmarks.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link
            to="/upload"
            className="px-3 py-1.5 rounded-lg border border-slate-300 bg-white hover:bg-slate-50 text-slate-700 text-xs font-semibold shadow-xs transition-colors"
          >
            Upload Data
          </Link>
          <Link
            to="/forecast"
            className="px-3 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-700 text-white text-xs font-semibold shadow-xs transition-colors flex items-center gap-1.5"
          >
            <span>Forecast Models</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </Link>
        </div>
      </section>

      {/* 2. Four KPI Stat Cards */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Stat Card 1: Forecast accuracy */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Forecast accuracy (1 - WAPE)
              </span>
              <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                <CheckCircle2 className="w-3 h-3" />
                LightGBM
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-bold text-slate-900">
                {overviewLoading || runsLoading ? '—' : `${accuracyPct}%`}
              </span>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>LightGBM error:</span>
            <span className="font-semibold text-emerald-600 font-mono">
              WAPE: {wapeFormatted}
            </span>
          </div>
        </div>

        {/* Stat Card 2: Stockout risks */}
        <div className="bg-white border border-red-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-status-stockout uppercase tracking-wider">
                Stockout risks
              </span>
              <span className="p-1.5 bg-red-50 text-status-stockout rounded-lg">
                <AlertCircle className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-bold text-status-stockout">
                {summaryLoading ? '—' : `${summary?.counts?.stockout_risk ?? 0} SKUs`}
              </span>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-red-100 flex items-center justify-between text-xs">
            <span className="text-slate-500">Replenishment trigger:</span>
            <span className="font-semibold text-status-stockout">Immediate attention</span>
          </div>
        </div>

        {/* Stat Card 3: Reorder now */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Reorder now
              </span>
              <span className="p-1.5 bg-orange-50 text-status-reorder rounded-lg">
                <AlertTriangle className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-bold text-status-reorder">
                {summaryLoading ? '—' : `${summary?.counts?.reorder_now ?? 0} SKUs`}
              </span>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Buffer status:</span>
            <span className="font-semibold text-status-reorder">At reorder point</span>
          </div>
        </div>

        {/* Stat Card 4: Overstock units */}
        <div className="bg-white border border-slate-200 rounded-xl p-5 shadow-xs flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between gap-2">
              <span className="text-xs font-semibold text-slate-500 uppercase tracking-wider">
                Overstock units
              </span>
              <span className="p-1.5 bg-purple-50 text-status-overstock rounded-lg">
                <Layers className="w-4 h-4" />
              </span>
            </div>
            <div className="mt-3 flex items-baseline gap-2">
              <span className="text-3xl font-bold text-slate-900">
                {summaryLoading
                  ? '—'
                  : summary?.estimated_overstock_units
                  ? `${Math.round(summary.estimated_overstock_units).toLocaleString()}`
                  : '0'}
              </span>
              <span className="text-xs text-slate-500 font-medium">units</span>
            </div>
          </div>
          <div className="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between text-xs text-slate-500">
            <span>Threshold condition:</span>
            <span className="font-semibold text-status-overstock">&gt; 21 days cover</span>
          </div>
        </div>
      </section>

      {/* 3. Analytics Section: Left (Total demand line chart) + Right (Model comparison bars) */}
      <section className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Left: Line chart "Total demand: actual vs forecast" (8 cols) */}
        <div className="lg:col-span-8 bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-xs flex flex-col gap-4">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-100">
            <div>
              <h3 className="text-sm font-semibold text-slate-900">
                Total demand: actual vs forecast
              </h3>
              <p className="text-xs text-slate-500 mt-0.5">
                Aggregated portfolio volume across all stores and SKUs.
              </p>
            </div>
            <div className="flex items-center gap-4 text-xs">
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-slate-800 inline-block" />
                <span className="text-slate-700 font-medium">Actual Demand</span>
              </div>
              <div className="flex items-center gap-1.5">
                <span className="w-3 h-0.5 bg-blue-600 inline-block" />
                <span className="text-blue-700 font-semibold">Forecast</span>
              </div>
              {overview?.first_future_date && (
                <div className="flex items-center gap-1.5">
                  <span className="w-3 border-t border-dashed border-red-500 inline-block" />
                  <span className="text-red-600 font-medium">Future Horizon</span>
                </div>
              )}
            </div>
          </div>

          {/* Chart Canvas */}
          {overviewLoading ? (
            <div className="h-64 flex flex-col items-center justify-center text-xs text-slate-400 gap-2">
              <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
              <span>Loading aggregated overview points...</span>
            </div>
          ) : chartData.length === 0 ? (
            <div className="h-64 flex items-center justify-center text-xs text-slate-400">
              No forecast runs completed yet. Upload data and trigger a run to view demand trajectories.
            </div>
          ) : (
            <div className="h-64 w-full pt-1">
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={chartData} margin={{ top: 15, right: 20, left: 0, bottom: 15 }}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                  <XAxis
                    dataKey="date"
                    tick={{ fontSize: 11, fill: '#64748B' }}
                    tickFormatter={(val: string) => val.slice(5)}
                  />
                  <YAxis
                    tick={{ fontSize: 11, fill: '#64748B' }}
                    tickFormatter={(val: number) => `${Math.round(val / 1000)}k`}
                  />
                  <Tooltip
                    content={({ active, payload, label }) => {
                      if (!active || !payload || !payload.length) return null;
                      const pt = payload[0]?.payload;
                      if (!pt) return null;
                      return (
                        <div className="bg-slate-900 text-white rounded-lg p-3 shadow-lg text-xs space-y-1 border border-slate-700">
                          <p className="font-semibold text-slate-200 border-b border-slate-800 pb-1">
                            Date: {label}
                          </p>
                          <p className="flex justify-between gap-4">
                            <span className="text-blue-300">Forecast:</span>
                            <span className="font-mono font-bold">
                              {pt.forecast.toLocaleString()} units
                            </span>
                          </p>
                          {pt.actual !== null && (
                            <p className="flex justify-between gap-4 text-emerald-400">
                              <span>Actual:</span>
                              <span className="font-mono font-bold">
                                {pt.actual.toLocaleString()} units
                              </span>
                            </p>
                          )}
                        </div>
                      );
                    }}
                  />

                  {/* Cutoff Reference Line for future horizon */}
                  {overview?.first_future_date && (
                    <ReferenceLine
                      x={overview.first_future_date}
                      stroke="#EF4444"
                      strokeDasharray="4 4"
                      strokeWidth={1.5}
                      label={{
                        value: 'Forecast begins',
                        position: 'top',
                        fill: '#DC2626',
                        fontSize: 10,
                        fontWeight: 600,
                      }}
                    />
                  )}

                  {/* Actual demand line */}
                  <Line
                    type="monotone"
                    dataKey="actual"
                    stroke="#0F172A"
                    strokeWidth={2}
                    dot={{ r: 2, fill: '#0F172A' }}
                    connectNulls={false}
                    name="Actual Sales"
                  />

                  {/* Forecast line */}
                  <Line
                    type="monotone"
                    dataKey="forecast"
                    stroke="#2563EB"
                    strokeWidth={2.5}
                    dot={false}
                    name="Forecast"
                  />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        {/* Right: Card "Model comparison" (4 cols) */}
        <div className="lg:col-span-4 bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-xs flex flex-col justify-between gap-5">
          <div>
            <div className="flex items-center justify-between pb-1 border-b border-slate-100">
              <h3 className="text-sm font-semibold text-slate-900">Model comparison</h3>
              <span className="text-[10px] font-bold px-2 py-0.5 rounded bg-blue-50 text-blue-700 border border-blue-200 uppercase">
                Test Window
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-1">
              Weighted Absolute Percentage Error (WAPE) across backtest series.
            </p>

            {/* Three Horizontal Bars */}
            <div className="mt-5 space-y-4">
              {/* Bar 1: Naive (Baseline) */}
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-slate-700">1. Naive (Baseline)</span>
                  <span className="font-mono text-slate-600">
                    {naiveMetrics?.WAPE !== undefined ? `${(naiveMetrics.WAPE * 100).toFixed(1)}% WAPE` : '—'}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                  <div
                    className="bg-slate-400 h-full rounded-full"
                    style={{
                      width: `${Math.min(100, ((naiveMetrics?.WAPE ?? 0.25) / 0.3) * 100)}%`,
                    }}
                  />
                </div>
                <span className="text-[10px] text-slate-400 block">Flat last observed value</span>
              </div>

              {/* Bar 2: Seasonal Naive */}
              <div className="p-3 rounded-lg bg-slate-50 border border-slate-200 space-y-1.5">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-slate-700">2. Seasonal Naive (28d)</span>
                  <span className="font-mono text-slate-600">
                    {sNaiveMetrics?.WAPE !== undefined
                      ? `${(sNaiveMetrics.WAPE * 100).toFixed(1)}% WAPE`
                      : '—'}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-slate-200 overflow-hidden">
                  <div
                    className="bg-slate-500 h-full rounded-full"
                    style={{
                      width: `${Math.min(100, ((sNaiveMetrics?.WAPE ?? 0.15) / 0.3) * 100)}%`,
                    }}
                  />
                </div>
                <span className="text-[10px] text-slate-400 block">28-day cyclical day-of-week mirror</span>
              </div>

              {/* Bar 3: LightGBM (Best) */}
              <div className="p-3 rounded-lg bg-emerald-50 border border-emerald-200 space-y-1.5 relative overflow-hidden">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <div className="flex items-center gap-1.5">
                    <span className="text-emerald-900 font-bold">3. LightGBM</span>
                    <span className="inline-flex items-center px-1.5 py-0.2 rounded-full text-[9px] font-bold bg-emerald-600 text-white uppercase">
                      Best
                    </span>
                  </div>
                  <span className="font-mono font-bold text-emerald-700">
                    {lgbmMetrics?.WAPE !== undefined ? `${(lgbmMetrics.WAPE * 100).toFixed(1)}% WAPE` : '—'}
                  </span>
                </div>
                <div className="w-full h-2 rounded-full bg-emerald-200 overflow-hidden">
                  <div
                    className="bg-status-ok h-full rounded-full"
                    style={{
                      width: `${Math.min(100, ((lgbmMetrics?.WAPE ?? 0.088) / 0.3) * 100)}%`,
                    }}
                  />
                </div>
                <div className="flex items-center justify-between text-[10px] text-emerald-800">
                  <span>Gradient boosting regressor</span>
                  {naiveMetrics?.WAPE && lgbmMetrics?.WAPE && (
                    <span className="font-bold">
                      -{(((naiveMetrics.WAPE - lgbmMetrics.WAPE) / naiveMetrics.WAPE) * 100).toFixed(1)}% error vs Naive
                    </span>
                  )}
                </div>
              </div>
            </div>
          </div>

          <div className="text-[11px] text-slate-400 border-t border-slate-100 pt-3">
            Early stopping on a validation window; scored on a held-out test window.
          </div>
        </div>
      </section>

      {/* 4. Table "Most urgent items" */}
      <section className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        <div className="p-4 sm:p-5 flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-200">
          <div>
            <div className="flex items-center gap-2">
              <h3 className="text-sm font-semibold text-slate-900">Most urgent items</h3>
              <span className="px-2 py-0.5 rounded-full text-[10px] font-bold bg-red-100 text-status-stockout uppercase">
                Priority Action
              </span>
            </div>
            <p className="text-xs text-slate-500 mt-0.5">
              Top critical stockout vulnerabilities and replenishment triggers.
            </p>
          </div>
          <div>
            <Link
              to="/inventory"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 flex items-center gap-1 group"
            >
              <span>View all inventory alerts</span>
              <ArrowRight className="w-3.5 h-3.5 group-hover:translate-x-0.5 transition-transform" />
            </Link>
          </div>
        </div>

        {urgentLoading ? (
          <div className="p-12 text-center text-xs text-slate-400 flex items-center justify-center gap-2">
            <Loader2 className="w-5 h-5 animate-spin text-blue-600" />
            <span>Loading urgent replenishment alerts...</span>
          </div>
        ) : !urgentItems || urgentItems.length === 0 ? (
          <div className="p-8 text-center text-xs text-slate-400">
            No urgent alerts found. All series are currently balanced.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-2.5">Store</th>
                  <th className="px-4 py-2.5">SKU</th>
                  <th className="px-4 py-2.5 text-right">On Hand</th>
                  <th className="px-4 py-2.5 text-right">Days Cover</th>
                  <th className="px-4 py-2.5 text-center">Status</th>
                  <th className="px-4 py-2.5 text-right">Suggested Order</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {urgentItems.map((item) => (
                  <tr key={`${item.store}-${item.sku}`} className="hover:bg-slate-50 transition-colors">
                    <td className="px-4 py-2.5 font-semibold text-slate-800">{item.store}</td>
                    <td className="px-4 py-2.5 font-semibold text-slate-800">{item.sku}</td>
                    <td className="px-4 py-2.5 text-right font-mono font-medium text-slate-900">
                      {Math.round(item.on_hand).toLocaleString('en-US')}
                    </td>
                    <td className="px-4 py-2.5 text-right font-mono">
                      <span
                        className={
                          item.days_of_cover < 3
                            ? 'text-status-stockout font-bold'
                            : item.days_of_cover < 10
                            ? 'text-status-reorder font-semibold'
                            : 'text-slate-700'
                        }
                      >
                        {item.days_of_cover.toFixed(1)}d
                      </span>
                    </td>
                    <td className="px-4 py-2.5 text-center">{renderStatusBadge(item.status)}</td>
                    <td className="px-4 py-2.5 text-right font-mono">
                      {item.suggested_order_qty > 0 ? (
                        <span className="font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                          +{Math.round(item.suggested_order_qty).toLocaleString('en-US')}
                        </span>
                      ) : (
                        <span className="text-slate-400">0</span>
                      )}
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

export default DashboardPage;
