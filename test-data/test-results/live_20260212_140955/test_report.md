# aihr Live E2E Test Report

**Server**: http://api.172-237-5-254.sslip.io
**Time**: 2026-02-12 14:14:53
**Duration**: 298.4s

## Summary

| Phase | Pass/Total | Score | % | Time |
|-------|-----------|-------|---|------|
| Phase 0 | 5/5 | 5/5 | 100% | 3.1s |
| Phase 1 | 15/15 | 15/15 | 100% | 8.5s |
| Phase 2 | 5/5 | 20/20 | 100% | 35.0s |
| Phase 3 | 3/3 | 12/12 | 100% | 35.0s |
| Phase 4 | 2/2 | 8/8 | 100% | 10.1s |
| Phase 5 | 2/2 | 8/8 | 100% | 29.6s |
| Phase 6 | 4/4 | 4/4 | 100% | 1.6s |
| Phase 7 | 2/2 | 8/8 | 100% | 31.9s |
| Phase 8 | 2/2 | 0/0 | N/A% | 16.9s |

**Total: 80/80 (100.0%) -- EXCELLENT**

## Details

### Phase 0

| Step | Action | Status | Score | Time | Detail |
|------|--------|--------|-------|------|--------|
| 0.1 | Health Check | OK | 1/1 | 580ms |  |
| 0.2 | Superuser Login | OK | 1/1 | 712ms | eyJhbGciOiJIUzI1NiIs... |
| 0.3 | Get Tenant | OK | 1/1 | 298ms | ID=7a77da32-b9b... |
| 0.4 | Create HR User | OK | 1/1 | 619ms | hr-test-1770876596@example.com |
| 0.5 | HR User Login | OK | 1/1 | 863ms |  |

### Phase 1

| Step | Action | Status | Score | Time | Detail |
|------|--------|--------|-------|------|--------|
| 1.1 | Upload hr-policy-test.md | OK | 1/1 | 481ms | ID=fb248a78 |
| 1.2 | Upload 新增文件說明.md | OK | 1/1 | 421ms | ID=c0d5c0b2 |
| 1.3 | Upload 勞動契約書-謝雅玲.pdf | OK | 1/1 | 1075ms | ID=0b92b5b9 |
| 1.4 | Upload 勞動契約書-謝雅玲.txt | OK | 1/1 | 341ms | ID=e99b0d9b |
| 1.5 | Upload 員工名冊.csv | OK | 1/1 | 323ms | ID=a1a3f804 |
| 1.6 | Upload 員工名冊.pdf | OK | 1/1 | 689ms | ID=779b7141 |
| 1.7 | Upload 請假單範本-E012-周秀蘭.pdf | OK | 1/1 | 919ms | ID=44b31049 |
| 1.8 | Upload 請假單範本-E012-周秀蘭.txt | OK | 1/1 | 372ms | ID=74ed1325 |
| 1.9 | Upload 健康檢查報告-E016-高淑珍.pdf | OK | 1/1 | 824ms | ID=6add3082 |
| 1.10 | Upload 健康檢查報告-E016-高淑珍.txt | OK | 1/1 | 367ms | ID=8e4097f2 |
| 1.11 | Upload 員工手冊-第一章-總則.md | OK | 1/1 | 310ms | ID=da82012c |
| 1.12 | Upload 員工手冊-第一章-總則.pdf | OK | 1/1 | 906ms | ID=79550b37 |
| 1.13 | Upload 獎懲管理辦法.md | OK | 1/1 | 288ms | ID=585eee5e |
| 1.14 | Upload 獎懲管理辦法.pdf | OK | 1/1 | 886ms | ID=b2ec8663 |
| 1.15 | Upload README.md | OK | 1/1 | 336ms | ID=de118849 |

### Phase 2

| Step | Action | Status | Score | Time | Detail |
|------|--------|--------|-------|------|--------|
| A1 | Q: 我們公司有交通津貼嗎？補助多少？ | OK | 4/4 | 487ms | hits=3/3 ans=公司提供交通津貼，依通勤距離補貼 500-2,000 元。金額範圍依員工手冊規定辦理，實際補助以距離... |
| A2 | Q: 公司績效考核是一年幾次？ | OK | 4/4 | 340ms | hits=3/3 ans=公司績效考核一年 2 次，分別在 6 月與 12 月各進行一次。此為公司內規規定的考核週期，詳見員工... |
| A3 | Q: 請問公司報帳有時間限制嗎？ | OK | 4/4 | 378ms | hits=1/3 ans=報帳需在費用發生後 30 日內完成，超過 30 日需填寫逾期報帳說明。超過 60 日不予核銷；代墊公... |
| A4 | Q: 新人到職第一天需要準備什麼？ | OK | 4/4 | 15075ms | hits=3/4 ans=根據目前的參考資料，並未明確指出新人到職第一天需要準備的具體事項。建議您諮詢 HR 部門以獲取詳細資... |
| A5 | Q: 公司的加班費怎麼算？ | OK | 4/4 | 18691ms | hits=3/3 ans=根據公司內規，加班費的計算方式如下：

### 加班費計算公式
1. **平日加班**：
   - ... |

### Phase 3

| Step | Action | Status | Score | Time | Detail |
|------|--------|--------|-------|------|--------|
| C1 | Q: 我們公司平日加班給 1.5 倍工資，這樣合法嗎？ | OK | 4/4 | 399ms | hits=2/4 ans=公司平日加班給 1.5 倍，高於法定前 2 小時 1.34 倍，原則合法。但超過 2 小時仍需 1.... |
| C2 | Q: 員工特休沒休完，公司規定逾期視同放棄，這樣可以嗎？ | OK | 4/4 | 17123ms | hits=1/4 ans=根據公司內規，特休假（年假）未休畢可於次年度 3 月底前使用，逾期視同放棄的規定，這樣的做法是違反勞... |
| C3 | Q: 全勤獎金因為員工請生理假被扣掉，合法嗎？ | OK | 4/4 | 17523ms | hits=2/5 ans=根據公司內規，女性員工每月可請 1 天生理假，且全年不扣全勤獎金 3 天。因此，若員工因請生理假而被... |

### Phase 4

| Step | Action | Status | Score | Time | Detail |
|------|--------|--------|-------|------|--------|
| D1 | Q: 公司目前有多少位員工？ | OK | 4/4 | 9678ms | hits=3/3 ans=根據目前的參考資料，並未提供公司目前有多少位員工的具體資訊。建議您諮詢 HR 部門以獲取準確的員工人... |
| D2 | Q: 技術部的平均月薪是多少？ | OK | 4/4 | 397ms | hits=3/3 ans=技術部平均月薪約 70,667 元（共 3 人平均）。計算使用員工名冊中所有該部門月薪欄位，已排除空... |

### Phase 5

| Step | Action | Status | Score | Time | Detail |
|------|--------|--------|-------|------|--------|
| E1 | Q: 如果明天有新人到職，我需要準備哪些流程和文件？ | OK | 4/4 | 15735ms | hits=3/5 ans=根據目前的參考資料，並未提供有關新人到職所需準備的具體流程和文件的詳細資訊。建議您諮詢 HR 部門以... |
| E2 | Q: 請幫我比較正職和約聘人員在福利上有什麼差異？ | OK | 4/4 | 13863ms | hits=4/4 ans=根據目前的參考資料，並未明確列出正職和約聘人員在福利上的具體差異。建議您諮詢 HR 部門以獲取準確的... |

### Phase 6

| Step | Action | Status | Score | Time | Detail |
|------|--------|--------|-------|------|--------|
| 6.1 | List Documents | OK | 1/1 | 567ms | 100 docs |
| 6.2 | Get Document Detail | OK | 1/1 | 373ms |  |
| 6.3 | GET /users/me | OK | 1/1 | 372ms | hr-test-1770876596@example.com |
| 6.4 | GET /audit/ | OK | 1/1 | 312ms |  |

### Phase 7

| Step | Action | Status | Score | Time | Detail |
|------|--------|--------|-------|------|--------|
| F1 | Follow: 承上題，如果這位員工年資未滿一年呢？ | OK | 4/4 | 17338ms | hits=3/3 |
| F2 | Follow: 那他可以申請育嬰假嗎？ | OK | 4/4 | 14571ms | hits=3/3 |

### Phase 8

| Step | Action | Status | Score | Time | Detail |
|------|--------|--------|-------|------|--------|
| 8.1 | Chat Latency (5x avg) | OK | 0/0 | 16576ms | avg=16577ms min=14085ms max=23191ms |
| 8.2 | Health Latency (10x) | OK | 0/0 | 328ms | avg=328ms |
