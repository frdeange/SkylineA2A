# client-e2e

## Final APIM validation test

Validates both APIM-published agents with both product subscription keys (`FREE`
and `PRO`):

- Agent Card reachability and metadata shape
- Runtime JSON-RPC invocation with real responses

```powershell
python .\client-e2e\final_test_apim_cards.py
```

Required `.env` keys:

- `APIM_SUBSCRIPTION_KEY_FREE`
- `APIM_SUBSCRIPTION_KEY_PRO`
- `APIM_DEMO1_AGENT_CARD_URL`
- `APIM_DEMO2_AGENT_CARD_URL`
- `APIM_DEMO1_BASE_URL`
- `APIM_DEMO2_BASE_URL`

> Security note: subscription keys are **not hardcoded** in the script; they are
> read from environment variables only.
