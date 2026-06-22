import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/nlp/:path*",
        destination: `${process.env.NLP_SERVICE_URL || "http://nlp:8001"}/:path*`,
      },
      {
        source: "/api/go/:path*",
        destination: `${process.env.GO_API_URL || "http://api:8080"}/:path*`,
      },
    ];
  },
};

export default nextConfig;
