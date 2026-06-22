export interface Note {
  id: number;
  title: string;
  content: string;
  created_at: string;
  updated_at: string;
}

export interface Entity {
  text: string;
  label: string;
}

export interface Relation {
  source: string;
  target: string;
  context: string;
}

export interface GraphNode {
  id: string;
  label: string;
  group: string;
  count: number;
  // D3 simulation properties added at runtime
  x?: number;
  y?: number;
  vx?: number;
  vy?: number;
  fx?: number | null;
  fy?: number | null;
}

export interface GraphLink {
  source: string | GraphNode;
  target: string | GraphNode;
  context: string;
}

export interface GraphData {
  nodes: GraphNode[];
  links: GraphLink[];
}
