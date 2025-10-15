package aob

default allow = true

# Example: deny if edge requires human and ctx has no approval
deny_no_approval {
  input.edge.policies[_] == "require_human_for_risk_high"
  not input.ctx.bag.approval
}

allow {
  not deny_no_approval
}

