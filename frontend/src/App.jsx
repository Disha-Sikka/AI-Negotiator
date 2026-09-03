import { useState } from "react";
import {
  ShoppingCart,
  MessageCircle,
  Plus,
  Minus,
  X,
  Send,
  CreditCard
} from "lucide-react";

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

  const addToCart = (product) => {

    setCart((currentCart) => {

      const existing = currentCart.find(
        item => item.id === product.id
      );

      if (existing) {

        return currentCart.map(item =>
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

    setCart(currentCart =>
      currentCart
        .map(item =>
          item.id === id
            ? {
                ...item,
                quantity: item.quantity + amount
              }
            : item
        )
        .filter(item => item.quantity > 0)
    );
  };

  const cartTotal = cart.reduce(
    (total, item) =>
      total + item.price * item.quantity,
    0
  );

  const startNegotiation = async () => {

    if (cart.length === 0) return;

    setShowNegotiator(true);
    setLoading(true);

    const cartDescription = cart
      .map(
        item =>
          `${item.quantity} ${item.name}`
      )
      .join(", ");

    try {

      const response = await fetch(
        "http://127.0.0.1:8000/negotiate/start",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json"
          },
          body: JSON.stringify({
            message:
              `I want to buy ${cartDescription}`
          })
        }
      );

      const data = await response.json();

      if (data.success) {

        setSessionId(data.session_id);

        setMessages([
          {
            sender: "ai",
            text:
              `Your cart total is ₹${cartTotal.toFixed(
                2
              )}. ${data.message}`
          }
        ]);
      }

    } catch (error) {

      setMessages([
        {
          sender: "ai",
          text:
            "I'm having trouble connecting to the negotiation service."
        }
      ]);
    }

    setLoading(false);
  };

  const sendMessage = async () => {

    if (!input.trim() || !sessionId || loading) {
      return;
    }

    const customerMessage = input;

    setMessages(current => [
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
        "http://127.0.0.1:8000/negotiate/continue",
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
      if (data.decision === "QUANTITY_ACCEPTED") {
    if (data.cart) {
        setCart(prevCart =>
            prevCart.map(item => {
                const updatedItem = data.cart.find(
                    cartItem =>
                        cartItem.product_name === item.name
                );

                if (updatedItem) {
                    return {
                        ...item,
                        quantity: updatedItem.quantity
                    };
                }

                return item;
            })
        );
    }

    setFinalPrice(data.offer);
    setAccepted(true);
}
      setMessages(current => [
        ...current,
        {
          sender: "ai",
          text: data.message
        }
      ]);

      if (data.decision === "ACCEPT") {

        setAccepted(true);
        setFinalPrice(data.offer);
      }

    } catch (error) {

      setMessages(current => [
        ...current,
        {
          sender: "ai",
          text:
            "Something went wrong. Please try again."
        }
      ]);
    }

    setLoading(false);
  };

  return (
    <div className="app">

      <header className="header">

        <div className="logo">
          <MessageCircle size={26} />
          <span>AI Negotiator</span>
        </div>

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

      </header>

      <main>

        <section className="hero">

          <h1>
            Shop smarter.
            <br />
            <span>Negotiate your price.</span>
          </h1>

          <p>
            Your AI shopping agent negotiates
            a better deal while keeping
            everything fair.
          </p>

        </section>

        <section className="products">

          <h2>Featured Products</h2>

          <div className="product-grid">

            {products.map(product => (

              <div
                className="product-card"
                key={product.id}
              >

                <div className="product-image">
                  {product.name.charAt(0)}
                </div>

                <h3>{product.name}</h3>

                <p className="price">
                  ₹{product.price.toLocaleString()}
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

        {cart.length > 0 && (

          <section className="cart-section">

            <div>

              <h2>Your Cart</h2>

              {cart.map(item => (

                <div
                  className="cart-item"
                  key={item.id}
                >

                  <div>

                    <strong>
                      {item.name}
                    </strong>

                    <p>
                      ₹{item.price.toLocaleString()}
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
                <span>Total</span>
                <strong>
                  ₹{cartTotal.toLocaleString()}
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

      {showNegotiator && (

        <div className="overlay">

          <div className="chat-window">

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
                onClick={() =>
                  setShowNegotiator(false)
                }
              >
                <X />
              </button>

            </div>

            <div className="messages">

              {messages.map(
                (message, index) => (

                  <div
                    key={index}
                    className={
                      message.sender === "user"
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

            {accepted ? (

              <div className="payment-area">

                <div className="accepted">
                  ✓ Deal accepted
                </div>

                <strong>
                  Final price: ₹
                  {finalPrice?.toFixed(2)}
                </strong>

                <button className="payment-button">
                  <CreditCard size={19} />
                  Proceed to Payment
                </button>

              </div>

            ) : (

              <div className="chat-input">

                <input
                  value={input}
                  onChange={e =>
                    setInput(e.target.value)
                  }
                  onKeyDown={e => {
                    if (
                      e.key === "Enter"
                    ) {
                      sendMessage();
                    }
                  }}
                  placeholder="Make an offer..."
                />

                <button
                  onClick={sendMessage}
                >
                  <Send size={19} />
                </button>

              </div>

            )}

          </div>

        </div>

      )}

    </div>
  );
}

export default App;