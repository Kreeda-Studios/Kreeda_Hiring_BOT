import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  webpack: (config) => {
    // Ignore canvas module for browser builds (pdfjs-dist tries to load it for Node.js)
    config.resolve.alias = config.resolve.alias || {};
    config.resolve.alias.canvas = false;
    
    // Handle other Node-only modules that might be imported
    config.resolve.fallback = config.resolve.fallback || {};
    config.resolve.fallback.fs = false;
    config.resolve.fallback.path = false;
    config.resolve.fallback.stream = false;
    
    return config;
  },
};

export default nextConfig;
