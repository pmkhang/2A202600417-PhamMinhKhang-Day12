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

---

## Task 4: API Gateway và Security

### Bản develop (`04-api-gateway/develop/app.py`)

Cơ chế bảo vệ đơn giản: kiểm tra header `X-API-Key` so với env var `AGENT_API_KEY`.

**Chạy:**
```bash
AGENT_API_KEY=my-secret-key uvicorn app:app --port 8010
```

**Kết quả test develop:**

| Tình huống | Command | HTTP Status | Response |
|---|---|---|---|
| Có API key hợp lệ | `curl -H "X-API-Key: my-secret-key" -X POST .../ask?question=hello` | 200 | `{"question":"hello","answer":"..."}` |
| Không có API key | `curl -X POST .../ask?question=hello` | 401 | `{"detail":"Missing API key..."}` |
| API key sai | `curl -H "X-API-Key: wrong-key" -X POST .../ask?question=hello` | 403 | `{"detail":"Invalid API key."}` |

### Bản production (`04-api-gateway/production/`)

#### Vai trò từng module

| Module | Vai trò |
|---|---|
| `auth.py` | JWT authentication — tạo và verify JWT token. Stateless: không cần DB mỗi request. Hỗ trợ role (user/admin). |
| `rate_limiter.py` | Sliding window rate limiter — giới hạn số request/phút theo user. User: 10 req/min, Admin: 100 req/min. In-memory (production nên dùng Redis). |
| `cost_guard.py` | Budget protection — đếm token đã dùng, tính chi phí, block khi vượt $1/ngày/user hoặc $10/ngày global. |
| `app.py` | Orchestrator — kết hợp tất cả middleware, định nghĩa endpoints, thêm security headers (CORS, X-Frame-Options, v.v.). |

#### Luồng request qua production

```
Request đến /ask
    │
    ▼
[1] JWT Auth (verify_token)
    ├── Không có token → 401
    ├── Token sai/hết hạn → 401/403
    └── OK → extract username, role
    │
    ▼
[2] Rate Limiting (rate_limiter_user / rate_limiter_admin)
    ├── Vượt 10 req/min (user) → 429 Too Many Requests
    └── OK → ghi nhận timestamp
    │
    ▼
[3] Input Validation (Pydantic AskRequest)
    ├── question rỗng hoặc > 1000 ký tự → 422
    └── OK
    │
    ▼
[4] Cost Guard (cost_guard.check_budget)
    ├── Global budget vượt $10/ngày → 503
    ├── User budget vượt $1/ngày → 402
    └── OK (warning log nếu > 80%)
    │
    ▼
[5] Agent Execution (ask())
    └── Gọi LLM, ghi nhận usage
    │
    ▼
[6] Response + record_usage
    └── Trả về answer + usage stats
```

**Kết quả test production:**

| Tình huống | HTTP Status | Ghi chú |
|---|---|---|
| Không có token | 401 | `Authentication required` |
| Token sai | 403 | `Invalid token.` |
| Request hợp lệ | 200 | Trả về answer + usage |
| Spam 10 req liên tiếp | 429 từ req thứ 10 | Rate limit 10 req/min |
| Vượt budget | 402 | `Daily budget exceeded` |

**Test spam (rate limit):**
```
Request 1–9:  HTTP 200
Request 10:   HTTP 429 (Rate limit exceeded, retry_after_seconds: 60)
Request 11:   HTTP 429
```

**Kết luận:** Hệ thống production chặn được unauthorized request (401/403), spam request (429), và vượt budget (402/503).

---

## Task 5: Scaling và Reliability

### Bản develop (`05-scaling-reliability/develop/app.py`)

Các cơ chế reliability cơ bản:

| Cơ chế | Mô tả |
|---|---|
| **Health check** (`/health`) | Liveness probe — platform check agent còn sống không. Trả về status, uptime, version, checks (memory). |
| **Readiness check** (`/ready`) | Readiness probe — agent sẵn sàng nhận request chưa. Trả về 503 khi đang startup hoặc shutdown. |
| **Graceful shutdown** | Lifespan context manager + SIGTERM handler. Chờ in-flight requests hoàn thành (max 30s) trước khi tắt. |
| **Request tracking** | Middleware đếm `_in_flight_requests` để biết có request nào đang xử lý. |

**Kết quả test develop:**
```json
GET /health
{"status":"ok","uptime_seconds":36.9,"version":"1.0.0","environment":"development","timestamp":"2026-04-17T10:06:42.973477+00:00","checks":{"memory":{"status":"ok","note":"psutil not installed"}}}

GET /ready
{"ready":true,"in_flight_requests":1}
```

### Bản production (`05-scaling-reliability/production/app.py`)

Thêm **stateless architecture** với Redis session storage:

| Tính năng | Mô tả |
|---|---|
| **Stateless** | Không lưu state trong memory. Session/conversation history lưu trong Redis. |
| **Session management** | `save_session()`, `load_session()`, `append_to_history()` — tất cả qua Redis. |
| **Multi-instance ready** | Bất kỳ instance nào cũng đọc được session của user. |
| **Fallback** | Nếu không có Redis → dùng in-memory dict (không scale được, chỉ để demo). |

### Kiến trúc scale-out (`docker-compose.yml` + `nginx.conf`)

```
                    ┌─────────────┐
                    │   Nginx     │  (Load Balancer)
                    │  Port 8080  │
                    └──────┬──────┘
                           │ round-robin
           ┌───────────────┼───────────────┐
           │               │               │
      ┌────▼────┐    ┌────▼────┐    ┌────▼────┐
      │ Agent 1 │    │ Agent 2 │    │ Agent 3 │
      │ :8000   │    │ :8000   │    │ :8000   │
      └────┬────┘    └────┬────┘    └────┬────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                    ┌──────▼──────┐
                    │    Redis    │  (Shared State)
                    │   :6379     │
                    └─────────────┘
```

**Vai trò từng component:**

| Component | Vai trò |
|---|---|
| **Nginx** | Load balancer — nhận request từ client, phân phối round-robin đến các agent instance. Retry nếu instance lỗi. |
| **Agent (x3)** | FastAPI app — xử lý request. Đọc/ghi session từ Redis. Mỗi instance có `INSTANCE_ID` riêng. |
| **Redis** | Shared state store — lưu session, conversation history. Tất cả instance đều access cùng Redis. |

**Nginx config highlights:**
- `upstream agent_cluster` — Docker DNS tự resolve "agent" thành nhiều IP (3 instances)
- `proxy_next_upstream error timeout http_503` — retry instance khác nếu lỗi
- `add_header X-Served-By $upstream_addr` — thấy rõ instance nào xử lý request

### Tại sao stateless quan trọng khi scale ngang?

**Vấn đề với stateful:**
```
User A → Request 1 → Instance 1 (lưu session trong memory)
User A → Request 2 → Instance 2 (KHÔNG có session!) → Bug!
```

**Giải pháp stateless:**
```
User A → Request 1 → Instance 1 → lưu session vào Redis
User A → Request 2 → Instance 2 → đọc session từ Redis → OK!
```

**Lợi ích:**
- Scale ngang dễ dàng: thêm/bớt instance không ảnh hưởng user
- Rolling update không mất session: instance cũ tắt, instance mới đọc session từ Redis
- Load balancer có thể route bất kỳ request nào đến bất kỳ instance nào

### Kết quả test stateless

**Test với 1 instance (instance-aaa):**
```
Session: 9b029e6c-dd57-456c-b26e-a6aa9632b4c7

Request 1: [instance-aaa] turn=2
  Q: What is Docker?
  A: Container là cách đóng gói app để chạy ở mọi nơi...

Request 2: [instance-aaa] turn=3
  Q: Why containers?
  A: Agent đang hoạt động tốt! (mock response)...

Request 3: [instance-aaa] turn=4
  Q: What is Redis?
  A: Đây là câu trả lời từ AI agent (mock)...

History messages: 6 (expected 6)
Instances seen: {'instance-aaa'}
✅ Session history preserved!
```

**Kết quả mong đợi với Docker Compose scale=3:**
- `Instances seen: {'instance-aaa', 'instance-bbb', 'instance-ccc'}`
- Mỗi request có thể đến instance khác nhau
- History vẫn đầy đủ 6 messages vì lưu trong Redis

**Kết luận:** Stateless architecture cho phép scale ngang mà không mất session. Redis là single source of truth cho state.
