import { IBM_Plex_Mono, Inter_Tight, Tektur } from "next/font/google";

const display = Tektur({ subsets: ["latin"], weight: ["500", "600", "700"], variable: "--font-build-display" });
const body = Inter_Tight({ subsets: ["latin"], variable: "--font-build-body" });
const mono = IBM_Plex_Mono({ subsets: ["latin"], weight: ["400", "500"], variable: "--font-build-mono" });

export const build2026Fonts = `${display.variable} ${body.variable} ${mono.variable}`;
