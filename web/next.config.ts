import type { NextConfig } from "next";

// DEMO_BASE_PATH serves the static demo from a sub-path, e.g. /demos/pr-tone-coach
// on a personal site.
const basePath = process.env.DEMO_BASE_PATH ?? "";

const nextConfig: NextConfig = {
  output: "export",
  images: { unoptimized: true },
  trailingSlash: true,
  basePath,
};

export default nextConfig;
