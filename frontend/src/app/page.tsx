"use client";

import { useEffect, useState, useRef } from "react";

interface Flow {
  timestamp: number;
  src_ip: string;
  dst_ip: string;
  src_port: number | null;
  dst_port: number | null;
  protocol: string;
  length: number;
  classification: string;
  confidence: number;
}

export default function LiveFeed() {
  const [flows, setFlows] = useState<Flow[]>([]);
  const ws = useRef<WebSocket | null>(null);
  
  useEffect(() => {
    ws.current = new WebSocket("ws://localhost:8000/ws");
    ws.current.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === "flow") {
        setFlows((prev) => [...prev, message.data]);
      }
    };
    return () => {
      ws.current?.close();
    };
  }, []);

  // auto scroll logic
  const feedEndRef = useRef<HTMLDivElement | null>(null);
  useEffect(() => {
    feedEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [flows]);

  return (
    <div className="min-h-screen bg-gray-50 p-8 text-gray-900 font-sans">
      <div className="max-w-6xl mx-auto bg-white rounded-xl shadow overflow-hidden flex flex-col h-[calc(100vh-4rem)]">
        <div className="px-6 py-4 border-b border-gray-200 bg-white z-10 sticky top-0 flex justify-between items-center">
          <h1 className="text-xl font-semibold text-gray-800">Live Traffic Feed</h1>
          <div className="flex items-center space-x-2">
            <span className="relative flex h-3 w-3">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>
              <span className="relative inline-flex rounded-full h-3 w-3 bg-green-500"></span>
            </span>
            <span className="text-sm text-gray-500 font-medium">Recording</span>
          </div>
        </div>
        
        <div className="overflow-y-auto flex-1 p-0">
          <table className="w-full text-left border-collapse">
            <thead className="bg-gray-100 text-gray-600 sticky top-0 shadow-sm text-sm z-10">
              <tr>
                <th className="py-3 px-6 font-medium border-b border-gray-200">Time</th>
                <th className="py-3 px-6 font-medium border-b border-gray-200">Source</th>
                <th className="py-3 px-6 font-medium border-b border-gray-200">Destination</th>
                <th className="py-3 px-6 font-medium border-b border-gray-200">Protocol</th>
                <th className="py-3 px-6 font-medium border-b border-gray-200">Port</th>
                <th className="py-3 px-6 font-medium border-b border-gray-200">Class</th>
              </tr>
            </thead>
            <tbody className="text-sm">
              {flows.length === 0 && (
                <tr>
                  <td colSpan={6} className="text-center py-12 text-gray-500 bg-white">
                    Waiting for traffic...
                  </td>
                </tr>
              )}
              {flows.map((f, i) => {
                let bgTemplate = "bg-white text-gray-800 border-b border-gray-100 hover:bg-gray-50";
                if (f.classification === "suspicious") {
                  bgTemplate = "bg-red-500 text-white font-medium border-b border-red-600 hover:bg-red-600";
                } else if (f.classification === "unknown") {
                  bgTemplate = "bg-amber-100 text-amber-900 border-b border-amber-200 hover:bg-amber-200";
                }
                
                const timeStr = new Date(f.timestamp * 1000).toLocaleTimeString();
                
                return (
                  <tr key={i} className={`${bgTemplate} transition-colors duration-150 ease-in-out`}>
                    <td className="py-3 px-6">{timeStr}</td>
                    <td className="py-3 px-6 font-mono text-xs">{f.src_ip}</td>
                    <td className="py-3 px-6 font-mono text-xs">{f.dst_ip}</td>
                    <td className="py-3 px-6 font-semibold">{f.protocol}</td>
                    <td className="py-3 px-6 font-mono">{f.dst_port ?? f.src_port ?? '-'}</td>
                    <td className="py-3 px-6 uppercase tracking-wider text-xs font-bold">
                      {f.classification} 
                      <span className="text-[10px] opacity-75 ml-2">({f.confidence.toFixed(2)})</span>
                    </td>
                  </tr>
                );
              })}
              <tr ref={feedEndRef} />
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
