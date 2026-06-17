import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Allow cross-origin requests to the Go API during development.
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8080/api/:path*",
      },
      {
        source: "/r/:code",
        destination: "http://localhost:8080/r/:code",
      },
    ];
  },
};

export default nextConfig;
