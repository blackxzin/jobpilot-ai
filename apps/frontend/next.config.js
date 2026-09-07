/**
 * Two build targets:
 *
 * - Default: a server build that proxies /api to the FastAPI backend.
 * - `STATIC_DEMO=true`: a fully static export for GitHub Pages, where every
 *   request is answered in the browser from captured fixtures. Rewrites do not
 *   exist in a static export, so the proxy is dropped in that mode.
 */
const isStaticDemo = process.env.STATIC_DEMO === "true";

// Pages serves the site from /<repo>, so assets need that prefix.
const basePath = isStaticDemo ? process.env.STATIC_DEMO_BASE_PATH || "" : "";

/** @type {import('next').NextConfig} */
const nextConfig = {
  poweredByHeader: false,
  compress: true,
  ...(isStaticDemo
    ? {
        output: "export",
        basePath,
        assetPrefix: basePath || undefined,
        // The export has no image optimization server.
        images: { unoptimized: true },
        // Pages serves /path/ as /path/index.html.
        trailingSlash: true,
      }
    : {
        async rewrites() {
          const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
          return [{ source: "/api/:path*", destination: `${apiUrl}/api/:path*` }];
        },
      }),
};

export default nextConfig;
