import type { NextConfig } from "next";
import { assertPublicEnvironment } from "./lib/public-environment";

assertPublicEnvironment(process.env);

const nextConfig: NextConfig = {
  // Vercel builds native Next.js functions; Docker uses the standalone server.
  output: process.env.VERCEL === "1" ? undefined : "standalone",
  distDir: process.env.NODE_ENV === "development" ? ".next-dev" : ".next",
};

export default nextConfig;
