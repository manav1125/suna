# VentureVerse Production Activation + Internal Testing

This runbook activates full billing/credits behavior in production mode while preserving internal QA workflows.

## Internal QA in production

You can run this in production mode now and still test safely:

- Create normal user accounts for internal testers.
- Grant targeted QA balances via admin credits (by email).
- Keep trial and referrals enabled to exercise full lifecycle paths.
- Reserve public launch controls (marketing domain, open signup campaigns, staging split) for later.

## 1) Required environment mode

Set both services to non-local mode so billing and credits are enforced:

- Frontend: `NEXT_PUBLIC_ENV_MODE=production`
- Backend: `ENV_MODE=production`

Also ensure standard production billing/env values are set:

- `STRIPE_SECRET_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `SUPABASE_URL`
- `SUPABASE_ANON_KEY`
- `SUPABASE_SERVICE_ROLE_KEY`
- `SUPABASE_WEBHOOK_SECRET`
- `KORTIX_ADMIN_API_KEY`

## 2) Policy choices currently applied

Configured from product decisions:

- Trial enabled
- Credit top-ups enabled for Plus, Pro, and Ultra
- Referral reward kept at current configured value
- Referrals visible in production settings/sidebar

## 3) Critical webhook wiring

### Stripe webhook

- Endpoint: `POST <BACKEND_URL>/v1/billing/webhook`
- Events at minimum:
  - `checkout.session.completed`
  - `invoice.payment_succeeded`
  - `customer.subscription.updated`
  - `customer.subscription.deleted`
- Secret must match `STRIPE_WEBHOOK_SECRET`.

### Supabase user-created webhook

- Endpoint: `POST <BACKEND_URL>/v1/webhooks/user-created`
- Header: `x-webhook-secret: <SUPABASE_WEBHOOK_SECRET>`
- Purpose: initialize account, tier defaults, and onboarding.

## 4) Internal tester workflow (recommended)

Use production app with internal tester users, then manually top up credits.

### 4.1 Grant admin access to your operator user (once)

Run in Supabase SQL editor:

```sql
insert into public.user_roles (user_id, role, granted_by)
select id, 'super_admin', id
from auth.users
where email = '<your-admin-email>'
on conflict (user_id)
do update set role = excluded.role, granted_at = now();
```

### 4.2 Verify your role

Request:

```bash
curl -X GET "<BACKEND_URL>/v1/user-roles" \
  -H "Authorization: Bearer <SUPABASE_USER_JWT>"
```

Expected: `isAdmin: true`.

### 4.3 Grant test credits by email (new admin endpoint)

Request:

```bash
curl -X POST "<BACKEND_URL>/v1/admin/billing/credits/adjust-by-email" \
  -H "Authorization: Bearer <SUPABASE_USER_JWT>" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "tester@example.com",
    "amount": 50,
    "reason": "internal QA top-up",
    "is_expiring": false
  }'
```

Notes:

- Amount is in dollars.
- System conversion is `1 dollar = 100 credits`.
- `amount: 50` grants `5000 credits`.
- Use `is_expiring: false` for stable QA balances.

### 4.5 Optional: tester reset flow

For repeatable QA, you can reset a tester by:

1. cancelling active subscription/trial,
2. applying a fresh non-expiring admin grant,
3. re-running the same scenario (trial, checkout, top-up, referral).

### 4.4 Check tester billing summary

```bash
curl -X GET "<BACKEND_URL>/v1/admin/billing/user/<ACCOUNT_ID>/summary" \
  -H "Authorization: Bearer <SUPABASE_USER_JWT>"
```

## 5) Verification checklist

Run these in order after deploy:

1. Sign up a new user and confirm account initializes.
2. Confirm `/settings` shows Referrals tab in production mode.
3. Start trial from `activate-trial` flow and verify trial state is returned by `/v1/billing/trial/status`.
4. Complete one paid checkout and confirm webhook updates subscription tier.
5. Purchase top-up credits on Plus and Pro users (should now be allowed).
6. Grant manual internal QA credits via `/v1/admin/billing/credits/adjust-by-email`.
7. Verify credit deductions after actual tool usage.

## 6) Staging note

You can keep production active for internal testing now. Before public launch, add a dedicated staging stack with Stripe test mode and parallel webhook endpoints.
