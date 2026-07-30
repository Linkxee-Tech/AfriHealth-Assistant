"""Compatibility wrapper for the canonical model downloader.

The old script downloaded TinyLlama and stored it under a Llama-3 filename,
which could produce an incompatible or misidentified production model.  Keep
this entry point for existing setup instructions, but delegate to the one
canonical downloader instead.
"""

from scripts.download_models import main


if __name__ == "__main__":
    main()
