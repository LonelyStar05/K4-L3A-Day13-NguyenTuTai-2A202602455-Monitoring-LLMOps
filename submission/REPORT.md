# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyen Tu Tai
- **MSSV:** 2A202602455
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/LonelyStar05/K4-L3A-Day13-NguyenTuTai-2A202602455-Monitoring-LLMOps
- **Commit SHA cuối:** 2132614c9988a9890e7d41e88f8bfe4e85dea496
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1`
- **Tên project Langfuse cá nhân:** `day13-k4-l3a-2A202602455`

## 2. Evidence index

Điền đúng đường dẫn tới evidence thực tế. Có thể đổi tên hoặc dùng nhiều ảnh nếu cần.

| Evidence | Đường dẫn |
|---|---|
| Pytest cuối | `evidence/01-pytest.txt` |
| Log validator | `evidence/02-log-validator.txt` |
| Dashboard validator | `evidence/03-dashboard-validator.txt` |
| Structured log | `evidence/04-structured-log.txt` |
| PII redaction | `evidence/05-pii-redaction.txt` |
| Trace list | `evidence/06-trace-list.txt` |
| Trace waterfall | `evidence/07-trace-waterfall.png` |
| Trace metadata | `evidence/08-trace-metadata.txt` |
| Prompt versions | `evidence/09-prompt-versions.txt` |
| Prompt rollback | `evidence/10-prompt-rollback.txt` |
| Dashboard runtime | `evidence/11-dashboard-overview.png` |
| Incident metric | `evidence/12-incident-metric.txt` |
| Incident log | `evidence/13-incident-log.txt` |
| Incident trace | `evidence/14-incident-trace.png` |

## 3. Kết quả kỹ thuật

| Nội dung | Baseline | Kết quả cuối | Nhận xét |
|---|---|---|---|
| `validate_logs.py` | chưa đạt (TODO CP1) | 100/100 | đủ correlation ID, enrichment, PII redaction |
| `validate_dashboard.py` | 6/6 (contract có sẵn) | 6/6 | contract giữ nguyên, thêm SLO/alert/runbook |
| `pytest` | 22 pass | 24 pass | thêm test CCCD + credit card |
| Số traces hợp lệ | 0 | 14 | 14 traces tự tạo, đủ 10 theo rubric |
| Số PII leak | >0 (baseline) | 0 | email/phone/CCCD/thẻ đều bị scrub |
| Latency P95 / TTFT P95 | ~151ms / 50ms | 3551ms (challenge `rag_slow`) / 50ms | tail latency vượt ngưỡng challenge 2000ms và SLO 3000ms |
| Retrieval success rate | 100% | 100% (chưa bật `tool_fail`) | — |

## 4. Logging và PII

- **Cách tạo/nhận và truyền correlation ID:** `app/middleware.py` xóa context cũ bằng `clear_contextvars()`, lấy `x-request-id` nếu khớp `req-<8-hex>` còn không thì sinh `req-<8-hex>`, bind vào structlog context và trả lại các header `x-request-id`, `x-response-time-ms`.
- **Các metadata được ghi vào structured log:** `user_id_hash`, `session_id`, `feature`, `model`, `env` được bind trong `app/main.py` trước `request_received`, cộng với `correlation_id` từ middleware.
- **Cách bảo đảm PII được scrub trước khi ghi:** `app/logging_config.py` chèn `scrub_event` trước `JsonlFileProcessor` và JSON renderer nên payload/event được redact trước khi map/serialize.
- **Cách kiểm chứng kết quả:** `validate_logs.py` báo 0 PII leak, 100/100; `evidence/04-structured-log.txt`, `evidence/05-pii-redaction.txt`.

## 5. Tracing và prompt versioning

- **Cách xác nhận traces do chính tôi tạo trong project cá nhân:** Dùng project `day13-k4-l3a-2A202602455` riêng, chạy workload từ repo và đối chiếu `correlation_id` giữa trace metadata và log; evidence `06-trace-list.txt` liệt kê 14 traces do tôi tự tạo.
- **Cấu trúc root/retrieval/generation observations:** `LabAgent.run` là root `agent`; bên trong dùng `start_as_current_observation` cho `retrieve-documents` (loại `retriever`) và `fake-llm-generate` (loại `generation`) với model, prompt, `usage_details` và `cost_details`.
- **Cách nối trace với log:** `correlation_id` được đưa vào `propagate_attributes` metadata của trace khớp với field cùng tên trong `data/logs.jsonl`.
- **Prompt name:** `day13-chat`
- **Version/label baseline:** v1 (`baseline`, `production`)
- **Version/label candidate:** v2 (`candidate`)
- **Trace ID của mỗi version:**
  - candidate v2: `0e0aca6e81a8ede253a3c96334082087` (corr `req-e5a8d5e3`)
  - production v2 sau promote: `312469840e6d4efef3d711f318dcf3da` (corr `req-da624bc7`)
  - production v1 sau rollback: `db8ebe323b51c74199087670a82cbeff` (corr `req-f2076365`)
  - 10 traces baseline v1 production: xem `evidence/06-trace-list.txt` / `evidence/09-prompt-versions.txt`
- **Cách promote và rollback `production`:** `scripts/setup_prompts.py create` tạo v1/v2; `--version 2 promote` chuyển production sang v2; `--version 1 rollback` quay lại v1.

## 6. Dashboard, SLO và alerts

- **Dashboard và sáu panel:** `config/dashboard.yaml` đủ 6 panel latency, traffic, errors, cost, tokens, quality; runtime render từ `data/logs.jsonl` bằng `scripts/render_dashboard.py`.
- **SLO và lý do chọn:** `primary_slo.fast_successful_requests` với mục tiêu 99.5% request có latency <= 3000ms trong 28 ngày.
- **Cách tính error budget:** `100% - 99.5% = 0.5%`; nếu tổng request trong window là N thì cho phép tối đa `0.005 * N` request vi phạm.
- **Ba alert và runbook tương ứng:** `config/alert_rules.yaml` định nghĩa `high_tail_latency`, `elevated_error_rate`, `low_quality_proxy`; `docs/alerts.md` mô tả runbook/kiểm tra/mitigation cho từng alert.

## 7. Điều tra challenge

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (cohort `K4`, seed `1311`, `affected_feature=monitoring`, `latency_threshold_ms=2000`).
- **Khoảng thời gian điều tra:** args challenge chạy lúc 09:48:16–09:48:42 UTC, sau khi `inject_incident.py` bật incident từ `config/challenge.json`.
- **Triệu chứng từ metrics:** `/metrics` sau challenge báo `latency_p50=2652ms`, `latency_p95=3551ms`, `latency_p99=3551ms`, `ttft_p95=50ms`; latency vượt ngưỡng challenge `2000ms` và SLO `3000ms`, trong khi TTFT không đổi → chậm xảy ra trước khi sinh token đầu tiên.
- **Log line và correlation ID liên quan:** `evidence/13-incident-log.txt` chứa `correlation_id` `req-f3870d1e`, `latency_ms: 3551`.
- **Trace ID và span gây ảnh hưởng:** trace `532d51dbc043dc4c661d51c2557a0012` — span `retrieve-documents` (RETRIEVER) mất 2500ms trong khi `fake-llm-generate` (GENERATION) chỉ 151ms (`evidence/14-incident-trace.png`).
- **Root cause:** incident `rag_slow` (từ challenge file) làm `retrieve()` giữ 2.5s → span retrieval là span chậm, không phải LLM.
- **Fix action:** disable incident (`python scripts/inject_incident.py --disable`), khoanh vùng vector store và thêm timeout/fallback cho bước retrieval.
- **Preventive measure:** bám sát tail latency qua SLO `high_tail_latency` (P95 > 3000ms) và error budget, map về `data/logs.jsonl` → trace retrieval trước khi kết luận.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Đặt `scrub_event` trước file writer/JSON renderer và scrub ngay cả các string trong metadata/trả lời, để không có PII nguyên văn đi vào file log.
- **Một lỗi/blocker đã gặp:** Ban đầu log validator từ chối khi có dòng baseline cũ chưa scrub.
- **Cách tìm nguyên nhân và xử lý:** Xóa/đổi tên `data/logs.jsonl`, khởi động lại API và chạy load test mới trước khi đo lại.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics chỉ ra triệu chứng và khoảng thời gian; Logs cho correlation_id của request bất thường; Traces cho span chậm/lỗi; ba lớp cùng khớp mới chốt root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version giúp truy vết thay đổi chính xác và rollback an toàn về version đang hoạt động; token/cost và SLO dùng để giám sát hiệu suất và chi phí theo ngưỡng thực tế.
- **Điều quan trọng nhất đã học:** Observability ba lớp metrics/logs/traces giúp điều tra đúng nguyên nhân thay vì đoán.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Screenshot UI Langfuse nên do chính học viên chụp trực tiếp để hiển thị tên project; các file evidence đã lưu bằng API/script tương đương.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
