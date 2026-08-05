# Literature Survey（P5 规划）

P5 的 SurveyScribe 将使用版本化 artifact、语义检索和知识图谱组织跨论文综述：

```text
query / paper set
  → retrieve artifacts
  → graph-based grouping/evolution
  → outline with citation IDs
  → section synthesis
  → claim-citation-evidence validation
  → SurveyReport + bibliography
```

当前 P1 只能逐篇生成 `PaperNote`，尚未建立跨论文存储、检索、图关系或综述。
规划中的任何事实声明必须绑定 artifact/evidence；无法绑定的内容要删除或标记
为 synthesis/inference。详见 [P5 实施规划](../P5-IMPLEMENTATION-PLAN.md)。
