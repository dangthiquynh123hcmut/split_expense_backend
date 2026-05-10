# Quy Trình CI/CD và Triển Khai Backend với Docker

## Tổng Quan Kiến Trúc

Hệ thống sử dụng pipeline CI/CD tự động hoàn toàn thông qua **GitHub Actions**, kết hợp **Docker** để đóng gói ứng dụng và **AWS** làm nền tảng hạ tầng. Mỗi lần developer push code lên nhánh `main`, toàn bộ quy trình từ kiểm thử đến triển khai production được thực thi tự động mà không cần can thiệp thủ công.

```
Developer Push Code
        │
        ▼
┌───────────────────┐
│   GitHub Actions  │
│                   │
│  Job 1: CI        │  ← Lint + Unit Test
│      │            │
│      ▼            │
│  Job 2: Build     │  ← Docker Build + Push to Docker Hub
│      │            │
│      ▼            │
│  Job 3: Deploy    │  ← Canary Deploy → Health Check → Full Rollout
└───────────────────┘
        │
        ▼
┌───────────────────────────────────────┐
│           AWS Infrastructure          │
│                                       │
│  ALB (port 80/443)                    │
│    │                                  │
│    ▼                                  │
│  Auto Scaling Group                   │
│    ├── EC2 Instance 1 (private subnet)│
│    └── EC2 Instance N (private subnet)│
│                                       │
│  RDS PostgreSQL  │  ElastiCache Redis │
└───────────────────────────────────────┘
```

---

## 1. Đóng Gói Ứng Dụng với Docker

### 1.1 Dockerfile – Multi-stage Build

Ứng dụng được đóng gói theo mô hình **multi-stage build** nhằm tách biệt môi trường biên dịch và môi trường chạy, giúp giảm kích thước image cuối cùng:

```
Stage 1 (builder): python:3.11-bookworm
  - Cài đặt build dependencies (gcc, libpq-dev, ...)
  - pip install requirements.txt → /root/.local

Stage 2 (runtime): python:3.11-slim-bookworm
  - Chỉ copy /root/.local từ builder (không cần compiler)
  - Copy source code
  - CMD: daphne (ASGI server) lắng nghe 0.0.0.0:8000
```

**Kết quả:** Image production nhẹ hơn đáng kể so với image build, không chứa các công cụ biên dịch không cần thiết.

### 1.2 Docker Compose Production (`docker-compose.prod.yml`)

Trên EC2, ứng dụng chạy qua Docker Compose với hai service:

| Service | Image | Vai trò |
|---------|-------|---------|
| `django` | `quynhdangq1/split-expense-backend:<tag>` | ASGI server (Daphne), port 8000 |
| `nginx` | `nginx:alpine` | Reverse proxy, port 80/443 |

**Luồng khởi động container Django:**
1. `python manage.py migrate --noinput` — chạy migration database
2. `python manage.py collectstatic --noinput` — thu thập static files
3. `daphne -b 0.0.0.0 -p 8000 split_expense_system.asgi:application` — khởi động ASGI server hỗ trợ WebSocket

**Bí mật được quản lý qua AWS SSM Parameter Store:**
- `.env.prod` — biến môi trường production (DB, Redis, API keys...)
- `firebase.json` — Firebase service account credentials
- Cả hai được fetch tự động khi deploy, mount vào container qua volume

---

## 2. Quy Trình CI/CD với GitHub Actions

Pipeline được định nghĩa trong `.github/workflows/ci-cd.yml`, gồm 3 job tuần tự:

### Job 1: CI – Kiểm Tra Chất Lượng Code

**Trigger:** Mọi push lên `main`/`develop` và Pull Request vào `main`

**Môi trường:** GitHub Actions runner (Ubuntu), spin up các service container:
- PostgreSQL 15 (test database)
- Redis 7 (test cache/channel layer)

**Các bước:**

```
1. Checkout source code
2. Setup Python 3.12 (với pip cache)
3. pip install requirements.txt + requirements-dev.txt
4. ruff check src/          ← Static analysis, style check
5. pytest tests/ -v         ← Chạy toàn bộ unit/integration tests
```

Nếu bất kỳ bước nào fail, pipeline dừng lại và các job tiếp theo không chạy.

### Job 2: Build & Push Docker Image

**Trigger:** Chỉ chạy khi push lên nhánh `main` (không chạy với PR), sau khi Job 1 pass.

**Các bước:**

```
1. Checkout code
2. Setup Docker Buildx (multi-platform build support)
3. Login vào Docker Hub bằng secret credentials
4. Trích xuất metadata:
   - Tag theo git SHA ngắn (vd: a1b2c3d)
   - Tag "latest"
5. docker build + push lên Docker Hub
   - Sử dụng GitHub Actions Cache để tăng tốc build
```

**Image được push lên:** `quynhdangq1/split-expense-backend:<git-sha>`

### Job 3: Deploy to Production

**Trigger:** Sau khi Job 2 pass. Yêu cầu phê duyệt qua GitHub Environments (`production`).

**Xác thực AWS:** Sử dụng **OIDC (OpenID Connect)** — không lưu AWS credentials dài hạn trong GitHub Secrets. GitHub Actions tự động lấy token tạm thời từ AWS IAM Role thông qua trust relationship.

#### 3a. Canary Deploy (Triển khai thử nghiệm)

Chiến lược **Canary Deployment** được áp dụng để giảm rủi ro:

```
1. Lấy danh sách EC2 instances đang InService trong ASG
2. Chọn instance đầu tiên làm "canary"
3. Gửi lệnh deploy lên canary instance qua AWS SSM Run Command:
   - Git pull code mới nhất
   - Fetch secrets từ SSM Parameter Store nếu chưa có
   - docker pull image mới
   - docker compose up --force-recreate (zero-downtime restart)
   - Health check nội bộ
4. Poll kết quả SSM command mỗi 15 giây, tối đa 10 phút
```

**AWS SSM Run Command** được dùng thay vì SSH vì các EC2 instance nằm trong **private subnet** (không có public IP), chỉ accessible qua SSM Agent.

#### 3b. Health Check qua ALB

Sau khi canary deploy thành công, GitHub Actions runner kiểm tra ứng dụng qua **Application Load Balancer** (DNS public):

```
GET http://<alb-dns>/health/ → 200 OK
Retry 15 lần × 20 giây = tối đa 5 phút
```

Endpoint `/health/` trả về `{"status": "ok"}` nếu ứng dụng đang hoạt động.

#### 3c. Full Rollout

Nếu health check pass, deploy đồng thời lên tất cả instances còn lại trong ASG với cùng lệnh SSM.

---

## 3. Hạ Tầng AWS

### Kiến Trúc Mạng

```
Internet
   │
   ▼
Application Load Balancer (public subnet, port 80 → redirect 443, port 443 HTTPS)
   │
   ▼ (Target Group port 8000)
Auto Scaling Group (private subnet)
   ├── EC2 t3.small – Django + Nginx (Docker)
   └── EC2 t3.small – Django + Nginx (Docker)
   │
   ▼
RDS PostgreSQL (default VPC) ──── VPC Peering ──── split-expense-vpc
Redis ElastiCache (hoặc Redis container)
```

### Các Thành Phần Chính

| Thành phần | Dịch vụ AWS | Mô tả |
|------------|-------------|-------|
| Container Registry | Docker Hub | Lưu trữ Docker image |
| Compute | EC2 + Auto Scaling Group | Chạy ứng dụng, tự scale |
| Load Balancing | Application Load Balancer | Phân tải, terminate SSL/TLS |
| Database | RDS PostgreSQL | Cơ sở dữ liệu quan hệ |
| Cache/WebSocket | Redis | Cache và Django Channels |
| Secret Management | SSM Parameter Store | Lưu `.env.prod`, `firebase.json` |
| Remote Execution | SSM Run Command | Chạy lệnh deploy trên private EC2 |
| Authentication | IAM OIDC | Xác thực GitHub Actions với AWS |
| SSL Certificate | ACM (AWS Certificate Manager) | Chứng chỉ TLS cho HTTPS |
| Infrastructure as Code | Terraform | Quản lý toàn bộ hạ tầng |

### Bảo Mật

- **Không có AWS credentials dài hạn** trong GitHub: sử dụng OIDC federation
- **EC2 trong private subnet**: không có public IP, chỉ truy cập qua SSM và ALB
- **Secrets không trong source code**: `.env.prod` và `firebase.json` lưu trong SSM Parameter Store (SecureString, mã hóa bằng KMS)
- **HTTPS bắt buộc**: HTTP listener redirect 301 sang HTTPS, certificate từ ACM
- **VPC Peering**: kết nối mạng riêng giữa EC2 VPC và RDS VPC, không qua public internet

---

## 4. Quy Trình Deploy Tự Động (Tóm Tắt)

```
Developer: git push origin main
                │
                ▼
GitHub Actions khởi chạy pipeline
                │
       ┌────────┴────────┐
       ▼                 │
  [Job 1: CI]            │
  ruff lint ✓            │
  pytest 178 tests ✓     │
       │                 │
       ▼                 │
  [Job 2: Build]         │
  docker build ✓         │
  push to Hub ✓          │
  tag: <git-sha> ✓       │
       │                 │
       ▼                 │
  [Job 3: Deploy]        │
  OIDC → AWS token ✓     │
  SSM → EC2 canary:      │
    git pull ✓           │
    docker pull ✓        │
    migrate ✓            │
    daphne start ✓       │
  ALB health check ✓     │
  SSM → EC2 all ✓        │
       │                 │
       ▼                 └──→ (fail fast, không deploy)
  Production Updated ✓
```

**Thời gian trung bình một lần deploy hoàn chỉnh:** ~5–8 phút

---

## 5. Script Deploy trên EC2 (`scripts/deploy-ec2.sh`)

Script được thực thi trên EC2 instance qua SSM với các bước:

```bash
# 0. Bootstrap: clone repo nếu instance mới chưa có
# 1. git pull: lấy code và config mới nhất
# 2. Fetch .env.prod từ SSM nếu chưa có
# 3. Fetch firebase.json từ SSM nếu chưa có
# 4. docker pull: tải image mới
# 5. docker compose run: chạy migrate + collectstatic
# 6. docker compose up --force-recreate: restart container (zero-downtime)
# 7. Health check: curl localhost:8000/health/ tối đa 20 lần
# 8. Start/reload nginx
# 9. docker image prune: dọn dẹp image cũ
```

Zero-downtime đạt được nhờ `--force-recreate` — Docker dừng container cũ và khởi động container mới với image mới, quá trình này chỉ mất vài giây trong khi ALB có health check grace period.
