import React, { useState, useEffect, useMemo, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Play,
  Loader2,
  TrendingUp,
  Store as StoreIcon,
  Package,
  Calendar,
  AlertCircle,
  CheckCircle2,
  Info,
} from 'lucide-react';
import {
  ResponsiveContainer,
  ComposedChart,
  Area,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  CartesianGrid,
  ReferenceLine,
} from 'recharts';
import api from '../api/client';

export interface StoreOption {
  id: number;
  code: string;
  name: string;
}

export interface ProductOption {
  id: number;
  sku: string;
  name: string;
  category: string;
}

export interface MetricValues {
  WAPE?: number;
  Bias?: number;
  RMSSE?: number;
}

export interface ForecastRunData {
  id: number;
  status: 'pending' | 'running' | 'done' | 'failed';
  horizon_days: number;
  metrics: {
    Naive?: MetricValues;
    'Seasonal Naive (28d)'?: MetricValues;
    LightGBM?: MetricValues;
    best_iteration?: number;
    [key: string]: any;
  } | null;
  error?: string;
  created_at: string;
  finished_at?: string | null;
}

export interface ForecastResultPoint {
  id: number;
  date: string;
  store: string;
  sku: string;
  forecast: number;
  lower: number;
  upper: number;
  actual: number | null;
}

export const ForecastPage: React.FC = () => {
  const queryClient = useQueryClient();

  // Selection state
  const [selectedStore, setSelectedStore] = useState<string>('S1097');
  const [selectedSku, setSelectedSku] = useState<string>('P1');
  const [activeRunId, setActiveRunId] = useState<number | null>(null);

  // Polling state for new forecast run
  const [pollingRunId, setPollingRunId] = useState<number | null>(null);
  const [runError, setRunError] = useState<string | null>(null);
  const pollingTimerRef = useRef<number | null>(null);

  // 1. Fetch Stores from /api/retail/stores/
  const { data: stores, isLoading: storesLoading } = useQuery<StoreOption[]>({
    queryKey: ['retail-stores'],
    queryFn: async () => {
      const res = await api.get<StoreOption[]>('/retail/stores/');
      return res.data;
    },
  });

  // 2. Fetch SKUs from /api/retail/products/
  const { data: products, isLoading: productsLoading } = useQuery<ProductOption[]>({
    queryKey: ['retail-products'],
    queryFn: async () => {
      const res = await api.get<ProductOption[]>('/retail/products/');
      return res.data;
    },
  });

  // Automatically pick defaults once stores and products load
  useEffect(() => {
    if (stores && stores.length > 0 && !selectedStore) {
      const defaultStore = stores.find((s) => s.code === 'S1097') || stores[0];
      setSelectedStore(defaultStore.code);
    }
  }, [stores, selectedStore]);

  useEffect(() => {
    if (products && products.length > 0 && !selectedSku) {
      const defaultProd = products.find((p) => p.sku === 'P1') || products[0];
      setSelectedSku(defaultProd.sku);
    }
  }, [products, selectedSku]);

  // 3. Fetch Forecast Runs list from /api/forecasts/
  const {
    data: runs,
    isLoading: runsLoading,
    refetch: refetchRuns,
  } = useQuery<ForecastRunData[]>({
    queryKey: ['forecast-runs'],
    queryFn: async () => {
      const res = await api.get<ForecastRunData[]>('/forecasts/');
      return res.data;
    },
  });

  // On initial load, set active run to the latest done run
  useEffect(() => {
    if (runs && runs.length > 0 && activeRunId === null) {
      const doneRun = runs.find((r) => r.status === 'done');
      if (doneRun) {
        setActiveRunId(doneRun.id);
      } else {
        setActiveRunId(runs[0].id);
      }
    }
  }, [runs, activeRunId]);

  // Find the currently active run object
  const activeRun = useMemo(() => {
    if (!runs || activeRunId === null) return null;
    return runs.find((r) => r.id === activeRunId) || runs[0];
  }, [runs, activeRunId]);

  // Latest run overall (for header chip)
  const latestRun = useMemo(() => {
    if (!runs || runs.length === 0) return null;
    return runs[0];
  }, [runs]);

  // 4. Fetch Forecast Results for the selected series from /api/forecasts/{id}/results/?store=&sku=
  const {
    data: results,
    isLoading: resultsLoading,
    error: resultsError,
  } = useQuery<ForecastResultPoint[]>({
    queryKey: ['forecast-results', activeRunId, selectedStore, selectedSku],
    queryFn: async () => {
      if (!activeRunId || !selectedStore || !selectedSku) return [];
      const res = await api.get<ForecastResultPoint[]>(
        `/forecasts/${activeRunId}/results/?store=${encodeURIComponent(
          selectedStore
        )}&sku=${encodeURIComponent(selectedSku)}`
      );
      return res.data;
    },
    enabled: !!activeRunId && !!selectedStore && !!selectedSku,
  });

  // 5. Trigger New Forecast Mutation
  const runMutation = useMutation({
    mutationFn: async () => {
      const res = await api.post<ForecastRunData>('/forecasts/run/', { horizon_days: 28 });
      return res.data;
    },
    onSuccess: (newRun) => {
      setRunError(null);
      setPollingRunId(newRun.id);
      refetchRuns();
    },
    onError: (err: any) => {
      const msg =
        err.response?.data?.detail ||
        err.response?.data?.error ||
        err.message ||
        'Failed to trigger forecast run.';
      setRunError(msg);
    },
  });

  // 6. Polling effect: poll GET /forecasts/{id}/ every 2 seconds
  useEffect(() => {
    if (!pollingRunId) return;

    let isSubscribed = true;

    const poll = async () => {
      try {
        const res = await api.get<ForecastRunData>(`/forecasts/${pollingRunId}/`);
        const runData = res.data;

        if (!isSubscribed) return;

        if (runData.status === 'done' || runData.status === 'failed') {
          if (pollingTimerRef.current) {
            clearInterval(pollingTimerRef.current);
            pollingTimerRef.current = null;
          }
          setPollingRunId(null);
          await refetchRuns();
          queryClient.invalidateQueries({ queryKey: ['forecast-results'] });
          if (runData.status === 'done') {
            setActiveRunId(runData.id);
          } else {
            setRunError(runData.error || 'Forecast training pipeline failed.');
          }
        }
      } catch (err: any) {
        console.error('Polling error:', err);
      }
    };

    poll();
    pollingTimerRef.current = window.setInterval(poll, 2000);

    return () => {
      isSubscribed = false;
      if (pollingTimerRef.current) {
        clearInterval(pollingTimerRef.current);
        pollingTimerRef.current = null;
      }
    };
  }, [pollingRunId, refetchRuns, queryClient]);

  const isRunning = !!pollingRunId || latestRun?.status === 'running';

  // Format chart data
  // Prediction interval: stacked Area with transparent base
  // bandBase = lower
  // bandSpread = upper - lower
  const chartData = useMemo(() => {
    if (!results || results.length === 0) return [];
    return results.map((r) => {
      const lower = Math.max(0, Math.round(r.lower));
      const upper = Math.max(lower, Math.round(r.upper));
      const spread = upper - lower;
      return {
        date: r.date,
        forecast: Math.round(r.forecast),
        actual: r.actual !== null && r.actual !== undefined ? Math.round(r.actual) : null,
        lower,
        upper,
        bandBase: lower,
        bandSpread: spread,
      };
    });
  }, [results]);

  // Find the first future date where actual is null (for the ReferenceLine)
  const firstFutureDate = useMemo(() => {
    if (!results) return null;
    const futurePoint = results.find((r) => r.actual === null);
    return futurePoint ? futurePoint.date : null;
  }, [results]);

  // Future rows for the "Next 28 days" table
  const futureRows = useMemo(() => {
    if (!results) return [];
    return results.filter((r) => r.actual === null);
  }, [results]);

  // Model Metrics breakdown & Best model calculation
  const metricsData = useMemo(() => {
    const rawMetrics = activeRun?.metrics;
    if (!rawMetrics) return null;

    const naive = rawMetrics['Naive'];
    const sNaive = rawMetrics['Seasonal Naive (28d)'];
    const lgbm = rawMetrics['LightGBM'];

    const candidates = [
      { name: 'Naive', data: naive },
      { name: 'Seasonal Naive (28d)', data: sNaive },
      { name: 'LightGBM', data: lgbm },
    ].filter((c) => c.data && typeof c.data.WAPE === 'number');

    if (candidates.length === 0) return null;

    // Find candidate with min WAPE
    let bestModel = candidates[0];
    for (const c of candidates) {
      if (c.data!.WAPE! < bestModel.data!.WAPE!) {
        bestModel = c;
      }
    }

    // Comparison summary: LightGBM vs best baseline
    const baselines = candidates.filter((c) => c.name !== 'LightGBM');
    let summaryText = '';
    if (lgbm?.WAPE !== undefined && baselines.length > 0) {
      let bestBaseline = baselines[0];
      for (const b of baselines) {
        if (b.data!.WAPE! < bestBaseline.data!.WAPE!) {
          bestBaseline = b;
        }
      }

      if (bestBaseline.data?.WAPE !== undefined) {
        const diff = bestBaseline.data.WAPE - lgbm.WAPE;
        const reductionPct = (diff / bestBaseline.data.WAPE) * 100;
        if (reductionPct > 0) {
          summaryText = `LightGBM reduces forecast error by ${reductionPct.toFixed(
            1
          )}% compared to the best baseline (${bestBaseline.name}).`;
        } else {
          summaryText = `LightGBM WAPE (${(lgbm.WAPE * 100).toFixed(
            1
          )}%) is comparable to ${bestBaseline.name} (${(
            bestBaseline.data.WAPE * 100
          ).toFixed(1)}%).`;
        }
      }
    }

    return {
      naive,
      sNaive,
      lgbm,
      bestName: bestModel.name,
      summaryText,
    };
  }, [activeRun]);

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Header Toolbar */}
      <section className="bg-white border border-slate-200 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4">
        {/* Title */}
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Demand Forecasts
          </h1>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            28-day LightGBM demand projections with empirical prediction intervals.
          </p>
        </div>

        {/* Toolbar Controls */}
        <div className="flex flex-wrap items-center gap-2.5">
          {/* Store Selector Dropdown */}
          <div className="relative">
            <label htmlFor="store-dropdown" className="sr-only">
              Select Store
            </label>
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors">
              <StoreIcon className="w-3.5 h-3.5 text-slate-500" />
              <select
                id="store-dropdown"
                value={selectedStore}
                onChange={(e) => setSelectedStore(e.target.value)}
                disabled={storesLoading}
                aria-label="Select Store"
                className="bg-transparent pr-4 focus:outline-none cursor-pointer text-slate-900 font-semibold"
              >
                {stores?.map((s) => (
                  <option key={s.id} value={s.code}>
                    {s.code} {s.name ? `· ${s.name}` : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* SKU Selector Dropdown */}
          <div className="relative">
            <label htmlFor="sku-dropdown" className="sr-only">
              Select SKU
            </label>
            <div className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-100 transition-colors">
              <Package className="w-3.5 h-3.5 text-slate-500" />
              <select
                id="sku-dropdown"
                value={selectedSku}
                onChange={(e) => setSelectedSku(e.target.value)}
                disabled={productsLoading}
                aria-label="Select SKU"
                className="bg-transparent pr-4 focus:outline-none cursor-pointer text-slate-900 font-semibold"
              >
                {products?.map((p) => (
                  <option key={p.id} value={p.sku}>
                    {p.sku} {p.name ? `· ${p.name}` : ''}
                  </option>
                ))}
              </select>
            </div>
          </div>

          {/* Status Chip for latest run */}
          {latestRun && (
            <div
              className={`flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium border ${
                latestRun.status === 'done'
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                  : latestRun.status === 'running' || isRunning
                  ? 'bg-blue-50 text-blue-700 border-blue-200'
                  : 'bg-red-50 text-red-700 border-red-200'
              }`}
            >
              {latestRun.status === 'running' || isRunning ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-blue-600" />
                  <span>Training Run #{latestRun.id}...</span>
                </>
              ) : latestRun.status === 'done' ? (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Run #{latestRun.id} &middot; Done</span>
                </>
              ) : (
                <>
                  <AlertCircle className="w-3.5 h-3.5 text-red-600" />
                  <span>Run #{latestRun.id} &middot; Failed</span>
                </>
              )}
            </div>
          )}

          {/* Run New Forecast Button */}
          <button
            onClick={() => runMutation.mutate()}
            disabled={isRunning || runMutation.isPending}
            className="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium text-xs rounded-lg flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer shadow-xs"
          >
            {isRunning || runMutation.isPending ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Training Pipeline...</span>
              </>
            ) : (
              <>
                <Play className="w-3.5 h-3.5 fill-current" />
                <span>Run new forecast</span>
              </>
            )}
          </button>
        </div>
      </section>

      {/* Error alert banner if any */}
      {(runError || (latestRun?.status === 'failed' && (latestRun.error || 'Forecast run failed.'))) && (
        <div className="p-4 rounded-xl bg-red-50 border border-red-200 text-red-700 text-xs flex items-center justify-between">
          <div className="flex items-center gap-2">
            <AlertCircle className="w-4 h-4 shrink-0" />
            <span>{runError || latestRun?.error || 'Forecast run failed.'}</span>
          </div>
          <button
            onClick={() => setRunError(null)}
            className="font-semibold underline ml-4 hover:text-red-900 cursor-pointer"
          >
            Dismiss
          </button>
        </div>
      )}

      {/* Loading Skeleton */}
      {runsLoading ? (
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center text-sm text-slate-500 flex flex-col items-center justify-center gap-3">
          <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
          <span>Loading forecasting models and series metadata...</span>
        </div>
      ) : !runs || runs.length === 0 ? (
        /* Empty State */
        <div className="bg-white rounded-xl border border-slate-200 p-12 text-center shadow-xs">
          <div className="w-12 h-12 rounded-full bg-blue-50 text-blue-600 flex items-center justify-center mx-auto mb-3">
            <TrendingUp className="w-6 h-6" />
          </div>
          <h2 className="text-base font-semibold text-slate-900">No forecast yet</h2>
          <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
            Upload your sales data on the Data Upload page, then click "Run new forecast" above to generate 28-day predictive demand curves.
          </p>
        </div>
      ) : (
        <>
          {/* 2. Main Forecast Chart Card */}
          <section className="bg-white border border-slate-200 rounded-xl p-5 sm:p-6 shadow-xs flex flex-col gap-4">
            {/* Chart Card Header */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-slate-100">
              <div>
                <div className="flex items-center gap-2">
                  <h2 className="text-sm font-semibold text-slate-900">
                    Demand Projection: {selectedStore} &middot; SKU {selectedSku}
                  </h2>
                  <span className="px-2 py-0.5 rounded-full text-[10px] font-semibold bg-blue-50 text-blue-700 border border-blue-200">
                    28-Day Horizon
                  </span>
                </div>
                <p className="text-xs text-slate-500 mt-0.5">
                  Test window actuals compared against LightGBM and 80% prediction interval.
                </p>
              </div>

              {/* Legend Summary */}
              <div className="flex flex-wrap items-center gap-4 text-xs">
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-full bg-slate-800 inline-block" />
                  <span className="text-slate-700 font-medium">Actual Sales</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-0.5 bg-blue-600 inline-block" />
                  <span className="text-slate-700 font-medium">Forecast (p50)</span>
                </div>
                <div className="flex items-center gap-1.5">
                  <span className="w-3 h-3 rounded-sm bg-blue-200 border border-blue-300 inline-block" />
                  <span className="text-slate-500 font-medium">80% Prediction Band</span>
                </div>
                {firstFutureDate && (
                  <div className="flex items-center gap-1.5">
                    <span className="w-3 border-t border-dashed border-red-500 inline-block" />
                    <span className="text-red-600 font-medium">Forecast starts</span>
                  </div>
                )}
              </div>
            </div>

            {/* Chart Canvas */}
            {resultsLoading ? (
              <div className="h-80 flex flex-col items-center justify-center text-xs text-slate-400 gap-2">
                <Loader2 className="w-6 h-6 animate-spin text-blue-600" />
                <span>Loading series trajectory points...</span>
              </div>
            ) : resultsError ? (
              <div className="h-80 flex items-center justify-center text-xs text-red-500">
                Failed to load forecast results for {selectedStore} / {selectedSku}.
              </div>
            ) : chartData.length === 0 ? (
              <div className="h-80 flex items-center justify-center text-xs text-slate-400">
                No data points found for {selectedStore} / {selectedSku}.
              </div>
            ) : (
              <div className="h-80 w-full pt-2">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart
                    data={chartData}
                    margin={{ top: 20, right: 20, left: 0, bottom: 20 }}
                  >
                    <CartesianGrid strokeDasharray="3 3" stroke="#F1F5F9" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 11, fill: '#64748B' }}
                      tickFormatter={(val: string) => val.slice(5)}
                    />
                    <YAxis
                      tick={{ fontSize: 11, fill: '#64748B' }}
                      tickFormatter={(val: number) => val.toLocaleString()}
                    />
                    <Tooltip
                      content={({ active, payload, label }) => {
                        if (!active || !payload || !payload.length) return null;
                        const dataPoint = payload[0]?.payload;
                        if (!dataPoint) return null;
                        return (
                          <div className="bg-slate-900 text-white rounded-lg p-3 shadow-lg text-xs space-y-1.5 border border-slate-700">
                            <p className="font-semibold text-slate-200 border-b border-slate-800 pb-1">
                              Date: {label}
                            </p>
                            <div className="space-y-1">
                              <p className="flex justify-between gap-4">
                                <span className="text-blue-300">Forecast:</span>
                                <span className="font-mono font-bold">
                                  {dataPoint.forecast.toLocaleString()}
                                </span>
                              </p>
                              <p className="flex justify-between gap-4">
                                <span className="text-slate-300">Lower (10%):</span>
                                <span className="font-mono">{dataPoint.lower.toLocaleString()}</span>
                              </p>
                              <p className="flex justify-between gap-4">
                                <span className="text-slate-300">Upper (90%):</span>
                                <span className="font-mono">{dataPoint.upper.toLocaleString()}</span>
                              </p>
                              {dataPoint.actual !== null && (
                                <p className="flex justify-between gap-4 pt-1 border-t border-slate-800 text-emerald-400 font-semibold">
                                  <span>Actual Sales:</span>
                                  <span className="font-mono">
                                    {dataPoint.actual.toLocaleString()}
                                  </span>
                                </p>
                              )}
                            </div>
                          </div>
                        );
                      }}
                    />

                    {/* Dotted Reference Line at first future date */}
                    {firstFutureDate && (
                      <ReferenceLine
                        x={firstFutureDate}
                        stroke="#EF4444"
                        strokeDasharray="4 4"
                        strokeWidth={1.5}
                        label={{
                          value: 'Forecast starts',
                          position: 'top',
                          fill: '#DC2626',
                          fontSize: 11,
                          fontWeight: 600,
                        }}
                      />
                    )}

                    {/* Shaded Prediction Band using stacked Area with transparent base */}
                    <Area
                      type="monotone"
                      dataKey="bandBase"
                      stackId="predictionInterval"
                      stroke="none"
                      fill="transparent"
                      legendType="none"
                      isAnimationActive={false}
                    />
                    <Area
                      type="monotone"
                      dataKey="bandSpread"
                      stackId="predictionInterval"
                      stroke="none"
                      fill="#93C5FD"
                      fillOpacity={0.35}
                      name="80% Prediction Band"
                      isAnimationActive={false}
                    />

                    {/* Dark actual sales line (test window) */}
                    <Line
                      type="monotone"
                      dataKey="actual"
                      stroke="#0F172A"
                      strokeWidth={2}
                      dot={{ r: 2, fill: '#0F172A' }}
                      connectNulls={false}
                      name="Actual Sales"
                    />

                    {/* Solid blue forecast line */}
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
          </section>

          {/* 3. Metrics Row: Three Cards (Naive, Seasonal Naive 28d, LightGBM) */}
          {metricsData && (
            <section className="space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <h2 className="text-sm font-semibold text-slate-900">
                    Model Evaluation Benchmark
                  </h2>
                  <p className="text-xs text-slate-500">
                    Metrics measured on the held-out final 28 days.
                  </p>
                </div>
                {metricsData.summaryText && (
                  <div className="inline-flex items-center gap-1.5 px-3 py-1 rounded-full bg-blue-50 text-blue-700 text-xs font-medium border border-blue-200">
                    <Info className="w-3.5 h-3.5 shrink-0" />
                    <span>{metricsData.summaryText}</span>
                  </div>
                )}
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                {/* Card 1: Naive (Baseline) */}
                <div
                  className={`bg-white rounded-xl border p-5 shadow-xs flex flex-col justify-between transition-all ${
                    metricsData.bestName === 'Naive'
                      ? 'border-emerald-500 ring-2 ring-emerald-100'
                      : 'border-slate-200'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-slate-900">Naive (Baseline)</span>
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600">
                        Flat Last Value
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mb-4">
                      Carries forward the last observed sales value without seasonality adjustment.
                    </p>
                    <div className="grid grid-cols-3 gap-2 py-3 border-y border-slate-100 text-center">
                      <div>
                        <span className="text-[10px] text-slate-400 font-semibold uppercase">WAPE</span>
                        <p
                          className={`text-base font-bold mt-0.5 ${
                            metricsData.bestName === 'Naive' ? 'text-emerald-600' : 'text-slate-800'
                          }`}
                        >
                          {metricsData.naive?.WAPE !== undefined
                            ? `${(metricsData.naive.WAPE * 100).toFixed(1)}%`
                            : '—'}
                        </p>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-semibold uppercase">Bias</span>
                        <p className="text-base font-bold text-slate-800 mt-0.5">
                          {metricsData.naive?.Bias !== undefined
                            ? metricsData.naive.Bias.toFixed(3)
                            : '—'}
                        </p>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-semibold uppercase">RMSSE</span>
                        <p className="text-base font-bold text-slate-800 mt-0.5">
                          {metricsData.naive?.RMSSE !== undefined
                            ? metricsData.naive.RMSSE.toFixed(2)
                            : '—'}
                        </p>
                      </div>
                    </div>
                  </div>
                  {metricsData.bestName === 'Naive' && (
                    <div className="pt-2 text-right">
                      <span className="text-[11px] font-semibold text-emerald-600">
                        ★ Best Benchmark
                      </span>
                    </div>
                  )}
                </div>

                {/* Card 2: Seasonal Naive (28d) */}
                <div
                  className={`bg-white rounded-xl border p-5 shadow-xs flex flex-col justify-between transition-all ${
                    metricsData.bestName === 'Seasonal Naive (28d)'
                      ? 'border-emerald-500 ring-2 ring-emerald-100'
                      : 'border-slate-200'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-slate-900">
                        Seasonal Naive (28d)
                      </span>
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-slate-100 text-slate-600">
                        28d Cycle
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mb-4">
                      Replicates day-of-week sales values from exactly 28 days prior.
                    </p>
                    <div className="grid grid-cols-3 gap-2 py-3 border-y border-slate-100 text-center">
                      <div>
                        <span className="text-[10px] text-slate-400 font-semibold uppercase">WAPE</span>
                        <p
                          className={`text-base font-bold mt-0.5 ${
                            metricsData.bestName === 'Seasonal Naive (28d)'
                              ? 'text-emerald-600'
                              : 'text-slate-800'
                          }`}
                        >
                          {metricsData.sNaive?.WAPE !== undefined
                            ? `${(metricsData.sNaive.WAPE * 100).toFixed(1)}%`
                            : '—'}
                        </p>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-semibold uppercase">Bias</span>
                        <p className="text-base font-bold text-slate-800 mt-0.5">
                          {metricsData.sNaive?.Bias !== undefined
                            ? metricsData.sNaive.Bias.toFixed(3)
                            : '—'}
                        </p>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-400 font-semibold uppercase">RMSSE</span>
                        <p className="text-base font-bold text-slate-800 mt-0.5">
                          {metricsData.sNaive?.RMSSE !== undefined
                            ? metricsData.sNaive.RMSSE.toFixed(2)
                            : '—'}
                        </p>
                      </div>
                    </div>
                  </div>
                  {metricsData.bestName === 'Seasonal Naive (28d)' && (
                    <div className="pt-2 text-right">
                      <span className="text-[11px] font-semibold text-emerald-600">
                        ★ Best Benchmark
                      </span>
                    </div>
                  )}
                </div>

                {/* Card 3: LightGBM (Production ML) */}
                <div
                  className={`bg-white rounded-xl border p-5 shadow-xs flex flex-col justify-between transition-all relative overflow-hidden ${
                    metricsData.bestName === 'LightGBM'
                      ? 'border-blue-600 ring-2 ring-blue-100'
                      : 'border-slate-200'
                  }`}
                >
                  {metricsData.bestName === 'LightGBM' && (
                    <div className="absolute top-0 right-0 bg-blue-600 text-white text-[10px] font-bold px-3 py-0.5 rounded-bl-lg uppercase tracking-wider">
                      Best Model
                    </div>
                  )}
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-sm font-semibold text-slate-900">LightGBM</span>
                      <span className="px-2 py-0.5 rounded-full text-[11px] font-medium bg-blue-50 text-blue-700 border border-blue-200">
                        ML Model
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mb-4">
                      Gradient boosting regressor with lag features, promotions, and time series splits.
                    </p>
                    <div className="grid grid-cols-3 gap-2 py-3 border-y border-slate-100 text-center bg-blue-50/30 rounded-lg">
                      <div>
                        <span className="text-[10px] text-slate-500 font-semibold uppercase">WAPE</span>
                        <p className="text-base font-bold text-emerald-600 mt-0.5">
                          {metricsData.lgbm?.WAPE !== undefined
                            ? `${(metricsData.lgbm.WAPE * 100).toFixed(1)}%`
                            : '—'}
                        </p>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 font-semibold uppercase">Bias</span>
                        <p className="text-base font-bold text-slate-900 mt-0.5">
                          {metricsData.lgbm?.Bias !== undefined
                            ? metricsData.lgbm.Bias.toFixed(3)
                            : '—'}
                        </p>
                      </div>
                      <div>
                        <span className="text-[10px] text-slate-500 font-semibold uppercase">RMSSE</span>
                        <p className="text-base font-bold text-blue-700 mt-0.5">
                          {metricsData.lgbm?.RMSSE !== undefined
                            ? metricsData.lgbm.RMSSE.toFixed(2)
                            : '—'}
                        </p>
                      </div>
                    </div>
                  </div>
                  <div className="pt-2 text-right">
                    <span className="text-[11px] font-semibold text-blue-600">
                      Active Model &middot; {activeRun?.metrics?.best_iteration ?? 0} Trees
                    </span>
                  </div>
                </div>
              </div>
            </section>
          )}

          {/* 4. 'Next 28 Days' Data Table Card */}
          <section className="bg-white border border-slate-200 rounded-xl shadow-xs overflow-hidden">
            <div className="px-5 py-4 border-b border-slate-200 flex flex-col sm:flex-row sm:items-center justify-between gap-2">
              <div>
                <h3 className="text-sm font-semibold text-slate-900">
                  Next 28 Days Forecast Table
                </h3>
                <p className="text-xs text-slate-500 mt-0.5">
                  Granular daily projected demand quantities with lower and upper bounds.
                </p>
              </div>
              <div className="text-xs text-slate-500 bg-slate-50 px-3 py-1.5 rounded-lg border border-slate-200 flex items-center gap-1.5">
                <Info className="w-3.5 h-3.5 text-blue-600 shrink-0" />
                <span>Note: Prediction interval is an empirical 80% range (p10 to p90).</span>
              </div>
            </div>

            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                  <tr>
                    <th className="px-5 py-3">Date</th>
                    <th className="px-5 py-3 text-right">Forecast (Units)</th>
                    <th className="px-5 py-3 text-right">Lower Bound (p10)</th>
                    <th className="px-5 py-3 text-right">Upper Bound (p90)</th>
                    <th className="px-5 py-3 text-center">Status</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {futureRows.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="px-5 py-8 text-center text-slate-400">
                        No future forecast rows available for this series.
                      </td>
                    </tr>
                  ) : (
                    futureRows.map((r, idx) => (
                      <tr key={r.id || idx} className="hover:bg-slate-50/80 transition-colors">
                        <td className="px-5 py-3 font-medium text-slate-800 flex items-center gap-2">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          <span>{r.date}</span>
                          {idx === 0 && (
                            <span className="px-1.5 py-0.5 rounded bg-blue-100 text-blue-700 text-[10px] font-semibold">
                              Forecast Start
                            </span>
                          )}
                        </td>
                        <td className="px-5 py-3 text-right font-mono font-bold text-blue-700">
                          {Math.round(r.forecast).toLocaleString('en-US')}
                        </td>
                        <td className="px-5 py-3 text-right font-mono text-slate-600">
                          {Math.round(r.lower).toLocaleString('en-US')}
                        </td>
                        <td className="px-5 py-3 text-right font-mono text-slate-600">
                          {Math.round(r.upper).toLocaleString('en-US')}
                        </td>
                        <td className="px-5 py-3 text-center">
                          <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-medium bg-emerald-50 text-emerald-700 border border-emerald-200">
                            Projected
                          </span>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}
    </div>
  );
};

export default ForecastPage;
