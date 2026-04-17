# DEPLOYMENT

## Nền tảng: Render

## Public URL

```
https://ai-agent-rpsm.onrender.com/
```

## Lệnh test

```bash
# Health check
curl https://ai-agent-rpsm.onrender.com/health

# Root
curl https://ai-agent-rpsm.onrender.com/

# Ask
curl -X POST https://ai-agent-rpsm.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "hello"}'
```

## Biến môi trường đã cấu hình

| Key | Cách set |
|---|---|
| `ENVIRONMENT` | render.yaml (`production`) |
| `PYTHON_VERSION` | render.yaml (`3.11.0`) |
| `OPENAI_API_KEY` | Render Dashboard (manual) |
| `AGENT_API_KEY` | Render tự sinh (`generateValue: true`) |

## File cấu hình deploy

- `03-cloud-deployment/render/render.yaml`
