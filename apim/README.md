# APIM policies for SkylineA2A

This folder keeps the APIM XML policies used in the demo so they are versioned.

## Files

- `policies/demo1-foundry-policy.xml`
  - Backend routing to Foundry A2A runtime.
  - Managed identity auth (`authentication-managed-identity`).
  - Subscription key removed before backend call.

- `policies/demo2-maf-policy.xml`
  - Backend routing to ACA runtime.
  - Subscription key removed before backend call.
  - Agent card response rewrite so APIM URL is advertised (`strategy #2`).

## Apply manually in APIM portal

1. Open API Management -> APIs -> select API.
2. Go to **Inbound processing** / **Outbound processing** policy editor.
3. Paste the corresponding XML and save.

## Notes

- For Demo 1 (Foundry), APIM managed identity must have RBAC on Foundry (at minimum `Azure AI User`).
- For Demo 2 (ACA), no managed-identity auth policy is needed in APIM.
