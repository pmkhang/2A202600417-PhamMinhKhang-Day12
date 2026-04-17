# Day 12 Tasks

## Mục tiêu chung

Xây dựng và triển khai một AI agent từ bản chạy localhost thành dịch vụ production-ready trên cloud, có bảo mật, khả năng scale và độ tin cậy cơ bản.

## Task 1: Localhost vs Production

- Đọc `01-localhost-vs-production/develop/app.py`.
- Tìm tối thiểu 5 anti-pattern trong bản develop.
- Chạy bản develop và test endpoint `/ask`.
- Đọc và chạy bản `01-localhost-vs-production/production`.
- So sánh `develop/app.py` và `production/app.py`.
- Hoàn thành bảng so sánh:
  - Config
  - Secrets
  - Port
  - Health check
  - Logging
  - Graceful shutdown
- Kết luận vì sao code chạy ở localhost chưa đủ để deploy production.

## Task 2: Docker Containerization

- Đọc `02-docker/develop/Dockerfile`.
- Trả lời các câu hỏi:
  - Base image là gì?
  - Working directory là gì?
  - Vì sao `requirements.txt` được copy trước source code?
  - `CMD` và `ENTRYPOINT` khác nhau thế nào?
- Build image của bản develop.
- Chạy container và test endpoint `/health` hoặc `/ask`.
- Đo kích thước image develop.
- Đọc `02-docker/production/Dockerfile`.
- Xác định vai trò của từng stage trong multi-stage build.
- Build image production và so sánh kích thước với bản develop.
- Đọc `02-docker/production/docker-compose.yml`.
- Xác định các service trong stack và cách chúng giao tiếp với nhau.
- Chạy toàn bộ stack bằng Docker Compose và test qua Nginx.

## Task 3: Cloud Deployment

- Đọc thư mục `03-cloud-deployment`.
- Chọn một nền tảng để deploy:
  - Railway
  - Render
  - Cloud Run
- Nếu dùng Railway:
  - Đọc `03-cloud-deployment/railway/app.py`
  - Đọc `03-cloud-deployment/railway/railway.toml`
  - Thiết lập biến môi trường cần thiết
  - Deploy và lấy public URL
- Nếu dùng Render:
  - Đọc `03-cloud-deployment/render/render.yaml`
  - Push code lên GitHub
  - Tạo service từ `render.yaml`
  - Thiết lập secrets và deploy
- Nếu dùng Cloud Run:
  - Đọc `03-cloud-deployment/production-cloud-run/cloudbuild.yaml`
  - Đọc `03-cloud-deployment/production-cloud-run/service.yaml`
  - Cấu hình build/deploy pipeline
- Sau khi deploy, test public URL với health check.
- Chụp lại bằng chứng deploy thành công.

## Task 4: API Gateway và Security

- Đọc `04-api-gateway/develop/app.py`.
- Chạy bản develop với `AGENT_API_KEY`.
- Test các tình huống:
  - Có API key hợp lệ
  - Không có API key
  - API key sai
- Đọc bản production trong `04-api-gateway/production`.
- Tìm hiểu vai trò của:
  - `auth.py`
  - `rate_limiter.py`
  - `cost_guard.py`
  - `app.py`
- Mô tả luồng request:
  - Auth
  - Rate limiting
  - Validation
  - Cost guard
  - Agent execution
- Kiểm tra hệ thống có chặn được:
  - Unauthorized request
  - Spam request
  - Vượt budget

## Task 5: Scaling và Reliability

- Đọc `05-scaling-reliability/develop/app.py`.
- Xác định các cơ chế reliability cơ bản đã có.
- Đọc `05-scaling-reliability/production/app.py`.
- Đọc `05-scaling-reliability/production/docker-compose.yml`.
- Đọc `05-scaling-reliability/production/nginx.conf`.
- Hiểu kiến trúc scale-out:
  - Nginx load balancer
  - Nhiều app instance
  - Redis cho state dùng chung
- Giải thích tại sao stateless quan trọng khi scale ngang.
- Chạy test liên quan đến stateless/reliability nếu có.
- Đọc `05-scaling-reliability/production/test_stateless.py` và ghi lại kết quả mong đợi.

## Task 6: Final Project

- Hoàn thiện project trong `06-lab-complete`.
- Đọc `06-lab-complete/app/main.py` và `06-lab-complete/app/config.py`.
- Đảm bảo project cuối có đủ các tính năng:
  - Config từ environment variables
  - Structured logging
  - API key authentication
  - Rate limiting
  - Cost guard
  - Health check `/health`
  - Readiness check `/ready`
  - Graceful shutdown
  - Dockerfile multi-stage
  - `docker-compose.yml`
  - File deploy cloud (`railway.toml` hoặc `render.yaml`)
- Chạy `06-lab-complete/check_production_ready.py`.
- Sửa các mục còn thiếu cho đến khi project sẵn sàng deploy.

## Deliverables cần nộp

- `MISSION_ANSWERS.md`
  - Trả lời toàn bộ câu hỏi và bài tập trong lab
  - Ghi kết quả test, so sánh, nhận xét
- `DEPLOYMENT.md`
  - Public URL
  - Nền tảng deploy
  - Lệnh test
  - Các biến môi trường đã cấu hình
  - Screenshot minh chứng
- Source code hoàn chỉnh của project cuối
  - `app/`
  - `Dockerfile`
  - `docker-compose.yml`
  - `.env.example`
  - `requirements.txt`
  - File cấu hình deploy
  - `README.md`

## Checklist hoàn thành

- [ ] Hoàn thành Part 1 và ghi lại anti-patterns
- [ ] Hoàn thành Part 2 và so sánh image size
- [ ] Hoàn thành Part 3 và có public URL hoạt động
- [ ] Hoàn thành Part 4 và test security thành công
- [ ] Hoàn thành Part 5 và giải thích được stateless scaling
- [ ] Hoàn thành Part 6 production-ready agent
- [ ] Có `MISSION_ANSWERS.md`
- [ ] Có `DEPLOYMENT.md`
- [ ] Không commit `.env`
- [ ] Không có hardcoded secrets
- [ ] Public deployment chạy được

## Gợi ý thứ tự làm

1. Làm lần lượt từ `01` đến `05` để hiểu từng concept.
2. Sau đó dùng `06-lab-complete` làm bản tích hợp cuối.
3. Viết `MISSION_ANSWERS.md` song song trong lúc làm để tránh quên kết quả.
4. Deploy sớm một bản đơn giản trước, rồi mới nâng cấp bảo mật và reliability.
