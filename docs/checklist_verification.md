# Final checklist verification

Run the repository-side checker with the supplied checklist:

```powershell
venv\Scripts\python.exe scripts\verify_checklist.py --checklist C:\path\to\pasted-text.txt
```

The checker proves repository structure, route groups, password recovery storage/routes, required clinical components, and the final GGUF path. It reports the GGUF file separately because the model is intentionally supplied later. Use `--require-model` only after the file has been saved at the configured path.

The following require external evidence and are not fabricated by the checker: Gemini credentials and response quality, SMTP delivery, internet search availability, MIRIAD licensing/download availability, measured model performance on the deployment computer, hallucination-rate testing, and qualified clinical validation/sign-off.

Note: the supplied checklist declares **328** total features, but its unique identifiers enumerate **524** checks (including the 213 frontend, 90 backend, 47 integration, and 15 executive IDs). The checker reports this discrepancy explicitly instead of marking the count as consistent.
