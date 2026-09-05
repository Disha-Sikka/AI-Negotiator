# AI Payment Negotiator

An AI agent that negotiates price with a customer **within merchant-set
economic constraints**, then hands the agreed deal to **Razorpay** to
complete the transaction.

Built for the **Razorpay AI Buildathon 2026** --- **Track 01: AI Growth
& Agentic Commerce**.

## The problem

Online pricing is mostly static: one listed price, take it or leave it.

A physical shopkeeper can price more contextually. They may consider
quantity, how long stock has been sitting, current demand, available
margin, and how much flexibility they actually have before agreeing to a
deal.

**AI Payment Negotiator brings that contextual, bounded negotiation to
online checkout, then closes the sale through Razorpay.**

The goal is not to discount every cart. It is to find a deal that can
help convert a hesitant customer while keeping the merchant's minimum
economics protected.

## Architecture

``` text
Customer message ("can you do ₹4500 for the headphones?")
        │
        ▼
┌────────────────────────────┐
│ Local parsing / resolution │   Fast path for straightforward
│                            │   product, quantity, acceptance,
│ cart_builder.py            │   and price messages. Avoids an
│ product_resolver.py        │   LLM call when one is not needed.
└────────────┬───────────────┘
             │
             │ falls through when needed
             ▼
┌────────────────────────────┐
│ Gemini 2.5 Flash           │   Used for natural-language
│                            │   understanding: extracting intent,
│ src/llm_agent.py           │   requested price/discount, items,
│                            │   and quantities from free text.
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│ Negotiation engine         │   Deterministic financial logic.
│                            │
│ negotiation_session.py     │   Handles merchant floors,
│ pricing_engine.py          │   concessions, negotiability,
│ negotiability.py           │   quantity/cart offers, acceptance,
│ cart_engine.py             │   and the 5-round limit.
│ quantity_offer.py          │
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│ FastAPI / Razorpay         │   An order is created only after
│                            │   a deal is accepted. Payment is
│ api.py                     │   completed through Razorpay and
│ /payment/create-order      │   verified on the backend.
│ /payment/verify            │
└────────────┬───────────────┘
             │
             ▼
┌────────────────────────────┐
│ Merchant dashboard         │   Tracks negotiation and payment
│                            │   outcomes for the prototype.
│ /merchant/dashboard        │
└────────────────────────────┘
```

**Why split it this way?**

Language understanding is exactly where an LLM is useful. A customer can
write something like:

``` text
I'll take 5 USB-C cables for ₹3000.
```

and that free-form message can be converted into structured negotiation
intent.

Pricing decisions are different. They need to be **deterministic,
auditable, and bounded by merchant rules**.

So the LLM never decides a price. It only helps extract what the
customer said. **The merchant floor and negotiation decisions are
enforced in code, not in a prompt.**

## How negotiation works

-   **Floor price:** Each product gets a minimum safe price:

    ``` text
    max(
        selling_price × (1 - max_discount_pct),
        cost_price × (1 + min_margin_pct)
    )
    ```

    The more conservative value becomes the merchant floor. The
    negotiation engine never intentionally generates an offer below it.

-   **Negotiability:** Product-level signals such as demand, inventory
    conditions, margin, and related product attributes influence how
    much room the system has to negotiate.

-   **Opening offer:** The engine creates an initial offer between the
    listed price and merchant floor based on the cart's negotiation
    strength.

-   **Concessions:** When the customer makes a safe offer below the
    current AI offer, the engine can move toward the customer while
    clamping the result to the merchant floor.

-   **Round limit:** Price negotiation is capped at **5 rounds**. Once
    the fifth round is reached, the system returns its final offer
    rather than continuing to concede.

-   **Quantity offers:** For eligible single-product carts, the system
    can propose a higher quantity at a better effective price before
    moving deeper into price negotiation.

-   **Cart-level negotiation:** Multi-item carts are evaluated using the
    negotiability and floor constraints of the products in the cart
    rather than treating the entire cart as one unrestricted discount
    pool.

The overall strategy is:

> **Quantity opportunity first → Price negotiation second → Never below
> merchant floor → Explicit acceptance → Payment**

## Quantity offers

For a single-product cart, the agent can first look for an opportunity
to increase quantity instead of immediately giving a deeper discount.

The prototype uses the following tiers:

    Quantity   Discount
  ---------- ----------
           2         5%
           3         7%
           5        10%
          10        12%

Every quantity deal is still checked against the applicable merchant
floor.

For example, with the prototype's **Bluetooth Speaker**:

``` text
1 speaker listed price:       ₹3,000
2 speakers normal total:      ₹6,000
2-speaker quantity deal:      ₹5,700
Customer saving:                ₹300
```

The customer gets a meaningful saving while the merchant gets a larger
cart.

## Merchant protection

Merchant protection is a hard rule in the negotiation engine.

For each product:

``` text
Margin Floor =
Cost Price × (1 + Minimum Margin %)

Discount Floor =
Selling Price × (1 - Maximum Discount %)

Merchant Floor =
max(Margin Floor, Discount Floor)
```

This means a customer can negotiate aggressively, but repeated low
offers cannot force the engine to cross the merchant's configured floor.

For the **Bluetooth Speaker** in the prototype:

``` text
Listed price:      ₹3,000
Merchant floor:    ₹2,400
Initial AI offer:  ~₹2,798
```

An offer such as ₹1,500 is below the floor, so the engine will not
accept it or counter below ₹2,400.

## Negotiation decisions

During a price conversation, the engine returns a small set of explicit
decisions:

  -----------------------------------------------------------------------
  Decision                            Meaning
  ----------------------------------- -----------------------------------
  `ACCEPT`                            The customer's offer is acceptable
                                      and the deal is locked.

  `COUNTER`                           The offer is safe, but the engine
                                      responds with another price.

  `BELOW_FLOOR`                       The customer's offer is below the
                                      merchant's minimum safe price.

  `FINAL_OFFER`                       The negotiation limit has been
                                      reached and the engine holds its
                                      final offer.

  `QUANTITY_ACCEPTED`                 The customer accepts the proposed
                                      quantity deal.
  -----------------------------------------------------------------------

Keeping these outcomes explicit makes the negotiation flow easier to
test and reason about.

## Payment flow

1.  The customer negotiates until the session reaches an accepted state.

2.  The frontend calls:

    ``` text
    POST /payment/create-order
    ```

    The backend refuses to create a payment order unless the negotiation
    session has been accepted.

3.  The accepted negotiated amount is converted to paise and used to
    create a Razorpay order.

4.  The customer completes payment through **Razorpay Checkout**.

5.  The frontend sends the returned payment details to:

    ``` text
    POST /payment/verify
    ```

6.  The backend verifies the Razorpay signature using **HMAC-SHA256**
    and a timing-safe comparison.

7.  After successful verification, the session is treated as paid and
    contributes to the merchant dashboard metrics.

This keeps the negotiated amount tied to backend session state rather
than trusting a price supplied by the browser.

## Merchant dashboard

The prototype includes a merchant-facing dashboard with:

-   **Total negotiations**
-   **Accepted deals**
-   **Paid orders**
-   **Revenue**
-   **Customer savings**
-   **Average discount**

The dashboard is intentionally lightweight and uses the current
in-memory session store.

## Automated testing

The negotiation engine is tested separately from Gemini so that the
financial logic can be validated deterministically.

Run:

``` bash
python judge_simulator.py
```

The current suite contains **60 scenarios across 6 categories**:

  ------------------------------------------------------------------------
  Category                                     Cases Focus
  --------------------- ---------------------------- ---------------------
  Basic negotiation                               10 Initial offers and
                                                     safe counteroffers

  Quantity safety                                 10 Quantity changes and
                                                     floor-safe quantity
                                                     deals

  Cart negotiation                                10 Multi-item
                                                     negotiation behavior

  Floor protection                                10 Repeated below-floor
                                                     pressure

  Round limits                                    10 Five-round
                                                     enforcement and final
                                                     offers

  Edge & consistency                              10 Extreme offers and
                                                     acceptance behavior

  **Total**                                   **60** **End-to-end
                                                     negotiation
                                                     behavior**
  ------------------------------------------------------------------------

Current result:

``` text
FINAL SCORE: 60/60
PASS RATE:   100.0%
STATUS:      READY FOR FINAL DEMO
```

The judge uses the real cart and negotiation logic and records
assertions, transcripts, and post-action session state.

**Gemini is intentionally not called by this suite**, which keeps the
pricing and guardrail tests reproducible.

## Running it

### Backend

``` bash
cd AI-Negotiator-main
pip install -r requirements.txt
```

Create a `.env` file:

``` env
GEMINI_API_KEY=your_key
RAZORPAY_KEY_ID=your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
```

Then start the API:

``` bash
uvicorn api:app --reload
```

The backend runs at:

``` text
http://127.0.0.1:8000
```

FastAPI interactive docs are available at:

``` text
http://127.0.0.1:8000/docs
```

### Frontend

Open another terminal:

``` bash
cd frontend
npm install
npm run dev
```

The Vite frontend normally runs at:

``` text
http://localhost:5173
```

### CLI demo

The raw negotiation flow can also be run without the frontend:

``` bash
python main.py
```

### Automated test suite

``` bash
python judge_simulator.py
```

## Project structure

``` text
AI-Negotiator-main/
│
├── api.py
├── main.py
├── judge_simulator.py
├── judge_cases.json
├── requirements.txt
│
├── data/
│   └── products.csv
│
├── src/
│   ├── cart_builder.py
│   ├── cart_engine.py
│   ├── data_loader.py
│   ├── llm_agent.py
│   ├── negotiation_engine.py
│   ├── negotiation_session.py
│   ├── negotiability.py
│   ├── pricing_engine.py
│   ├── product_resolver.py
│   ├── quantity_offer.py
│   └── simulator.py
│
└── frontend/
    └── src/
        ├── App.jsx
        └── index.css
```

## Tech stack

**Backend:** FastAPI · Python · pandas\
**AI:** Gemini 2.5 Flash (`google-genai`)\
**Payments:** Razorpay Python SDK + Razorpay Checkout\
**Frontend:** React · Vite · JavaScript · CSS\
**Testing:** Custom deterministic negotiation judge

## Known limitations

This is a buildathon prototype, so a few things are intentionally kept
simple:

-   **Sessions are stored in memory.** The current `sessions = {}`
    approach is suitable for a demo and single-process prototype, not a
    production data layer.
-   **The product catalog is static.** Products are loaded from
    `data/products.csv` rather than a live merchant inventory system.
-   **Razorpay is configured for test-mode payments** during development
    and demonstration.
-   **Dashboard metrics are derived from the in-memory sessions**, so
    they reset when the backend restarts.
-   The current catalog and merchant rules are intentionally small
    enough to make negotiation behavior easy to demonstrate and test.

## What this prototype is trying to show

The project is not about attaching a chatbot to a checkout page.

The main idea is the separation between **conversation and commerce
logic**:

-   the customer can speak naturally,
-   Gemini can help interpret the request,
-   deterministic code controls pricing,
-   merchant constraints remain enforceable,
-   quantity offers can create a larger cart,
-   and Razorpay turns an accepted negotiation into a transaction.

> **The AI handles the conversation. The merchant still controls the
> economics.**
