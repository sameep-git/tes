import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone", // Required for Docker — produces a self-contained node server
};

export default nextConfig;
