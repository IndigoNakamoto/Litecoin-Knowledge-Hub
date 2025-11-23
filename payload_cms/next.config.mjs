import { withPayload } from '@payloadcms/next/withPayload'

/** @type {import('next').NextConfig} */
const nextConfig = {
  // Enable standalone output for Docker deployment
  output: process.env.NODE_ENV === 'production' ? 'standalone' : undefined,
  // Ensure proper module handling
  serverExternalPackages: ['sharp'],
  // Webpack config to handle ESM properly
  webpack: (config, { isServer }) => {
    if (isServer) {
      config.externals = [...(config.externals || []), 'sharp'];
    }
    return config;
  },
}

export default withPayload(nextConfig, { devBundleServerPackages: false })
