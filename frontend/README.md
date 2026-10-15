# Command interface

This is the Command and Field interface for the Kerr County flood scenario, built with React, Vinext and CesiumJS. Command shows priority areas on a 3D terrain map and assigns teams, and Field shows a phone view where teams report observations. The Plan review tab sends a proposed plan to the historical critic service on `http://localhost:8001` and shows its cited objections. Flood extent, teams and reports are mock data; the terrain is real USGS elevation data.

## Run it

Needs Node 22.13+ and pnpm.

```bash
pnpm install
pnpm dev          # http://localhost:3000
```

Checks: `pnpm test`, `pnpm typecheck`, `pnpm build`. For plan review, also start the critic (see `ingestion/README.md`). Full reference: [`docs/frontend.md`](../docs/frontend.md).
