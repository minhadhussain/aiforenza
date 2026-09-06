# **AI Model API Credit Platform — MVP Build Specification**

## **1\. Objective**

Build a simple paid API platform that allows developers and researchers to access multiple AI models through a single **OpenAI-compatible API**.

The platform exists to convert available AI model credits into customer revenue.

The product should NOT attempt to become a full AI infrastructure platform.

The MVP goal is:

> **Sign up → receive $5 free credit → test the API → top up balance → use models through our API.**

Users should be able to use the API with existing developer tools such as:

* Claude Code  
* OpenCode  
* Cline  
* OpenAI-compatible SDKs  
* Python applications  
* JavaScript/TypeScript applications  
* coding agents  
* research scripts  
* other OpenAI-compatible clients

---

# **2\. Core Product**

The platform has two components:

### **Web application**

Used for:

* signup/login  
* viewing balance  
* viewing models  
* creating/revoking API keys  
* adding funds  
* viewing basic usage  
* viewing transactions

### **API**

Used by developers to actually consume models.

Primary endpoint:

POST /v1/chat/completions

The API should follow the OpenAI API format wherever practical so developers can use existing tooling without learning a new API.

---

# **3\. Core User Journey**

Visitor  
   ↓  
Landing page  
   ↓  
Sign up  
   ↓  
Account created  
   ↓  
Automatically receive $5.00 trial credit  
   ↓  
Create API key  
   ↓  
Copy API endpoint  
   ↓  
Configure Claude Code / OpenCode / SDK / application  
   ↓  
Make requests  
   ↓  
$5 balance decreases  
   ↓  
User sees balance getting low  
   ↓  
Add funds  
   ↓  
Stripe Checkout  
   ↓  
Payment succeeds  
   ↓  
Wallet credited  
   ↓  
Continue using API

Keep this journey extremely simple.

---

# **4\. Technology Stack**

## **Frontend**

* Next.js  
* TypeScript  
* Tailwind CSS  
* shadcn/ui

## **Backend**

* Python  
* FastAPI  
* Pydantic

## **Database / Authentication**

* Supabase  
* Supabase Auth  
* Supabase PostgreSQL

## **Model Gateway**

* LiteLLM

Use LiteLLM primarily for provider/model normalization and routing.

Do NOT put core business logic inside LiteLLM.

The application owns:

* users  
* wallets  
* pricing  
* API keys  
* transactions  
* usage  
* payments  
* model availability

## **Payments**

* Stripe  
* Stripe Checkout  
* Stripe Webhooks

Use prepaid top-ups rather than subscriptions.

## **Cache / Rate Limiting**

* Redis

## **Deployment**

Everything application-side must be Dockerized.

Use:

* Docker  
* Docker Compose

Initial containers:

web  
api  
redis  
litellm  
reverse-proxy

Supabase, Stripe, and external model infrastructure remain external services.

## **Reverse Proxy**

Use Caddy or Nginx.

Recommended:

Caddy

because HTTPS configuration should remain simple.

## **Monitoring**

* Sentry

Only implement basic error monitoring initially.

## **Product Analytics**

* PostHog

Track the conversion funnel:

visit  
→ signup  
→ trial usage  
→ API key creation  
→ first API request  
→ trial exhausted  
→ top-up  
→ repeat usage  
---

# **5\. Repository Structure**

Use a simple monorepo:

project/  
│  
├── apps/  
│   ├── web/  
│   │   ├── app/  
│   │   ├── components/  
│   │   ├── lib/  
│   │   └── ...  
│   │  
│   └── api/  
│       ├── app/  
│       │   ├── api/  
│       │   ├── core/  
│       │   ├── models/  
│       │   ├── services/  
│       │   ├── repositories/  
│       │   ├── middleware/  
│       │   └── main.py  
│       ├── tests/  
│       └── ...  
│  
├── packages/  
│   └── shared/  
│  
├── infra/  
│   ├── caddy/  
│   └── docker/  
│  
├── docker-compose.yml  
├── .env.example  
├── README.md  
└── Makefile

Do not introduce unnecessary microservices.

---

# **6\. Database Design**

Use Supabase PostgreSQL.

Money must NEVER be represented as floating-point numbers.

Use integer cents.

For example:

$5.00 \= 500  
$10.00 \= 1000  
$49.99 \= 4999

## **users**

Supabase Auth owns authentication.

Application profile table:

profiles  
\---------  
id  
email  
created\_at  
updated\_at

The `id` should correspond to the Supabase Auth user ID.

---

## **wallets**

wallets  
\-------  
id  
user\_id  
balance\_cents  
currency  
created\_at  
updated\_at

Rules:

* one wallet per user  
* currency initially USD  
* balance cannot become negative  
* all balance changes must have a corresponding transaction

---

## **transactions**

This is the financial ledger.

transactions  
\------------  
id  
user\_id  
wallet\_id  
type  
amount\_cents  
balance\_after\_cents  
reference\_id  
description  
created\_at

Allowed transaction types:

FREE\_TRIAL  
TOPUP  
USAGE  
REFUND  
ADJUSTMENT

Examples:

FREE\_TRIAL \+500  
USAGE \-142  
TOPUP \+5000  
USAGE \-781

Never modify historical financial transactions.

If a correction is necessary, create a new `ADJUSTMENT` transaction.

---

# **7\. API Keys**

Table:

api\_keys  
\--------  
id  
user\_id  
name  
key\_prefix  
key\_hash  
last\_used\_at  
created\_at  
revoked\_at

Never store the full API key in plaintext.

Generate a secure random key.

Example format:

sk\_live\_xxxxxxxxxxxxxxxxx

Only show the full key once when created.

Store only a secure hash.

API authentication:

Authorization: Bearer sk\_live\_xxxxx  
---

# **8\. Models**

Table:

models  
\------  
id  
slug  
display\_name  
provider  
enabled  
input\_price\_per\_million  
output\_price\_per\_million  
cached\_input\_price\_per\_million  
created\_at  
updated\_at

Example:

slug: gpt-5.6-luna  
display\_name: GPT-5.6 Luna  
provider: azure  
enabled: true

Do not hard-code customer pricing throughout the application.

Pricing must be database/config driven.

---

# **9\. Usage Records**

Table:

usage\_records  
\-------------  
id  
user\_id  
api\_key\_id  
model\_id  
request\_id  
input\_tokens  
output\_tokens  
cached\_input\_tokens  
customer\_charge\_cents  
provider\_cost\_reference  
status  
created\_at

The `request_id` should uniquely identify an API request.

This is necessary for debugging and billing reconciliation.

---

# **10\. Top-Ups**

Table:

topups  
\------  
id  
user\_id  
stripe\_checkout\_session\_id  
stripe\_payment\_intent\_id  
amount\_cents  
currency  
status  
created\_at  
completed\_at

Possible statuses:

PENDING  
COMPLETED  
FAILED  
REFUNDED

Stripe should be the source of truth for payment confirmation.

---

# **11\. Initial Free Credit**

Every newly created user receives:

$5.00

This should happen automatically after successful account creation.

Create:

wallet.balance\_cents \= 500

and:

transaction.type \= FREE\_TRIAL  
transaction.amount\_cents \= 500

Do this transactionally.

A user must never receive the $5 twice because of duplicate requests, retries, or webhook duplication.

Use an idempotency mechanism such as:

reference\_id \= signup:{user\_id}

with a uniqueness constraint.

---

# **12\. Wallet Rules**

The wallet is the core financial system.

Never simply do:

balance \-= cost

without transactional protection.

Balance deductions must be atomic.

Conceptually:

BEGIN TRANSACTION

lock wallet

verify balance \>= required amount

deduct balance

create USAGE transaction

create usage record

COMMIT

If the transaction fails, no partial balance deduction should remain.

Prevent:

* negative balances  
* double charges  
* double refunds  
* duplicate Stripe credits  
* race-condition spending

---

# **13\. Customer Pricing**

The customer-facing price is independent from the provider cost.

Example:

Provider economic cost:  
$1.00

Customer charge:  
$0.60

The exact pricing strategy can be configured later.

The system must support:

customer\_input\_price  
customer\_output\_price

per model.

Do not hard-code one global percentage.

---

# **14\. OpenAI-Compatible API**

The API should expose:

/v1/models  
/v1/chat/completions

Additional endpoints can be added later.

## **GET /v1/models**

Return available models in an OpenAI-compatible structure.

Example:

{  
  "object": "list",  
  "data": \[  
    {  
      "id": "gpt-5.6-luna",  
      "object": "model",  
      "owned\_by": "your-platform"  
    }  
  \]  
}

Only expose models where:

enabled \= true  
---

# **15\. Chat Completions**

Endpoint:

POST /v1/chat/completions

Accept standard OpenAI-compatible request fields wherever possible.

At minimum support:

model  
messages  
temperature  
max\_tokens / max\_completion\_tokens  
stream

The initial implementation must support both:

stream \= false

and:

stream \= true

Streaming is important for coding agents.

---

# **16\. API Request Flow**

Every request should follow this flow:

HTTP Request  
     ↓  
Validate API key  
     ↓  
Find user  
     ↓  
Find wallet  
     ↓  
Validate model  
     ↓  
Check balance  
     ↓  
Create internal request ID  
     ↓  
Send request to model provider  
     ↓  
Receive response  
     ↓  
Read token usage  
     ↓  
Calculate customer charge  
     ↓  
Atomically deduct balance  
     ↓  
Record usage  
     ↓  
Return response

For streaming responses, design the implementation so that usage is correctly captured and charged after the provider returns final usage information.

If the provider cannot reliably return usage for a particular streaming configuration, implement a safe fallback rather than silently charging zero.

---

# **17\. Insufficient Balance**

If the user does not have enough balance:

Return an OpenAI-compatible HTTP error response.

Do NOT send the request to the provider.

Example conceptual error:

{  
  "error": {  
    "message": "Insufficient balance. Please add funds to continue.",  
    "type": "insufficient\_balance",  
    "code": "insufficient\_balance"  
  }  
}

HTTP status:

402 Payment Required

The dashboard should clearly show:

> Your balance is too low. Add funds to continue.

---

# **18\. Model Routing**

Initially:

Customer API  
      ↓  
FastAPI  
      ↓  
Model configuration  
      ↓  
LiteLLM  
      ↓  
Azure

The customer should never need to know the underlying Azure deployment name.

For example:

Customer model:  
gpt-5.6-luna

Internal deployment:  
azure-specific-deployment-name

Keep this mapping configurable.

---

# **19\. API Base URL**

Production API:

https://api.YOURDOMAIN.com/v1

Dashboard:

https://YOURDOMAIN.com

Documentation:

https://YOURDOMAIN.com/docs

Do not require developers to use different endpoints for different providers.

The whole point is:

ONE API  
ONE API KEY  
MULTIPLE MODELS  
---

# **20\. Claude Code / OpenCode Compatibility**

The platform should be designed around standard OpenAI-compatible request/response behavior.

Do not build separate integrations initially.

Developers should be able to configure their tools using:

Base URL  
API Key  
Model

Provide copy-paste configuration examples in the documentation.

The API must support streaming correctly because coding agents commonly rely on streaming responses.

---

# **21\. Dashboard**

Keep the dashboard minimal.

## **Home**

Show:

Balance

$427.50

\[ Add Funds \]

Today's Usage  
$18.42

This Month  
$312.40

API Requests  
48,291  
---

## **API Keys**

API Keys

Production  
sk\_live\_••••••••••••

\[ Create Key \]  
\[ Revoke \]

When creating:

Name:  
\[ Claude Code \]

\[ Create API Key \]

Display the full key only once.

---

## **Models**

Show:

Model             Input       Output

GPT-6 Astra       $X          $Y  
GPT-5.6 Sol       $X          $Y  
GPT-5.6 Luna      $X          $Y  
Grok 4.6          $X          $Y  
DeepSeek V4 Pro   $X          $Y  
DeepSeek V4 Flash $X          $Y  
Kimi K2.7 Code    $X          $Y  
GPT-5.4           $X          $Y

Prices should come from the database/configuration.

---

## **Usage**

Basic table:

Date  
Model  
Input tokens  
Output tokens  
Cost  
Status

Do not build advanced analytics initially.

---

## **Transactions**

Show:

Date  
Type  
Amount  
Balance  
Description

Example:

Sep 10  
TOPUP  
\+$100.00  
$427.50

Sep 10  
USAGE  
\-$4.72  
$327.50  
---

# **22\. Stripe Integration**

Use Stripe Checkout for top-ups.

Initial amounts:

$10  
$25  
$50  
$100  
$500  
$1,000

Optionally allow custom amounts later.

Flow:

User clicks Add Funds  
       ↓  
Select amount  
       ↓  
FastAPI creates Stripe Checkout Session  
       ↓  
User pays on Stripe  
       ↓  
Stripe sends webhook  
       ↓  
Backend verifies webhook signature  
       ↓  
Check event has not already been processed  
       ↓  
Create TOPUP transaction  
       ↓  
Increase wallet balance  
       ↓  
Mark topup COMPLETED

Never credit the wallet based only on the frontend redirect.

The Stripe webhook must be the authoritative payment confirmation.

---

# **23\. Stripe Idempotency**

Stripe webhooks can be delivered more than once.

Therefore:

stripe\_event\_id

must be stored and unique.

Before processing an event:

if event already processed:  
    return success

Otherwise process it once.

The same principle applies to all payment operations.

---

# **24\. Authentication**

Use Supabase Auth.

Support initially:

* email/password  
* email verification if enabled

Do not build custom authentication.

Frontend gets the Supabase session.

Backend validates the authenticated user when accessing dashboard APIs.

The model API uses API keys independently of Supabase sessions.

---

# **25\. Security**

Minimum requirements:

* HTTPS everywhere in production  
* API keys hashed at rest  
* Supabase service-role key only on backend  
* Stripe secret only on backend  
* Azure credentials only on backend  
* never expose provider credentials to customers  
* rate-limit API requests  
* validate request sizes  
* restrict model names to enabled models  
* prevent negative balances  
* atomic wallet operations  
* audit financial transactions  
* secure webhook verification  
* CORS configured explicitly  
* no secrets committed to Git

---

# **26\. Redis**

Use Redis initially for:

* API rate limiting  
* short-lived request state  
* optional caching

Do not use Redis as the financial source of truth.

The wallet remains in PostgreSQL.

---

# **27\. Rate Limiting**

Implement basic limits.

Examples:

Per API key:  
requests/minute

Per user:  
requests/minute

Maximum concurrent requests

Exact limits can be configurable.

When rate-limited:

HTTP 429

Return a useful error message.

---

# **28\. Error Handling**

Normalize provider errors into OpenAI-compatible errors where possible.

Examples:

401 → invalid API key  
402 → insufficient balance  
404 → model not found  
429 → rate limited  
500 → internal error  
502/503 → provider unavailable

Do not leak:

* Azure credentials  
* internal deployment names  
* infrastructure details  
* database errors  
* stack traces

to customers.

---

# **29\. Logging**

Every API request should have an internal request ID.

Example:

req\_01KXXXXXXXX

Log:

request\_id  
user\_id  
api\_key\_id  
model  
provider  
latency  
status  
input\_tokens  
output\_tokens  
customer\_cost

Do not log full prompts/responses by default.

Treat user prompts as potentially sensitive.

---

# **30\. Observability**

Sentry should capture:

* API exceptions  
* payment errors  
* provider errors  
* database failures  
* background job failures

PostHog should capture product events such as:

signup\_completed  
trial\_credit\_granted  
api\_key\_created  
first\_api\_request  
first\_model\_used  
trial\_credit\_exhausted  
topup\_started  
topup\_completed

The most important conversion metric is:

Signup → Paid Top-up  
---

# **31\. Landing Page**

Keep the landing page simple.

Primary message:

> **One API. Multiple frontier models.**

Supporting message:

> Build with the models you want through one OpenAI-compatible API.

CTA:

\[ Start with $5 Free \]

Secondary CTA:

\[ View Models \]

Do not over-explain the company.

The target audience already understands AI APIs.

---

# **32\. Pricing Page**

The pricing page should communicate:

Start free

$5 free API credit

Then pay only for what you use.

Add:  
$10  
$25  
$50  
$100  
$500  
$1,000

Show model pricing clearly.

Avoid complicated subscription tiers for MVP.

---

# **33\. Documentation**

Create a simple developer documentation section.

Required pages:

Introduction  
Quickstart  
Authentication  
Models  
Chat Completions  
Streaming  
Claude Code  
OpenCode  
Python  
JavaScript  
Errors  
Usage & Billing

Quickstart should take a developer from:

signup  
→ API key  
→ first request

in a few minutes.

---

# **34\. Example Python**

Documentation should contain a standard OpenAI SDK example:

from openai import OpenAI

client \= OpenAI(  
    api\_key="YOUR\_API\_KEY",  
    base\_url="https://api.YOURDOMAIN.com/v1"  
)

response \= client.chat.completions.create(  
    model="YOUR\_MODEL",  
    messages=\[  
        {  
            "role": "user",  
            "content": "Hello"  
        }  
    \]  
)

print(response.choices\[0\].message.content)  
---

# **35\. Example curl**

curl https://api.YOURDOMAIN.com/v1/chat/completions \\  
  \-H "Authorization: Bearer YOUR\_API\_KEY" \\  
  \-H "Content-Type: application/json" \\  
  \-d '{  
    "model": "YOUR\_MODEL",  
    "messages": \[  
      {  
        "role": "user",  
        "content": "Hello"  
      }  
    \]  
  }'  
---

# **36\. Docker**

Create production Dockerfiles for:

web  
api  
litellm

Example architecture:

docker-compose.yml

services:

  web:  
    build: ./apps/web

  api:  
    build: ./apps/api

  litellm:  
    image: ...

  redis:  
    image: redis

  caddy:  
    image: caddy

Supabase is external.

Stripe is external.

Azure is external.

---

# **37\. Environment Variables**

Create `.env.example`.

Example:

NEXT\_PUBLIC\_SUPABASE\_URL=  
NEXT\_PUBLIC\_SUPABASE\_ANON\_KEY=

SUPABASE\_URL=  
SUPABASE\_SERVICE\_ROLE\_KEY=

DATABASE\_URL=

REDIS\_URL=

STRIPE\_SECRET\_KEY=  
STRIPE\_WEBHOOK\_SECRET=

AZURE\_API\_KEY=  
AZURE\_ENDPOINT=

LITELLM\_MASTER\_KEY=

SENTRY\_DSN=  
POSTHOG\_KEY=  
POSTHOG\_HOST=

Never commit `.env`.

---

# **38\. Testing**

Before launch, automated tests must cover:

### **Authentication**

* signup  
* login  
* logout  
* unauthorized access

### **Trial**

* exactly $5 granted  
* trial cannot be granted twice

### **API keys**

* create  
* authenticate  
* revoke  
* revoked key cannot call API

### **Wallet**

* sufficient balance  
* insufficient balance  
* exact balance  
* balance reaches zero  
* concurrent requests  
* no negative balance

### **Usage**

* token usage captured  
* customer cost calculated correctly  
* transaction created  
* usage record created

### **Stripe**

* successful payment  
* failed payment  
* duplicate webhook  
* invalid webhook  
* refund handling

### **API**

* valid model  
* invalid model  
* streaming  
* non-streaming  
* provider error  
* rate limiting

---

# **39\. Critical Financial Invariants**

The following must always be true:

### **Invariant 1**

Wallet balance equals the sum of its immutable transactions.

Conceptually:

initial credits  
\+ topups  
\+ refunds  
\+ adjustments  
\- usage  
\= current balance

### **Invariant 2**

No wallet can become negative.

### **Invariant 3**

Every paid Stripe top-up creates exactly one corresponding wallet credit.

### **Invariant 4**

Every billable API request produces exactly one usage charge.

### **Invariant 5**

Retrying a request internally must not accidentally charge the customer twice.

### **Invariant 6**

Retrying a Stripe webhook must not credit the customer twice.

These are more important than visual polish.

---

# **40\. Initial Models**

Start with a small curated model list.

Use the available model inventory and enable only the models that are ready for production.

Initial target:

GPT-6 Astra  
GPT-5.6 Sol  
GPT-5.6 Luna  
Grok 4.6  
DeepSeek V4 Pro  
DeepSeek V4 Flash  
Kimi K2.7 Code  
GPT-5.4

The system must allow additional models to be enabled without deploying new frontend code.

Models should be configuration/database driven.

---

# **41\. Admin Capability**

A minimal internal admin interface is required.

Admin should be able to:

View users  
View wallets  
View transactions  
View usage  
Enable/disable models  
Change model pricing  
View top-ups  
View basic revenue  
View basic credit consumption

Do not build a large admin platform.

A basic protected admin dashboard is sufficient.

---

# **42\. Internal Business Metrics**

The dashboard should eventually show:

Customer revenue  
Model consumption  
Trial credits given  
Paid credits purchased  
Active customers  
Number of API requests  
Average customer spend

Most importantly:

Cash collected

and:

Model credit consumed

The business experiment is fundamentally measuring how effectively expiring model credits are converted into cash.

---

# **43\. MVP Success Criteria**

The MVP is complete when a new developer can:

1\. Visit website  
2\. Sign up  
3\. Automatically receive $5  
4\. Create API key  
5\. Copy API endpoint  
6\. Make an API request  
7\. Receive a model response  
8\. See their balance decrease  
9\. Add money through Stripe  
10\. See the new balance  
11\. Continue making API requests  
12\. View their usage

An administrator must be able to:

1\. See customers  
2\. See revenue  
3\. See model usage  
4\. See wallet balances  
5\. Configure models  
6\. Configure pricing  
---

# **44\. Explicitly Out of Scope**

Do NOT build these for the MVP:

* AI agents  
* prompt marketplace  
* model fine-tuning  
* vector database  
* RAG  
* model benchmarking platform  
* workflow builder  
* team collaboration  
* enterprise SSO  
* complex organizations  
* custom SDKs  
* mobile application  
* native desktop application  
* advanced analytics  
* advanced observability  
* custom model training  
* Kubernetes  
* Kafka  
* complex microservices  
* multi-region infrastructure  
* sophisticated routing algorithms

If a feature does not directly help:

signup  
→ API usage  
→ top-up  
→ continued API usage

it should probably not be built now.

---

# **45\. Development Order**

Build in this order.

## **Phase 1 — Foundation**

Repository  
Docker  
Next.js  
FastAPI  
Supabase  
Redis  
environment configuration

## **Phase 2 — Authentication**

Supabase Auth  
profiles  
protected dashboard

## **Phase 3 — Wallet**

wallets  
transactions  
$5 trial  
atomic balance operations

## **Phase 4 — API Keys**

create key  
hash key  
authenticate key  
revoke key

## **Phase 5 — Model API**

/v1/models  
/v1/chat/completions  
LiteLLM  
Azure  
model mapping  
streaming

## **Phase 6 — Usage Billing**

token accounting  
customer pricing  
usage records  
wallet deduction

## **Phase 7 — Stripe**

top-up UI  
Checkout  
webhook  
wallet credit  
idempotency

## **Phase 8 — Dashboard**

balance  
usage  
transactions  
models  
API keys

## **Phase 9 — Documentation**

Quickstart  
API docs  
Claude Code  
OpenCode  
SDK examples

## **Phase 10 — Production**

Docker production build  
Caddy  
HTTPS  
Sentry  
PostHog  
rate limiting  
backups  
security review  
load testing  
---

# **46\. Launch Requirement**

Before accepting real customer money, verify that the specific Azure account, credits, sponsorship/program terms, model access terms, and applicable Microsoft licensing terms permit the intended commercial/customer-facing use.

Do not assume that possession of Azure credits automatically grants the right to resell raw model inference.

The application architecture should remain flexible enough to support compliant provider/customer arrangements.

---

# **47\. Product Philosophy**

The implementation must follow one principle:

> **Build the smallest possible machine that converts customer demand into API usage and API usage into cash.**

The customer does not need:

50 features

They need:

API key  
\+  
good models  
\+  
simple pricing  
\+  
reliable endpoint  
\+  
easy top-up

The company does not need:

complex infrastructure

It needs:

customers  
→ deposits  
→ model usage  
→ revenue

Do not over-engineer the MVP.

The first objective is not to build a massive AI platform.

The first objective is to prove that people will put their own money into the platform and consume the available model capacity.

**Ship the API, give every new user $5, enable top-ups, and measure how much real cash the platform can generate.**

