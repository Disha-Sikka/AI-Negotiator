import { useState } from "react";
import {
  ShoppingCart,
  MessageCircle,
  Plus,
  Minus,
  X,
  Send,
  CreditCard,
  BarChart3
} from "lucide-react";

const API_URL = "http://127.0.0.1:8000";

const products = [
  {
    id: "P001",
    name: "Premium Wireless Headphones",
    price: 5000
  },
  {
    id: "P002",
    name: "Bluetooth Speaker",
    price: 3000
  },
  {
    id: "P003",
    name: "USB-C Cable",
    price: 800
  },
  {
    id: "P004",
    name: "Mechanical Keyboard",
    price: 4500
  },
  {
    id: "P005",
    name: "Wireless Mouse",
    price: 1800
  },
  {
    id: "P007",
    name: "Laptop Stand",
    price: 2200
  }
];

function App() {
  const [cart, setCart] = useState([]);

  const [showNegotiator, setShowNegotiator] = useState(false);

  const [messages, setMessages] = useState([]);

  const [input, setInput] = useState("");

  const [sessionId, setSessionId] = useState(null);

  const [loading, setLoading] = useState(false);

  const [accepted, setAccepted] = useState(false);

  const [finalPrice, setFinalPrice] = useState(null);

  const [paymentSuccess, setPaymentSuccess] = useState(false);

  const [paymentLoading, setPaymentLoading] = useState(false);

  const [showDashboard, setShowDashboard] = useState(false);

  const [dashboard, setDashboard] = useState({
    total_negotiations: 0,
    accepted_deals: 0,
    paid_orders: 0,
    revenue: 0,
    customer_savings: 0,
    average_discount: 0
  });

  // --------------------------------------------------
  // CART
  // --------------------------------------------------

  const addToCart = (product) => {
    setCart((currentCart) => {
      const existing = currentCart.find(
        (item) => item.id === product.id
      );

      if (existing) {
        return currentCart.map((item) =>
          item.id === product.id
            ? {
                ...item,
                quantity: item.quantity + 1
              }
            : item
        );
      }

      return [
        ...currentCart,
        {
          ...product,
          quantity: 1
        }
      ];
    });
  };

  const changeQuantity = (id, amount) => {
    setCart((currentCart) =>
      currentCart
        .map((item) =>
          item.id === id
            ? {
                ...item,
                quantity: item.quantity + amount
              }
            : item
        )
        .filter((item) => item.quantity > 0)
    );
  };

  const cartTotal = cart.reduce(
    (total, item) =>
      total + item.price * item.quantity,
    0
  );

  // --------------------------------------------------
  // START NEGOTIATION
  // --------------------------------------------------

  const startNegotiation = async () => {
    if (cart.length === 0) return;

    setShowNegotiator(true);
    setLoading(true);
    setAccepted(false);
    setPaymentSuccess(false);
    setFinalPrice(null);
    setMessages([]);

    const cartDescription = cart
      .map(
        (item) =>
          `${item.quantity} ${item.name}`
      )
      .join(", ");

    try {
      const response = await fetch(
        `${API_URL}/negotiate/start`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            message: `I want to buy ${cartDescription}`
          })
        }
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        setMessages([
          {
            sender: "ai",
            text:
              data.message ||
              "Unable to start negotiation."
          }
        ]);

        return;
      }

      setSessionId(data.session_id);

      setMessages([
        {
          sender: "ai",
          text:
            `Your cart total is ₹${cartTotal.toLocaleString(
              "en-IN"
            )}. ${data.message}`
        }
      ]);
    } catch (error) {
      console.error(error);

      setMessages([
        {
          sender: "ai",
          text:
            "I'm having trouble connecting to the negotiation service."
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------
  // CONTINUE NEGOTIATION
  // --------------------------------------------------

  const sendMessage = async () => {
    if (
      !input.trim() ||
      !sessionId ||
      loading ||
      accepted
    ) {
      return;
    }

    const customerMessage = input.trim();

    setMessages((current) => [
      ...current,
      {
        sender: "user",
        text: customerMessage
      }
    ]);

    setInput("");
    setLoading(true);

    try {
      const response = await fetch(
        `${API_URL}/negotiate/continue`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            session_id: sessionId,
            message: customerMessage
          })
        }
      );

      const data = await response.json();

      if (!response.ok) {
        throw new Error(
          data.message || "Negotiation failed"
        );
      }

      // ----------------------------------------------
      // QUANTITY DEAL ACCEPTED
      // ----------------------------------------------

      if (
        data.decision ===
        "QUANTITY_ACCEPTED"
      ) {
        if (data.cart) {
          setCart((prevCart) =>
            prevCart.map((item) => {
              const updatedItem =
                data.cart.find(
                  (cartItem) =>
                    cartItem.product_name ===
                    item.name
                );

              if (updatedItem) {
                return {
                  ...item,
                  quantity:
                    updatedItem.quantity
                };
              }

              return item;
            })
          );
        }

        setFinalPrice(data.offer);
        setAccepted(true);
      }

      // ----------------------------------------------
      // NORMAL ACCEPTANCE
      // ----------------------------------------------

      if (data.decision === "ACCEPT") {
        setAccepted(true);
        setFinalPrice(data.offer);
      }

      // ----------------------------------------------
      // AI RESPONSE
      // ----------------------------------------------

      setMessages((current) => [
        ...current,
        {
          sender: "ai",
          text:
            data.message ||
            "Let me consider that offer."
        }
      ]);
    } catch (error) {
      console.error(error);

      setMessages((current) => [
        ...current,
        {
          sender: "ai",
          text:
            "Something went wrong. Please try again."
        }
      ]);
    } finally {
      setLoading(false);
    }
  };

  // --------------------------------------------------
  // RAZORPAY PAYMENT
  // --------------------------------------------------

  const handlePayment = async () => {
    if (!sessionId || finalPrice === null) {
      return;
    }

    setPaymentLoading(true);

    try {
      // Load Razorpay Checkout if not already loaded
      if (!window.Razorpay) {
        const script =
          document.createElement("script");

        script.src =
          "https://checkout.razorpay.com/v1/checkout.js";

        script.onload = () => {
          openRazorpayCheckout();
        };

        script.onerror = () => {
          alert(
            "Unable to load Razorpay. Please check your internet connection."
          );

          setPaymentLoading(false);
        };

        document.body.appendChild(script);
      } else {
        openRazorpayCheckout();
      }
    } catch (error) {
      console.error(error);

      alert(
        "Unable to start payment."
      );

      setPaymentLoading(false);
    }
  };

  const openRazorpayCheckout = async () => {
    try {
      const response = await fetch(
        `${API_URL}/payment/create-order`,
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            session_id: sessionId
          })
        }
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        alert(
          data.message ||
            "Unable to create payment order."
        );

        setPaymentLoading(false);

        return;
      }

      const options = {
        key: data.key_id,

        amount: data.amount,

        currency: data.currency,

        name: "AI Negotiator",

        description:
          "Negotiated purchase",

        order_id: data.order_id,

        handler: async function (response) {
          try {
            const verifyResponse =
              await fetch(
                `${API_URL}/payment/verify`,
                {
                  method: "POST",
                  headers: {
                    "Content-Type":
                      "application/json"
                  },
                  body: JSON.stringify({
                    session_id: sessionId,

                    razorpay_order_id:
                      response.razorpay_order_id,

                    razorpay_payment_id:
                      response.razorpay_payment_id,

                    razorpay_signature:
                      response.razorpay_signature
                  })
                }
              );

            const verifyData =
              await verifyResponse.json();

            if (
              verifyResponse.ok &&
              verifyData.success
            ) {
              setPaymentSuccess(true);
              setPaymentLoading(false);
            } else {
              alert(
                verifyData.message ||
                  "Payment verification failed."
              );

              setPaymentLoading(false);
            }
          } catch (error) {
            console.error(error);

            alert(
              "Payment verification failed."
            );

            setPaymentLoading(false);
          }
        },

        modal: {
          ondismiss: function () {
            setPaymentLoading(false);
          }
        },

        theme: {
          color: "#111827"
        }
      };

      const razorpay =
        new window.Razorpay(options);

      razorpay.on(
        "payment.failed",
        function (response) {
          console.error(
            "Payment failed:",
            response
          );

          setPaymentLoading(false);

          alert(
            "Payment failed. Please try again."
          );
        }
      );

      razorpay.open();
    } catch (error) {
      console.error(error);

      alert(
        "Something went wrong with payment."
      );

      setPaymentLoading(false);
    }
  };

  // --------------------------------------------------
  // MERCHANT DASHBOARD
  // --------------------------------------------------

  const openDashboard = async () => {
    try {
      const response = await fetch(
        `${API_URL}/merchant/dashboard`
      );

      const data = await response.json();

      if (!response.ok || !data.success) {
        alert(
          data.message ||
            "Unable to load dashboard."
        );

        return;
      }

      setDashboard({
        total_negotiations:
          data.total_negotiations || 0,

        accepted_deals:
          data.accepted_deals || 0,

        paid_orders:
          data.paid_orders || 0,

        revenue:
          data.revenue || 0,

        customer_savings:
          data.customer_savings || 0,

        average_discount:
          data.average_discount || 0
      });

      setShowDashboard(true);
    } catch (error) {
      console.error(error);

      alert(
        "Unable to connect to merchant dashboard."
      );
    }
  };

  // --------------------------------------------------
  // CLOSE NEGOTIATOR
  // --------------------------------------------------

  const closeNegotiator = () => {
    setShowNegotiator(false);
  };

  // --------------------------------------------------
  // RENDER
  // --------------------------------------------------

  return (
    <div className="app">

      {/* ==========================================
          HEADER
      ========================================== */}

      <header className="header">

        <div className="logo">
          <MessageCircle size={26} />

          <span>
            AI Negotiator
          </span>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "18px"
          }}
        >

          <button
            className="dashboard-button"
            onClick={openDashboard}
          >
            <BarChart3 size={18} />

            <span>
              Merchant Dashboard
            </span>
          </button>

          <div className="cart-icon">

            <ShoppingCart size={24} />

            <span>
              {cart.reduce(
                (sum, item) =>
                  sum + item.quantity,
                0
              )}
            </span>

          </div>

        </div>

      </header>


      {/* ==========================================
          MAIN CONTENT
      ========================================== */}

      <main>

        {/* HERO */}

        <section className="hero">

          <h1>
            Shop smarter.
            <br />

            <span>
              Negotiate your price.
            </span>
          </h1>

          <p>
            Your AI shopping agent negotiates
            a better deal while keeping
            everything fair.
          </p>

        </section>


        {/* PRODUCTS */}

        <section className="products">

          <h2>
            Featured Products
          </h2>

          <div className="product-grid">

            {products.map((product) => (

              <div
                className="product-card"
                key={product.id}
              >

                <div className="product-image">
                  {product.name.charAt(0)}
                </div>

                <h3>
                  {product.name}
                </h3>

                <p className="price">
                  ₹
                  {product.price.toLocaleString(
                    "en-IN"
                  )}
                </p>

                <button
                  onClick={() =>
                    addToCart(product)
                  }
                >
                  <Plus size={18} />

                  Add to Cart
                </button>

              </div>

            ))}

          </div>

        </section>


        {/* CART */}

        {cart.length > 0 && (

          <section className="cart-section">

            <div>

              <h2>
                Your Cart
              </h2>

              {cart.map((item) => (

                <div
                  className="cart-item"
                  key={item.id}
                >

                  <div>

                    <strong>
                      {item.name}
                    </strong>

                    <p>
                      ₹
                      {item.price.toLocaleString(
                        "en-IN"
                      )}
                    </p>

                  </div>

                  <div className="quantity">

                    <button
                      onClick={() =>
                        changeQuantity(
                          item.id,
                          -1
                        )
                      }
                    >
                      <Minus size={15} />
                    </button>

                    <span>
                      {item.quantity}
                    </span>

                    <button
                      onClick={() =>
                        changeQuantity(
                          item.id,
                          1
                        )
                      }
                    >
                      <Plus size={15} />
                    </button>

                  </div>

                </div>

              ))}

            </div>


            <div className="cart-bottom">

              <div className="cart-total">

                <span>
                  Total
                </span>

                <strong>
                  ₹
                  {cartTotal.toLocaleString(
                    "en-IN"
                  )}
                </strong>

              </div>

              <button
                className="negotiate-button"
                onClick={startNegotiation}
              >
                <MessageCircle size={20} />

                Negotiate with AI
              </button>

            </div>

          </section>

        )}

      </main>


      {/* ==========================================
          NEGOTIATOR MODAL
      ========================================== */}

      {showNegotiator && (

        <div className="overlay">

          <div className="chat-window">

            {/* CHAT HEADER */}

            <div className="chat-header">

              <div>

                <strong>
                  AI Negotiator
                </strong>

                <small>
                  Your personal shopping agent
                </small>

              </div>

              <button
                onClick={closeNegotiator}
              >
                <X />
              </button>

            </div>


            {/* MESSAGES */}

            <div className="messages">

              {messages.map(
                (message, index) => (

                  <div
                    key={index}
                    className={
                      message.sender ===
                      "user"
                        ? "message user"
                        : "message ai"
                    }
                  >
                    {message.text}
                  </div>

                )
              )}


              {loading && (

                <div className="message ai">
                  Thinking...
                </div>

              )}

            </div>


            {/* ACCEPTED / PAYMENT */}

            {accepted ? (

              paymentSuccess ? (

                <div className="payment-area">

                  <div className="accepted">
                    ✓ Payment Successful
                  </div>

                  <strong>
                    Order confirmed for ₹
                    {finalPrice?.toLocaleString(
                      "en-IN",
                      {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      }
                    )}
                  </strong>

                  <p>
                    Your negotiated deal
                    has been successfully paid.
                  </p>

                  <p
                    style={{
                      fontSize: "13px",
                      opacity: 0.65
                    }}
                  >
                    Thank you for shopping
                    with AI Negotiator.
                  </p>

                </div>

              ) : (

                <div className="payment-area">

                  <div className="accepted">
                    ✓ Deal accepted
                  </div>

                  <strong>
                    Final price: ₹
                    {finalPrice?.toLocaleString(
                      "en-IN",
                      {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      }
                    )}
                  </strong>

                  <p>
                    Your negotiated price
                    has been locked in.
                  </p>

                  <button
                    className="payment-button"
                    onClick={handlePayment}
                    disabled={paymentLoading}
                  >

                    <CreditCard size={19} />

                    {paymentLoading
                      ? "Opening Payment..."
                      : "Proceed to Payment"}

                  </button>

                </div>

              )

            ) : (

              /* CHAT INPUT */

              <div className="chat-input">

                <input
                  value={input}
                  onChange={(e) =>
                    setInput(e.target.value)
                  }
                  onKeyDown={(e) => {

                    if (
                      e.key === "Enter" &&
                      !e.shiftKey
                    ) {
                      e.preventDefault();
                      sendMessage();
                    }

                  }}
                  placeholder="Make an offer..."
                  disabled={loading}
                />

                <button
                  onClick={sendMessage}
                  disabled={loading}
                >
                  <Send size={19} />
                </button>

              </div>

            )}

          </div>

        </div>

      )}


      {/* ==========================================
          MERCHANT DASHBOARD
      ========================================== */}

      {showDashboard && (

        <div className="overlay">

          <div
            className="chat-window dashboard-window"
          >

            <div className="chat-header">

              <div>

                <strong>
                  Merchant Dashboard
                </strong>

                <small>
                  AI Negotiator performance
                </small>

              </div>

              <button
                onClick={() =>
                  setShowDashboard(false)
                }
              >
                <X />
              </button>

            </div>


            <div className="dashboard-content">

              {/* TOTAL NEGOTIATIONS */}

              <div className="dashboard-card">

                <span>
                  Total Negotiations
                </span>

                <strong>
                  {dashboard.total_negotiations}
                </strong>

              </div>


              {/* ACCEPTED DEALS */}

              <div className="dashboard-card">

                <span>
                  Accepted Deals
                </span>

                <strong>
                  {dashboard.accepted_deals}
                </strong>

              </div>


              {/* PAID ORDERS */}

              <div className="dashboard-card">

                <span>
                  Paid Orders
                </span>

                <strong>
                  {dashboard.paid_orders}
                </strong>

              </div>


              {/* REVENUE */}

              <div className="dashboard-card">

                <span>
                  Revenue
                </span>

                <strong>
                  ₹
                  {dashboard.revenue.toLocaleString(
                    "en-IN"
                  )}
                </strong>

              </div>


              {/* CUSTOMER SAVINGS */}

              <div className="dashboard-card">

                <span>
                  Customer Savings
                </span>

                <strong>
                  ₹
                  {dashboard.customer_savings.toLocaleString(
                    "en-IN"
                  )}
                </strong>

              </div>


              {/* AVERAGE DISCOUNT */}

              <div className="dashboard-card">

                <span>
                  Average Discount
                </span>

                <strong>
                  {dashboard.average_discount}%
                </strong>

              </div>

            </div>

          </div>

        </div>

      )}

    </div>
  );
}

export default App;