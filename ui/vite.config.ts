import react from "@vitejs/plugin-react-swc";
import "dotenv/config";
import path from "node:path";
import { type Plugin, defineConfig, splitVendorChunkPlugin } from "vite";
import injectHTML from "vite-plugin-html-inject";
import tsConfigPaths from "vite-tsconfig-paths";
import { componentTaggerPlugin } from "./server/component-tagger-plugin";
import {
  ExtensionName,
  getExtensionConfig,
  isExtensionEnabled,
} from "./server/extensions";
import { hotReloadTrackerPlugin } from "./server/hotreload-tracker";
import { createDatabuttonLogger } from "./server/logger";
import { buildOpenApiSpecHandler } from "./server/openapi-spec-handler";
import { handleTryTscCompile } from "./server/try-tsc-handler";

const isDevRun = process.env.NODE_ENV === "development";

const enableHotReloadTracker =
  process.env.ENABLE_UI_HOTRELOAD_TRACKER === "true";

const projectId = process.env.DATABUTTON_PROJECT_ID || "MISSING-PROJECT-ID";
const serviceType = process.env.DATABUTTON_SERVICE_TYPE || "devx";

// External host+path prefix to devx container root
const devxHost = process.env.DEVX_HOST || "https://api.databutton.com";
const devxBasePath =
  process.env.DEVX_BASE_PATH || `/_projects/${projectId}/dbtn/${serviceType}`;

// Caddy does: handle_path /ui/* { rewrite * {$DEVX_BASE_PATH}/ui{path}; ... }
// meaning browser hits (host)/{$DEVX_BASE_PATH}/ui/ to reach vite server.
// If UI_BASE_PATH is set, use it as override, otherwise use DEVX_BASE_PATH + ui combination
const APP_BASE_PATH = process.env.UI_BASE_PATH || `${devxBasePath}/ui`;

// API path is the path (not including host) to the user app api server.
// If running in production, use the prod API path,
// otherwise use the dev API path, e.g.:
// /_projects/${projectId}/dbtn/prodx/app
// /_projects/${projectId}/dbtn/devx/app
const API_PATH = process.env.API_PATH || `${devxBasePath}/app`;

// Full urls to reach the user app backend apis at
const API_URL = `${devxHost}${API_PATH}/routes`;
const WS_API_URL = `${devxHost.replace("http", "ws")}${API_PATH}/routes`;

const coalesce = (...args: (string | undefined)[]): string => {
  for (const s of args) {
    if (s) {
      return s;
    }
  }
  throw new Error("All values are falsy.");
};

const APP_TITLE = coalesce(
  process.env.APP_TITLE,
  process.env.DATABUTTON_APPNAME,
  "Databutton",
);

const APP_FAVICON_LIGHT = coalesce(
  process.env.APP_FAVICON_LIGHT,
  process.env.APP_FAVICON_DARK,
  `${APP_BASE_PATH}/light.ico`.replace("//", "/"),
);

const APP_FAVICON_DARK = coalesce(
  process.env.APP_FAVICON_DARK,
  process.env.APP_FAVICON_LIGHT,
  `${APP_BASE_PATH}/dark.ico`.replace("//", "/"),
);

const htmlPlugin = () => {
  return {
    name: "html-transform",
    transformIndexHtml(html: string) {
      let newHtml = html;

      if (APP_TITLE) {
        newHtml = newHtml.replace(
          /<title>(.*?)<\/title>/,
          `<title>${APP_TITLE}</title>`,
        );
      }

      if (APP_FAVICON_LIGHT) {
        newHtml = newHtml.replace(
          /href="(.*?)\/light.ico"/,
          `href="${APP_FAVICON_LIGHT}"`,
        );
      }

      if (APP_FAVICON_DARK) {
        newHtml = newHtml.replace(
          /href="(.*?)\/dark.ico"/,
          `href="${APP_FAVICON_DARK}"`,
        );
      }

      return newHtml;
    },
  };
};

const isFirebaseAuthExtensionEnabled = isExtensionEnabled(
  ExtensionName.FIREBASE_AUTH,
);

const isStackAuthExtensionEnabled = isExtensionEnabled(
  ExtensionName.STACK_AUTH,
);

const authExtensionEnabled =
  isFirebaseAuthExtensionEnabled || isStackAuthExtensionEnabled;

const uiDevServerPlugin = (): Plugin => {
  const openApiSpecHandler = buildOpenApiSpecHandler({
    authExtensionEnabled,
  });

  return {
    name: "vite-server",
    configureServer(server) {
      server.middlewares.use("/api/new-openapi-spec", openApiSpecHandler);
      server.middlewares.use("/api/tsc-diagnostics", handleTryTscCompile);
    },
  };
};

const allDefines: {
  __APP_ID__: string;
  __API_PATH__: string;
  __API_URL__: string;
  __WS_API_URL__: string;
  __APP_BASE_PATH__: string;
  __APP_TITLE__: string;
  __APP_FAVICON_LIGHT__: string;
  __APP_FAVICON_DARK__: string;
  __APP_DEPLOY_USERNAME__: string;
  __APP_DEPLOY_APPNAME__: string;
  __APP_DEPLOY_CUSTOM_DOMAIN__: string;
  __API_HOST__: string;
  __API_PREFIX_PATH__: string;
  __FIREBASE_CONFIG__?: string;
  __STACK_AUTH_CONFIG__?: string;
} = {
  __APP_ID__: JSON.stringify(projectId),
  __API_PATH__: JSON.stringify(API_PATH),
  __API_URL__: JSON.stringify(API_URL),
  __WS_API_URL__: JSON.stringify(WS_API_URL),
  __APP_BASE_PATH__: JSON.stringify(APP_BASE_PATH),
  __APP_TITLE__: JSON.stringify(APP_TITLE),
  __APP_FAVICON_LIGHT__: JSON.stringify(APP_FAVICON_LIGHT),
  __APP_FAVICON_DARK__: JSON.stringify(APP_FAVICON_DARK),
  __APP_DEPLOY_USERNAME__: JSON.stringify(process.env.DATABUTTON_USERNAME),
  __APP_DEPLOY_APPNAME__: JSON.stringify(process.env.DATABUTTON_APPNAME),
  __APP_DEPLOY_CUSTOM_DOMAIN__: JSON.stringify(
    process.env.DATABUTTON_CUSTOM_DOMAIN,
  ),
  __API_HOST__: JSON.stringify(process.env.API_HOST),
  __API_PREFIX_PATH__: JSON.stringify(process.env.API_PREFIX_PATH),
};

if (isFirebaseAuthExtensionEnabled) {
  allDefines.__FIREBASE_CONFIG__ = JSON.stringify(
    JSON.stringify(getExtensionConfig(ExtensionName.FIREBASE_AUTH)),
  );
}

if (isStackAuthExtensionEnabled) {
  allDefines.__STACK_AUTH_CONFIG__ = JSON.stringify(
    JSON.stringify(getExtensionConfig(ExtensionName.STACK_AUTH)),
  );
}

export default defineConfig({
  base: APP_BASE_PATH,
  define: allDefines,
  plugins: [
    react(),
    splitVendorChunkPlugin(),
    tsConfigPaths(),
    htmlPlugin(),
    injectHTML(),
    ...(isDevRun
      ? [
          enableHotReloadTracker && hotReloadTrackerPlugin(),
          uiDevServerPlugin(),
          componentTaggerPlugin(),
        ]
      : []),
  ].filter(Boolean),
  server: {
    port: 5173,
    hmr: {
      overlay: false,
    },
    watch: {
      usePolling: true,
      interval: 200,
      ignored: [
        "**/node_modules/**",
        "**/.git/**",
        "**/dist/**",
        "**/.log/**",
        "**/.cache/**",
        "**/.yarn/**",
      ],
    },
  },
  customLogger: isDevRun
    ? createDatabuttonLogger({
        isLocal: process.env.VITE_LOCAL === "true",
      })
    : undefined,
  // This looks weird but resolution of shadcn components don't work without this double nested resolve.alias.resolve.alias
  resolve: {
    alias: {
      resolve: {
        alias: {
          "@": path.resolve(__dirname, "./src"),
        },
      },
    },
  },
});
