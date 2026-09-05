::: {align="center"}

🤝 AI Payment Negotiator

Turn checkout into a conversation without giving up control of merchant margins.

Razorpay AI Buildathon 2026 · AI Growth & Agentic Commerce

<br>{=html}

An AI-powered checkout layer that lets customers negotiate a better
deal while keeping every offer inside merchant-defined pricing
constraints.
:::

✨ What is AI Payment Negotiator?

Online stores usually handle pricing in one of two ways: show the
listed price or apply a fixed discount.

That leaves very little room between "I'll buy this" and "this is a
little too expensive, so I'll leave."

AI Payment Negotiator explores that space by turning checkout into a
controlled conversation.

A customer can ask for a better deal, receive a quantity-based
offer, negotiate the price, accept the final deal, and complete the
payment through Razorpay.

The key idea

The AI handles the conversation. The merchant controls the
economics.

Gemini can help understand what the customer is asking for, but it does
not decide how low the price can go. Every offer is checked against
deterministic rules for minimum margins, maximum discounts, and
merchant price floors.

🎯 The Problem

Static discounts treat very different customers in exactly the same way.

A merchant may give the same 10% discount to:

someone who would have purchased at full price, and

someone who genuinely needed a small incentive to complete the
purchase.

Meanwhile, a customer who likes the product but is uncomfortable with
the current price may simply abandon the cart.

This project started with one question:

Can checkout become a negotiation while still protecting the merchant's economics?

Instead of giving every shopper the same discount, the system creates a
bounded negotiation around the transaction.

💡 The Approach

The strategy is intentionally simple:

Quantity upsell first → Price negotiation second → Never below
merchant floor → Explicit acceptance → Razorpay payment

Add to Cart
     ↓
Start Negotiation
     ↓
Check Quantity Opportunity
     ↓
Quantity Deal Available?
   ↙               ↘
 Yes                No
  ↓                  ↓
Offer More       Price Negotiation
for Less/Unit         ↓
   ↓             Counter / Accept
Accept or Reject      ↓
   ↘                  ↙
      Deal Accepted
           ↓
     Razorpay Payment
           ↓
   Merchant Dashboard

The system first tries to create value instead of immediately reducing
the price. For a single-product cart, it checks whether buying a larger
quantity can unlock a useful discount.

If the customer does not want the quantity deal, normal price
negotiation continues.

Price negotiation is capped at 5 rounds, preventing endless
bargaining.

🏗️ System Architecture

The architecture deliberately separates language understanding,
financial decision-making, and payment execution.

                              CUSTOMER
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │      React Frontend     │
                    │                         │
                    │  • Product Catalog      │
                    │  • Shopping Cart        │
                    │  • Negotiation Chat     │
                    │  • Payment Experience   │
                    │  • Merchant Dashboard   │
                    └────────────┬────────────┘
                                 │
                              REST API
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │      FastAPI Backend    │
                    │          api.py         │
                    └────────────┬────────────┘
                                 │
                  ┌──────────────┴───────────────┐
                  │                              │
                  ▼                              ▼
       ┌─────────────────────┐        ┌─────────────────────┐
       │ Request Understanding│        │ Product Resolution  │
       │                     │        │                     │
       │ Local Parser        │        │ product_resolver.py │
       │       ↓             │        │ cart_builder.py     │
       │ Gemini Fallback     │        │ data_loader.py      │
       └──────────┬──────────┘        └──────────┬──────────┘
                  │                              │
                  └──────────────┬───────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │   Negotiation Session   │
                    │                         │
                    │  • Current Offer        │
                    │  • Negotiation History  │
                    │  • Round Tracking       │
                    │  • Acceptance State     │
                    │  • Maximum 5 Rounds     │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │ Pricing Engine  │ │ Negotiability   │ │ Quantity Offer  │
    │                 │ │ Engine          │ │ Engine          │
    │ Merchant Floor  │ │ Product Signals │ │ Quantity Tiers  │
    │ Margin Rules    │ │ Demand Level    │ │ Safe Discounts  │
    │ Discount Limits │ │                 │ │                 │
    └────────┬────────┘ └────────┬────────┘ └────────┬────────┘
             │                   │                   │
             └───────────────────┼───────────────────┘
                                 │
                                 ▼
                    ┌─────────────────────────┐
                    │  Negotiation Decision   │
                    │                         │
                    │  ACCEPT                 │
                    │  COUNTER                │
                    │  BELOW_FLOOR            │
                    │  FINAL_OFFER            │
                    └────────────┬────────────┘
                                 │
                           Deal accepted?
                            ↙          ↘
                          No            Yes
                          │              │
                          ▼              ▼
                     Continue     ┌──────────────────┐
                    Negotiation   │     Razorpay     │
                                  │ Create Order     │
                                  │ Checkout         │
                                  │ Verify Payment   │
                                  └────────┬─────────┘
                                           │
                                           ▼
                                  ┌──────────────────┐
                                  │ Merchant         │
                                  │ Dashboard        │
                                  │                  │
                                  │ Negotiations     │
                                  │ Accepted Deals   │
                                  │ Paid Orders      │
                                  │ Revenue          │
                                  │ Savings          │
                                  │ Avg. Discount    │
                                  └──────────────────┘

Why this separation matters

Gemini understands language.
The negotiation engine makes the pricing decision.
Razorpay executes the accepted transaction.

An LLM therefore never receives unrestricted control over merchant
pricing.

🛍️ Customer Journey

From the customer's side, the experience stays simple:

Browse Products
      ↓
Add to Cart
      ↓
Negotiate with AI
      ↓
Quantity Opportunity
      ↓
Price Negotiation
      ↓
Accept Deal
      ↓
Pay with Razorpay
      ↓
Order Confirmed

The complexity stays behind the interface. The customer only sees a
storefront and a conversation about the deal.

🧠 How a Negotiation Works

When the customer clicks Negotiate with AI, the frontend sends the
cart to the FastAPI backend.

The backend resolves the products and creates a NegotiationSession
containing:

Original cart price

Merchant floor

Current AI offer

Negotiation history

Current round

Acceptance state

Available quantity opportunity

A customer offer can lead to four decisions:

Decision                            Meaning

ACCEPT                          The customer's offer is acceptable
and the deal is locked.

COUNTER                         The offer is safe, but the system
can negotiate for a better price.

BELOW_FLOOR                     The requested price violates the
merchant's minimum acceptable
price.

📦 Why Quantity Comes First

Negotiation does not always need to mean a deeper discount.

Instead of immediately reducing the price of one unit, the system first
checks whether a larger quantity at a slightly better per-unit price
can create a better transaction.

Current quantity tiers:

Quantity   Discount

   **2**     **5%**
   **3**     **7%**
   **5**    **10%**
  **10**    **12%**

Every quantity offer is still checked against the product's merchant
floor.

Growth logic: give the customer a meaningful saving while creating
an opportunity to increase cart value.

🛡️ Merchant Protection

Merchant protection is a hard constraint, not a suggestion to the
AI.

Each product contains business information such as selling price, cost
price, minimum margin, maximum discount, demand level, and negotiability
signals.

1. Margin Floor

Margin Floor = Cost Price × (1 + Minimum Margin %)

2. Discount Floor

Discount Floor = Selling Price × (1 - Maximum Discount %)

3. Final Merchant Floor

Merchant Floor = max(Margin Floor, Discount Floor)

Every generated deal must remain at or above this value.

Even repeated low offers cannot pressure the conversational layer into
violating the merchant's pricing rules.

🔎 Example: Bluetooth Speaker

Consider the Bluetooth Speaker in the prototype:

Metric                     Amount

Listed Price           ₹3,000
Merchant Floor         ₹2,400
Initial AI Offer     ~₹2,798

A reasonable offer above ₹2,400 can lead to another counteroffer.

But if the customer says:

I'll pay ₹1,500.

the system identifies it as BELOW_FLOOR and refuses to cross ₹2,400.

Quantity path

For two Bluetooth Speakers:

Metric                     Amount

Normal Total           ₹6,000
Quantity Deal          ₹5,700
Customer Saving          ₹300
Recalculated Floor     ₹4,800

The customer gets a real saving, the merchant gets a larger cart, and
the transaction remains safely above the floor.

✨ Role of Gemini

Gemini is useful in this project, but it is intentionally not in
charge of financial logic.

Customer Message
       ↓
Local Parsing
   ↙       ↘
Understood  Not Understood
   │             │
   │             ▼
   │       Gemini Fallback
   │             │
   └──────┬──────┘
          ▼
 Structured Request
          ↓
Deterministic Negotiation Engine

For straightforward product names, quantities, prices and acceptance
messages, the backend can understand the request locally.

When the language is less structured, Gemini 2.5 Flash acts as a
fallback.

This keeps the LLM focused on what it does well --- understanding
language --- while keeping financial behavior predictable and
testable.

💳 Razorpay Payment Flow

The negotiation does not stop at "here is your offer." An accepted
deal can become an actual transaction.

Deal Accepted
      ↓
Frontend requests payment order
      ↓
FastAPI creates Razorpay order
      ↓
Razorpay Checkout opens
      ↓
Customer completes payment
      ↓
Payment details return to backend
      ↓
Server verifies payment signature
      ↓
Order marked as paid

The amount sent to Razorpay comes from the accepted negotiation
session, rather than a price entered by the frontend.

Payment verification happens on the backend before the transaction is
treated as successful.

📊 Merchant Dashboard

The merchant-facing dashboard connects negotiation activity back to
commerce outcomes.

It currently tracks:

Metric                   What it shows

Total Negotiations   Number of negotiation sessions started
Accepted Deals       Negotiations that reached an agreement
Paid Orders          Successfully paid negotiated orders
Revenue              Revenue generated from paid deals
Customer Savings     Savings created through negotiation
Average Discount     Average discount across negotiated deals

For this prototype, session and dashboard data are stored in memory.

🛠️ Tech Stack

Layer              Technology

Frontend       React, Vite, JavaScript, CSS
UI             Lucide React
Backend        Python, FastAPI, Uvicorn
Product Data   Pandas
AI / NLP       Google Gemini 2.5 Flash + Local Parsing
Payments       Razorpay Checkout
Testing        Custom Evidence-Based Automated Judge

📁 Project Structure

ai_negotiator/
│
├── api.py
├── main.py
├── judge_simulator.py
├── judge_cases.json
├── .env
│
├── src/
│   ├── cart_builder.py
│   ├── cart_engine.py
│   ├── data_loader.py
│   ├── llm_agent.py
│   ├── negotiability.py
│   ├── negotiation_engine.py
│   ├── negotiation_session.py
│   ├── pricing_engine.py
│   ├── product_resolver.py
│   ├── quantity_offer.py
│   └── simulator.py
│
└── frontend/
    └── src/
        ├── App.jsx
        └── index.css

🧪 Testing

The negotiation engine has its own automated behavioral test suite
because pricing safety should not depend on a happy-path demo.

The suite contains 60 cases:

Test Group                                   Cases What It Checks

Basic Negotiation                           10 Initial pricing and
safe counteroffers

Quantity Safety                             10 Quantity changes and
floor-safe deals

Multi-item Carts                            10 Cart-level
negotiation

Floor Protection                            10 Repeated below-floor
pressure

Round Limits                                10 Five rounds, final
offer and blocked
sixth attempt

Edge &                                        10 Extreme offers and
Consistency                                      acceptance behavior

✅ Current Result

FINAL SCORE: 60/60
PASS RATE:   100.0%
STATUS:      READY FOR FINAL DEMO

The evidence report records assertions, customer offers, AI decisions,
and post-action session state, rather than only storing a final
pass/fail value.

The judge intentionally does not call Gemini, which isolates the
deterministic financial logic and keeps the result reproducible.

Run it with:

python judge_simulator.py

🚀 Running Locally

1. Clone the repository

git clone <YOUR_REPOSITORY_URL>
cd ai_negotiator

2. Create a virtual environment

python -m venv venv

Windows Command Prompt

venv\Scripts\activate

Git Bash

source venv/Scripts/activate

3. Install backend dependencies

pip install -r requirements.txt

4. Add environment variables

Create a .env file in the project root:

GEMINI_API_KEY=your_gemini_api_key
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

⚠️ Keep .env inside .gitignore. Never commit API keys or
Razorpay secrets.

5. Start the backend

uvicorn api:app --reload

Backend:

http://127.0.0.1:8000

6. Start the frontend

Open a second terminal:

cd frontend
npm install
npm run dev

Vite normally serves the app at:

http://localhost:5173

Keep both terminals running while using the application.

🎬 Suggested Demo Flow

1. Add the Bluetooth Speaker to the cart.

2. Click "Negotiate with AI."
Show that the offer comes from the pricing system rather than an
arbitrary discount.

3. Show the quantity opportunity.
Demonstrate the option to buy two units at a better per-unit price.

4. Reject it and continue to price negotiation.
Make a reasonable counteroffer and show the AI respond.

5. Try an unrealistically low offer.
Demonstrate that the ₹2,400 merchant floor cannot be crossed.

6. Reach and accept a deal.

7. Complete the payment through Razorpay.

8. Open the Merchant Dashboard.
Show how the completed flow affects merchant-facing metrics.

9. Finish with the automated test result.

60/60
100.0%
READY FOR FINAL DEMO

🌟 What Makes This Different?

This project is not just a chatbot attached to checkout.

The interesting part is the boundary between conversation and commerce
logic.

The customer can speak naturally.

Gemini can interpret less-structured language.

The negotiation engine controls concessions.

The pricing engine protects the merchant floor.

The quantity engine looks for opportunities to grow cart value.

Razorpay turns the accepted negotiation into a payment.

The system has room to behave like an agent without handing an LLM unrestricted control over pricing.

📌 Current Scope

This is a buildathon prototype, not a production commerce platform.

The current version uses:

an intentionally small product catalog

in-memory negotiation sessions

in-memory merchant dashboard metrics

These choices keep the prototype focused on the central question:

Can an AI negotiate a transaction while protecting the merchant's
economics?

The working negotiation flow, deterministic guardrails, Razorpay
integration and automated behavioral tests demonstrate that idea end to
end.

🔭 Where It Could Go Next

A production version could extend the same architecture with:

persistent negotiation and order storage

merchant accounts and authentication

configurable merchant pricing policies

inventory-aware negotiation

customer and product-level personalization

conversion experiments and A/B testing

richer negotiation analytics

payment webhooks and reconciliation

learned negotiation strategies constrained by deterministic merchant
rules

The principle stays the same:

The AI can handle the conversation. The merchant still controls the economics.

::: {align="center"}

Built for Razorpay AI Buildathon 2026

AI Growth & Agentic Commerce

AI Payment Negotiator explores an agentic checkout where AI does more
than recommend what to buy. It participates in the transaction itself,
looking for a deal the customer is willing to accept while staying
inside the merchant's business constraints.
:::