# Alert Runbook — Day 13 Monitoring & LLMOps

Mỗi alert đều là symptom-based (dựa trên triệu chứng quan sát được của người dùng/SLI),
không dựa trực tiếp vào tên implementation nội bộ. Kênh thông báo là Slack và mỗi alert
đều có `duration` (thời gian duy trì để tránh báo động nhiễu).

## Alert 1 — high_tail_latency

- **Tên:** high_tail_latency
- **Severity:** critical
- **Duration:** 5m
- **Kênh thông báo:** Slack `#day13-alerts`
- **SLI/SLO liên quan:** `primary_slo.fast_successful_requests` (P95 latency <= 3000ms, mục tiêu 99.5%)
- **Điều kiện và thời gian duy trì:** Latency P95 > 3000ms duy trì liên tục 5 phút, hoặc error budget tiêu thụ > 50%.
- **Ảnh hưởng tới người dùng:** Người dùng gặp phản hồi chậm; trải nghiệm QA/summary bị giảm.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở dashboard panel `Latency percentiles and TTFT`, xác định P95/P99 và khoảng thời gian.
  2. Lọc `data/logs.jsonl` theo event `response_sent`, chọn request chậm và lấy `correlation_id`.
  3. Mở trace trong Langfuse có cùng `correlation_id`, so sánh span `retrieve-documents` và `fake-llm-generate`.
- **Mitigation tạm thời:** Nếu span retrieval chậm/treo (ví dụ `rag_slow`), tắt scenario `rag_slow` và/hoặc giới hạn concurrency, chuyển fallback nhanh trong khi điều tra.
- **Owner:** platform-oncall

## Alert 2 — elevated_error_rate

- **Tên:** elevated_error_rate
- **Severity:** warning
- **Duration:** 10m
- **Kênh thông báo:** Slack `#day13-alerts`
- **SLI/SLO liên quan:** `guardrails.error_rate_pct_max` (error rate <= 2%) và `guardrails.retrieval_success_rate_pct_min` (>= 90%)
- **Điều kiện và thời gian duy trì:** Error rate > 2% hoặc retrieval success rate < 90% duy trì liên tục 10 phút.
- **Ảnh hưởng tới người dùng:** Một phần request thất bại; người dùng có thể thấy lỗi.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở dashboard panel `Error rate and retrieval success`, xem error rate, breakdown theo `error_type` và retrieval success rate.
  2. Lọc `data/logs.jsonl` theo event `request_failed`, lấy `correlation_id` của request lỗi.
  3. Mở trace tương ứng và kiểm tra span retrieval/LLM cùng status error và message.
- **Mitigation tạm thời:** Nếu `tool_fail` gây lỗi retrieval (ví dụ timeout), tắt scenario `tool_fail`; nếu LLM lỗi, thêm retry/fallback cache để giảm tác động.
- **Owner:** platform-oncall

## Alert 3 — low_quality_proxy

- **Tên:** low_quality_proxy
- **Severity:** warning
- **Duration:** 15m
- **Kênh thông báo:** Slack `#day13-alerts`
- **SLI/SLO liên quan:** `guardrails.quality_score_avg_min` (quality score trung bình >= 0.75)
- **Điều kiện và thời gian duy trì:** Quality score trung bình < 0.75 duy trì liên tục 15 phút.
- **Ảnh hưởng tới người dùng:** Câu trả lời kém chất lượng so với chuẩn, có thể không khớp context hoặc bị redact quá mức.
- **Ba bước kiểm tra đầu tiên:**
  1. Mở dashboard panel `Quality proxy`, xem giá trị mean và trend.
  2. Lọc `data/logs.jsonl` theo event `response_sent`, lấy vài `correlation_id` có `quality_score` thấp.
  3. Mở trace tương ứng, xem prompt/label/version và `doc_count` xem retrieval có thiếu context không.
- **Mitigation tạm thời:** Đánh giá lại prompt/label (rollback `production` về version hoạt động tốt hơn) hoặc cải thiện retrieval context; nếu do PII bị redact quá mức, điều chỉnh logic scrub.
- **Owner:** platform-oncall
