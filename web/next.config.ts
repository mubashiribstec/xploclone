import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // The browser never talks to the GPU server directly; all API calls go
  // through app/api/* routes (server-side proxy with the API key).
  reactStrictMode: true,
};

export default nextConfig;
