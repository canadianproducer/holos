# Security

Holos runs locally. It only goes online to:
- download the speech models from Hugging Face (first launch);
- check for and download updates from GitHub Releases;
- download the optional NVIDIA acceleration pack from PyPI;
- talk to a local Ollama on `127.0.0.1` (smart cleanup).

Updates and the NVIDIA pack are verified against SHA-256 checksums before they are run or unpacked.
Dictated text is not written to the log.

## Supported versions
Only the latest release.

## Reporting a vulnerability
Please do not open a public issue. Report it privately via **Security → Report a vulnerability** in this
repository. You will get a reply within a week.
