Express scaffold for Phase-2 migration (API parity scaffolding)

Quick start:

1. Copy the example env:

```bash
cp backend_express/.env.example backend_express/.env
# edit .env as needed
```

2. Install dependencies:

```bash
cd backend_express
npm install
```

3. Start server:

```bash
npm start
```

This scaffold provides route skeletons that match the Python FastAPI paths and response shapes. Each route currently returns example data or placeholder responses; implement DB logic and business rules incrementally to achieve 1:1 parity.
