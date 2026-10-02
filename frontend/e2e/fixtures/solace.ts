export const SOLACE_ENABLED_NODE = {
  key: 'solace', name: 'solace', description: '', icon: '', is_core: false, supports_kiosk: false,
  supports_sensitive_lock: false, can_view: true, is_enabled: true, is_hidden: false,
  requires_reauthentication: false, display_order: 0, custom_name: '', custom_icon: '',
}

export function billFixture() {
  const now = new Date().toISOString()
  return {
    id: 1, name: 'Electricity', category: 'utilities', provider: 'PowerCo', amount: '150.00',
    due_at: now, recurrence_rule: 'FREQ=MONTHLY', end_date: null, is_active: true,
    is_autopay: false, include_in_set_aside: true, notes: '', source_node: null,
    is_paid: false, is_overdue: false, next_due_at: now, next_occurrence_id: 1,
    annual_amount: '1800.00', fortnightly_amount: '69.23',
    created_at: now, updated_at: now,
  }
}

// SolaceBootstrap is a large aggregate (bills/paydays/buckets/plan/settings/health/forecast/...)
// consumed across every Solace tab. The Bills tab's `bills` state comes solely from this payload
// (not a separate list fetch), so exercising the Edit-bill sheet needs a shape complete enough
// that nothing downstream crashes on render — a partial/loosely-typed stub isn't enough here,
// unlike most other pages' fixtures in this suite.
export function bootstrapFixture(bills: ReturnType<typeof billFixture>[] = []) {
  const now = new Date().toISOString()
  return {
    bills, paydays: [], purchases: [], buckets: [], checklist: [],
    plan: {
      cycle_start: '2026-08-01', cycle_end: '2026-08-14', income_total: '0.00',
      individual_income_total: '0.00', shared_income_total: '0.00', allocated_total: '0.00',
      remaining: '0.00', sources: [], people: [], buckets: [],
      set_aside: { recurring_bills: '0.00', planned_purchases: '0.00', buffer: '0.00', required_total: '0.00', bills_bucket_total: '0.00', shortfall: '0.00', is_covered: true },
    },
    settings: {
      id: 1, currency_symbol: '$', budget_year: null, cycle_anchor_date: null,
      default_buffer_amount: '0.00', payday_bill_handling: 'new_cycle', show_help_tips: true,
      dashboard_reminders: true, due_soon_days: 7, created_at: now, updated_at: now,
    },
    categories: ['utilities'], balances: [],
    health: { status: 'healthy', issues: [], counts: { active_bills: bills.length, active_paydays: 0, active_buckets: 0, overdue_occurrences: 0 }, percentage_allocation_total: '0', latest_balance: null },
    category_report: { rows: [] }, closeout: { history: [] },
    forecast: { as_of: now, forecast_start: now, through: now, horizon_months: 1, latest_balance: null, opening_balance: null, buffer_amount: '0.00', total_bills: '0.00', total_contributions: '0.00', required_opening_balance: '0.00', timeline: [] },
    checklist_preferences: [],
  }
}

export function nowFixture() {
  return {
    cycle_start: '2026-08-01', cycle_end: '2026-08-14', days_until_cycle_end: 1,
    income_total: '0.00',
    set_aside: null,
    due: [{
      id: 1, bill_id: 1, bill_name: 'Electricity', amount: '150.00',
      due_at: new Date().toISOString(), status: 'due', paid_at: null, skipped_at: null,
      calendar_event_id: null, source_record_type: '', source_record_id: null,
    }],
    due_total: '150.00', overdue_count: 0, overdue_total: '0.00',
    paid_this_cycle_count: 0, paid_this_cycle_total: '0.00',
    bucket_total: '0.00', buckets: [],
  }
}
