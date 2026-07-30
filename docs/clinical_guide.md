# Clinical support guide

Clinical Support is decision support, not diagnosis or prescribing. Every workflow should be reviewed by a qualified health worker and the current national/WHO guidance.

The library is seeded from the source-labelled WHO/local documents in `backend/data/raw_data` and is searchable through `/clinical/guidelines` and `/clinical/drugs`. The interaction checker performs deterministic local checks first and may use Gemini only when configured. BMI and eGFR are estimates; the dose calculator intentionally returns a clinician-review gate instead of inventing a generic dose.

Emergency symptoms should be referred to the nearest emergency service immediately. Do not delay care while using the application.
