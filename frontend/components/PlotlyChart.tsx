"use client";

import React, { useEffect, useRef, useState } from "react";

interface PlotlyChartProps {
  data: any[];
  layout?: Record<string, any>;
  config?: Record<string, any>;
  height?: number;
  className?: string;
}

export default function PlotlyChart({
  data,
  layout = {},
  config = {},
  height = 360,
  className = "",
}: PlotlyChartProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [isLoaded, setIsLoaded] = useState(false);
  const [plotlyInstance, setPlotlyInstance] = useState<any>(null);

  useEffect(() => {
    let isMounted = true;
    // Dynamically import plotly client-side to prevent SSR window issues
    import("plotly.js-dist-min")
      .then((PlotlyModule) => {
        if (isMounted) {
          const Plotly = PlotlyModule.default || PlotlyModule;
          setPlotlyInstance(Plotly);
          setIsLoaded(true);
        }
      })
      .catch((err) => {
        console.error("Failed to load Plotly:", err);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  useEffect(() => {
    if (!isLoaded || !plotlyInstance || !containerRef.current || !data || data.length === 0) {
      return;
    }

    const defaultLayout = {
      autosize: true,
      height: height,
      margin: { l: 50, r: 30, t: 30, b: 40 },
      paper_bgcolor: "transparent",
      plot_bgcolor: "transparent",
      font: {
        family: "Inter, system-ui, sans-serif",
        color: "#475569", // slate-600
        size: 11,
      },
      xaxis: {
        gridcolor: "#e2e8f0", // slate-200
        zerolinecolor: "#cbd5e1",
      },
      yaxis: {
        gridcolor: "#e2e8f0",
        zerolinecolor: "#cbd5e1",
      },
      legend: {
        orientation: "h",
        y: 1.15,
        x: 0,
        font: { color: "#1e293b" }, // slate-800
      },
      ...layout,
    };

    const defaultConfig = {
      responsive: true,
      displayModeBar: false,
      ...config,
    };

    plotlyInstance.newPlot(containerRef.current, data, defaultLayout, defaultConfig);

    const handleResize = () => {
      if (containerRef.current && plotlyInstance) {
        plotlyInstance.Plots.resize(containerRef.current);
      }
    };

    window.addEventListener("resize", handleResize);

    return () => {
      window.removeEventListener("resize", handleResize);
      if (containerRef.current && plotlyInstance) {
        plotlyInstance.purge(containerRef.current);
      }
    };
  }, [isLoaded, plotlyInstance, data, layout, config, height]);

  if (!isLoaded) {
    return (
      <div
        style={{ height }}
        className={`flex items-center justify-center bg-slate-50 border border-slate-200 rounded-lg text-xs text-slate-500 ${className}`}
      >
        <div className="flex items-center gap-2">
          <div className="w-3.5 h-3.5 border-2 border-blue-900 border-t-transparent rounded-full animate-spin"></div>
          <span>Rendering analytics visualization...</span>
        </div>
      </div>
    );
  }

  return (
    <div
      ref={containerRef}
      style={{ height }}
      className={`w-full overflow-hidden ${className}`}
    />
  );
}
