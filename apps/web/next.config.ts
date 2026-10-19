import type { NextConfig } from "next";
import { assertPublicEnvironment } from "./lib/public-environment";

assertPublicEnvironment(process.env);

const nextConfig: NextConfig = {
  output: "standalone",
  distDir: process.env.NODE_ENV === "development" ? ".next-dev" : ".next",
};

export default nextConfig;
