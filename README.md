AI Payment Negotiator

Turn checkout into a conversation, without giving up control of merchant margins.

Built for the Razorpay AI Buildathon 2026 under the AI Growth &
Agentic Commerce track.

What is AI Payment Negotiator?

Online stores usually handle pricing in one of two ways: show the listed
price, or apply a fixed discount.

That works, but it leaves very little room between "I'll buy this" and
"this is a little too expensive, so I'll leave."

AI Payment Negotiator explores that space.

It adds a conversational negotiation layer to checkout. A customer can
ask for a better deal, the system can suggest a quantity-based offer or
negotiate the price, and once both sides reach an acceptable deal, the
customer can complete the payment through Razorpay.

The merchant still stays in control.

The AI cannot simply invent discounts. Every offer is checked against
deterministic pricing rules, including minimum margins and maximum
allowed discounts. The conversational layer helps understand what the
customer wants, while the pricing engine decides what is financially
safe.

The problem

Static discounts have a few limitations.

A merchant may give the same 10% discount to someone who would have
purchased at full price and to someone who genuinely needed an incentive
to complete the purchase.

At the same time, a customer who is interested but not comfortable with
the current price may simply abandon the cart.

The question behind this project was:

Can checkout become a negotiation, while still keeping the
merchant's economics protected?

Instead of treating every shopper the same, AI Payment Negotiator
creates a bounded conversation around the transaction.

The approach

The negotiation follows a simple strategy:

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

The system tries to create value before simply reducing the price.

For a single-product cart, it first checks whether buying a larger
quantity can unlock a useful discount. If the customer does not want
that offer, normal price negotiation continues.

The price negotiation is limited to five rounds, so the conversation
cannot continue indefinitely.

System Architecture

The project separates language understanding, financial
decision-making, and payment execution.

That separation is important: Gemini can help understand the customer's
message, but it does not control the merchant's pricing boundaries.

                              CUSTOMER
                                  │
                                  ▼
                    ┌─────────────────────────┐
                    │      React Frontend     │
                    │                         │
                    │  Product Catalog        │
                    │  Shopping Cart          │
                    │  Negotiation Chat       │
                    │  Payment Experience     │
                    │  Merchant Dashboard     │
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
                    │  Current Offer          │
                    │  Negotiation History    │
                    │  Round Tracking         │
                    │  Acceptance State       │
                    │  Maximum 5 Rounds       │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
              ▼                  ▼                  ▼
    ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
    │ Pricing Engine  │ │ Negotiability   │ │ Quantity Offer  │
    │                 │ │ Engine          │ │ Engine          │
    │ Merchant Floor  │ │                 │ │                 │
    │ Margin Rules    │ │ Product Signals │ │ Quantity Tiers  │
    │ Discount Limits │ │ Demand Level    │ │ Safe Discounts  │
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
                                  │                  │
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

Customer journey

From the customer's side, the experience stays much simpler than the
internal architecture:

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
normal storefront and a conversation about the deal.

How a negotiation works

When the customer clicks Negotiate with AI, the frontend sends the
cart to the FastAPI backend.

The backend resolves the products and creates a NegotiationSession.

That session keeps track of:

the original cart price

the merchant floor

the current AI offer

negotiation history

the current round

whether the deal has been accepted

any available quantity opportunity

The session then works with the pricing, negotiability and
quantity-offer logic to decide what the system can safely offer.

A customer price attempt can result in four main decisions:

ACCEPT

The customer's offer is acceptable. The negotiated price is locked and
the customer can proceed to payment.

COUNTER

The customer's price is safe but below the AI's current offer. The
system makes another concession while remaining above the merchant
floor.

BELOW_FLOOR

The customer's offer violates the merchant's minimum acceptable price.
The AI refuses to cross the floor.

FINAL_OFFER

The negotiation has reached its five-round limit. The system holds its
final safe price instead of negotiating indefinitely.

Why quantity comes first

Negotiation does not always need to mean a deeper discount.

Imagine a customer wants one product for ₹3,000.

Instead of immediately reducing the price of that one unit, the system
can ask:

Would buying two units at a slightly better per-unit price create a
better transaction?

This gives the customer a saving while potentially increasing the
merchant's cart value.

The prototype currently uses these quantity tiers:

Quantity   Discount

       2         5%
       3         7%
       5        10%
      10        12%

The quantity engine still respects the product's merchant floor. A
quantity discount is never allowed to bypass the same financial
constraints used during normal negotiation.

So the overall strategy is:

Quantity upsell first → Price negotiation second → Never below
merchant floor

Merchant Protection

This is the most important guardrail in the project.

The LLM does not decide how low the merchant should go.

Each product contains pricing and business information such as:

selling price

cost price

minimum margin percentage

maximum discount percentage

demand level

negotiability-related signals

The pricing engine calculates two boundaries.

Margin floor

Margin Floor = Cost Price × (1 + Minimum Margin %)

Discount floor

Discount Floor = Selling Price × (1 - Maximum Discount %)

The actual merchant floor is:

Merchant Floor = max(Margin Floor, Discount Floor)

Every generated deal must remain at or above this value.

This means even repeated low offers cannot pressure the conversational
AI into violating the merchant's pricing rules.

Example: Bluetooth Speaker

Consider the Bluetooth Speaker in the prototype.

Listed price:      ₹3,000
Merchant floor:    ₹2,400
Initial AI offer:  ~₹2,798

If the customer makes a reasonable offer below the AI's current price
but above the merchant floor, the system can make a counteroffer.

If the customer says:

I'll pay ₹1,500.

the offer is below ₹2,400, so it is rejected as a below-floor attempt.

The AI can negotiate, but the floor does not move.

There is also a quantity path.

For two Bluetooth Speakers:

Normal total:       ₹6,000
Quantity deal:      ₹5,700
Customer saving:      ₹300
Recalculated floor: ₹4,800

The customer receives a real saving while the merchant gets a larger
cart, and the final deal still remains safely above the merchant floor.

Role of Gemini

Gemini is useful in this project, but intentionally not placed in charge
of the financial logic.

The backend first tries to understand common requests locally. For
straightforward product names, quantities, prices and acceptance
messages, there is no reason to make an LLM call.

When the request is less structured, Gemini 2.5 Flash can be used as
a fallback for natural-language understanding.

The flow is:

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

This keeps the AI useful where language is ambiguous while keeping
pricing behavior predictable and testable.

Razorpay Payment Flow

Negotiation is only useful if the agreed deal can become a real
transaction.

Once the customer explicitly accepts an offer:

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

The amount sent to Razorpay comes from the accepted negotiation session
rather than a price entered by the frontend.

Payment verification happens on the backend before the transaction is
treated as successful.

Merchant Dashboard

After negotiations and payments, the prototype exposes a merchant-facing
dashboard.

It currently tracks:

Total Negotiations

Accepted Deals

Paid Orders

Revenue

Customer Savings

Average Discount

This helps connect the AI interaction back to commerce outcomes rather
than treating negotiation as an isolated chatbot feature.

For the prototype, sessions and dashboard metrics are stored in memory.

Tech Stack

Layer          Technology

Frontend       React, Vite, JavaScript, CSS
UI Icons       Lucide React
Backend        Python, FastAPI, Uvicorn
Product Data   Pandas
AI / NLP       Google Gemini 2.5 Flash + local parsing
Payments       Razorpay Checkout
Testing        Custom evidence-based automated judge

Project Structure

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

Testing

Pricing is the part of this project where unexpected behavior would
matter most, so the negotiation engine has its own automated test suite.

Instead of testing only whether the application starts, the judge
interacts with the actual negotiation sessions and records what happens
after each action.

The suite contains 60 behavioral cases.

Test Group                                   Cases Purpose

Basic Negotiation                               10 Initial pricing and
safe counteroffers

Quantity Safety                                 10 Quantity changes and
floor-safe quantity
deals

Multi-item Carts                                10 Cart-level
negotiation behavior

Floor Protection                                10 Repeated below-floor
pressure

Round Limit                                     10 Five rounds, final
offer and blocked
sixth attempt

Edge & Consistency                              10 Extreme offers and
acceptance behavior

Current result:

FINAL SCORE: 60/60
PASS RATE:   100.0%
STATUS:      READY FOR FINAL DEMO

The generated evidence report contains the assertions, customer offers,
AI decisions and post-action session state for the tested flows.

The judge intentionally does not call Gemini. This isolates the
deterministic financial logic and makes the test result reproducible.

Run the suite with:

python judge_simulator.py

Running the Project Locally

1. Clone the repository

git clone <YOUR_REPOSITORY_URL>
cd ai_negotiator

2. Create a virtual environment

python -m venv venv

On Windows Command Prompt:

venv\Scripts\activate

On Git Bash:

source venv/Scripts/activate

3. Install backend dependencies

If the repository contains requirements.txt:

pip install -r requirements.txt

4. Add environment variables

Create a .env file in the project root:

GEMINI_API_KEY=your_gemini_api_key
RAZORPAY_KEY_ID=your_razorpay_key_id
RAZORPAY_KEY_SECRET=your_razorpay_key_secret

Keep .env inside .gitignore.

Never commit real API keys or Razorpay secrets.

5. Start the backend

From the project root:

uvicorn api:app --reload

The API should start at:

http://127.0.0.1:8000

6. Start the frontend

Open a second terminal:

cd frontend
npm install
npm run dev

Vite will normally serve the frontend at:

http://localhost:5173

Keep both terminals running while using the application.

Suggested Demo

A short demo can tell the whole story without showing every possible
feature.

1. Start with the storefront

Add a product such as the Bluetooth Speaker to the cart.

2. Open AI negotiation

Show that the system knows the cart and starts from a calculated offer
rather than an arbitrary discount.

3. Show the quantity opportunity

Demonstrate the option to buy two units at a better per-unit price.

This establishes the growth side of the project.

4. Continue to price negotiation

Reject the quantity offer and make a reasonable customer counteroffer.

Show the AI making another safe counter.

5. Test the guardrail

Make an unrealistically low offer.

For the Bluetooth Speaker, an offer below its ₹2,400 floor should not be
accepted.

This establishes the merchant-protection side.

6. Reach and accept a deal

Accept the negotiated offer.

7. Pay with Razorpay

Complete the test payment and show the successful payment state.

8. Open the Merchant Dashboard

Finish by showing how the negotiation is reflected in merchant-facing
metrics.

9. Show automated validation

A quick terminal shot of:

60/60
100.0%
READY FOR FINAL DEMO

shows that the pricing behavior was tested beyond the happy-path demo.

What Makes This Different?

The goal is not to attach a chatbot to a checkout page.

The interesting part is the boundary between conversation and commerce
logic.

The customer can speak naturally.

Gemini can help interpret that language.

But the merchant's financial constraints remain deterministic.

The negotiation engine can make concessions, but it cannot cross the
floor. Quantity offers can increase cart value, but they must still
satisfy the same pricing rules. A deal only moves to payment after
explicit acceptance.

That gives the system room to behave like an agent without handing an
LLM unrestricted control over pricing.

Current Scope

This is a buildathon prototype rather than a production commerce
platform.

The current implementation uses in-memory negotiation sessions and
dashboard data. The product catalog is also intentionally small so that
the negotiation behavior is easy to demonstrate and test.

Those choices keep the prototype focused on the central question:

Can an AI negotiate a transaction while protecting the merchant's
economics?

For this prototype, the answer is demonstrated through the working
checkout flow, deterministic guardrails, Razorpay payment integration
and automated behavioral testing.

Where It Could Go Next

A production version could extend the same architecture with:

persistent negotiation and order storage

merchant accounts and authentication

configurable merchant pricing policies

inventory-aware negotiation

customer and product-level personalization

conversion and A/B testing

richer negotiation analytics

payment webhooks and production reconciliation

learned negotiation strategies constrained by deterministic merchant
rules

The important principle would stay the same:

The AI can handle the conversation. The merchant still controls the
economics.

Built for Razorpay AI Buildathon 2026

Track: AI Growth & Agentic Commerce

AI Payment Negotiator explores an agentic checkout where AI does more
than recommend what to buy. It participates in the transaction itself,
looking for a deal the customer is willing to accept while staying
inside the merchant's business constraints.