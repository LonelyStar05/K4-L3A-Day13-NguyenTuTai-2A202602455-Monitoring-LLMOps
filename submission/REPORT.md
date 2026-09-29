# Báo cáo cá nhân — K4-L3A Day 13 Monitoring & LLMOps

> Mỗi học viên hoàn thiện một file duy nhất này. Khi dẫn evidence, dùng đường dẫn tương đối, ví dụ `evidence/07-trace-waterfall.png`.

## 1. Thông tin học viên

- **Họ và tên:** Nguyen Tu Tai
- **MSSV:** 2A202602455
- **Lớp:** K4-L3A
- **Repository URL:** https://github.com/LonelyStar05/K4-L3A-Day13-NguyenTuTai-2A202602455-Monitoring-LLMOps
- **Commit SHA cuối:** 2132614c9988a9890e7d41e88f8bfe4e85dea496
- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (chạy khi Lab Coach release `config/challenge.json`)
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
| Latency P95 / TTFT P95 | ~151ms / 50ms | 3568ms (request chậm) / 50ms khi bật `rag_slow` | incident practice làm tail latency vượt SLO 3000ms |
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

- **Challenge ID:** `day13-k4-l3a-monitoring-llmops-v1` (đây là practice `--scenario rag_slow`; challenge chính thức sẽ dùng `config/challenge.json` do Lab Coach gửi riêng tại CP3).
- **Khoảng thời gian điều tra:** run lúc 08:06:29–08:06:33 UTC, khi bật incident `rag_slow` (`evidence/12-incident-metric.txt`).
- **Triệu chứng từ metrics:** Basline latency P95 ~151ms; khi `rag_slow` bật, request latency vọt lên 3568ms (vượt SLO 3000ms), TTFT vẫn 50ms → triệu chứng chậm do xử lý trước khi sinh token, không phải token đầu tiên.
- **Log line và correlation ID liên quan:** `evidence/13-incident-log.txt` chứa `correlation_id` `req-127a5cca`, `latency_ms: 3568`.
- **Trace ID và span gây ảnh hưởng:** trace `26200cde04c8a84f0ef579f9439407a1` — span `retrieve-documents` (RETRIEVER) mất 2501ms trong khi `fake-llm-generate` (GENERATION) chỉ 152ms (`evidence/14-incident-trace.png`).
- **Root cause:** scenario `rag_slow` làm `retrieve()` ngủ 2.5s; span retrieval là thủ phạm, không phải LLM.
- **Fix action:** tắt `rag_slow`; với sự cố thật sẽ khoanh vùng vector store, thêm timeout/fallback.
- **Preventive measure:** bám sát tail latency qua SLO `high_tail_latency` (P95 > 3000ms), ăn khớp error budget.

Lưu ý: đây là chuỗi điều tra practice hoàn chỉnh metric → log → trace; chưa chạy challenge chính thức vì `config/challenge.json` chưa được Coach release cho lớp K4-L3A.

## 8. Giải thích và tự đánh giá

- **Một quyết định kỹ thuật quan trọng và lý do:** Đặt `scrub_event` trước file writer/JSON renderer và scrub ngay cả các string trong metadata/trả lời, để không có PII nguyên văn đi vào file log.
- **Một lỗi/blocker đã gặp:** Ban đầu log validator từ chối khi có dòng baseline cũ chưa scrub.
- **Cách tìm nguyên nhân và xử lý:** Xóa/đổi tên `data/logs.jsonl`, khởi động lại API và chạy load test mới trước khi đo lại.
- **Cách hiểu luồng Metrics → Logs → Traces:** Metrics chỉ ra triệu chứng và khoảng thời gian; Logs cho correlation_id của request bất thường; Traces cho span chậm/lỗi; ba lớp cùng khớp mới chốt root cause.
- **Vai trò của prompt version, token/cost, SLO hoặc rollback trong vận hành LLM:** Prompt version giúp truy vết thay đổi chính xác và rollback an toàn về version đang hoạt động; token/cost và SLO dùng để giám sát hiệu suất và chi phí theo ngưỡng thực tế.
- **Điều quan trọng nhất đã học:** Observability ba lớp metrics/logs/traces giúp điều tra đúng nguyên nhân thay vì đoán.
- **Hạn chế hoặc phần chưa hoàn thành, nếu có:** Challenge chính thức chưa chạy vì chưa có `config/challenge.json` từ Lab Coach; phần incident trong report là practice `rag_slow`. Screenshot UI Langfuse nên do chính học viên chụp trực tiếp để hiển thị tên project; các file evidence tôi đã lưu bằng API/script tương đương.

## 9. Checklist trước khi nộp

- [x] Kết quả và evidence thuộc commit SHA cuối.
- [x] Tất cả ảnh/output mở được bằng đường dẫn tương đối.
- [x] Incident evidence nối đúng metric → log → trace.
- [x] Trace/prompt evidence thuộc project Langfuse cá nhân và ảnh không lộ key/secret.
- [x] Repository chạy lại được theo README.
- [x] Không có secret, API key, PII thô hoặc evidence của người khác/lớp khác.
- [ ] URL repo và commit SHA cuối đã được nộp trên LMS/Codelabs.
