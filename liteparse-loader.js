/* Loads liteparse and exposes it globally.
   Loaded via <script type="module" src="..."> — uses static import
   instead of dynamic import() which may fail on some configurations. */
import { LiteParse, default as initLiteParse } from './liteparse/liteparse_wasm.js';

// Initialize the WASM module immediately
const initPromise = initLiteParse('./liteparse/liteparse_wasm_bg.wasm').then(() => {
  window.__LiteParseReady = true;
  window.__LiteParse = LiteParse;
});

// Export for use by other modules
export { LiteParse, initLiteParse, initPromise };
