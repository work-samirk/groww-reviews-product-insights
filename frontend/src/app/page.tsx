"use client";

import React, { useState, useEffect, useMemo } from "react";

// Types matching backend payload
interface Theme {
  theme_name: string;
  severity: string;
  review_count: number;
  summary: string;
  quotes: string[];
  action_ideas: string[];
  cluster_id: number;
}

interface Review {
  id: string;
  platform: string;
  author: string;
  date: string;
  rating: number;
  review_text: string;
  cluster_id: number;
}

interface Report {
  product: string;
  iso_week: string; // contains the month code in this version, e.g. "2026-06"
  period_start: string;
  period_end: string;
  themes: Theme[];
}

interface Week {
  week_label: string;
  start_date: string;
  end_date: string;
}

interface MonthData {
  month_code: string;
  month_label: string;
  weeks: Week[];
}

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8006/api/v1/groww-product-insights";

export default function Dashboard() {
  // Navigation & Data States
  const [periods, setPeriods] = useState<MonthData[]>([]);
  const [selectedMonthCode, setSelectedMonthCode] = useState<string>("");
  const [selectedWeek, setSelectedWeek] = useState<Week | null>(null);
  const [report, setReport] = useState<Report | null>(null);
  const [reviews, setReviews] = useState<Review[]>([]);
  
  // UI States
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedReviewForModal, setSelectedReviewForModal] = useState<Review | null>(null);
  const [monthDropdownOpen, setMonthDropdownOpen] = useState<boolean>(false);

  // Derived active month object
  const selectedMonthData = useMemo(() => {
    return periods.find((p) => p.month_code === selectedMonthCode) || null;
  }, [periods, selectedMonthCode]);

  // Handler for month changes
  const handleMonthChange = (monthCode: string) => {
    setSelectedMonthCode(monthCode);
    const mData = periods.find((p) => p.month_code === monthCode);
    if (mData && mData.weeks.length > 0) {
      setSelectedWeek(mData.weeks[0]);
    } else {
      setSelectedWeek(null);
    }
  };

  // Close month dropdown when clicking outside
  useEffect(() => {
    if (!monthDropdownOpen) return;
    const handleOutsideClick = () => {
      setMonthDropdownOpen(false);
    };
    document.addEventListener("click", handleOutsideClick);
    return () => document.removeEventListener("click", handleOutsideClick);
  }, [monthDropdownOpen]);
  
  // Filters & Search
  const [searchQuery, setSearchQuery] = useState<string>("");
  const [selectedClusterId, setSelectedClusterId] = useState<number | null>(null); // null means All Themes
  const [selectedPlatform, setSelectedPlatform] = useState<string>("All"); // All, appstore, playstore
  
  // Pagination
  const [currentPage, setCurrentPage] = useState<number>(1);
  const reviewsPerPage = 10;

  // Format month codes like "2026-06" into "June 2026"
  const formatMonthLabel = (monthId: string) => {
    if (!monthId) return "";
    const parts = monthId.split("-");
    if (parts.length !== 2) return monthId;
    const [year, monthStr] = parts;
    const monthNames = [
      "January", "February", "March", "April", "May", "June",
      "July", "August", "September", "October", "November", "December"
    ];
    const idx = parseInt(monthStr, 10) - 1;
    if (idx >= 0 && idx < 12) {
      return `${monthNames[idx]} ${year}`;
    }
    return monthId;
  };

  // Fetch available periods on mount
  useEffect(() => {
    async function loadPeriods() {
      try {
        setLoading(true);
        const res = await fetch(`${API_BASE_URL}/available-periods`);
        if (!res.ok) throw new Error("Failed to load periods list from API");
        const data = await res.json();
        setPeriods(data);
        if (data.length > 0) {
          const firstMonth = data[0];
          setSelectedMonthCode(firstMonth.month_code);
          if (firstMonth.weeks && firstMonth.weeks.length > 0) {
            setSelectedWeek(firstMonth.weeks[0]);
          } else {
            setLoading(false);
          }
        } else {
          setLoading(false);
        }
      } catch (err: any) {
        console.error(err);
        setError("Unable to connect to the backend server. Please verify it is running on port 8006.");
        setLoading(false);
      }
    }
    loadPeriods();
  }, []);

  // Fetch report & reviews when selected week changes
  useEffect(() => {
    if (!selectedWeek) return;
    const { start_date, end_date, week_label } = selectedWeek;

    async function loadWeekData() {
      try {
        setLoading(true);
        setError(null);
        
        // Fetch report and reviews in parallel
        const [reportRes, reviewsRes] = await Promise.all([
          fetch(`${API_BASE_URL}/insights-report?start_date=${start_date}&end_date=${end_date}`),
          fetch(`${API_BASE_URL}/customer-reviews?start_date=${start_date}&end_date=${end_date}`)
        ]);

        if (!reportRes.ok) throw new Error(`Failed to load report for ${week_label}`);
        if (!reviewsRes.ok) throw new Error(`Failed to load reviews for ${week_label}`);

        const reportData = await reportRes.json();
        const reviewsData = await reviewsRes.json();

        setReport(reportData);
        setReviews(reviewsData);
        
        // Reset filters for the new week
        setSelectedClusterId(null);
        setSearchQuery("");
        setSelectedPlatform("All");
        setCurrentPage(1);
      } catch (err: any) {
        console.error(err);
        setError(`Failed to retrieve data for week ${week_label}. Check API logs.`);
      } finally {
        setLoading(false);
      }
    }

    loadWeekData();
  }, [selectedWeek]);

  // Derived KPI Stats
  const kpis = useMemo(() => {
    if (reviews.length === 0) {
      return { total: 0, appStoreRating: "0.0", playStoreRating: "0.0", topTheme: "N/A" };
    }
    
    const appStoreReviews = reviews.filter(r => r.platform === "appstore");
    const playStoreReviews = reviews.filter(r => r.platform === "playstore");
    
    const avgAppStore = appStoreReviews.length > 0
      ? (appStoreReviews.reduce((sum, r) => sum + r.rating, 0) / appStoreReviews.length).toFixed(1)
      : "0.0";
      
    const avgPlayStore = playStoreReviews.length > 0
      ? (playStoreReviews.reduce((sum, r) => sum + r.rating, 0) / playStoreReviews.length).toFixed(1)
      : "0.0";

    const topThemeName = report && report.themes.length > 0
      ? report.themes.reduce((prev, current) => (prev.review_count > current.review_count) ? prev : current).theme_name
      : "N/A";

    return {
      total: reviews.length,
      appStoreRating: avgAppStore,
      playStoreRating: avgPlayStore,
      topTheme: topThemeName
    };
  }, [reviews, report]);

  // Filtered Reviews list
  const filteredReviews = useMemo(() => {
    return reviews.filter(review => {
      // 1. Filter by search query
      const matchesSearch = review.review_text.toLowerCase().includes(searchQuery.toLowerCase()) ||
                            review.author.toLowerCase().includes(searchQuery.toLowerCase());
                            
      // 2. Filter by Theme / Cluster ID
      const matchesCluster = selectedClusterId === null || review.cluster_id === selectedClusterId;
      
      // 3. Filter by Platform
      const matchesPlatform = selectedPlatform === "All" || review.platform === selectedPlatform;
      
      return matchesSearch && matchesCluster && matchesPlatform;
    });
  }, [reviews, searchQuery, selectedClusterId, selectedPlatform]);

  // Paginated reviews list
  const paginatedReviews = useMemo(() => {
    const startIndex = (currentPage - 1) * reviewsPerPage;
    return filteredReviews.slice(startIndex, startIndex + reviewsPerPage);
  }, [filteredReviews, currentPage]);

  const totalPages = Math.max(1, Math.ceil(filteredReviews.length / reviewsPerPage));

  // Reset pagination when filters change
  useEffect(() => {
    setCurrentPage(1);
  }, [searchQuery, selectedClusterId, selectedPlatform]);

  const handleExportCSV = () => {
    if (filteredReviews.length === 0) return;
    const headers = ["ID", "Date", "Platform", "Rating", "Review Text", "Cluster ID"];
    const rows = filteredReviews.map(r => [
      r.id,
      r.date,
      r.platform,
      r.rating,
      `"${r.review_text.replace(/"/g, '""')}"`,
      r.cluster_id
    ]);
    
    const csvContent = "data:text/csv;charset=utf-8," 
      + [headers.join(","), ...rows.map(e => e.join(","))].join("\n");
      
    const encodedUri = encodeURI(csvContent);
    const link = document.createElement("a");
    link.setAttribute("href", encodedUri);
    const filenameLabel = selectedWeek 
      ? selectedWeek.week_label.replace(/\s+/g, "_").replace(/[()]/g, "") 
      : selectedMonthCode;
    link.setAttribute("download", `Groww_Reviews_${filenameLabel}.csv`);
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  const getThemeNameByClusterId = (cid: number) => {
    if (cid === -1) return "Noise / Uncategorized";
    const foundTheme = report?.themes.find(t => t.cluster_id === cid);
    return foundTheme ? foundTheme.theme_name : "Other Issues";
  };

  const getThemeIcon = (themeName: string) => {
    const name = themeName.toLowerCase();
    if (name.includes("performance") || name.includes("lag") || name.includes("crash")) return "speed";
    if (name.includes("support") || name.includes("ticket") || name.includes("customer")) return "contact_support";
    if (name.includes("ux") || name.includes("ui") || name.includes("navigation") || name.includes("reporting")) return "design_services";
    return "payments";
  };

  const getThemeColorClass = (themeName: string) => {
    const name = themeName.toLowerCase();
    if (name.includes("performance") || name.includes("lag") || name.includes("crash")) return "bg-error/10 text-error";
    if (name.includes("support") || name.includes("ticket") || name.includes("customer")) return "bg-primary/10 text-primary";
    return "bg-tertiary-container/30 text-on-tertiary-container";
  };

  return (
    <div className="min-h-screen bg-background font-body-md text-on-surface custom-scrollbar flex flex-col md:flex-row w-full max-w-full overflow-x-hidden">
      {/* ========================================== */}
      {/* DESKTOP SIDEBAR (md and up) */}
      {/* ========================================== */}
      <aside className="h-screen w-64 fixed left-0 top-0 hidden md:flex flex-col py-stack-lg bg-surface shadow-sm z-50">
        <div className="px-6 mb-10">
          <h1 className="text-headline-md font-bold text-primary font-sans">Groww Insights</h1>
          <p className="text-body-sm text-secondary">Product Analytics</p>
        </div>
        <nav className="flex-grow space-y-2 px-2">
          <a className="flex items-center gap-3 px-4 py-3 text-primary font-bold border-r-4 border-primary bg-primary-container/10 transition-all" href="#">
            <span className="material-symbols-outlined">dashboard</span>
            <span>Dashboard</span>
          </a>
        </nav>
        
        {/* Month Selector in Sidebar */}
        <div className="px-4 mt-auto">
          <div className="p-4 bg-surface-container-low rounded-2xl border border-outline-variant/30 relative">
            <p className="text-[10px] tracking-wider text-on-surface-variant font-bold mb-2">CURRENT PERIOD</p>
            <div className="relative flex items-center justify-between">
              <button 
                onClick={(e) => {
                  e.stopPropagation();
                  setMonthDropdownOpen(!monthDropdownOpen);
                }}
                className="w-full flex items-center justify-between bg-transparent border-none p-0 text-body-sm font-semibold text-primary focus:outline-none cursor-pointer font-sans"
              >
                <span>{selectedMonthData ? selectedMonthData.month_label : "Select Month"}</span>
                <span className="material-symbols-outlined text-secondary text-sm">unfold_more</span>
              </button>

              {monthDropdownOpen && (
                <div className="absolute left-0 bottom-full mb-3 w-full bg-surface-container-lowest border border-outline-variant/30 rounded-2xl shadow-lg py-2 z-50 animate-in fade-in slide-in-from-bottom-2 duration-200">
                  {periods.map((p) => (
                    <button
                      key={p.month_code}
                      onClick={() => {
                        handleMonthChange(p.month_code);
                        setMonthDropdownOpen(false);
                      }}
                      className={`w-full text-left px-4 py-2.5 text-body-sm font-semibold hover:bg-primary/5 transition-colors cursor-pointer block ${
                        selectedMonthCode === p.month_code ? "text-primary bg-primary/5" : "text-secondary"
                      }`}
                    >
                      {p.month_label}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
          
          <button className="w-full mt-4 py-3 px-4 bg-primary text-on-primary rounded-xl font-bold flex items-center justify-center gap-2 hover:opacity-90 transition-all cursor-pointer">
            <span className="material-symbols-outlined">analytics</span>
            Weekly Insights
          </button>
        </div>
      </aside>

      {/* ========================================== */}
      {/* MAIN CANVAS */}
      {/* ========================================== */}
      <main className="flex-grow md:ml-64 min-h-screen pb-24 md:pb-8 flex flex-col max-w-full overflow-x-hidden">
        
        {/* ========================================== */}
        {/* DESKTOP HEADER */}
        {/* ========================================== */}
        <header className="sticky top-0 z-40 bg-surface-container-low border-b border-outline-variant hidden md:flex justify-between items-center px-4 md:px-margin-desktop py-4 glass-effect">
          <div className="flex flex-col">
            <h2 className="font-semibold text-headline-md text-primary font-sans">Groww Product Insights Dashboard</h2>
            <div className="flex items-center gap-2 text-body-sm text-on-surface-variant">
              <span className="material-symbols-outlined text-sm">calendar_today</span>
              <span>{report ? `${report.period_start} to ${report.period_end}` : "Loading range..."}</span>
              <span className="mx-1">•</span>
              <a className="text-primary font-semibold hover:underline flex items-center gap-1 font-sans" href="https://docs.google.com/document/d/1l3McaCJvAUz3ZX3J58T2pkjJ6giyPG6PoImTiGm2Eu0/edit" target="_blank" rel="noreferrer">
                View Google Doc <span className="material-symbols-outlined text-sm">open_in_new</span>
              </a>
            </div>
          </div>
          
          <div className="flex items-center gap-stack-md">
            <div className="relative">
              <span className="absolute inset-y-0 left-3 flex items-center text-on-surface-variant">
                <span className="material-symbols-outlined text-sm">search</span>
              </span>
              <input 
                type="text" 
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="pl-10 pr-4 py-2 bg-surface-container-highest/50 border-none rounded-full text-body-sm w-64 focus:ring-2 focus:ring-primary/20 transition-all focus:outline-none font-sans"
                placeholder="Search reviews..."
              />
            </div>
            <button className="p-2 text-on-surface-variant hover:text-primary transition-colors relative">
              <span className="material-symbols-outlined">notifications</span>
              <span className="absolute top-2 right-2 w-2 h-2 bg-error rounded-full"></span>
            </button>
            <button 
              onClick={handleExportCSV}
              className="px-5 py-2 bg-primary-container text-on-primary-container rounded-full font-bold text-body-sm flex items-center gap-2 transition-transform active:scale-95 hover:opacity-90 cursor-pointer"
            >
              <span className="material-symbols-outlined text-sm">download</span>
              Export CSV
            </button>
          </div>
        </header>

        {/* ========================================== */}
        {/* MOBILE STITCH HEADER (below md) */}
        {/* ========================================== */}
        <header className="sticky top-0 z-40 bg-surface-container-low border-b border-outline-variant px-margin-mobile py-4 flex md:hidden items-center justify-between glass-effect">
          <div className="flex flex-col">
            <h1 className="font-bold text-headline-md text-primary leading-tight font-sans">Groww Weekly</h1>
            <p className="text-[10px] tracking-wider text-on-surface-variant font-bold uppercase">
              Product Sentiment Analysis
            </p>
          </div>
          <div className="flex gap-2">
            <a 
              className="w-10 h-10 flex items-center justify-center rounded-full bg-surface-container hover:bg-secondary-container transition-colors active:scale-90"
              href="https://docs.google.com/document/d/1l3McaCJvAUz3ZX3J58T2pkjJ6giyPG6PoImTiGm2Eu0/edit"
              target="_blank"
              rel="noreferrer"
            >
              <span className="material-symbols-outlined text-primary">description</span>
            </a>
            <button 
              onClick={handleExportCSV}
              className="w-10 h-10 flex items-center justify-center rounded-full bg-primary text-white hover:bg-primary-container transition-colors active:scale-90 cursor-pointer"
            >
              <span className="material-symbols-outlined">download</span>
            </button>
          </div>
        </header>

        {/* ========================================== */}
        {/* MONTHS TABS SECTION (DESKTOP & MOBILE) */}
        {/* ========================================== */}
        <section className="bg-surface-container-low border-b border-outline-variant/30 px-4 md:px-margin-desktop py-3 flex items-center overflow-x-auto no-scrollbar scroll-smooth w-full">
          <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant mr-4 hidden md:block">Select Month:</span>
          <div className="flex gap-2 min-w-max">
            {periods.map((p) => {
              const isSelected = selectedMonthCode === p.month_code;
              return (
                <button
                  key={p.month_code}
                  onClick={() => handleMonthChange(p.month_code)}
                  className={`px-4 py-2 text-xs md:text-body-sm font-bold rounded-full transition-all cursor-pointer whitespace-nowrap ${
                    isSelected
                      ? "bg-primary text-on-primary shadow-sm"
                      : "bg-surface-container-lowest text-secondary border border-outline-variant/30 hover:border-primary/55"
                  }`}
                >
                  {p.month_label}
                </button>
              );
            })}
          </div>
        </section>

        {/* ========================================== */}
        {/* WEEKS TABS SECTION (DESKTOP & MOBILE) */}
        {/* ========================================== */}
        {selectedMonthData && (
          <section className="bg-surface-container-low/75 border-b border-outline-variant/30 px-4 md:px-margin-desktop py-2.5 flex items-center overflow-x-auto no-scrollbar scroll-smooth w-full">
            <span className="text-xs font-bold uppercase tracking-wider text-on-surface-variant mr-4 hidden md:block">Select Week:</span>
            <div className="flex gap-2 min-w-max">
              {selectedMonthData.weeks.map((w) => {
                const isSelected = selectedWeek?.week_label === w.week_label;
                return (
                  <button
                    key={w.week_label}
                    onClick={() => setSelectedWeek(w)}
                    className={`px-3.5 py-1.5 text-xs font-bold rounded-full transition-all cursor-pointer whitespace-nowrap ${
                      isSelected
                        ? "bg-primary-container text-on-primary-container border border-primary/30"
                        : "bg-surface-container-lowest text-secondary border border-outline-variant/20 hover:border-primary/40"
                    }`}
                  >
                    {w.week_label}
                  </button>
                );
              })}
            </div>
          </section>
        )}

        {/* ========================================== */}
        {/* DATA CONTAINER */}
        {/* ========================================== */}
        <div className="flex-1 px-4 md:px-margin-desktop py-6 md:py-stack-lg max-w-container-max mx-auto w-full">
          
          {loading && (
            <div className="flex flex-col items-center justify-center py-20 text-secondary">
              <div className="animate-spin rounded-full h-10 w-10 border-b-2 border-primary mb-4"></div>
              <p>Fetching {selectedWeek ? selectedWeek.week_label : selectedMonthCode} insights...</p>
            </div>
          )}

          {error && (
            <div className="bg-error-container/30 border border-error/20 p-6 rounded-2xl mb-8 flex items-start gap-4">
              <span className="material-symbols-outlined text-error">warning</span>
              <div>
                <h4 className="font-bold text-on-error-container">Configuration Required</h4>
                <p className="text-body-sm text-on-error-container mt-1">{error}</p>
              </div>
            </div>
          )}

          {!loading && !error && (
            <>
              {/* ========================================== */}
              {/* DESKTOP KPI SECTION */}
              {/* ========================================== */}
              <section className="hidden md:grid grid-cols-4 gap-gutter mb-12">
                <div className="bg-surface-container-lowest p-stack-lg rounded-[24px] shadow-sm border border-outline-variant/10 hover:shadow-md transition-all group">
                  <div className="flex justify-between items-start mb-4">
                    <div className="p-3 bg-primary/10 rounded-xl">
                      <span className="material-symbols-outlined text-primary">reviews</span>
                    </div>
                  </div>
                  <p className="text-on-surface-variant text-body-sm font-medium">Reviews Analyzed</p>
                  <h3 className="text-headline-md font-bold text-on-surface mt-1">{kpis.total}</h3>
                </div>

                <div className="bg-surface-container-lowest p-stack-lg rounded-[24px] shadow-sm border border-outline-variant/10 hover:shadow-md transition-all group">
                  <div className="flex justify-between items-start mb-4">
                    <div className="p-3 bg-error-container/10 rounded-xl">
                      <span className="material-symbols-outlined text-error">priority_high</span>
                    </div>
                    <span className="text-error text-xs font-bold px-2 py-1 bg-error/10 rounded-full">Urgent</span>
                  </div>
                  <p className="text-on-surface-variant text-body-sm font-medium">Top Theme</p>
                  <h3 className="text-title-sm font-bold text-on-surface mt-1 truncate" title={kpis.topTheme}>{kpis.topTheme}</h3>
                </div>

                <div className="bg-surface-container-lowest p-stack-lg rounded-[24px] shadow-sm border border-outline-variant/10 hover:shadow-md transition-all group">
                  <div className="flex justify-between items-start mb-4">
                    <div className="p-3 bg-tertiary-container/10 rounded-xl">
                      <span className="material-symbols-outlined text-tertiary">apps</span>
                    </div>
                    <div className="flex items-center gap-1 text-primary">
                      <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                      <span className="text-xs font-bold">{kpis.appStoreRating}</span>
                    </div>
                  </div>
                  <p className="text-on-surface-variant text-body-sm font-medium">App Store Rating</p>
                  <h3 className="text-headline-md font-bold text-on-surface mt-1">{kpis.appStoreRating} <span className="text-body-sm font-normal text-on-surface-variant">/ 5</span></h3>
                </div>

                <div className="bg-surface-container-lowest p-stack-lg rounded-[24px] shadow-sm border border-outline-variant/10 hover:shadow-md transition-all group">
                  <div className="flex justify-between items-start mb-4">
                    <div className="p-3 bg-secondary-container/50 rounded-xl">
                      <span className="material-symbols-outlined text-on-surface-variant">phone_android</span>
                    </div>
                    <div className="flex items-center gap-1 text-primary">
                      <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                      <span className="text-xs font-bold">{kpis.playStoreRating}</span>
                    </div>
                  </div>
                  <p className="text-on-surface-variant text-body-sm font-medium">Play Store Rating</p>
                  <h3 className="text-headline-md font-bold text-on-surface mt-1">{kpis.playStoreRating} <span className="text-body-sm font-normal text-on-surface-variant">/ 5</span></h3>
                </div>
              </section>

              {/* ========================================== */}
              {/* MOBILE KPI SECTION (Stitch Horizontal Scrollable) */}
              {/* ========================================== */}
              <section className="block md:hidden mb-6">
                <h2 className="font-bold text-title-sm mb-3 flex items-center justify-between">
                  Performance Overview
                  <span className="font-bold text-[9px] tracking-wider text-primary bg-primary/10 px-2 py-0.5 rounded-full">LIVE</span>
                </h2>
                <div className="flex overflow-x-auto gap-4 no-scrollbar pb-2 scroll-smooth -mx-4 px-4">
                  {/* Total Reviews Card */}
                  <div className="premium-card flex-shrink-0 w-44 flex flex-col justify-between border-l-4 border-primary">
                    <div>
                      <p className="text-[10px] tracking-wider text-on-surface-variant font-bold">REVIEWS ANALYZED</p>
                      <h3 className="text-headline-md font-bold text-on-surface leading-tight mt-1">{kpis.total}</h3>
                    </div>
                    <div className="flex items-center text-primary mt-2 text-xs">
                      <span className="material-symbols-outlined text-sm">trending_up</span>
                      <span className="font-bold font-sans ml-1">+12% increase</span>
                    </div>
                  </div>

                  {/* Top Theme Card */}
                  <div className="premium-card flex-shrink-0 w-44 flex flex-col justify-between">
                    <div>
                      <p className="text-[10px] tracking-wider text-on-surface-variant font-bold">TOP ISSUE</p>
                      <h3 className="text-body-sm font-bold text-on-surface mt-1 line-clamp-2 leading-snug">{kpis.topTheme}</h3>
                    </div>
                    <div className="flex items-center text-error mt-2 text-xs">
                      <span className="material-symbols-outlined text-sm">priority_high</span>
                      <span className="font-bold ml-1">Urgent Review</span>
                    </div>
                  </div>

                  {/* App Store Card */}
                  <div className="premium-card flex-shrink-0 w-44 flex flex-col justify-between">
                    <div>
                      <p className="text-[10px] tracking-wider text-on-surface-variant font-bold">APP STORE</p>
                      <h3 className="text-headline-md font-bold text-on-surface leading-tight mt-1">{kpis.appStoreRating}</h3>
                    </div>
                    <div className="flex items-center text-primary mt-2 text-xs">
                      <span className="material-symbols-outlined text-sm" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                      <span className="font-bold ml-1">Out of 5.0</span>
                    </div>
                  </div>

                  {/* Play Store Card */}
                  <div className="premium-card flex-shrink-0 w-44 flex flex-col justify-between">
                    <div>
                      <p className="text-[10px] tracking-wider text-on-surface-variant font-bold">PLAY STORE</p>
                      <h3 className="text-headline-md font-bold text-on-surface leading-tight mt-1">{kpis.playStoreRating}</h3>
                    </div>
                    <div className="flex items-center text-error mt-2 text-xs">
                      <span className="material-symbols-outlined text-sm">trending_down</span>
                      <span className="font-bold ml-1">↓ 0.1 decrease</span>
                    </div>
                  </div>
                </div>
              </section>

              {/* ========================================== */}
              {/* MOBILE HERO VISUAL (Stitch Design Style) */}
              {/* ========================================== */}
              <section className="block md:hidden mb-6">
                <div className="relative overflow-hidden premium-card h-40 flex flex-col justify-end bg-gradient-to-tr from-primary/20 via-primary/5 to-white border border-outline-variant/10 shadow-sm">
                  <div className="absolute right-0 top-0 w-32 h-32 bg-primary/10 rounded-full blur-2xl -mr-10 -mt-10"></div>
                  <div className="absolute right-6 top-6 text-primary/20">
                    <span className="material-symbols-outlined text-6xl" style={{ fontVariationSettings: "'wght' 100" }}>analytics</span>
                  </div>
                  <div className="relative z-10">
                    <h2 className="font-bold text-headline-md text-primary leading-snug">{selectedWeek ? selectedWeek.week_label : selectedMonthCode} Pulse</h2>
                    <p className="text-xs text-on-surface-variant mt-1 leading-relaxed">
                      Showing synthesized customer themes, action items, and verification data specific to this period.
                    </p>
                  </div>
                </div>
              </section>

              {/* ========================================== */}
              {/* DESKTOP DISCOVERED THEMES */}
              {/* ========================================== */}
              <section className="hidden md:block mb-12">
                <div className="flex items-center justify-between mb-stack-md">
                  <h4 className="text-title-sm font-bold text-on-surface font-sans">Discovered Themes for {selectedWeek ? selectedWeek.week_label : selectedMonthCode}</h4>
                  {selectedClusterId !== null && (
                    <button 
                      onClick={() => setSelectedClusterId(null)}
                      className="text-primary font-bold text-body-sm flex items-center gap-1 hover:underline cursor-pointer"
                    >
                      Clear Filter <span className="material-symbols-outlined text-sm">close</span>
                    </button>
                  )}
                </div>
                
                <div className="grid grid-cols-3 gap-gutter">
                  {report?.themes.map((theme) => {
                    const isSelected = selectedClusterId === theme.cluster_id;
                    return (
                      <div 
                        key={theme.theme_name} 
                        onClick={() => setSelectedClusterId(isSelected ? null : theme.cluster_id)}
                        className={`p-stack-lg rounded-[24px] shadow-sm border transition-all cursor-pointer flex flex-col group ${
                          isSelected 
                            ? "bg-primary/5 border-primary ring-2 ring-primary/20 scale-102 shadow-md" 
                            : "bg-surface-container-lowest border-outline-variant/10 hover:border-primary/30 hover:shadow-md hover:-translate-y-1"
                        }`}
                      >
                        <div className="flex justify-between items-center mb-4 gap-2">
                          <h5 className="font-bold text-on-surface group-hover:text-primary transition-colors line-clamp-1">{theme.theme_name}</h5>
                          <span className={`px-3 py-1 text-label-caps rounded-full font-bold uppercase text-[10px] flex-shrink-0 ${
                            theme.severity === "HIGH" 
                              ? "bg-error-container text-on-error-container" 
                              : "bg-primary-container text-on-primary-container"
                          }`}>
                            {theme.review_count} Reviews
                          </span>
                        </div>
                        <p className="text-body-sm text-on-surface-variant mb-6 leading-relaxed flex-1">
                          {theme.summary}
                        </p>
                        
                        <div className="bg-primary/5 p-4 rounded-xl border border-primary/10 mt-auto">
                          <div className="flex items-center gap-2 mb-2 text-primary">
                            <span className="material-symbols-outlined text-sm">task_alt</span>
                            <span className="text-[10px] tracking-wider font-bold">ACTION ITEM</span>
                          </div>
                          <p className="text-body-sm font-semibold text-primary leading-snug">
                            {theme.action_ideas[0]}
                          </p>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* ========================================== */}
              {/* MOBILE STRATEGIC THEMES (Stitch Stack) */}
              {/* ========================================== */}
              <section id="strategic-themes" className="block md:hidden mb-8">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-bold text-title-sm">Strategic Themes</h2>
                  {selectedClusterId !== null && (
                    <button 
                      onClick={() => setSelectedClusterId(null)}
                      className="text-primary font-bold text-xs flex items-center gap-0.5 cursor-pointer"
                    >
                      Reset <span className="material-symbols-outlined text-xs">close</span>
                    </button>
                  )}
                </div>
                
                <div className="space-y-4">
                  {report?.themes.map((theme) => {
                    const isSelected = selectedClusterId === theme.cluster_id;
                    const totalVolume = report.themes.reduce((sum, t) => sum + t.review_count, 0);
                    const percentage = totalVolume > 0 ? Math.round((theme.review_count / totalVolume) * 100) : 0;
                    
                    return (
                      <div 
                        key={theme.theme_name}
                        onClick={() => setSelectedClusterId(isSelected ? null : theme.cluster_id)}
                        className={`premium-card transition-all cursor-pointer ${
                          isSelected 
                            ? "bg-primary/5 border border-primary ring-2 ring-primary/10" 
                            : "bg-surface-container-low border border-primary/5"
                        }`}
                      >
                        <div className="flex items-start justify-between mb-3">
                          <div className={`p-2.5 rounded-xl ${getThemeColorClass(theme.theme_name)}`}>
                            <span className="material-symbols-outlined text-base">{getThemeIcon(theme.theme_name)}</span>
                          </div>
                          <span className={`text-[9px] tracking-wider font-bold uppercase px-3 py-1 rounded-full ${
                            theme.severity === "HIGH" 
                              ? "bg-error/10 text-error" 
                              : "bg-primary/10 text-primary"
                          }`}>
                            {theme.severity === "HIGH" ? "HIGH IMPACT" : "MAINTENANCE"}
                          </span>
                        </div>
                        <h3 className="font-bold text-body-md text-on-surface mb-1">{theme.theme_name}</h3>
                        <p className="text-xs text-on-surface-variant mb-4 leading-relaxed">{theme.summary}</p>
                        
                        {/* Custom Progress Bar for theme review density */}
                        <div className="w-full bg-surface-container-highest h-1.5 rounded-full overflow-hidden mb-3">
                          <div 
                            className="bg-primary-container h-full transition-all duration-500"
                            style={{ width: `${Math.max(10, percentage)}%` }}
                          ></div>
                        </div>
                        <div className="flex justify-between items-center text-[10px] text-on-surface-variant font-medium">
                          <span>Volume Ratio: {percentage}%</span>
                          <span>{theme.review_count} reviews</span>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </section>

              {/* ========================================== */}
              {/* REVIEWS GRID & VERIFICATION PORTAL (Desktop) */}
              {/* ========================================== */}
              <section className="hidden md:block bg-surface-container-lowest rounded-[24px] shadow-sm border border-outline-variant/10 overflow-hidden">
                <div className="p-stack-lg border-b border-outline-variant/10 flex flex-col md:flex-row md:items-center justify-between gap-4">
                  <div>
                    <h4 className="text-title-sm font-bold text-on-surface font-sans">Review Verification Portal</h4>
                    <p className="text-body-sm text-on-surface-variant">Verify synthesized insights against raw user review texts</p>
                  </div>
                  
                  <div className="flex items-center gap-3">
                    <div className="relative">
                      <select 
                        value={selectedClusterId === null ? "All" : selectedClusterId.toString()}
                        onChange={(e) => {
                          const val = e.target.value;
                          setSelectedClusterId(val === "All" ? null : parseInt(val));
                        }}
                        className="bg-surface-container-low border-none rounded-xl pl-4 pr-10 py-2 text-body-sm font-medium text-on-surface focus:ring-2 focus:ring-primary/20 appearance-none cursor-pointer"
                      >
                        <option value="All">All Themes</option>
                        {report?.themes.map(t => (
                          <option key={t.cluster_id} value={t.cluster_id}>{t.theme_name}</option>
                        ))}
                        <option value="-1">Noise / Uncategorized</option>
                      </select>
                      <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">expand_more</span>
                    </div>

                    <div className="relative">
                      <select 
                        value={selectedPlatform}
                        onChange={(e) => setSelectedPlatform(e.target.value)}
                        className="bg-surface-container-low border-none rounded-xl pl-4 pr-10 py-2 text-body-sm font-medium text-on-surface focus:ring-2 focus:ring-primary/20 appearance-none cursor-pointer"
                      >
                        <option value="All">All Platforms</option>
                        <option value="appstore">App Store</option>
                        <option value="playstore">Play Store</option>
                      </select>
                      <span className="material-symbols-outlined absolute right-3 top-1/2 -translate-y-1/2 pointer-events-none text-on-surface-variant">expand_more</span>
                    </div>

                    <div className="relative">
                      <input 
                        type="text" 
                        value={searchQuery}
                        onChange={(e) => setSearchQuery(e.target.value)}
                        className="bg-surface-container-low border-none rounded-xl pl-10 pr-4 py-2 text-body-sm w-64 focus:ring-2 focus:ring-primary/20 focus:outline-none font-sans"
                        placeholder="Search text..."
                      />
                      <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant">filter_list</span>
                    </div>
                  </div>
                </div>

                <div className="overflow-x-auto">
                  <table className="w-full text-left">
                    <thead>
                      <tr className="bg-surface-container-low/50 text-label-caps text-on-surface-variant">
                        <th className="px-6 py-4">Date</th>
                        <th className="px-6 py-4 text-center">Platform</th>
                        <th className="px-6 py-4">Rating</th>
                        <th className="px-6 py-4">Theme mapping</th>
                        <th className="px-6 py-4">Review Text</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-outline-variant/10">
                      {paginatedReviews.length === 0 ? (
                        <tr>
                          <td colSpan={5} className="text-center py-10 text-secondary">
                            No reviews found matching the filters.
                          </td>
                        </tr>
                      ) : (
                        paginatedReviews.map((review) => (
                          <tr key={review.id} className="hover:bg-secondary-container/5 transition-colors group">
                            <td className="px-6 py-5 text-body-sm text-secondary truncate">
                              {new Date(review.date).toLocaleDateString("en-IN", {
                                day: "2-digit",
                                month: "short",
                                year: "numeric",
                                hour: "2-digit",
                                minute: "2-digit"
                              })}
                            </td>
                            <td className="px-6 py-5 text-center">
                              {review.platform === "appstore" ? (
                                <span className="material-symbols-outlined text-secondary-fixed-dim" title="App Store">apps</span>
                              ) : (
                                <span className="material-symbols-outlined text-secondary-fixed-dim" title="Play Store">phone_android</span>
                              )}
                            </td>
                            <td className="px-6 py-5">
                              <div className="flex gap-0.5 text-primary">
                                {Array.from({ length: 5 }).map((_, i) => (
                                  <span 
                                    key={i} 
                                    className="material-symbols-outlined text-sm md:text-base"
                                    style={{ fontVariationSettings: i < review.rating ? "'FILL' 1" : "'FILL' 0" }}
                                  >
                                    star
                                  </span>
                                ))}
                              </div>
                            </td>
                            <td className="px-6 py-5">
                              <span className={`px-2 py-1 text-xs font-bold rounded-md ${
                                review.cluster_id === -1 
                                  ? "bg-secondary-container text-secondary" 
                                  : review.cluster_id === 1 
                                    ? "bg-primary-container/20 text-primary" 
                                    : "bg-tertiary-container/30 text-on-tertiary-container"
                              }`}>
                                {getThemeNameByClusterId(review.cluster_id)}
                              </span>
                            </td>
                            <td className="px-6 py-5">
                              <p className="text-body-sm text-on-surface line-clamp-1 max-w-2xl" title={review.review_text}>
                                {review.review_text}
                              </p>
                            </td>
                          </tr>
                        ))
                      )}
                    </tbody>
                  </table>
                </div>

                {/* Desktop Pagination */}
                {filteredReviews.length > 0 && (
                  <div className="p-6 border-t border-outline-variant/10 flex items-center justify-between">
                    <p className="text-body-sm text-secondary">
                      Showing {(currentPage - 1) * reviewsPerPage + 1} - {Math.min(currentPage * reviewsPerPage, filteredReviews.length)} of {filteredReviews.length} reviews
                    </p>
                    <div className="flex items-center gap-2">
                      <button 
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                        className="p-2 hover:bg-surface-container rounded-lg transition-colors disabled:opacity-30 cursor-pointer"
                      >
                        <span className="material-symbols-outlined">chevron_left</span>
                      </button>
                      
                      <div className="flex gap-1">
                        {Array.from({ length: Math.min(5, totalPages) }).map((_, idx) => {
                          let pageNo = idx + 1;
                          if (currentPage > 3 && totalPages > 5) {
                            pageNo = currentPage - 3 + idx;
                            if (pageNo + (4 - idx) > totalPages) {
                              pageNo = totalPages - 4 + idx;
                            }
                          }
                          return (
                            <button 
                              key={pageNo}
                              onClick={() => setCurrentPage(pageNo)}
                              className={`w-8 h-8 flex items-center justify-center rounded-lg text-body-sm font-semibold cursor-pointer ${
                                currentPage === pageNo 
                                  ? "bg-primary text-on-primary" 
                                  : "hover:bg-surface-container"
                              }`}
                            >
                              {pageNo}
                            </button>
                          );
                        })}
                      </div>

                      <button 
                        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                        disabled={currentPage === totalPages}
                        className="p-2 hover:bg-surface-container rounded-lg transition-colors disabled:opacity-30 cursor-pointer"
                      >
                        <span className="material-symbols-outlined">chevron_right</span>
                      </button>
                    </div>
                  </div>
                )}
              </section>

              {/* ========================================== */}
              {/* MOBILE REVIEW STATUS LIST */}
              {/* ========================================== */}
              <section className="block md:hidden mb-6">
                <div className="flex items-center justify-between mb-3">
                  <h2 className="font-bold text-title-sm">Review Status</h2>
                  <div className="flex items-center gap-1.5">
                    <select
                      value={selectedPlatform}
                      onChange={(e) => setSelectedPlatform(e.target.value)}
                      className="bg-primary/5 text-primary text-[10px] font-bold border-none rounded-full px-2.5 py-1 focus:outline-none"
                    >
                      <option value="All">All Platforms</option>
                      <option value="appstore">App Store</option>
                      <option value="playstore">Play Store</option>
                    </select>
                  </div>
                </div>

                <div className="relative mb-3">
                  <input 
                    type="text" 
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="bg-surface-container-low border border-outline-variant/30 rounded-xl pl-9 pr-4 py-2 text-xs w-full focus:outline-none focus:ring-1 focus:ring-primary/20"
                    placeholder="Search raw review text..."
                  />
                  <span className="material-symbols-outlined absolute left-3 top-1/2 -translate-y-1/2 text-on-surface-variant text-base">search</span>
                </div>

                <div className="premium-card p-0 overflow-hidden">
                  <div className="divide-y divide-outline-variant/30">
                    {paginatedReviews.length === 0 ? (
                      <div className="p-8 text-center text-xs text-secondary">
                        No matching reviews found.
                      </div>
                    ) : (
                      paginatedReviews.map((review) => (
                        <div 
                          key={review.id} 
                          onClick={() => setSelectedReviewForModal(review)}
                          className="p-4 flex items-center justify-between active:bg-surface-container transition-colors cursor-pointer"
                        >
                          <div className="flex items-center gap-3 min-w-0 flex-1 mr-2">
                            <div className="w-9 h-9 rounded-full bg-primary/5 flex items-center justify-center text-primary flex-shrink-0">
                              {review.platform === "appstore" ? (
                                <span className="material-symbols-outlined text-base">apps</span>
                              ) : (
                                <span className="material-symbols-outlined text-base">phone_android</span>
                              )}
                            </div>
                            <div className="min-w-0 flex-1">
                              <h4 className="font-semibold text-xs text-on-surface truncate">
                                {getThemeNameByClusterId(review.cluster_id)}
                              </h4>
                              <p className="text-[10px] text-on-surface-variant truncate mt-0.5 font-sans leading-tight">
                                {review.review_text}
                              </p>
                              <div className="flex text-primary gap-0.5 mt-1">
                                {Array.from({ length: review.rating }).map((_, i) => (
                                  <span key={i} className="material-symbols-outlined text-[10px]" style={{ fontVariationSettings: "'FILL' 1" }}>star</span>
                                ))}
                              </div>
                            </div>
                          </div>
                          <div className="text-right flex-shrink-0">
                            <p className="font-sans text-[10px] text-primary font-bold tracking-wider">
                              {review.rating >= 4 ? "VERIFIED" : "PENDING"}
                            </p>
                            <p className="text-[8px] text-on-surface-variant uppercase font-semibold mt-0.5">
                              {new Date(review.date).toLocaleDateString("en-IN", {
                                day: "numeric",
                                month: "short"
                              })}
                            </p>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                {/* Mobile Pagination */}
                {filteredReviews.length > 0 && (
                  <div className="flex justify-between items-center mt-3 text-[11px] text-on-surface-variant px-1">
                    <span>Page {currentPage} of {totalPages}</span>
                    <div className="flex gap-2">
                      <button 
                        onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                        disabled={currentPage === 1}
                        className="px-2.5 py-1 bg-surface-container-low rounded-lg font-bold disabled:opacity-30"
                      >
                        Prev
                      </button>
                      <button 
                        onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                        disabled={currentPage === totalPages}
                        className="px-2.5 py-1 bg-surface-container-low rounded-lg font-bold disabled:opacity-30"
                      >
                        Next
                      </button>
                    </div>
                  </div>
                )}
              </section>

              {/* ========================================== */}
              {/* MOBILE CHARTS SECTION */}
              {/* ========================================== */}
              <section className="block md:hidden mb-12">
                <div className="premium-card">
                  <div className="flex justify-between items-start mb-4">
                    <div>
                      <h3 className="font-bold text-body-md text-on-surface">Monthly Engagement</h3>
                      <p className="text-xs text-on-surface-variant mt-0.5">Scraped review frequency by weekday</p>
                    </div>
                    <span className="material-symbols-outlined text-on-surface-variant text-base">more_vert</span>
                  </div>
                  <div className="h-28 w-full flex items-end justify-between gap-2 px-1">
                    <div className="bg-primary/20 w-full rounded-t-lg h-[40%]"></div>
                    <div className="bg-primary/20 w-full rounded-t-lg h-[60%]"></div>
                    <div className="bg-primary/20 w-full rounded-t-lg h-[45%]"></div>
                    <div className="bg-primary/20 w-full rounded-t-lg h-[75%]"></div>
                    <div className="bg-primary/20 w-full rounded-t-lg h-[65%]"></div>
                    <div className="bg-primary/20 w-full rounded-t-lg h-[90%]"></div>
                    <div className="bg-primary w-full rounded-t-lg h-[95%]"></div>
                  </div>
                  <div className="flex justify-between mt-2 px-1 text-[9px] font-bold text-on-surface-variant uppercase tracking-wider">
                    <span>MON</span><span>TUE</span><span>WED</span><span>THU</span><span>FRI</span><span>SAT</span><span>SUN</span>
                  </div>
                </div>
              </section>
            </>
          )}

        </div>

        {/* Ambient background glow */}
        <div className="fixed bottom-0 right-0 w-1/3 h-1/3 bg-primary/5 blur-[120px] -z-10 rounded-full pointer-events-none"></div>
      </main>

      {/* ========================================== */}
      {/* MOBILE BOTTOM NAVIGATION BAR */}
      {/* ========================================== */}
      <nav className="fixed bottom-0 left-0 right-0 bg-surface-container-low shadow-[0_-4px_12px_rgba(0,0,0,0.05)] px-stack-lg py-3 flex justify-between items-center z-50 md:hidden border-t border-outline-variant/10 font-sans">
        <a className="flex flex-col items-center gap-1 group flex-1" href="#" onClick={(e) => { e.preventDefault(); setSelectedClusterId(null); window.scrollTo({ top: 0, behavior: 'smooth' }); }}>
          <div className="text-primary font-bold">
            <span className="material-symbols-outlined" style={{ fontVariationSettings: "'FILL' 1" }}>dashboard</span>
          </div>
          <span className="text-[9px] text-primary font-bold uppercase tracking-wider">Dashboard</span>
          <div className="active-dot"></div>
        </a>
        
        {/* Stitch Middle Action Floating Icon */}
        <div className="bg-primary p-3.5 rounded-full shadow-lg active:scale-95 transition-transform flex items-center justify-center text-white border border-primary/20 cursor-pointer">
          <span className="material-symbols-outlined text-xl">analytics</span>
        </div>

        <a 
          className="flex flex-col items-center gap-1 group flex-1 animate-pulse" 
          href="#" 
          onClick={(e) => { 
            e.preventDefault(); 
            const el = document.getElementById('strategic-themes');
            if (el) el.scrollIntoView({ behavior: 'smooth' });
          }}
        >
          <div className="text-on-surface-variant hover:text-primary transition-all">
            <span className="material-symbols-outlined">analytics</span>
          </div>
          <span className="text-[9px] text-on-surface-variant uppercase tracking-wider">Insights</span>
        </a>
      </nav>

      {/* ========================================== */}
      {/* REVIEW DETAILS MODAL */}
      {/* ========================================== */}
      {selectedReviewForModal && (
        <div className="fixed inset-0 bg-black/60 backdrop-blur-sm z-100 flex items-end md:items-center justify-center p-4">
          <div 
            className="bg-white rounded-t-3xl md:rounded-3xl w-full max-w-lg p-6 shadow-2xl animate-in slide-in-from-bottom duration-300 md:animate-in md:zoom-in-95"
            onClick={(e) => e.stopPropagation()}
          >
            <div className="flex justify-between items-start mb-4">
              <div>
                <span className={`px-2 py-0.5 text-[9px] font-bold rounded uppercase tracking-wider ${
                  selectedReviewForModal.platform === "appstore" ? "bg-black text-white" : "bg-primary text-white"
                }`}>
                  {selectedReviewForModal.platform === "appstore" ? "App Store" : "Play Store"}
                </span>
                <h3 className="font-bold text-body-md text-on-surface mt-2 leading-tight">
                  Theme: {getThemeNameByClusterId(selectedReviewForModal.cluster_id)}
                </h3>
              </div>
              <button 
                onClick={() => setSelectedReviewForModal(null)}
                className="w-8 h-8 rounded-full bg-surface-container-low flex items-center justify-center text-secondary hover:text-primary"
              >
                <span className="material-symbols-outlined text-lg">close</span>
              </button>
            </div>
            
            <div className="flex gap-0.5 text-primary mb-3">
              {Array.from({ length: 5 }).map((_, i) => (
                <span 
                  key={i} 
                  className="material-symbols-outlined text-base"
                  style={{ fontVariationSettings: i < selectedReviewForModal.rating ? "'FILL' 1" : "'FILL' 0" }}
                >
                  star
                </span>
              ))}
            </div>

            <p className="text-xs md:text-body-sm text-secondary font-semibold mb-3">
              User: {selectedReviewForModal.author} • {new Date(selectedReviewForModal.date).toLocaleDateString("en-IN", {
                day: "numeric",
                month: "long",
                year: "numeric",
                hour: "2-digit",
                minute: "2-digit"
              })}
            </p>

            <div className="bg-surface-container-low p-4 rounded-xl border border-outline-variant/20 mb-5 max-h-48 overflow-y-auto">
              <p className="text-body-sm text-on-surface font-sans leading-relaxed whitespace-pre-line italic">
                "{selectedReviewForModal.review_text}"
              </p>
            </div>

            <div className="flex justify-end gap-2">
              <button 
                onClick={() => setSelectedReviewForModal(null)}
                className="w-full py-3 bg-primary text-on-primary rounded-xl font-bold text-body-sm hover:opacity-90 transition-all cursor-pointer"
              >
                Close
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
