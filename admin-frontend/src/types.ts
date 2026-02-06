// ─── User ───
export interface User {
  id: string
  email: string
  full_name: string | null
  tenant_id: string
  role: string
  status: string | null
  is_superuser?: boolean
}

// ─── Tenant ───
export interface Tenant {
  id: string
  name: string
  plan: string | null
  status: string | null
  created_at: string | null
  updated_at: string | null
}

// ─── Audit ───
export interface AuditLog {
  id: string
  tenant_id: string
  actor_user_id: string | null
  action: string
  resource_type: string | null
  resource_id: string | null
  details: Record<string, unknown> | null
  ip_address: string | null
  created_at: string
}

export interface UsageSummary {
  tenant_id: string
  total_input_tokens: number
  total_output_tokens: number
  total_pinecone_queries: number
  total_embedding_calls: number
  total_cost: number
  total_actions: number
}

export interface UsageByAction {
  action_type: string
  count: number
  total_input_tokens: number
  total_output_tokens: number
  total_cost: number
}

export interface UsageRecord {
  id: string
  tenant_id: string
  user_id: string | null
  action_type: string
  input_tokens: number
  output_tokens: number
  pinecone_queries: number
  embedding_calls: number
  estimated_cost_usd: number
  created_at: string
}
