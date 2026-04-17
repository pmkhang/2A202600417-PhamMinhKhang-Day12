# MISSION ANSWERS

## Task 1: Localhost vs Production

### 5 Anti-patterns trong `develop/app.py`

1. **Hardcoded secrets** — `OPENAI_API_KEY` và `DATABASE_URL` viết thẳng trong code. Push lên GitHub là lộ key ngay.
2. **Không có config management** — `DEBUG`, `MAX_TOKENS` hardcode, không đọc từ env var, không thể thay đổi giữa các môi trường.
3. **Dùng `print` thay vì logging** — Không có log level, không có structured format, còn in ra cả secret (`OPENAI_API_KEY`).
4. **Không có health check endpoint** — Platform (Railway, Render, K8s) không biết app còn sống hay đã crash để restart.
5. **Port và host cố định** — `host="localhost"` chỉ nhận kết nối nội bộ (không hoạt động trong container), `port=8000` hardcode thay vì đọc từ `PORT` env var mà platform inject.

### Kết quả test develop

```
GET /
{"message":"Hello! Agent is running on my machine :)"}

POST /ask?question=Hello
{"answer":"Đây là câu trả lời từ AI agent (mock). Trong production, đây sẽ là response từ OpenAI/Anthropic."}
```

### Kết quả test production

```
GET /
{"app":"AI Agent","version":"1.0.0","environment":"development","status":"running"}

GET /health
{"status":"ok","uptime_seconds":54.5,"version":"1.0.0","environment":"development","timestamp":"2026-04-17T06:01:02.009205+00:00"}

GET /ready
{"ready":true}

POST /ask (JSON body)
{"question":"Hello, who are you?","answer":"Hello! I'm an AI language model created by OpenAI. I'm here to assist you with information, answer questions, and help with a variety of topics. How can I assist you today?","model":"gpt-4o-mini"}
```

### Bảng so sánh develop vs production

| Tiêu chí | develop/app.py | production/app.py |
|---|---|---|
| Config | Hardcode trong code (`DEBUG = True`, `MAX_TOKENS = 500`) | Đọc từ env var qua `config.py` (dataclass `Settings`) |
| Secrets | Hardcode (`sk-hardcoded-fake-key-never-do-this`) | Đọc từ `OPENAI_API_KEY` env var, không có trong code |
| Port | Cố định `8000`, host `localhost` | Đọc từ `PORT` env var, host `0.0.0.0` |
| Health check | Không có | Có `/health` (liveness) và `/ready` (readiness) |
| Logging | `print()` — in ra cả secret | Structured JSON logging, không log secret |
| Graceful shutdown | Không có | Có `lifespan` context manager + `SIGTERM` handler |

### Kết luận

Code chạy được ở localhost chưa đủ để deploy production vì:

- **Secrets bị lộ**: Hardcode key trong code → push lên repo là mất key.
- **Không scale được**: `host="localhost"` không nhận traffic từ bên ngoài container; port cứng xung đột khi chạy nhiều instance.
- **Platform không quản lý được**: Không có `/health` → platform không biết khi nào cần restart; không có graceful shutdown → request đang xử lý bị cắt đứt khi deploy.
- **Không debug được trên production**: `print()` không có log level, không có timestamp, không parse được bằng log aggregator.
- **Cấu hình không linh hoạt**: Không thể thay đổi behavior giữa dev/staging/prod mà không sửa code.

---

## Task 2: Docker Containerization

### Câu hỏi về `02-docker/develop/Dockerfile`

**Base image là gì?**
`python:3.11` — full Python distribution, khoảng ~1 GB. Có đầy đủ pip, build tools, header files.

**Working directory là gì?**
`/app` — tất cả lệnh tiếp theo (`COPY`, `RUN`, `CMD`) đều chạy trong thư mục này bên trong container.

**Vì sao `requirements.txt` được copy trước source code?**
Docker build theo từng layer và cache lại. Nếu `requirements.txt` không thay đổi, Docker dùng lại layer đã cache → không cần `pip install` lại. Nếu copy source code trước, mỗi lần sửa code sẽ invalidate cache và phải cài lại toàn bộ dependencies.

**`CMD` và `ENTRYPOINT` khác nhau thế nào?**
- `ENTRYPOINT`: lệnh cố định, không bị override khi chạy `docker run`. Dùng khi container có một mục đích duy nhất.
- `CMD`: lệnh mặc định, có thể bị override bằng argument sau `docker run image <override>`. Dùng khi muốn cho phép thay đổi command linh hoạt.
- Kết hợp: `ENTRYPOINT ["python"]` + `CMD ["app.py"]` → `docker run image other.py` sẽ chạy `python other.py`.

### Kích thước image (ước tính, không chạy Docker)

| Image | Base | Kích thước ước tính |
|---|---|---|
| `agent-develop` | `python:3.11` (full) | ~900–1000 MB |
| `agent-production` | `python:3.11-slim` + multi-stage | ~150–200 MB |

### Phân tích Multi-stage build (`02-docker/production/Dockerfile`)

| Stage | Tên | Vai trò |
|---|---|---|
| Stage 1 | `builder` | Dùng `python:3.11-slim` + `gcc`, `libpq-dev` để compile và cài dependencies vào `/root/.local`. Image này không được deploy. |
| Stage 2 | `runtime` | Dùng `python:3.11-slim` sạch, copy chỉ `/root/.local` từ builder. Không có pip, không có build tools → nhỏ và an toàn hơn. Chạy với non-root user `appuser`. |

**Kết quả:** Final image chỉ chứa runtime + packages, không có compiler hay build tools → giảm attack surface và kích thước.

### Các service trong `docker-compose.yml` và cách giao tiếp

| Service | Image | Vai trò | Giao tiếp |
|---|---|---|---|
| `agent` | Build từ Dockerfile (stage `runtime`) | FastAPI AI agent | Nhận request từ Nginx qua internal network |
| `redis` | `redis:7-alpine` | Cache session, rate limiting | Agent kết nối qua `redis://redis:6379/0` |
| `qdrant` | `qdrant/qdrant:v1.9.0` | Vector database cho RAG | Agent kết nối qua `http://qdrant:6333` |
| `nginx` | `nginx:alpine` | Reverse proxy, load balancer | Expose port 80/443 ra ngoài, forward vào `agent` |

Tất cả service dùng chung network `internal` (bridge). Chỉ `nginx` expose port ra host. Agent không expose port trực tiếp → traffic phải đi qua Nginx.

---

## Task 3: Cloud Deployment

### Nền tảng: Render

### Public URL

```
https://ai-agent-rpsm.onrender.com/
```

### Các file cấu hình

- `03-cloud-deployment/render/render.yaml` — Blueprint config
- `03-cloud-deployment/render/app.py` — FastAPI app
- `03-cloud-deployment/render/requirements.txt` — Dependencies
- `03-cloud-deployment/render/utils/mock_llm.py` — Mock LLM

### Biến môi trường đã cấu hình

| Key | Giá trị | Cách set |
|---|---|---|
| `ENVIRONMENT` | `production` | render.yaml |
| `PYTHON_VERSION` | `3.11.0` | render.yaml |
| `OPENAI_API_KEY` | (set thủ công trên dashboard) | Dashboard |
| `AGENT_API_KEY` | (Render tự sinh) | generateValue: true |

### Lệnh test

```bash
# Health check
curl https://ai-agent-rpsm.onrender.com/health

# Ask endpoint
curl -X POST https://ai-agent-rpsm.onrender.com/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "hello"}'
```

### Kết quả deploy thành công

- Service `ai-agent` deploy thành công trên Render (region: Singapore)
- Health check tại `/health` trả về `200 OK`
- Public URL hoạt động: https://ai-agent-rpsm.onrender.com/
