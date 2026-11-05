import React, { useState, useMemo } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  AlertTriangle,
  AlertCircle,
  CheckCircle2,
  Layers,
  Search,
  Store,
  HelpCircle,
  Loader2,
  Check,
  X,
  Edit2,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react';
import api from '../api/client';

export interface InventoryAlertItem {
  stock_id?: number;
  store: string;
  sku: string;
  on_hand: number;
  lead_time_days: number;
  avg_daily_forecast: number;
  lead_time_demand: number;
  safety_stock: number;
  reorder_point: number;
  days_of_cover: number;
  status: 'stockout_risk' | 'reorder_now' | 'overstock' | 'ok';
  suggested_order_qty: number;
}

export interface InventorySummary {
  run_id: number;
  counts: {
    stockout_risk: number;
    reorder_now: number;
    overstock: number;
    ok: number;
  };
  status_counts?: {
    stockout_risk: number;
    reorder_now: number;
    overstock: number;
    ok: number;
  };
  total_suggested_order_units: number;
  estimated_overstock_units: number;
}

export interface StoreOption {
  id: number;
  code: string;
  name: string;
}

export const InventoryPage: React.FC = () => {
  const queryClient = useQueryClient();

  // Filters state
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [storeFilter, setStoreFilter] = useState<string>('');
  const [skuSearch, setSkuSearch] = useState<string>('');

  // Pagination state (client-side over fetched alerts)
  const [currentPage, setCurrentPage] = useState<number>(1);
  const pageSize = 10;

  // Editing on-hand state
  const [editingStockId, setEditingStockId] = useState<number | null>(null);
  const [editValue, setEditValue] = useState<string>('');
  const [editError, setEditError] = useState<string | null>(null);

  // Tooltip visibility state
  const [showRopTooltip, setShowRopTooltip] = useState(false);
  const [showSsTooltip, setShowSsTooltip] = useState(false);

  // 1. Fetch Stores for dropdown
  const { data: stores } = useQuery<StoreOption[]>({
    queryKey: ['retail-stores'],
    queryFn: async () => {
      const res = await api.get<StoreOption[]>('/retail/stores/');
      return res.data;
    },
  });

  // 2. Fetch Inventory Summary counts
  const {
    data: summary,
    isLoading: summaryLoading,
  } = useQuery<InventorySummary>({
    queryKey: ['inventory-summary'],
    queryFn: async () => {
      const res = await api.get<InventorySummary>('/inventory/summary/');
      return res.data;
    },
  });

  // 3. Fetch Inventory Alerts (filtered by status and store on backend)
  const {
    data: alerts,
    isLoading: alertsLoading,
    isFetching: alertsFetching,
    error: alertsError,
  } = useQuery<InventoryAlertItem[]>({
    queryKey: ['inventory-alerts', statusFilter, storeFilter],
    queryFn: async () => {
      const params = new URLSearchParams();
      if (statusFilter) params.append('status', statusFilter);
      if (storeFilter) params.append('store', storeFilter);
      const res = await api.get<InventoryAlertItem[]>(`/inventory/alerts/?${params.toString()}`);
      return res.data;
    },
  });

  // 4. Mutation for updating StockLevel on-hand (PATCH /inventory/stock/{id}/)
  const updateStockMutation = useMutation({
    mutationFn: async ({ stockId, newOnHand }: { stockId: number; newOnHand: number }) => {
      const res = await api.patch(`/inventory/stock/${stockId}/`, {
        on_hand: newOnHand,
      });
      return res.data;
    },
    onSuccess: () => {
      setEditingStockId(null);
      setEditValue('');
      setEditError(null);
      queryClient.invalidateQueries({ queryKey: ['inventory-alerts'] });
      queryClient.invalidateQueries({ queryKey: ['inventory-summary'] });
    },
    onError: (err: any) => {
      const msg =
        err.response?.data?.on_hand?.[0] ||
        err.response?.data?.detail ||
        'Failed to update on-hand stock.';
      setEditError(msg);
    },
  });

  const handleStartEdit = (item: InventoryAlertItem) => {
    if (item.stock_id) {
      setEditingStockId(item.stock_id);
      setEditValue(String(item.on_hand));
      setEditError(null);
    }
  };

  const handleSaveEdit = (stockId: number) => {
    const val = parseFloat(editValue);
    if (isNaN(val) || val < 0) {
      setEditError('Please enter a valid positive number');
      return;
    }
    updateStockMutation.mutate({ stockId, newOnHand: val });
  };

  const handleCancelEdit = () => {
    setEditingStockId(null);
    setEditValue('');
    setEditError(null);
  };

  // Filter alerts by SKU search query client-side
  const filteredAlerts = useMemo(() => {
    if (!alerts) return [];
    if (!skuSearch.trim()) return alerts;
    const query = skuSearch.trim().toLowerCase();
    return alerts.filter(
      (a) => a.sku.toLowerCase().includes(query) || a.store.toLowerCase().includes(query)
    );
  }, [alerts, skuSearch]);

  // Paginated alerts
  const totalPages = Math.max(1, Math.ceil(filteredAlerts.length / pageSize));
  const paginatedAlerts = useMemo(() => {
    const start = (currentPage - 1) * pageSize;
    return filteredAlerts.slice(start, start + pageSize);
  }, [filteredAlerts, currentPage, pageSize]);

  // Handle clicking a status filter chip
  const handleChipClick = (statusKey: string) => {
    if (statusFilter === statusKey) {
      setStatusFilter(''); // Toggle off
    } else {
      setStatusFilter(statusKey);
    }
    setCurrentPage(1);
  };

  // Status Badge Component
  const renderStatusBadge = (status: string) => {
    switch (status) {
      case 'stockout_risk':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-red-50 text-status-stockout border border-red-200">
            <span className="w-1.5 h-1.5 rounded-full bg-status-stockout animate-pulse" />
            Stockout risk
          </span>
        );
      case 'reorder_now':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-orange-50 text-status-reorder border border-orange-200">
            <span className="w-1.5 h-1.5 rounded-full bg-status-reorder" />
            Reorder now
          </span>
        );
      case 'overstock':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-purple-50 text-status-overstock border border-purple-200">
            <span className="w-1.5 h-1.5 rounded-full bg-status-overstock" />
            Overstock
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-status-ok border border-emerald-200">
            <span className="w-1.5 h-1.5 rounded-full bg-status-ok" />
            OK
          </span>
        );
    }
  };

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* 1. Header & Context */}
      <section className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-xl sm:text-2xl font-bold text-slate-900 tracking-tight">
            Inventory Alerts &amp; Replenishment
          </h2>
          <p className="text-xs sm:text-sm text-slate-500 mt-0.5">
            Dynamic reorder triggers, safety stock margins, and suggested purchase quantities.
          </p>
        </div>
        <div className="flex items-center gap-2">
          {alertsFetching && !alertsLoading && (
            <span className="text-xs text-blue-600 flex items-center gap-1.5">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span>Updating inventory data...</span>
            </span>
          )}
        </div>
      </section>

      {/* 2. Four Interactive Summary Filter Chips */}
      <section className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {/* Chip 1: Stockout Risk */}
        <div
          onClick={() => handleChipClick('stockout_risk')}
          className={`bg-white rounded-xl p-4 border transition-all cursor-pointer shadow-xs hover:shadow-md relative overflow-hidden ${
            statusFilter === 'stockout_risk'
              ? 'border-status-stockout ring-2 ring-red-200 bg-red-50/20'
              : 'border-slate-200 hover:border-red-300'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="p-1.5 bg-red-50 text-status-stockout rounded-lg">
                <AlertCircle className="w-4 h-4" />
              </span>
              <span className="text-xs font-semibold text-slate-800">Stockout Risk</span>
            </div>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-red-100 text-status-stockout uppercase">
              Urgent
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-status-stockout">
              {summaryLoading ? '—' : summary?.counts?.stockout_risk ?? 0}
            </span>
            <span className="text-xs text-slate-500">SKU locations</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100">
            On-hand stock is lower than expected lead-time demand.
          </p>
        </div>

        {/* Chip 2: Reorder Now */}
        <div
          onClick={() => handleChipClick('reorder_now')}
          className={`bg-white rounded-xl p-4 border transition-all cursor-pointer shadow-xs hover:shadow-md relative overflow-hidden ${
            statusFilter === 'reorder_now'
              ? 'border-status-reorder ring-2 ring-orange-200 bg-orange-50/20'
              : 'border-slate-200 hover:border-orange-300'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="p-1.5 bg-orange-50 text-status-reorder rounded-lg">
                <AlertTriangle className="w-4 h-4" />
              </span>
              <span className="text-xs font-semibold text-slate-800">Reorder Now</span>
            </div>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-orange-100 text-status-reorder uppercase">
              Trigger
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-status-reorder">
              {summaryLoading ? '—' : summary?.counts?.reorder_now ?? 0}
            </span>
            <span className="text-xs text-slate-500">at reorder point</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100">
            Stock is at or below ROP. Issue PO to avoid dipping into safety stock.
          </p>
        </div>

        {/* Chip 3: Overstock */}
        <div
          onClick={() => handleChipClick('overstock')}
          className={`bg-white rounded-xl p-4 border transition-all cursor-pointer shadow-xs hover:shadow-md relative overflow-hidden ${
            statusFilter === 'overstock'
              ? 'border-status-overstock ring-2 ring-purple-200 bg-purple-50/20'
              : 'border-slate-200 hover:border-purple-300'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="p-1.5 bg-purple-50 text-status-overstock rounded-lg">
                <Layers className="w-4 h-4" />
              </span>
              <span className="text-xs font-semibold text-slate-800">Overstock</span>
            </div>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-purple-100 text-status-overstock uppercase">
              Excess
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-status-overstock">
              {summaryLoading ? '—' : summary?.counts?.overstock ?? 0}
            </span>
            <span className="text-xs text-slate-500">&gt; 21d cover</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100">
            Estimated excess:{' '}
            <strong className="text-slate-700">
              {summary?.estimated_overstock_units
                ? Math.round(summary.estimated_overstock_units).toLocaleString('en-US')
                : '—'}{' '}
              units
            </strong>
          </p>
        </div>

        {/* Chip 4: OK / Optimal */}
        <div
          onClick={() => handleChipClick('ok')}
          className={`bg-white rounded-xl p-4 border transition-all cursor-pointer shadow-xs hover:shadow-md relative overflow-hidden ${
            statusFilter === 'ok'
              ? 'border-status-ok ring-2 ring-emerald-200 bg-emerald-50/20'
              : 'border-slate-200 hover:border-emerald-300'
          }`}
        >
          <div className="flex items-center justify-between mb-2">
            <div className="flex items-center gap-2">
              <span className="p-1.5 bg-emerald-50 text-status-ok rounded-lg">
                <CheckCircle2 className="w-4 h-4" />
              </span>
              <span className="text-xs font-semibold text-slate-800">Healthy (OK)</span>
            </div>
            <span className="text-[10px] font-bold px-1.5 py-0.5 rounded bg-emerald-100 text-status-ok uppercase">
              Optimal
            </span>
          </div>
          <div className="flex items-baseline gap-2">
            <span className="text-2xl font-bold text-status-ok">
              {summaryLoading ? '—' : summary?.counts?.ok ?? 0}
            </span>
            <span className="text-xs text-slate-500">balanced items</span>
          </div>
          <p className="text-[11px] text-slate-500 mt-2 pt-2 border-t border-slate-100">
            Stock levels comfortably cover expected demand plus safety buffers.
          </p>
        </div>
      </section>

      {/* 3. Toolbar: Store Dropdown, SKU Search, Clear Filter */}
      <section className="bg-white rounded-xl border border-slate-200 p-4 shadow-xs flex flex-col sm:flex-row items-center justify-between gap-3">
        <div className="flex flex-wrap items-center gap-3 w-full sm:w-auto">
          {/* Store Filter Dropdown */}
          <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-300 rounded-lg text-xs">
            <Store className="w-3.5 h-3.5 text-slate-500 shrink-0" />
            <select
              value={storeFilter}
              onChange={(e) => {
                setStoreFilter(e.target.value);
                setCurrentPage(1);
              }}
              aria-label="Filter by store location"
              className="bg-transparent focus:outline-none cursor-pointer text-slate-800 font-semibold"
            >
              <option value="">All Stores</option>
              {stores?.map((s) => (
                <option key={s.id} value={s.code}>
                  {s.code} {s.name ? `(${s.name})` : ''}
                </option>
              ))}
            </select>
          </div>

          {/* SKU Search Box */}
          <div className="relative w-full sm:w-64">
            <Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400" />
            <input
              type="text"
              value={skuSearch}
              onChange={(e) => {
                setSkuSearch(e.target.value);
                setCurrentPage(1);
              }}
              placeholder="Search SKU code (e.g. P1)..."
              className="w-full pl-9 pr-3 py-1.5 rounded-lg border border-slate-300 text-xs text-slate-800 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 bg-white"
            />
          </div>

          {/* Active status filter indicator */}
          {statusFilter && (
            <div className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-lg bg-blue-50 text-blue-700 text-xs font-medium">
              <span>Filtered: {statusFilter.replace('_', ' ')}</span>
              <button
                onClick={() => setStatusFilter('')}
                className="hover:text-blue-900 cursor-pointer"
                title="Clear filter"
              >
                <X className="w-3.5 h-3.5" />
              </button>
            </div>
          )}
        </div>

        {/* Total count and page size */}
        <div className="text-xs text-slate-500 text-right w-full sm:w-auto">
          Showing {filteredAlerts.length} total SKU series
        </div>
      </section>

      {/* Inline edit error notification */}
      {editError && (
        <div className="p-3 bg-red-50 border border-red-200 text-red-700 rounded-lg text-xs flex items-center justify-between">
          <span>{editError}</span>
          <button onClick={() => setEditError(null)} className="underline font-semibold ml-2">
            Dismiss
          </button>
        </div>
      )}

      {/* 4. Inventory Alerts Table */}
      <section className="bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden">
        {alertsLoading ? (
          <div className="p-16 text-center text-sm text-slate-500 flex flex-col items-center justify-center gap-2">
            <Loader2 className="w-8 h-8 animate-spin text-blue-600" />
            <span>Calculating dynamic safety stocks &amp; replenishment metrics...</span>
          </div>
        ) : alertsError ? (
          <div className="p-12 text-center text-sm text-red-600">
            Failed to load inventory alerts. Please verify that a completed forecast run exists.
          </div>
        ) : filteredAlerts.length === 0 ? (
          <div className="p-12 text-center text-sm text-slate-500">
            No inventory items match your current filter criteria.
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider">
                <tr>
                  <th className="px-4 py-3">Store</th>
                  <th className="px-4 py-3">SKU</th>
                  <th className="px-4 py-3 text-right">
                    <span title="Click on an on-hand value below to edit it inline">
                      On Hand <Edit2 className="w-3 h-3 inline-block ml-0.5 text-slate-400" />
                    </span>
                  </th>
                  <th className="px-4 py-3 text-right">Lead Time</th>
                  <th className="px-4 py-3 text-right">Avg Daily</th>
                  <th className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-1 relative">
                      <span>Safety Stock</span>
                      <button
                        type="button"
                        onMouseEnter={() => setShowSsTooltip(true)}
                        onMouseLeave={() => setShowSsTooltip(false)}
                        className="text-slate-400 hover:text-slate-600 focus:outline-none"
                      >
                        <HelpCircle className="w-3.5 h-3.5" />
                      </button>
                      {showSsTooltip && (
                        <div className="absolute top-6 right-0 z-50 w-60 p-2.5 bg-slate-900 text-white text-[11px] rounded-lg shadow-lg normal-case font-normal leading-relaxed">
                          Buffer inventory held to protect against unexpected sales surges and delivery delays.
                        </div>
                      )}
                    </div>
                  </th>
                  <th className="px-4 py-3 text-right">
                    <div className="inline-flex items-center gap-1 relative">
                      <span>Reorder Point</span>
                      <button
                        type="button"
                        onMouseEnter={() => setShowRopTooltip(true)}
                        onMouseLeave={() => setShowRopTooltip(false)}
                        className="text-slate-400 hover:text-slate-600 focus:outline-none"
                      >
                        <HelpCircle className="w-3.5 h-3.5" />
                      </button>
                      {showRopTooltip && (
                        <div className="absolute top-6 right-0 z-50 w-60 p-2.5 bg-slate-900 text-white text-[11px] rounded-lg shadow-lg normal-case font-normal leading-relaxed">
                          The minimum stock level that triggers purchase reordering before safety margins are breached.
                        </div>
                      )}
                    </div>
                  </th>
                  <th className="px-4 py-3 text-right">Days Cover</th>
                  <th className="px-4 py-3 text-center">Status</th>
                  <th className="px-4 py-3 text-right">Suggested Order</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {paginatedAlerts.map((row) => (
                  <tr
                    key={`${row.store}-${row.sku}`}
                    className="hover:bg-slate-50/80 transition-colors"
                  >
                    {/* Store */}
                    <td className="px-4 py-3 font-semibold text-slate-800">
                      {row.store}
                    </td>

                    {/* SKU */}
                    <td className="px-4 py-3 font-semibold text-slate-800">
                      {row.sku}
                    </td>

                    {/* On Hand (Clickable to Edit) */}
                    <td className="px-4 py-3 text-right">
                      {editingStockId === row.stock_id ? (
                        <div className="inline-flex items-center gap-1 justify-end">
                          <input
                            type="number"
                            step="any"
                            min="0"
                            value={editValue}
                            onChange={(e) => setEditValue(e.target.value)}
                            className="w-20 px-1.5 py-0.5 text-xs text-right border border-blue-500 rounded bg-white text-slate-900 focus:outline-none focus:ring-1 focus:ring-blue-600 font-mono"
                            autoFocus
                          />
                          <button
                            onClick={() => handleSaveEdit(row.stock_id!)}
                            disabled={updateStockMutation.isPending}
                            className="p-1 rounded bg-emerald-600 text-white hover:bg-emerald-700 cursor-pointer"
                            title="Save"
                          >
                            <Check className="w-3 h-3" />
                          </button>
                          <button
                            onClick={handleCancelEdit}
                            className="p-1 rounded bg-slate-200 text-slate-700 hover:bg-slate-300 cursor-pointer"
                            title="Cancel"
                          >
                            <X className="w-3 h-3" />
                          </button>
                        </div>
                      ) : (
                        <button
                          type="button"
                          onClick={() => handleStartEdit(row)}
                          className="font-mono font-bold text-slate-900 hover:text-blue-600 hover:underline px-1 py-0.5 rounded transition-colors cursor-pointer group"
                          title="Click to edit on-hand stock"
                        >
                          <span>{Math.round(row.on_hand).toLocaleString('en-US')}</span>
                          <Edit2 className="w-2.5 h-2.5 ml-1 inline-block opacity-0 group-hover:opacity-100 text-blue-500" />
                        </button>
                      )}
                    </td>

                    {/* Lead Time */}
                    <td className="px-4 py-3 text-right text-slate-600 font-mono">
                      {row.lead_time_days}d
                    </td>

                    {/* Avg Daily */}
                    <td className="px-4 py-3 text-right text-slate-600 font-mono">
                      {Math.round(row.avg_daily_forecast).toLocaleString('en-US')}
                    </td>

                    {/* Safety Stock */}
                    <td className="px-4 py-3 text-right text-slate-600 font-mono">
                      {Math.round(row.safety_stock).toLocaleString('en-US')}
                    </td>

                    {/* Reorder Point */}
                    <td className="px-4 py-3 text-right text-slate-800 font-mono font-medium">
                      {Math.round(row.reorder_point).toLocaleString('en-US')}
                    </td>

                    {/* Days of Cover */}
                    <td className="px-4 py-3 text-right font-mono font-medium">
                      <span
                        className={
                          row.days_of_cover < 3
                            ? 'text-status-stockout font-bold'
                            : row.days_of_cover < 10
                            ? 'text-status-reorder font-semibold'
                            : row.days_of_cover > 30
                            ? 'text-status-overstock'
                            : 'text-slate-700'
                        }
                      >
                        {row.days_of_cover.toFixed(1)}d
                      </span>
                    </td>

                    {/* Status Badge */}
                    <td className="px-4 py-3 text-center whitespace-nowrap">
                      {renderStatusBadge(row.status)}
                    </td>

                    {/* Suggested Order Qty */}
                    <td className="px-4 py-3 text-right font-mono">
                      {row.suggested_order_qty > 0 ? (
                        <span className="font-bold text-blue-700 bg-blue-50 px-2 py-0.5 rounded">
                          +{Math.round(row.suggested_order_qty).toLocaleString('en-US')}
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

        {/* 5. Pagination Footer */}
        {totalPages > 1 && (
          <div className="px-4 py-3 bg-slate-50 border-t border-slate-200 flex items-center justify-between text-xs text-slate-500">
            <div>
              Showing {(currentPage - 1) * pageSize + 1} to{' '}
              {Math.min(currentPage * pageSize, filteredAlerts.length)} of{' '}
              {filteredAlerts.length} items
            </div>
            <div className="flex items-center gap-1.5">
              <button
                onClick={() => setCurrentPage((p) => Math.max(1, p - 1))}
                disabled={currentPage === 1}
                className="px-2.5 py-1 rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 cursor-pointer flex items-center gap-1"
              >
                <ChevronLeft className="w-3.5 h-3.5" />
                <span>Previous</span>
              </button>
              <span className="px-2 font-medium text-slate-800">
                Page {currentPage} of {totalPages}
              </span>
              <button
                onClick={() => setCurrentPage((p) => Math.min(totalPages, p + 1))}
                disabled={currentPage === totalPages}
                className="px-2.5 py-1 rounded border border-slate-200 bg-white text-slate-700 hover:bg-slate-50 disabled:opacity-50 cursor-pointer flex items-center gap-1"
              >
                <span>Next</span>
                <ChevronRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        )}
      </section>
    </div>
  );
};

export default InventoryPage;
