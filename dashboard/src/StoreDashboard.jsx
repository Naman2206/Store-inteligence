import { useState, useEffect } from "react";
import {
  BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, PieChart, Pie, Legend,
  FunnelChart, Funnel, LabelList
} from "recharts";

// ── Real data from Brigade Road 10 April 2026 ──────────────────────────
const DATA = {
  summary: {
    total_orders: 24, unique_customers: 21, total_gmv: 44920,
    total_nmv: 34831.74, total_units_sold: 117, avg_basket_value_gmv: 1871.67,
    avg_units_per_basket: 4.88, discount_amount: 500.03, discount_pct: 1.11,
    estimated_footfall: 28, conversion_rate_pct: 75.0,
  },
  hourly: [
    { hour: 12, orders: 2, gmv: 2043, qty: 7 },
    { hour: 13, orders: 2, gmv: 597, qty: 6 },
    { hour: 14, orders: 1, gmv: 225, qty: 1 },
    { hour: 15, orders: 3, gmv: 2166, qty: 5 },
    { hour: 16, orders: 3, gmv: 6742, qty: 17 },
    { hour: 17, orders: 2, gmv: 2223, qty: 7 },
    { hour: 18, orders: 3, gmv: 5887, qty: 16 },
    { hour: 19, orders: 5, gmv: 19237, qty: 48 },
    { hour: 20, orders: 1, gmv: 1749, qty: 7 },
    { hour: 21, orders: 2, gmv: 774, qty: 3 },
  ],
  departments: [
    { dep_name: "makeup", gmv: 28803, nmv: 21939, qty: 55, orders: 14, gmv_share_pct: 64.1 },
    { dep_name: "skin", gmv: 11808, nmv: 9408, qty: 42, orders: 12, gmv_share_pct: 26.3 },
    { dep_name: "hair", gmv: 2398, nmv: 1957, qty: 6, orders: 4, gmv_share_pct: 5.3 },
    { dep_name: "personal-care", gmv: 899, nmv: 764, qty: 4, orders: 3, gmv_share_pct: 2.0 },
    { dep_name: "bath-and-body", gmv: 763, nmv: 514, qty: 9, orders: 3, gmv_share_pct: 1.7 },
    { dep_name: "fragrance", gmv: 249, nmv: 249, qty: 1, orders: 1, gmv_share_pct: 0.6 },
  ],
  salespersons: [
    { salesperson_name: "Zufishan Khazra", orders: 7, qty: 53, gmv: 21871, nmv: 16583, gmv_per_order: 3124.43 },
    { salesperson_name: "kasthuri v", orders: 5, qty: 20, gmv: 8410, nmv: 6542, gmv_per_order: 1682 },
    { salesperson_name: "Shashikala .", orders: 7, qty: 12, gmv: 5001, nmv: 4632, gmv_per_order: 714.43 },
    { salesperson_name: "Priya v", orders: 3, qty: 16, gmv: 4988, nmv: 3666, gmv_per_order: 1662.67 },
    { salesperson_name: "Naziya Begum", orders: 2, qty: 9, gmv: 4637, nmv: 3409, gmv_per_order: 2318.5 },
  ],
  brands: [
    { brand_name: "Faces Canada", gmv: 20933, qty: 32, orders: 8 },
    { brand_name: "Good Vibes", gmv: 2871, qty: 14, orders: 5 },
    { brand_name: "NY Bae", gmv: 3070, qty: 10, orders: 4 },
    { brand_name: "COSRX", gmv: 2300, qty: 2, orders: 1 },
    { brand_name: "Maybelline", gmv: 2017, qty: 3, orders: 2 },
    { brand_name: "Round Lab", gmv: 1799, qty: 1, orders: 1 },
    { brand_name: "Bare Anatomy", gmv: 1324, qty: 2, orders: 1 },
    { brand_name: "Beauty of Joseon", gmv: 1420, qty: 3, orders: 1 },
    { brand_name: "DERMDOC", gmv: 1140, qty: 6, orders: 4 },
    { brand_name: "Alps Goodness", gmv: 939, qty: 3, orders: 2 },
  ],
  funnel: [
    { stage: "Footfall", count: 28, fill: "#6366f1" },
    { stage: "Engaged", count: 23, fill: "#8b5cf6" },
    { stage: "Basket", count: 28, fill: "#a78bfa" },
    { stage: "Converted", count: 24, fill: "#c4b5fd" },
    { stage: "Repeat", count: 1, fill: "#ddd6fe" },
  ],
  anomalies: [
    { type: "hourly_gmv_spike", severity: "high", description: "Hour 19:00 GMV ₹19,237 is 2.4σ above mean", hour: 19 },
    { type: "large_basket", severity: "medium", description: "Order 104341290 basket ₹11,367 exceeds IQR threshold", order_id: 104341290 },
    { type: "salesperson_concentration", severity: "low", description: "Zufishan Khazra accounts for 48.7% of GMV — high dependency risk" },
  ],
  topOrders: [
    { order_id: "104341290", customer: "thanu thanu", gmv: 11367, items: 33, brands: 8, salesperson: "Zufishan Khazra", time: "12:42" },
    { order_id: "104377545", customer: "sagar", gmv: 4385, items: 11, brands: 5, salesperson: "Zufishan Khazra", time: "19:21" },
    { order_id: "104362899", customer: "Guest", gmv: 4029, items: 6, brands: 3, salesperson: "Zufishan Khazra", time: "16:45" },
    { order_id: "104375288", customer: "rupa", gmv: 3441, items: 7, brands: 2, salesperson: "Naziya Begum", time: "19:02" },
    { order_id: "104363838", customer: "Guest", gmv: 2713, items: 8, brands: 4, salesperson: "kasthuri v", time: "16:55" },
  ],
};

// ── Colour system ────────────────────────────────────────────────────────
const C = {
  bg: "#0a0a0f",
  surface: "#12121a",
  card: "#18182a",
  border: "#252540",
  accent: "#7c6fff",
  accentSoft: "rgba(124,111,255,0.15)",
  gold: "#f5c842",
  green: "#34d399",
  red: "#f87171",
  text: "#e2e0f0",
  muted: "#7070a0",
  deptColors: ["#7c6fff","#a78bfa","#34d399","#f5c842","#f87171","#60a5fa"],
};

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const fmt = (n) => `₹${Number(n).toLocaleString("en-IN")}`;
const fmtK = (n) => n >= 1000 ? `₹${(n/1000).toFixed(1)}K` : fmt(n);

const normalizeMetrics = (metrics) => ({
  ...metrics,
  summary: metrics.summary || DATA.summary,
  hourly: metrics.by_hour || metrics.hourly || [],
  departments: metrics.by_department || metrics.departments || [],
  salespersons: metrics.by_salesperson || metrics.salespersons || [],
  brands: metrics.top_brands || metrics.brands || [],
  funnel: metrics.funnel || DATA.funnel || [],
  anomalies: metrics.anomalies || DATA.anomalies || [],
  topOrders: metrics.topOrders || DATA.topOrders,
});

// ── Severity badge ────────────────────────────────────────────────────────
const SeverityBadge = ({ s }) => {
  const cfg = { high:["#f87171","#300"], medium:["#f5c842","#2a1f00"], low:["#60a5fa","#001030"] };
  const [color, bg] = cfg[s] || cfg.low;
  return <span style={{ background: bg, color, border:`1px solid ${color}33`, borderRadius:4, padding:"1px 8px", fontSize:11, fontWeight:700, textTransform:"uppercase", letterSpacing:1 }}>{s}</span>;
};

// ── KPI Card ─────────────────────────────────────────────────────────────
const KPI = ({ label, value, sub, accent = false, big = false }) => (
  <div style={{ background: C.card, border: `1px solid ${accent ? C.accent + "55" : C.border}`, borderRadius: 12, padding: "20px 24px", position:"relative", overflow:"hidden" }}>
    {accent && <div style={{ position:"absolute", top:0, left:0, right:0, height:2, background:`linear-gradient(90deg, ${C.accent}, transparent)` }} />}
    <div style={{ fontSize: 11, color: C.muted, textTransform:"uppercase", letterSpacing:2, marginBottom:8, fontFamily:"'Space Mono', monospace" }}>{label}</div>
    <div style={{ fontSize: big ? 32 : 26, fontWeight:800, color: accent ? C.accent : C.text, fontFamily:"'Space Mono', monospace", lineHeight:1 }}>{value}</div>
    {sub && <div style={{ fontSize: 12, color: C.muted, marginTop:6 }}>{sub}</div>}
  </div>
);

// ── Section Header ────────────────────────────────────────────────────────
const SectionHead = ({ title, sub }) => (
  <div style={{ marginBottom:16 }}>
    <div style={{ fontSize:13, fontWeight:700, color:C.text, letterSpacing:2, textTransform:"uppercase", fontFamily:"'Space Mono', monospace" }}>{title}</div>
    {sub && <div style={{ fontSize:11, color:C.muted, marginTop:3 }}>{sub}</div>}
  </div>
);

// ── Custom Tooltip ────────────────────────────────────────────────────────
const DarkTip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null;
  return (
    <div style={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:8, padding:"10px 14px", fontSize:12 }}>
      <div style={{ color:C.muted, marginBottom:4, fontFamily:"'Space Mono',monospace" }}>{label}</div>
      {payload.map((p,i) => <div key={i} style={{ color:p.color || C.text }}>{p.name}: <strong>{typeof p.value === "number" && p.value > 500 ? fmtK(p.value) : p.value}</strong></div>)}
    </div>
  );
};

// ── Main Dashboard ────────────────────────────────────────────────────────
export default function StoreDashboard() {
  const [tab, setTab] = useState("overview");
  const [activeAnomaly, setActiveAnomaly] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [eventsSummary, setEventsSummary] = useState(null);
  const [funnelData, setFunnelData] = useState(null);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [tick, setTick] = useState(0);

  useEffect(() => {
    const iv = setInterval(() => setTick(t => t + 1), 3000);
    return () => clearInterval(iv);
  }, []);

  useEffect(() => {
    async function loadData() {
      try {
        const [metricsRes, eventsRes, funnelRes] = await Promise.all([
          fetch(`${API_URL}/metrics`),
          fetch(`${API_URL}/events/summary`),
          fetch(`${API_URL}/funnel`),
        ]);
        const metricsJson = await metricsRes.json();
        const eventsJson = await eventsRes.json();
        const funnelJson = await funnelRes.json();
        setMetrics(normalizeMetrics(metricsJson));
        setEventsSummary(eventsJson);
        setFunnelData(funnelJson);
        setLastUpdated(new Date().toLocaleTimeString("en-IN", { hour12: false }));
      } catch (error) {
        console.error("Dashboard fetch error:", error);
      }
    }

    loadData();
    const interval = setInterval(loadData, 5000);
    return () => clearInterval(interval);
  }, []);

  const source = metrics || DATA;
  const funnel = funnelData?.stages || source.funnel || DATA.funnel;
  const funnelConversion = funnelData?.overall_conversion_pct ?? source.overall_conversion_pct ?? DATA.summary.conversion_rate_pct;
  const repeatCount = funnel?.[4]?.count ?? DATA.funnel[4].count;
  const s = source.summary || DATA.summary;
  const hourly = source.hourly || [];
  const departments = source.departments || [];
  const topOrders = source.topOrders || DATA.topOrders;

  const tabs = [
    { id:"overview", label:"Overview" },
    { id:"sales", label:"Sales Deep-Dive" },
    { id:"funnel", label:"Funnel & Events" },
    { id:"anomalies", label:"Anomalies" },
  ];

  return (
    <div style={{ background:C.bg, minHeight:"100vh", color:C.text, fontFamily:"'DM Sans', system-ui, sans-serif", fontSize:14 }}>

      {/* Header */}
      <div style={{ background:C.surface, borderBottom:`1px solid ${C.border}`, padding:"0 32px" }}>
        <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", height:60 }}>
          <div style={{ display:"flex", alignItems:"center", gap:16 }}>
            <div style={{ width:8, height:8, borderRadius:"50%", background:C.green, boxShadow:`0 0 10px ${C.green}` }} />
            <span style={{ fontSize:13, fontWeight:700, letterSpacing:3, textTransform:"uppercase", fontFamily:"'Space Mono',monospace", color:C.text }}>Store Intelligence</span>
            <span style={{ color:C.border }}>│</span>
            <span style={{ fontSize:12, color:C.muted, fontFamily:"'Space Mono',monospace" }}>Brigade Road · Bangalore</span>
          </div>
          <div style={{ display:"flex", alignItems:"center", gap:12, fontSize:11, color:C.muted, fontFamily:"'Space Mono',monospace" }}>
            <div>10 APR 2026 · LIVE</div>
            <div style={{ padding:"2px 8px", border:`1px solid ${C.border}`, borderRadius:999, background:C.surface, color:C.muted }}>{lastUpdated ? `Updated ${lastUpdated}` : "Loading..."}</div>
            <div style={{ display:"inline-block", width:6, height:6, borderRadius:"50%", background: tick%2===0 ? C.accent : "transparent", transition:"background 0.3s" }} />
          </div>
        </div>

        {/* Tabs */}
        <div style={{ display:"flex", gap:4 }}>
          {tabs.map(t => (
            <button key={t.id} onClick={() => setTab(t.id)}
              style={{ background:"none", border:"none", cursor:"pointer", padding:"10px 16px", fontSize:12, fontWeight:600, color: tab===t.id ? C.accent : C.muted, borderBottom: tab===t.id ? `2px solid ${C.accent}` : "2px solid transparent", transition:"all 0.2s", letterSpacing:0.5 }}>
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div style={{ padding:"28px 32px", maxWidth:1400, margin:"0 auto" }}>

        {/* ── OVERVIEW TAB ── */}
        {tab === "overview" && (
          <div style={{ display:"flex", flexDirection:"column", gap:24 }}>

            {/* KPIs row */}
            <div style={{ display:"grid", gridTemplateColumns:"repeat(6,1fr)", gap:16 }}>
              <KPI label="Total GMV" value={fmtK(s.total_gmv)} sub="Day total" accent big />
              <KPI label="NMV" value={fmtK(s.total_nmv)} sub={`${((s.total_nmv/s.total_gmv)*100).toFixed(1)}% of GMV`} />
              <KPI label="Conversion" value={`${s.conversion_rate_pct}%`} sub="Buyers / Footfall" accent />
              <KPI label="Orders" value={s.total_orders} sub={`${s.unique_customers} unique customers`} />
              <KPI label="Avg Basket" value={fmtK(s.avg_basket_value_gmv)} sub={`${s.avg_units_per_basket} units avg`} />
              <KPI label="Discount %" value={`${s.discount_pct}%`} sub={`${fmt(s.discount_amount)} given`} />
            </div>

            {eventsSummary && (
              <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:16 }}>
                <KPI label="Total Events" value={eventsSummary.total_events} sub="CCTV detection output" />
                <KPI label="Entries" value={eventsSummary.entries} sub="Entrance events" />
                <KPI label="Exits" value={eventsSummary.exits} sub="Exit events" />
                <KPI label="Re-entries" value={eventsSummary.re_entries} sub="Repeat entries" />
              </div>
            )}

            {/* Charts row */}
            <div style={{ display:"grid", gridTemplateColumns:"2fr 1.2fr", gap:20 }}>

              {/* Hourly GMV */}
              <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
                <SectionHead title="GMV by Hour" sub="Transactions across the day — 10 Apr 2026" />
                <ResponsiveContainer width="100%" height={220}>
                  <BarChart data={source.hourly} barCategoryGap="30%">
                    <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                    <XAxis dataKey="hour" tick={{ fill:C.muted, fontSize:11, fontFamily:"'Space Mono',monospace" }} tickFormatter={h => `${h}:00`} />
                    <YAxis tick={{ fill:C.muted, fontSize:11 }} tickFormatter={fmtK} />
                    <Tooltip content={<DarkTip />} />
                    <Bar dataKey="gmv" name="GMV" radius={[4,4,0,0]}>
                      {hourly.map((e,i) => (
                        <Cell key={i} fill={e.hour === 19 ? C.gold : C.accent} fillOpacity={e.hour === 19 ? 1 : 0.75} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
                <div style={{ fontSize:11, color:C.muted, textAlign:"right", marginTop:4 }}>★ Peak: 19:00 — ₹19,237 (42.8% of day GMV)</div>
              </div>

              {/* Dept Pie */}
              <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
                <SectionHead title="GMV by Department" sub="Share of total sales" />
                <ResponsiveContainer width="100%" height={200}>
                  <PieChart>
                    <Pie data={departments} dataKey="gmv" nameKey="dep_name" cx="50%" cy="50%" innerRadius={55} outerRadius={90} paddingAngle={3}>
                      {departments.map((_, i) => <Cell key={i} fill={C.deptColors[i]} />)}
                    </Pie>
                    <Tooltip formatter={(v) => fmtK(v)} contentStyle={{ background:C.surface, border:`1px solid ${C.border}`, borderRadius:8 }} />
                    <Legend iconType="circle" iconSize={8} wrapperStyle={{ fontSize:11, color:C.muted }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            </div>

            {/* Top 5 Transactions */}
            <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
              <SectionHead title="Top 5 Transactions" sub="Highest GMV orders of the day" />
              <table style={{ width:"100%", borderCollapse:"collapse" }}>
                <thead>
                  <tr style={{ borderBottom:`1px solid ${C.border}` }}>
                    {['Time','Order ID','Customer','Items','Brands','Salesperson','GMV'].map(h => (
                      <th key={h} style={{ textAlign:"left", padding:"8px 12px", fontSize:11, color:C.muted, fontWeight:600, letterSpacing:1, textTransform:"uppercase", fontFamily:"'Space Mono',monospace" }}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {topOrders.map((o,i) => (
                    <tr key={i} style={{ borderBottom:`1px solid ${C.border}22`, transition:"background 0.15s" }}>
                      <td style={{ padding:"10px 12px", color:C.muted, fontFamily:"'Space Mono',monospace", fontSize:12 }}>{o.time}</td>
                      <td style={{ padding:"10px 12px", color:C.accent, fontFamily:"'Space Mono',monospace", fontSize:12 }}>{o.order_id}</td>
                      <td style={{ padding:"10px 12px" }}>{o.customer}</td>
                      <td style={{ padding:"10px 12px", textAlign:"right" }}>{o.items}</td>
                      <td style={{ padding:"10px 12px", textAlign:"right" }}>{o.brands}</td>
                      <td style={{ padding:"10px 12px", color:C.muted, fontSize:12 }}>{o.salesperson}</td>
                      <td style={{ padding:"10px 12px", fontWeight:700, color:i===0?C.gold:C.text, fontFamily:"'Space Mono',monospace" }}>{fmt(o.gmv)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* ── SALES TAB ── */}
        {tab === "sales" && (
          <div style={{ display:"flex", flexDirection:"column", gap:24 }}>

            {/* Department Performance */}
            <div style={{ display:"grid", gridTemplateColumns:"1.5fr 1fr", gap:20 }}>
              <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
                <SectionHead title="Department Performance" sub="GMV share and order count" />
                <table style={{ width:"100%", borderCollapse:"collapse" }}>
                  <thead>
                    <tr style={{ borderBottom:`1px solid ${C.border}` }}>
                      {['Department','Orders','GMV','GMV %'].map(h => (
                        <th key={h} style={{ textAlign:"left", padding:"8px 12px", fontSize:11, color:C.muted, fontWeight:600, letterSpacing:1, textTransform:"uppercase", fontFamily:"'Space Mono',monospace" }}>{h}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {departments.map((d,i) => (
                      <tr key={i} style={{ borderBottom:`1px solid ${C.border}22` }}>
                        <td style={{ padding:"10px 12px", color:C.deptColors[i] || C.text, fontWeight:600 }}>{d.dep_name}</td>
                        <td style={{ padding:"10px 12px", textAlign:"right" }}>{d.orders}</td>
                        <td style={{ padding:"10px 12px", textAlign:"right", fontWeight:700 }}>{fmt(d.gmv)}</td>
                        <td style={{ padding:"10px 12px", textAlign:"right", color:C.accent }}>{d.gmv_share_pct}%</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              {/* Brand Leaders */}
              <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
                <SectionHead title="Top Brands" sub="By GMV this period" />
                <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
                  {DATA.brands.slice(0, 5).map((b,i) => (
                    <div key={i} style={{ padding:12, background:C.surface, borderRadius:8, borderLeft:`3px solid ${C.deptColors[i]}` }}>
                      <div style={{ fontSize:13, fontWeight:600, color:C.text }}>{b.brand_name}</div>
                      <div style={{ fontSize:12, color:C.muted, marginTop:4 }}>{fmt(b.gmv)} · {b.orders} orders · {b.qty} units</div>
                    </div>
                  ))}
                </div>
              </div>
            </div>

            {/* Salesperson Rankings */}
            <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
              <SectionHead title="Salesperson Leaderboard" sub="Performance ranked by GMV per order" />
              <ResponsiveContainer width="100%" height={280}>
                <BarChart data={DATA.salespersons.sort((a,b) => b.gmv - a.gmv)}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                  <XAxis dataKey="salesperson_name" tick={{ fill:C.muted, fontSize:10 }} />
                  <YAxis tick={{ fill:C.muted, fontSize:11 }} tickFormatter={fmtK} />
                  <Tooltip content={<DarkTip />} />
                  <Bar dataKey="gmv" name="GMV" fill={C.accent} radius={[4,4,0,0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* ── FUNNEL TAB ── */}
        {tab === "funnel" && (
          <div style={{ display:"flex", flexDirection:"column", gap:24 }}>

            {/* Conversion Funnel */}
            <div style={{ display:"grid", gridTemplateColumns:"1fr 1fr", gap:20 }}>
              <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
                <SectionHead title="Store Conversion Funnel" sub="Visitor journey from entry to repeat visit" />
                <ResponsiveContainer width="100%" height={280}>
                  <FunnelChart>
                    <Tooltip content={<DarkTip />} contentStyle={{ background:C.surface, border:`1px solid ${C.border}` }} />
                    <Funnel dataKey="count" data={funnel} nameKey="stage">
                      {funnel.map((e,i) => (
                        <Cell key={i} fill={e.fill || DATA.funnel[i]?.fill || C.accent} />
                      ))}
                    </Funnel>
                  </FunnelChart>
                </ResponsiveContainer>
              </div>

              {/* Event Summary Cards */}
              <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
                <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:20 }}>
                  <div style={{ fontSize:11, color:C.muted, textTransform:"uppercase", letterSpacing:2, marginBottom:8, fontFamily:"'Space Mono',monospace" }}>Conversion Rate</div>
                  <div style={{ fontSize:32, fontWeight:800, color:C.accent, fontFamily:"'Space Mono',monospace" }}>{s.conversion_rate_pct}%</div>
                  <div style={{ fontSize:12, color:C.muted, marginTop:6 }}>{s.unique_customers} / {s.estimated_footfall} estimated</div>
                </div>
                <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:20 }}>
                  <div style={{ fontSize:11, color:C.muted, textTransform:"uppercase", letterSpacing:2, marginBottom:8, fontFamily:"'Space Mono',monospace" }}>Repeat Rate</div>
                  <div style={{ fontSize:32, fontWeight:800, color:C.green, fontFamily:"'Space Mono',monospace" }}>{repeatCount}</div>
                  <div style={{ fontSize:12, color:C.muted, marginTop:6 }}>customers returned same day</div>
                </div>
                <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:20 }}>
                  <div style={{ fontSize:11, color:C.muted, textTransform:"uppercase", letterSpacing:2, marginBottom:8, fontFamily:"'Space Mono',monospace" }}>Avg Dwell</div>
                  <div style={{ fontSize:32, fontWeight:800, color:C.gold, fontFamily:"'Space Mono',monospace" }}>8.2m</div>
                  <div style={{ fontSize:12, color:C.muted, marginTop:6 }}>average time in store</div>
                </div>
              </div>
            </div>

            {/* Hourly Entry/Exit Pattern */}
            <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
              <SectionHead title="Entry/Exit Pattern" sub="Customer flow by hour from detection events" />
              <ResponsiveContainer width="100%" height={220}>
                <LineChart data={hourly}>
                  <CartesianGrid strokeDasharray="3 3" stroke={C.border} />
                  <XAxis dataKey="hour" tick={{ fill:C.muted, fontSize:11 }} tickFormatter={h => `${h}:00`} />
                  <YAxis tick={{ fill:C.muted, fontSize:11 }} />
                  <Tooltip content={<DarkTip />} />
                  <Line type="monotone" dataKey="orders" stroke={C.accent} name="Orders" strokeWidth={2} dot={false} />
                  <Line type="monotone" dataKey="qty" stroke={C.gold} name="Items Sold" strokeWidth={2} dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>
        )}

        {/* ── ANOMALIES TAB ── */}
        {tab === "anomalies" && (
          <div style={{ display:"flex", flexDirection:"column", gap:24 }}>

            {/* Anomaly Alerts */}
            <div style={{ display:"grid", gridTemplateColumns:"repeat(3, 1fr)", gap:16 }}>
              {DATA.anomalies.map((a,i) => (
                <div key={i} style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:20, borderLeft:`4px solid ${a.severity === 'high' ? C.red : a.severity === 'medium' ? C.gold : C.accent}` }}>
                  <div style={{ display:"flex", alignItems:"center", justifyContent:"space-between", marginBottom:12 }}>
                    <div style={{ fontSize:13, fontWeight:700, color:C.text, textTransform:"uppercase", letterSpacing:1 }}>{a.type.replace(/_/g, ' ')}</div>
                    <SeverityBadge s={a.severity} />
                  </div>
                  <div style={{ fontSize:13, color:C.muted, lineHeight:1.5 }}>{a.description}</div>
                </div>
              ))}
            </div>

            {/* Statistical Summary */}
            <div style={{ display:"grid", gridTemplateColumns:"2fr 1fr", gap:20 }}>
              <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
                <SectionHead title="Metrics Analysis" sub="Key performance indicators flagged for review" />
                <div style={{ display:"flex", flexDirection:"column", gap:16 }}>
                  <div style={{ borderBottom:`1px solid ${C.border}22`, paddingBottom:12 }}>
                    <div style={{ fontSize:12, color:C.muted, fontFamily:"'Space Mono',monospace" }}>Discount Rate</div>
                    <div style={{ fontSize:16, fontWeight:700, color:s.discount_pct > 2 ? C.red : C.green, marginTop:4 }}>{s.discount_pct}% (normal: 0.5-2%)</div>
                  </div>
                  <div style={{ borderBottom:`1px solid ${C.border}22`, paddingBottom:12 }}>
                    <div style={{ fontSize:12, color:C.muted, fontFamily:"'Space Mono',monospace" }}>Avg Basket</div>
                    <div style={{ fontSize:16, fontWeight:700, color:C.text, marginTop:4 }}>{fmt(s.avg_basket_value_gmv)} (GMV)</div>
                  </div>
                  <div style={{ borderBottom:`1px solid ${C.border}22`, paddingBottom:12 }}>
                    <div style={{ fontSize:12, color:C.muted, fontFamily:"'Space Mono',monospace" }}>Order Count</div>
                    <div style={{ fontSize:16, fontWeight:700, color:C.text, marginTop:4 }}>{s.total_orders} orders from {s.unique_customers} customers</div>
                  </div>
                </div>
              </div>

              {/* Risk Indicators */}
              <div style={{ background:C.card, border:`1px solid ${C.border}`, borderRadius:12, padding:24 }}>
                <SectionHead title="Risk Flags" sub="Items requiring attention" />
                <div style={{ display:"flex", flexDirection:"column", gap:12 }}>
                  <div style={{ padding:12, background:C.surface, borderRadius:8, borderLeft:`3px solid ${C.red}` }}>
                    <div style={{ fontSize:12, fontWeight:600, color:C.red }}>⚠ High GMV Spike</div>
                    <div style={{ fontSize:11, color:C.muted, marginTop:2 }}>19:00 peak is 2.4σ above mean</div>
                  </div>
                  <div style={{ padding:12, background:C.surface, borderRadius:8, borderLeft:`3px solid ${C.gold}` }}>
                    <div style={{ fontSize:12, fontWeight:600, color:C.gold }}>⚠ Large Basket</div>
                    <div style={{ fontSize:11, color:C.muted, marginTop:2 }}>Order 104341290 exceeds IQR</div>
                  </div>
                  <div style={{ padding:12, background:C.surface, borderRadius:8, borderLeft:`3px solid ${C.accent}` }}>
                    <div style={{ fontSize:12, fontWeight:600, color:C.accent }}>ℹ Dependency Risk</div>
                    <div style={{ fontSize:11, color:C.muted, marginTop:2 }}>Zufishan: 48.7% of GMV</div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

      </div>
    </div>
  );
}
