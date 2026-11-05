# ShelfWise Design Specification (As Built)

This document details the visual design system, UI architecture, layout principles, and component standards implemented across the ShelfWise retail demand forecasting and inventory replenishment application.

---

## 1. Visual Direction & Aesthetic Philosophy

ShelfWise is an enterprise-grade retail intelligence platform designed for boutique operators, inventory planners, and multi-location retail managers. The visual direction balances high-density data presentation with clean, modern clarity.

### Core Principles
- **Clarity Over Clutter**: Clean surfaces, hairline dividers, and deliberate spacing replace the overwhelming visual density typical of legacy ERP platforms.
- **Actionable Visual Hierarchy**: Important operational indicators (stockouts, reorder triggers, prediction intervals) are surfaced immediately through calibrated color accents and structured KPI cards.
- **Surface Elevation**: A light canvas (`#F8FAFC`, Tailwind `slate-50`) paired with crisp white cards (`#FFFFFF`, `rounded-xl`, 12px border radius) and subtle elevation (`shadow-xs` / `shadow-sm`) provides clear visual hierarchy without distracting drop shadows.
- **Consistent Precision**: Financial quantities, unit volumes, and percentages are formatted uniformly (thousands separators for volume, one-decimal precision for WAPE percentages, standardized currency and date formats).

---

## 2. Color System & Design Tokens

Theme tokens are declared in `frontend/src/index.css` via Tailwind v4 `@theme` directives and supplemented by standard Tailwind Slate utility classes.

### 2.1 Theme Tokens (`frontend/src/index.css`)

```css
@theme {
  /* Primary Brand Palette */
  --color-primary: #2563EB;
  --color-primary-dark: #1d4ed8;
  --color-primary-light: #3b82f6;

  /* Status Severity Palette */
  --color-status-stockout: #EF4444;
  --color-status-reorder: #F97316;
  --color-status-overstock: #A855F7;
  --color-status-ok: #10B981;

  /* Card Radius and Elevation */
  --radius-card: 12px;
  --shadow-soft: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px -1px rgba(0, 0, 0, 0.05);
}
```

### 2.2 Functional Palette

| Token Role | Hex Code / Tailwind Class | Intended Usage |
| :--- | :--- | :--- |
| **Primary Brand** | `#2563EB` (`blue-600`) | Primary CTA buttons, active sidebar navigation, chart forecast trajectories, focus rings |
| **Primary Dark / Hover** | `#1D4ED8` (`blue-700`) | Hover states on primary buttons, marketing gradient anchors |
| **Primary Light / Subtle** | `#EFF6FF` (`blue-50`), `#DBEAFE` (`blue-100`) | Selected container highlights, active running status chips |
| **Stockout Risk** | `#EF4444` (`status-stockout`), `bg-red-50`, `border-red-200` | Critical alerts: zero stock or stockout within lead time, failed runs |
| **Reorder Now** | `#F97316` (`status-reorder`), `bg-orange-50`, `border-orange-200` | Urgent warnings: stock level has breached reorder point |
| **Overstock** | `#A855F7` (`status-overstock`), `bg-purple-50`, `border-purple-200` | Capital tied up: stock coverage exceeds 21 days |
| **Optimal / Healthy** | `#10B981` (`status-ok`), `bg-emerald-50`, `border-emerald-200` | Normal operations: balanced inventory covering forecast + safety buffer |
| **App Canvas** | `#F8FAFC` (`slate-50`) | Full-page background behind all views |
| **Surface Card** | `#FFFFFF` (`bg-white`) | Cards, tables, navigation sidebar, toolbars |
| **Hairline Borders** | `#E2E8F0` (`border-slate-200`) | Card outlines, table dividers, topbar border |
| **Text Primary** | `#0F172A` (`text-slate-900`) | Main headings, bold table values, dark brand logo |
| **Text Secondary** | `#334155` (`text-slate-700`), `#475569` (`text-slate-600`) | Body copy, secondary titles, table headers |
| **Text Muted** | `#64748B` (`text-slate-500`) | Field labels, captions, helper text, empty states |
| **Text Subdued / Border** | `#94A3B8` (`text-slate-400`), `#CBD5E1` (`border-slate-300`) | Search icons, disabled states, input borders |

### 2.3 Data Visualization Palette (Recharts)

- **Forecast Line**: `#2563EB` (Primary blue, 2.5px solid stroke, circular active dots).
- **Historical Actuals Line**: `#0F172A` / `#334155` (Slate-900, 2px solid stroke, circular data dots).
- **Prediction Interval Band**: Recharts stacked `Area` component:
  - Base Area (0 to lower bound): `fillOpacity={0}` (transparent).
  - Spread Area (lower to upper bound): `fill="rgba(37, 99, 235, 0.12)"`, `stroke="#93C5FD"` (blue-300), stroke width 1px.
- **Forecast Cutoff Divider**: ReferenceLine positioned at the first future date, `stroke="#64748B"`, `strokeDasharray="4 4"`, labelled `"Forecast starts"`.
- **Chart Grid Lines**: `stroke="#E2E8F0"`, `strokeDasharray="3 3"`.

---

## 3. Typography

ShelfWise adheres to a clean modern sans-serif typography system for interface data, paired with a traditional serif treatment reserved exclusively for the brand logo.

### 3.1 Primary Interface Typeface
- **Font Family**: `'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif`
- **Base Body**: 14px (`text-sm`), regular or medium weight, line height 1.5.
- **Type Scale**:
  - `Display / Marketing Titles`: `text-3xl` (30px) or `text-[32px]`, bold (`700`), leading-tight, tracking-tight (Login showcase).
  - `Page Titles`: `text-xl sm:text-2xl` (20–24px), bold (`700`), text-slate-900, tracking-tight.
  - `Section / Card Titles`: `text-base` (16px), semibold (`600`), text-slate-900.
  - `Sub-headers & Toolbar Text`: `text-sm` (14px) or `text-xs` (12px), text-slate-500.
  - `Table Column Headers`: `text-xs` (12px), semibold (`600`), text-slate-600, uppercase, tracking-wider.
  - `Data Numerics & Code Identifiers`: `font-mono` (`text-xs`), used for SKU numbers, Store codes, dates, unit metrics, and dataset identifiers.
  - `Microcopy & Badges`: `text-[10px]` or `text-[11px]`, semibold or bold, uppercase or tracking-wide.

### 3.2 Brand Logo Specification (`Logo.tsx`)
The ShelfWise logo follows strict typographic rules:
- **Font Family**: `"Times New Roman", Times, serif`
- **Font Weight**: `400` (strictly regular weight; never bolded)
- **Font Style**: `normal` (never italicized)
- **Icon / Symbol**: Pure text mark only (no icon, logo mark, or accompanying glyph)
- **Variants**:
  - `variant="dark"` (default): `#0F172A` (Slate-900) on light canvases and sidebar.
  - `variant="white"`: `#FFFFFF` on the blue marketing showcase panel.
- **Sizes**: `sm` (`text-lg`), `md` (`text-2xl`), `lg` (`text-3xl`), `xl` (`text-4xl`), `2xl` (`text-5xl`).

---

## 4. Spacing, Elevation & Layout Architecture

### 4.1 Shell Layout Architecture (`Layout.tsx`)
The application uses a persistent two-pane shell layout:
- **Sidebar**: Fixed on the left (`fixed left-0 top-0 h-screen w-64 z-30`), background white (`bg-white`), bordered by hairline divider (`border-r border-slate-200`).
- **Main Viewport**: Offset by the sidebar width (`ml-64 flex-1 flex flex-col min-h-screen`).
- **Sticky Topbar**: `sticky top-0 z-20`, `bg-white/80 backdrop-blur`, `border-b border-slate-200`, `px-8 py-3`. Displays contextual current route page title, user email, and logout action.
- **Content Container**: `flex-1 p-8 overflow-y-auto`, constrained to `max-w-7xl mx-auto space-y-6`.

### 4.2 Spacing & Grid System
- **Page Vertical Spacing**: `space-y-6` (24px gap between functional page sections).
- **Grid Layouts**:
  - Inventory Status Summary Cards: `grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4`.
  - Model Performance Metric Cards: `grid grid-cols-1 md:grid-cols-3 gap-4`.
  - Two-Column Operational Views: `grid grid-cols-1 lg:grid-cols-3 gap-6`.
- **Card Padding**:
  - Compact Cards / Summary Chips: `p-4` (16px).
  - Standard Content Cards & Toolbars: `p-5` or `p-6` (20–24px).
  - Hero Panels: `p-8 xl:p-14`.

### 4.3 Borders and Shadows
- **Corner Radii**:
  - Interactive Cards / Containers: `rounded-xl` (12px, matching `--radius-card`).
  - Buttons and Dropdown Triggers: `rounded-lg` (8px).
  - Status Badges / Pills: `rounded-full`.
- **Shadows**:
  - Cards & Toolbars: `shadow-xs` (`0 1px 2px 0 rgba(0, 0, 0, 0.05)`).
  - Hover / Interactive Surfaces: `hover:shadow-md`.
  - Floating Tooltips & Modals: `shadow-lg`.

---

## 5. Reusable Components

### 5.1 Status Badges (`renderStatusBadge`)
Standardized pill indicators used across the Dashboard, Inventory alerts, and Forecast views:
- **Stockout Risk**: `bg-red-50 text-status-stockout border border-red-200`, with a pulsing red dot indicator (`animate-pulse`).
- **Reorder Now**: `bg-orange-50 text-status-reorder border border-orange-200`, with a solid orange dot indicator.
- **Overstock**: `bg-purple-50 text-status-overstock border border-purple-200`, with a solid purple dot indicator.
- **Healthy / OK**: `bg-emerald-50 text-status-ok border border-emerald-200`, with a solid emerald dot indicator.

### 5.2 Metric / KPI Stat Cards
- Enclosed in `bg-white rounded-xl border border-slate-200 p-4 shadow-xs`.
- Header: Small icon pill (14x14px icon) + muted title + optional right-aligned pill tag.
- Center: Large numeric readout (`text-2xl font-bold font-mono`).
- Footer: Bottom-bordered auxiliary context (e.g. baseline comparisons, day counts, total units).

### 5.3 Interactive Toolbars
- Container: `bg-white border border-slate-200 rounded-xl p-4 sm:p-5 shadow-xs flex flex-col lg:flex-row lg:items-center justify-between gap-4`.
- Select Controls: Embedded inside an icon wrapper (`StoreIcon`, `Package`) with `bg-slate-50 border border-slate-300 rounded-lg text-xs font-semibold px-3 py-2`.

### 5.4 Data Tables
- Wrapper: `bg-white rounded-xl border border-slate-200 shadow-xs overflow-hidden` with `overflow-x-auto`.
- Header (`thead`): `bg-slate-50 border-b border-slate-200 text-slate-600 font-semibold uppercase tracking-wider text-xs`.
- Body Rows (`tbody tr`): `divide-y divide-slate-100 hover:bg-slate-50/80 transition-colors`.
- Data Cells: Left-aligned for categorical text (Store, SKU, Date); right-aligned with `font-mono` for numbers (On Hand, Lead Time, Safety Stock, Reorder Point, Forecast, Actual).

### 5.5 Inline Table Editing
- Implemented on the Inventory alerts table for `on_hand` stock levels.
- Clicking the cell renders a numeric input (`w-20 px-1.5 py-0.5 text-xs text-right border border-blue-500 rounded bg-white text-slate-900 font-mono`) with green Save (checkmark) and gray Cancel (X) buttons.

### 5.6 Interactive Information Tooltips
- Located on table column headers (e.g. Safety Stock, Reorder Point).
- Triggered on hover over a `HelpCircle` icon, displaying a dark floating card (`bg-slate-900 text-white text-[11px] rounded-lg shadow-lg p-2.5 max-w-xs`).

---

## 6. Navigation Architecture

```
/ (Root)
│
├── /login ────────────── Dual-panel authentication, demo login, Google SSO
├── /register ─────────── Account registration
├── /auth/callback ────── OIDC SSO OAuth callback listener
│
└── / (Protected Shell Layout via Layout.tsx)
    ├── / (Dashboard) ─── Portfolio metrics, aggregated forecast, urgent alerts
    ├── /upload ───────── POS sales CSV upload, Pandera validation, audit log
    ├── /forecast ─────── Store/SKU LightGBM models, 28-day intervals, benchmarks
    ├── /inventory ────── Dynamic alerts, ROP/Safety stock, inline stock edits
    └── /assistant ────── Grounded AI chat assistant with multi-turn tool calling
```

- Navigation links are rendered in `Sidebar.tsx` via `NavLink`.
- Active Route: `bg-blue-600 text-white shadow-sm`.
- Inactive Routes: `text-slate-600 hover:bg-slate-100 hover:text-slate-900`.
- End parameter set on the dashboard link to prevent partial matching.

---

## 7. Forms & User Inputs

### 7.1 Text Inputs & Search Bars
- Standard Styling: `px-3.5 py-2.5 rounded-lg border border-slate-300 text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent bg-white shadow-xs`.
- Search Variants: Preceded by an absolute left icon (`Search className="w-3.5 h-3.5 absolute left-3 top-2.5 text-slate-400"`), with `pl-9` padding.

### 7.2 File Upload & Dropzone (`UploadPage.tsx`)
- Drag & Drop Zone: Dashed border container (`border-2 border-dashed rounded-xl p-8 text-center transition-all cursor-pointer`).
- States:
  - Default: `border-slate-300 hover:border-blue-400 hover:bg-slate-50/50`.
  - Dragging Active: `border-blue-600 bg-blue-50/50 scale-[0.99]`.
  - File Selected: `border-blue-400 bg-blue-50/20` with file metadata chip and remove button.
- Schema column hints: Listed as pills (`requiredColumns = ['store', 'sku', 'date', 'units_sold', 'price', 'on_promo']`).

### 7.3 Chat Input (`AssistantPage.tsx`)
- Sticky bottom footer containing a flex input bar with `focus-within:ring-2 focus-within:ring-blue-600`.
- Enter key submits query; Shift+Enter is reserved; button features a spinner during model tool execution.

---

## 8. Loading, Empty & Error States

### 8.1 Loading States
- **Full View / Table Loading**: Centered container with `Loader2 className="w-8 h-8 animate-spin text-blue-600"` and a descriptive message (e.g. *"Calculating dynamic safety stocks & replenishment metrics..."*).
- **Button Loading**: Button disabled, `Loader2` replacing or preceding the icon, label changing (e.g. *"Training Pipeline..."*, *"Importing & Validating..."*).
- **Background Refreshing**: Non-blocking subtle badge (e.g. *"Syncing..."*, *"Updating telemetry..."* with a pulsing blue indicator).
- **AI Assistant Response**: Animated typing card with `Bot` avatar and loading note (*"Querying retail telemetry and generating grounded recommendation..."*).

### 8.2 Empty States
- **Empty Inventory Filter**: Padded center card: *"No inventory items match your current filter criteria."*
- **Empty Datasets**: *"No datasets uploaded yet. Upload your first sales CSV above."*
- **Assistant Welcoming State**: Clean introductory card detailing capabilities (stockout detection, causal analysis, reorder planning, model benchmarks) with clickable starter prompt pills.

### 8.3 Error States
- **Validation Errors (Pandera Schema)**: Red container (`bg-red-50 border border-red-200 rounded-xl p-5`) with `AlertTriangle` icon, error count heading, and a scrollable monospace list of specific schema failure rows.
- **Model Training Failure**: Red status badge (`bg-red-50 text-red-700 border-red-200`) and an alert banner detailing the runtime failure (e.g., interrupted runs, insufficient training rows).
- **API Failure Banners**: Inline banners with dismiss action and retry guidance.

---

## 9. Responsive Behavior & Breakpoints

ShelfWise uses standard Tailwind CSS breakpoints:
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px

### Adaptations Implemented:
- **Dashboard & Inventory KPI Grids**: Collapse from 4 columns (`lg:grid-cols-4`) to 2 columns on tablets (`sm:grid-cols-2`) and 1 column on mobile phones (`grid-cols-1`).
- **Benchmark Metric Cards**: Collapse from 3 columns (`md:grid-cols-3`) to a single column on small devices.
- **Authentication Pages**: Display brand marketing hero and login form side-by-side (`lg:w-1/2 flex-row`), stacking vertically on smaller displays (`flex-col`).
- **Data Tables**: Wrapped in `overflow-x-auto` containers with minimum width requirements to prevent layout breakage on narrower screens.
- **Toolbars & Filter Bars**: Wrap horizontally and shift to vertical stacks on mobile (`flex-col sm:flex-row`).

---

## 10. Accessibility (a11y)

### Built-in Practices:
- **Semantic Structure**: Proper usage of HTML landmarks (`<header>`, `<main>`, `<aside>`, `<nav>`, `<table>`, `<form>`).
- **Visual Contrast**: Dark slate text (`#0F172A`, `#334155`) on white and light slate canvases exceeds standard contrast requirements.
- **Form Association**: Select dropdowns in the Forecast toolbar use hidden screen-reader labels (`<label className="sr-only">`) and explicit `aria-label` attributes.
- **Tabular Data**: Proper `<thead>`, `<tbody>`, `<th>`, and `<td>` tags with alignment indicators.

---

## 11. Gaps & Areas for Improvement

The following is an audit of real accessibility, responsive, and ergonomic gaps observed in the built codebase:

### 11.1 Mobile Layout & Sidebar Collision
- **Fixed Sidebar Offset**: In `Layout.tsx`, the main content area has hardcoded `ml-64 flex-1 flex flex-col min-h-screen`, and `Sidebar.tsx` has `fixed left-0 top-0 h-screen w-64 z-30`. There is no mobile drawer, slide-out toggle, or collapsing breakpoint (`hidden md:block`).
- **Impact**: On viewports narrower than 768px (smartphones and portrait tablets), the 256px sidebar permanently covers half or all of the viewport or causes severe horizontal blowout.

### 11.2 Missing Form Labels & Accessible Names
- **Inventory SKU Search**: In `InventoryPage.tsx`, the search `<input type="text" placeholder="Search SKU code (e.g. P1)..." />` lacks a `<label>` element and an `aria-label` attribute.
- **Upload Dataset Search**: In `UploadPage.tsx`, the search `<input type="text" placeholder="Search uploads..." />` has no `<label>` or `aria-label`.
- **Chat Query Input**: In `AssistantPage.tsx`, the prompt `<input type="text" placeholder="Ask a question..." />` lacks an explicit `<label>` or `aria-label`.
- **Inline Table On-Hand Input**: In `InventoryPage.tsx`, the inline stock editor input (`<input type="number" step="any" min="0" ... />`) has no `aria-label` identifying which SKU or store is being edited.

### 11.3 Interactive Non-Semantic Elements
- **Inventory Filter Summary Cards**: The four status summary cards at the top of `InventoryPage.tsx` act as interactive toggle filters (`onClick={() => handleChipClick('stockout_risk')}`), but are rendered as plain `<div>` elements without `role="button"`, `tabIndex={0}`, `aria-pressed`, or keyboard event listeners (`onKeyDown` for Enter / Space). Keyboard-only users cannot activate these filters.

### 11.4 Color Contrast Deficiencies (WCAG 2.1 AA)
- **Subdued Slate Text (`text-slate-400`)**: Hex `#94A3B8` is used for auxiliary labels, search icons, and table captions. On a white background (`#FFFFFF`), the contrast ratio is **2.5:1**, failing the WCAG AA minimum requirement of **4.5:1** for regular body text.
- **Status Badge Text on Light Backgrounds**:
  - Reorder Now Badge: `--color-status-reorder` (`#F97316`) on `bg-orange-50` (`#FFF7ED`) has a contrast ratio of **~2.9:1** (failing WCAG AA 4.5:1).
  - Healthy (OK) Badge: `--color-status-ok` (`#10B981`) on `bg-emerald-50` (`#ECFDF5`) has a contrast ratio of **~2.6:1** (failing WCAG AA 4.5:1).
  - Stockout Badge: `--color-status-stockout` (`#EF4444`) on white has a contrast ratio of **~3.9:1** (failing WCAG AA 4.5:1).
  - *Recommended Remediation*: Use darker text variants for pill badges (e.g. `text-red-700`, `text-amber-800`, `text-emerald-800`, `text-purple-800`) while preserving light background pastel fills.

### 11.5 Focus Ring Visibility
- Several interactive controls (Store and SKU dropdown containers, pagination buttons, table edit action buttons, and tooltip triggers) use `focus:outline-none` without declaring a replacement `focus-visible:ring-2` style, leaving keyboard navigators without a visible focus indicator.

### 11.6 Mouse-Only Tooltip Disclosure
- In `InventoryPage.tsx`, the Safety Stock and Reorder Point column header tooltips rely exclusively on `onMouseEnter` and `onMouseLeave` on a `<button type="button">`. Keyboard navigators tabbing through the table cannot trigger or read the tooltip descriptions, and the tooltips lack `role="tooltip"` and `aria-describedby` associations.

### 11.7 Dense Table Horizontal Navigation on Mobile
- Both the Inventory Alerts table (10 columns) and the Forecast Future table (4 columns) rely on container `overflow-x-auto`. On smaller screens, horizontal scrolling occurs without a pinned or sticky first column (Store and SKU), causing users to lose track of which row corresponds to which product when scrolling to the right.

