"use client";

import * as d3 from "d3";
import { useEffect, useRef } from "react";
import type { GraphData, GraphNode, GraphLink } from "@/lib/types";

interface GraphViewProps {
  data: GraphData;
  onNodeClick?: (node: GraphNode) => void;
}

// Color mapping for entity group/label
const GROUP_COLORS: Record<string, string> = {
  PERSON: "#58a6ff",    // blue
  PER: "#58a6ff",
  ORG: "#3fb950",       // green
  GPE: "#f78166",       // orange-red (geo-political)
  LOC: "#f0883e",       // orange
  LOCATION: "#f0883e",
  DATE: "#bc8cff",      // purple
  TIME: "#bc8cff",
  MONEY: "#ffa657",     // amber
  PRODUCT: "#79c0ff",   // light blue
  EVENT: "#ff7b72",     // red
  WORK_OF_ART: "#d2a8ff",
  LAW: "#ffa657",
  LANGUAGE: "#79c0ff",
  PERCENT: "#8b949e",
  QUANTITY: "#8b949e",
  ORDINAL: "#8b949e",
  CARDINAL: "#8b949e",
};

function getColor(group: string): string {
  return GROUP_COLORS[group] ?? "#8b949e";
}

export default function GraphView({ data, onNodeClick }: GraphViewProps) {
  const svgRef = useRef<SVGSVGElement>(null);
  const simulationRef = useRef<d3.Simulation<GraphNode, GraphLink> | null>(null);

  useEffect(() => {
    if (!svgRef.current) return;

    const svg = d3.select(svgRef.current);
    const { width, height } = svgRef.current.getBoundingClientRect();

    // Clear previous render
    svg.selectAll("*").remove();

    if (!data.nodes.length) {
      svg.append("text")
        .attr("x", width / 2)
        .attr("y", height / 2)
        .attr("text-anchor", "middle")
        .attr("fill", "#8b949e")
        .attr("font-size", "14px")
        .text("Crie notas para ver o grafo de conhecimento");
      return;
    }

    // Stop previous simulation
    simulationRef.current?.stop();

    // Deep-copy nodes and links to avoid mutating props
    const nodes: GraphNode[] = data.nodes.map((n) => ({ ...n }));
    const linkIndex = new Map(nodes.map((n) => [n.id, n]));

    const links: GraphLink[] = data.links.map((l) => ({
      ...l,
      source: typeof l.source === "string" ? l.source : (l.source as GraphNode).id,
      target: typeof l.target === "string" ? l.target : (l.target as GraphNode).id,
    }));

    // Root <g> with zoom support
    const g = svg.append("g");

    svg.call(
      d3.zoom<SVGSVGElement, unknown>()
        .scaleExtent([0.1, 4])
        .on("zoom", (event) => {
          g.attr("transform", event.transform);
        })
    );

    // Arrow marker
    svg.append("defs").append("marker")
      .attr("id", "arrowhead")
      .attr("viewBox", "0 -5 10 10")
      .attr("refX", 20)
      .attr("refY", 0)
      .attr("markerWidth", 6)
      .attr("markerHeight", 6)
      .attr("orient", "auto")
      .append("path")
      .attr("d", "M0,-5L10,0L0,5")
      .attr("fill", "#30363d");

    // Links
    const link = g.append("g")
      .selectAll<SVGLineElement, GraphLink>("line")
      .data(links)
      .join("line")
      .attr("stroke", "#30363d")
      .attr("stroke-width", 1.5)
      .attr("marker-end", "url(#arrowhead)");

    // Tooltip div
    const tooltip = d3.select("body")
      .append("div")
      .style("position", "absolute")
      .style("background", "#161b22")
      .style("border", "1px solid #30363d")
      .style("border-radius", "6px")
      .style("padding", "8px 12px")
      .style("color", "#e6edf3")
      .style("font-size", "12px")
      .style("pointer-events", "none")
      .style("opacity", "0")
      .style("z-index", "1000")
      .style("max-width", "220px");

    // Nodes
    const nodeRadius = (n: GraphNode) => Math.max(6, Math.min(24, 6 + n.count * 2));

    const node = g.append("g")
      .selectAll<SVGGElement, GraphNode>("g")
      .data(nodes)
      .join("g")
      .style("cursor", "pointer")
      .call(
        d3.drag<SVGGElement, GraphNode>()
          .on("start", (event, d) => {
            if (!event.active) simulation.alphaTarget(0.3).restart();
            d.fx = d.x;
            d.fy = d.y;
          })
          .on("drag", (event, d) => {
            d.fx = event.x;
            d.fy = event.y;
          })
          .on("end", (event, d) => {
            if (!event.active) simulation.alphaTarget(0);
            d.fx = null;
            d.fy = null;
          })
      )
      .on("click", (_event, d) => {
        onNodeClick?.(d);
      })
      .on("mouseover", (event, d) => {
        tooltip
          .style("opacity", "1")
          .html(`<strong>${d.label}</strong><br/><span style="color:#8b949e">${d.group}</span><br/>Aparições: ${d.count}`);
      })
      .on("mousemove", (event) => {
        tooltip
          .style("left", `${(event as MouseEvent).pageX + 12}px`)
          .style("top", `${(event as MouseEvent).pageY - 28}px`);
      })
      .on("mouseout", () => {
        tooltip.style("opacity", "0");
      });

    node.append("circle")
      .attr("r", nodeRadius)
      .attr("fill", (d) => getColor(d.group))
      .attr("fill-opacity", 0.85)
      .attr("stroke", "#0d1117")
      .attr("stroke-width", 2);

    node.append("text")
      .attr("dy", (d) => nodeRadius(d) + 12)
      .attr("text-anchor", "middle")
      .attr("fill", "#e6edf3")
      .attr("font-size", "10px")
      .attr("pointer-events", "none")
      .text((d) => d.label.length > 18 ? d.label.slice(0, 15) + "…" : d.label);

    // Force simulation
    const simulation = d3.forceSimulation<GraphNode>(nodes)
      .force(
        "link",
        d3.forceLink<GraphNode, GraphLink>(links)
          .id((d) => d.id)
          .distance(100)
      )
      .force("charge", d3.forceManyBody().strength(-120))
      .force("center", d3.forceCenter(width / 2, height / 2))
      .force("collision", d3.forceCollide().radius((d) => nodeRadius(d as GraphNode) + 8));

    simulationRef.current = simulation;

    simulation.on("tick", () => {
      link
        .attr("x1", (d) => (d.source as GraphNode).x ?? 0)
        .attr("y1", (d) => (d.source as GraphNode).y ?? 0)
        .attr("x2", (d) => (d.target as GraphNode).x ?? 0)
        .attr("y2", (d) => (d.target as GraphNode).y ?? 0);

      node.attr("transform", (d) => `translate(${d.x ?? 0},${d.y ?? 0})`);
    });

    return () => {
      simulation.stop();
      tooltip.remove();
    };
  }, [data, onNodeClick]);

  return (
    <svg
      ref={svgRef}
      className="w-full h-full"
      style={{ background: "#0d1117" }}
    />
  );
}
