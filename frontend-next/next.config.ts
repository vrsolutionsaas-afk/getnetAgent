import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  outputFileTracingIncludes: {
    "/api/admin/arquitetura": ["./assets/arquitetura-getnet.png"],
  },
};

export default nextConfig;
