# client-e2e

## Final APIM card smoke test

Checks that both APIM A2A agent-card routes are reachable with both product
subscription keys (`FREE` and `PRO`).

```powershell
python .\client-e2e\final_test_apim_cards.py
```

Required `.env` keys:

- `APIM_SUBSCRIPTION_KEY_FREE`
- `APIM_SUBSCRIPTION_KEY_PRO`
- `APIM_DEMO1_AGENT_CARD_URL`
- `APIM_DEMO2_AGENT_CARD_URL`
