import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: "standalone",

  images: {
    // The Pi container has a read-only root filesystem. Serving the original
    // remote asset avoids Next's writable image-cache requirement and saves
    // CPU on the Pi; the browser still fetches the allowed HTTPS image.
    unoptimized: true,
    remotePatterns: [
      {
        protocol: "https",
        hostname: "crests.football-data.org",
      },
    ],
  },

  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://api:8000/api/:path*",
      },
    ];
  },
};

export default nextConfig;
