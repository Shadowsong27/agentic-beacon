# Examples

This directory contains example configurations for the Agentic Beacon framework.

## Contents

### beacon-configs/

Example `beacon.yaml` configurations for common project setups (Python, TypeScript, etc.).

## Generating a Starter Warehouse

To see what `abc warehouse init` produces, run it yourself:

```bash
abc warehouse init demo-warehouse \
  --org "Your Org" \
  --languages python,typescript \
  --domains data-platform,web-services
```

This materializes the full warehouse structure with placeholder content you can inspect and customize.
