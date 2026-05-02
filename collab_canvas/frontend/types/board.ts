export type ConnectionStatus = "connecting" | "online" | "offline";

export type DrawPayload = {
  x: number;
  y: number;
  color: string;
};

export type ServerMessage =
  | {
      type: "init";
      width: number;
      height: number;
      pixels: string[][];
      users?: number;
    }
  | {
      type: "presence";
      users: number;
    }
  | {
      type: "draw";
      payload: DrawPayload;
    }
  | {
      type: "cooldown";
      retryAfterMs: number;
    }
  | {
      type: "error";
      payload: {
        message: string;
      };
    };
