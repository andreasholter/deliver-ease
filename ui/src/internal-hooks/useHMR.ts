import { useEffect, useRef } from "react";
import { sendMessageToParent } from "../internal-utils/iframe-utils";

export const useHMR = () => {
  const registered = useRef(false);

  useEffect(() => {
    if (registered.current) {
      return;
    }

    registered.current = true;

    if (!import.meta.hot) {
      return;
    }

    import.meta.hot.on("vite:error", (payload) => {
      sendMessageToParent({ event: "vite-error", payload });
    });

    import.meta.hot.on("vite:beforeUpdate", (payload) => {
      sendMessageToParent({ event: "vite-before-update", payload });
    });

    import.meta.hot.on("vite:afterUpdate", (payload) => {
      sendMessageToParent({ event: "vite-after-update", payload });
    });

    import.meta.hot.on("vite:beforeFullReload", (payload) => {
      sendMessageToParent({ event: "vite-before-full-reload", payload });
    });

    import.meta.hot.on("vite:beforePrune", (payload) => {
      sendMessageToParent({ event: "vite-before-prune", payload });
    });

    import.meta.hot.on("vite:invalidate", (payload) => {
      sendMessageToParent({ event: "vite-invalidate", payload });
    });

    import.meta.hot.on("vite:ws:disconnect", (payload) => {
      sendMessageToParent({ event: "vite-ws-disconnect", payload });
    });

    import.meta.hot.on("vite:ws:connect", (payload) => {
      sendMessageToParent({ event: "vite-ws-connect", payload });
    });
  }, []);
};
