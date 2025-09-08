# DeliverEase

A widget and admin app for checking delivery options based on phone number and postal code (Norway), built on Databutton.

- Deployed app: https://kosibox.databutton.app/deliver-ease
- Databutton preview matches this repository export.

## Repository Structure

- `ui/` – React (Vite) frontend, shadcn UI, Tailwind
- `src/` – FastAPI backend (Databutton app), APIs in `src/app/apis`

## Run the UI (local)

```bash
cd ui
npm install
npm run dev
```
The UI uses a generated client (brain) to call the deployed Databutton API, so you can run the frontend locally without running the API.

## Backend (FastAPI) notes
The backend is designed to run inside Databutton and relies on `databutton` SDK for secrets/storage. If you want to run it locally, you'll need to replace or shim `databutton` and provide secrets via your own mechanism. Typical dev command:
```bash
# Python 3.11+
python -m venv .venv && source .venv/bin/activate
pip install -r src/requirements.txt
uvicorn src.main:app --reload --port 8000
```
But note: endpoints expect secrets provided by Databutton (`db.secrets`).

## Secrets (used in backend)
- `API_1881_KEY` – 1881.no lookup
- `NROP_API_KEY`, `NROP_API_PASSWORD` – Instabox/NROP provider
- `GOOGLE_MAPS_API_KEY` – map tiles/static maps
- `FIREBASE_SERVICE_ACCOUNT_JSON` – Firebase admin if used
- `GITHUB_TOKEN` – CI/export helper (not needed by app at runtime)

Configure these in Databutton (Settings → Secrets). For local development you must wire your own secret loading.

## Deployment
- Databutton: Deploy from the workspace UI. The deployed URL above is the source of truth for the API used by the UI.
- GitHub Pages (Standalone Widget): Planned in a separate task to publish a pure JS widget bundle.

## License
Proprietary – © andreasholter