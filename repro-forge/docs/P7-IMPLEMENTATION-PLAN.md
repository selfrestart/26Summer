# P7 实施规划 — Guardrails, Security, and Governance

> **状态**：`Planned`（规划完成，尚未实现）
>
> **前置条件**：P6 服务边界和 P3 执行边界稳定
>
> **核心输出**：策略引擎、权限控制、安全门、审计与事件响应

## 1. 阶段目标

P7 对完整平台实施纵深防御。它不替代 P3 在执行生成代码前必须具备的最小沙箱，而是在输入、身份、API、Agent、工具、代码、容器、输出、存储和审计各层建立一致策略。

P7 的完整实现位于 P6 之后，但 P7.0 threat model 评审必须在 P6 API/MCP/job
contract 冻结前提前执行。提前评审只产出信任边界和 invariants，不允许把 P7
状态标为 `In Progress/Complete`，也不解除 P6 只能本机受信部署的限制。

## 2. 威胁边界

主要不可信输入：PDF/arXiv 内容、prompt、上传文件、生成代码、依赖包、MCP client/server、API 用户、外部 URL、artifact 和数据库查询。

关键资产：API keys、用户论文、生成代码、实验数据、宿主文件系统、Docker daemon、知识库、审计记录和模型预算。

## 3. Guardrail 层

| 层 | 控制 |
|---|---|
| Identity | authentication、RBAC/ABAC、session/token 生命周期 |
| Input | 文件类型/大小、恶意 PDF、prompt injection、URL/SSRF |
| Agent | system/tool boundary、untrusted content 标记、预算限制 |
| Tool | allowlist、argument validation、side-effect classification |
| Code | secret/license/SAST/dependency scan、人工批准门 |
| Execution | P3 sandbox 加固、network egress、resource、image policy |
| Output | secret/PII、引用完整性、plagiarism、危险内容 |
| Storage | tenant/resource authorization、encryption、retention/deletion |
| Audit | append-only event、actor/action/resource/policy decision |

## 4. 策略模型

```python
PolicyDecision(
    decision="allow|deny|require_approval|redact",
    policy_id="...",
    reasons=[...],
    obligations=[...],
)
```

每个有副作用动作必须先得到 policy decision。高风险操作如联网安装依赖、访问私有仓库、执行用户代码、导出数据需要明确权限或人工批准。

## 5. 代码和供应链安全

- 生成文件路径和 manifest 校验；
- AST/危险 API/命令扫描；
- secret scanner；
- 依赖漏洞和许可证检查；
- 锁文件/hash 和可信 package index；
- Docker image digest、SBOM 和非 root policy；
- 禁止 privileged、host network、Docker socket；
- artifact 签名/哈希验证；
- 修复结果必须重新通过全部安全门。

## 6. Prompt injection 防护

论文文本始终标记为 untrusted data，不能改变 system policy 或授予工具权限。Agent 工具描述明确副作用；retrieved content 与 instructions 分离；高风险工具不由模型单独授权。测试包含论文正文中的“忽略指令、泄漏 key、运行命令”等攻击文本。

## 7. 审计和隐私

审计事件包含 actor、tenant、request/job/run、action、resource、policy decision、timestamp 和 outcome，不记录完整 secret 或不必要正文。定义 retention、用户删除、导出和 incident correlation。审计存储权限独立于普通 artifact。

### 安全例外治理

任何安全门豁免必须记录 owner、风险、适用资源/版本、补偿控制、批准者、创建时间、
到期时间和复审结果。例外默认到期，不能使用永久 wildcard；过期或范围不匹配时
自动回到 deny。critical blocker 只有明确的书面风险接受才能暂时放行，且不能
豁免跨租户访问、secret 泄漏或 privileged/socket/host mount 等硬阻断项。

## 8. 工作包

### P7.0 Threat model 和 security invariants

在 P6 contract 冻结前先做接口预审；P7 开始时再按实际数据流更新威胁模型、
信任边界、资产和不可违反规则。

### P7.1 Identity/authorization

实现认证、资源 ownership、RBAC/ABAC 和 API/MCP/UI 一致授权。

### P7.2 Policy engine/tool ACL

实现 side-effect 分类、allow/deny/approval、budget 和审计。

### P7.3 Input/output guardrails

实现文件/URL/注入/secret/PII/citation/plagiarism 检查。

### P7.4 Code/execution hardening

整合 SAST、dependency、license、SBOM、image 和 sandbox policy。

### P7.5 Security testing

攻击 fixture、权限矩阵、SSRF、path traversal、prompt injection、secret exfiltration 和 container escape regression。

### P7.6 Incident/docs

更新 SECURITY.md、报告/响应流程、密钥轮换、数据删除和部署 hardening guide。

## 9. 安全测试矩阵

| 信任边界 | 必测攻击/失败 | 必须证明 |
|---|---|---|
| Upload/API | polyglot/超大文件、恶意 PDF、path traversal | 拒绝、隔离、审计且不读写越界 |
| URL fetch | localhost、metadata IP、DNS rebinding、redirect | SSRF policy 在每次解析/跳转生效 |
| LLM context | 论文内注入、tool escalation、secret 请求 | untrusted 内容不能改变 policy 或授权 |
| Tool/MCP | 参数混淆、越权 resource、重放、取消竞态 | schema、ownership、idempotency、audit 完整 |
| Sandbox | privileged、host mount、socket、egress、fork bomb | 配置被拒绝或限制实际生效 |
| Supply chain | 恶意包名、未知 index、漏洞/license、镜像漂移 | 锁定、扫描、digest/SBOM 和批准门 |
| Output/log | secret/PII、绝对路径、完整私有正文 | redact 且保留可解释的 policy event |
| Multi-tenant | 横向/纵向资源 ID 篡改 | 所有入口统一 deny，无数据侧信道 |
| Audit | 删除/篡改/缺 actor 或 decision | 普通用户不可修改，关联链完整 |
| Exception | 过期、越范围、无 owner/补偿控制 | 自动 deny，产生审计与告警 |
| Regression | P0–P6 功能与策略组合 | 安全控制不被旁路且核心流程可用 |

## 10. 发布阻断条件

- 任何跨租户读取/写入；
- secret 进入日志、prompt、artifact 或前端；
- 未授权高风险工具执行；
- 容器 privileged/host mount/socket 暴露；
- 可复现 SSRF/path traversal/任意文件写；
- critical/high 依赖漏洞无批准例外；
- security audit event 缺失或可被普通用户修改。

## 11. 准入与里程碑提升

P7 转为 `Ready` 前，P3 sandbox 和 P6 API/MCP/job contract 必须稳定，P7.0
threat model 必须映射到可测试 security invariants。

- **P7-A（可安全停止）**：identity/subject/resource、PolicyDecision、audit event、
  exception schema 和 deny-by-default skeleton；
- **P7-B**：输入/工具/输出/存储 guardrails 与 P3 execution/supply-chain hardening；
- **P7-C（完整阶段）**：攻击回归、审计防篡改、retention/deletion、事件响应和
  受控远程部署验证。

只有 P7-C 通过后才能解除 P6 的本机受信部署限制；单个 guardrail 或扫描器通过
不代表平台安全完成。

## 12. 完成定义

1. 威胁模型覆盖 API/MCP/UI/LLM/storage/execution；
2. 身份和资源授权贯穿所有入口；
3. 工具与执行动作有统一 PolicyDecision；
4. prompt injection、SSRF、path、secret、供应链和容器风险有测试；
5. 审计、例外到期、retention、删除、事件响应文档与测试齐全；
6. 安全扫描进入 CI 和发布门；
7. P0–P6 回归与安全 E2E 全部通过。
