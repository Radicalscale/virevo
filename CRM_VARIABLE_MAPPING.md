# CRM Variable Mapping Guide

## Overview

This document describes how variables flow from call initiation through extraction to CRM lead creation/update.

---

## Variable Sources (Priority Order)

The CRM system pulls variables from 3 sources, in this order:

1. **Active Session Variables** - Extracted during the call via agent's `extract_variables` nodes
2. **Custom Variables** - Passed at call initiation via API
3. **Call Log Variables** - Stored in `call_logs.extracted_variables` after call ends

---

## 1. Variables at Call Initiation

Pass these when triggering a call via the outbound call API:

```json
POST /api/calls/outbound
{
  "agent_id": "your-agent-id",
  "to_number": "+1234567890",
  "custom_variables": {
    "customer_name": "John Doe",
    "email": "john@example.com",
    "lead_id": "existing-lead-id",
    "income_range": "$50k-$75k",
    "company": "Acme Corp",
    "any_custom_field": "any value"
  }
}
```

### Common Pre-Call Variables

| Variable | Description |
|----------|-------------|
| `customer_name` | Lead's name (pre-populated from CRM) |
| `email` | Lead's email address |
| `lead_id` | Existing CRM lead ID to link |
| `company` | Company/employer name |
| `appointment_time` | Scheduled appointment time |

---

## 2. Variables Extracted During Call

Configure these in your agent's call flow using `extract_variables` nodes:

### Name Fields
- `customer_name`
- `name`
- `full_name`
- `first_name`
- `last_name`

### Contact Fields
- `customer_email`
- `email`
- `email_address`
- `phone` (alternate phone)

### Financial Fields
- `income_range`
- `annual_income`
- `income`
- `yearly_income`
- `salary`
- `credit_score`
- `debt_amount`

### Employment Fields
- `employment_status`
- `job_title`
- `occupation`
- `employment`
- `job`
- `years_employed`

### Company Fields
- `company`
- `employer`
- `company_name`
- `business`

### Location Fields
- `address`
- `street_address`
- `city`
- `state`
- `zip`
- `zip_code`
- `postal_code`
- `country`

### Appointment Fields
- `preferred_date`
- `preferred_time`
- `appointment_confirmed`
- `callback_time`

---

## 3. CRM Lead Field Mapping

When a call ends, variables are automatically mapped to CRM lead fields:

| Variable Names (aliases) | CRM Lead Field | Notes |
|-------------------------|----------------|-------|
| `customer_name`, `name`, `full_name`, `first_name` | `name` | First non-null value used |
| `customer_email`, `email`, `email_address` | `email` | |
| `income_range`, `annual_income`, `income`, `salary` | `income_range` | |
| `employment_status`, `job_title`, `occupation` | `employment_status` | |
| `company`, `employer`, `business` | `company` | |
| `address` | `address` | |
| `city` | `city` | |
| `state` | `state` | |
| `zip`, `zip_code`, `postal_code` | `zip_code` | |
| **Everything else** | `custom_fields` | Stored as JSON object |

---

## 4. Example: Agent Extract Variables Configuration

In your agent's call flow, configure an `extract_variables` node like this:

```json
{
  "type": "extract_variable",
  "data": {
    "extract_variables": [
      {
        "name": "customer_name",
        "description": "The customer's full name",
        "extraction_hint": "Listen for when they introduce themselves or say their name"
      },
      {
        "name": "income_range",
        "description": "Annual household income range",
        "extraction_hint": "Look for mentions of salary, income, or earnings"
      },
      {
        "name": "employment_status",
        "description": "Current employment status",
        "extraction_hint": "Are they employed, self-employed, retired, etc."
      }
    ]
  }
}
```

---

## 5. CRM Lead Structure

After a call, the CRM lead will contain:

```json
{
  "id": "uuid",
  "user_id": "owner-user-id",
  "phone": "+1234567890",
  
  // Standard fields (from variable mapping)
  "name": "John Doe",
  "email": "john@example.com",
  "income_range": "$75k-$100k",
  "employment_status": "Full-time employed",
  "company": "Acme Corp",
  "address": "123 Main St",
  "city": "Atlanta",
  "state": "GA",
  "zip_code": "30301",
  
  // Custom fields (anything else extracted)
  "custom_fields": {
    "credit_score": "720",
    "preferred_callback": "afternoon",
    "vehicle_interest": "SUV"
  },
  
  // Auto-populated fields
  "source": "outbound_call",
  "status": "contacted",
  "tags": ["auto_created"],
  "total_calls": 1,
  "last_contact": "2025-12-03T09:30:00Z",
  "last_agent_id": "agent-uuid",
  "last_agent_name": "Sales Agent"
}
```

---

## 6. System Variables (Read-Only)

These are automatically set by the system:

| Variable | Description |
|----------|-------------|
| `to_number` | Called phone number |
| `from_number` | Caller ID used |
| `phone_number` | Alias for to_number |
| `now` | Current date/time when call started |
| `lead_id` | CRM lead ID if linked |

---

## 7. Best Practices

### For Variable Extraction
1. Use clear, specific `extraction_hint` to improve accuracy
2. Mark important variables as `mandatory: true` for re-prompting
3. Use consistent naming across your agents

### For CRM Integration
1. Pass `lead_id` in custom_variables if calling an existing lead
2. Use standard field names for automatic mapping
3. Custom variables go to `custom_fields` - retrieve them from there

### For Debugging
1. Check `call_logs.extracted_variables` to see what was captured
2. Use the debug endpoint: `POST /api/debug/test-post-call-automation/{call_id}`
3. Review backend logs for `📇 CRM:` entries

---

## 8. API Reference

### Trigger Call with Variables
```bash
curl -X POST "https://your-api/api/calls/outbound" \
  -H "Content-Type: application/json" \
  -H "Cookie: your-auth-cookie" \
  -d '{
    "agent_id": "agent-uuid",
    "to_number": "+1234567890",
    "custom_variables": {
      "customer_name": "John Doe",
      "income_range": "$50k-$75k"
    }
  }'
```

### Check Extracted Variables
```bash
# Query MongoDB
db.call_logs.findOne(
  { call_id: "your-call-id" },
  { extracted_variables: 1, custom_variables: 1 }
)
```

### Debug Post-Call Automation
```bash
curl -X POST "https://your-api/api/debug/test-post-call-automation/{call_id}" \
  -H "Cookie: your-auth-cookie"
```

---

## Changelog

- **2025-12-03**: Enhanced CRM variable mapping with multi-source collection and extended field support
- **2025-12-03**: Added session variable persistence to call_logs
- **2025-12-03**: Added support for income_range, employment_status, company, address fields
