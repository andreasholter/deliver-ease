# React + Vite

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react/README.md) uses [Babel](https://babeljs.io/) for Fast Refresh
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react-swc) uses [SWC](https://swc.rs/) for Fast Refresh

## Generate JS client from example payload

If you want to generate a client for a given project you can get the OpenAPI spec for that project by looking at the web socket traffic with devx

```sh
./test-scripts/generate-js-client/post-api-spec.sh
```

## Linting

For internal development, we use a stricter linting than what the user has to work with. Therefore we have these files:

```txt
tsconfig.json <-- Users tsconfig
tsconfig.strict.json <-- The one we use for linting
tsconfig.node.json <-- Used for vite config and similar
```

For the strict type checking not to fail we need to add the comment `// @ts-nocheck` at the topp of `src/App.tsx`. The user do not need that line as they are not using the strict tsconfig.

For linting as a tool used by the AI agents, we use two biome variants:

```txt
biome.json <-- The one used by default
biome.fix.jsonc <-- The one the agents use for autofixes, fixing as much as possible
biome.check.jsonc <-- The one the agents use for checks, getting only the important rule violations
```
