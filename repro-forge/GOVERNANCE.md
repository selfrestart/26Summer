# Governance Model

ReproForge uses a lightweight, merit-based governance model inspired by the
[Apache Software Foundation](https://www.apache.org/foundation/governance/)
and [Python Governance](https://www.python.org/dev/peps/pep-0013/).

---

## Roles

### Users

Anyone using ReproForge. Users contribute by reporting bugs, suggesting
features, and participating in community discussions.

**How to join**: Install and use ReproForge. That's it.

### Contributors

Users who have had at least one pull request accepted.

**Privileges**:
- Name listed in CONTRIBUTORS
- Eligible for Reviewer role

**How to join**: Submit and merge a PR.

### Reviewers

Contributors who consistently provide high-quality code review.

**Privileges**:
- Approve pull requests
- Triage issues (label, assign, close)
- Merge privileges on non-protected branches

**Requirements**: 3+ accepted PRs, active for 1+ months, demonstrated
understanding of the codebase.

**How to join**: Nominated by an existing Maintainer. Approved by majority
vote of Maintainers.

### Maintainers

Trusted long-term contributors who maintain specific subsystems.

**Privileges**:
- Merge PRs on all branches
- Cut releases
- Manage CI/CD
- Nominate new Reviewers and Maintainers

**Requirements**: Reviewer for 2+ months, significant contributions in
at least one subsystem, consistent participation in community calls.

**How to join**: Nominated by an existing Maintainer. Approved by
majority vote of PMC.

### Project Management Committee (PMC)

Sets the strategic direction of the project.

**Privileges**:
- Approve architectural decisions
- Manage project resources and funding
- Vote on Maintainer promotions
- Resolve disputes

**Requirements**: Maintainer for 6+ months, deep understanding of the
full system, active in community leadership.

**How to join**: Nominated by PMC. Approved by 2/3 majority.

---

## Decision Making

### Consensus Default

We operate by [lazy consensus](https://www.apache.org/foundation/glossary.html#LazyConsensus):
a proposal is accepted unless someone objects within 72 hours.

### Voting

When consensus cannot be reached, decisions go to a vote:

| Decision Type | Voters | Threshold |
|--------------|--------|-----------|
| Feature inclusion | Maintainers | Simple majority |
| Architecture change | PMC | 2/3 majority |
| Role promotion | PMC | Simple majority |
| Code of Conduct violation | PMC | 2/3 majority |

### Conflict Resolution

1. Discuss on Discord or GitHub Discussions
2. Escalate to Maintainers
3. Escalate to PMC for final decision

---

## Community Calls

- **Frequency**: Bi-weekly
- **Duration**: 45 minutes
- **Format**: Async agenda in GitHub Discussions, sync discussion on Discord
- **Open to**: Everyone

Agenda items should be posted at least 24 hours before the call.
