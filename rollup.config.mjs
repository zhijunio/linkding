import resolve from '@rollup/plugin-node-resolve';
import terser from '@rollup/plugin-terser';

const production = !process.env.ROLLUP_WATCH;

// Custom plugin to exclude dev-tool.js from production builds
const excludeDevTool = {
  name: 'exclude-dev-tool',
  load(id) {
    if (production && id.endsWith('dev-tool.js')) {
      return '';
    }
    return null;
  },
};

export default {
  input: 'bookmarks/frontend/index.js',
  output: {
    sourcemap: production,
    format: 'iife',
    name: 'linkding',
    file: 'bookmarks/static/bundle.js',
  },
  plugins: [
    excludeDevTool,
    resolve({
      browser: true,
    }),
    production && terser({
      format: { comments: false },
      compress: {
        drop_console: true,
        drop_debugger: true,
      },
    }),
  ],
  watch: {
    clearScreen: false,
  },
};
