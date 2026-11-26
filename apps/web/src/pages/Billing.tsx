
import { useEffect, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api, type Plan, type Subscription } from "../api";

type RazorpaySuccess = {
  razorpay_payment_id: string;
  razorpay_subscription_id: string;
  razorpay_signature: string;
};

type RazorpayFailure = {
  error?: {
    description?: string;
  };
};

type RazorpayOptions = {
  key: string;
  subscription_id: string;
  name: string;
  description: string;
  handler: (response: RazorpaySuccess) => void | Promise<void>;
  modal?: {
    ondismiss?: () => void;
  };
  theme?: {
    color: string;
  };
};

type RazorpayInstance = {
  open: () => void;
  on: (
    event: "payment.failed",
    callback: (response: RazorpayFailure) => void
  ) => void;
};

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayOptions) => RazorpayInstance;
  }
}

const RAZORPAY_SCRIPT =
  "https://checkout.razorpay.com/v1/checkout.js";

function loadRazorpayScript(): Promise<boolean> {
  return new Promise((resolve) => {
    if (window.Razorpay) {
      resolve(true);
      return;
    }

    const existing = document.querySelector(
      `script[src="${RAZORPAY_SCRIPT}"]`
    ) as HTMLScriptElement | null;

    if (existing) {
      existing.addEventListener(
        "load",
        () => resolve(true),
        { once: true }
      );
      existing.addEventListener(
        "error",
        () => resolve(false),
        { once: true }
      );
      return;
    }

    const script = document.createElement("script");
    script.src = RAZORPAY_SCRIPT;
    script.async = true;

    script.onload = () => resolve(true);
    script.onerror = () => resolve(false);

    document.body.appendChild(script);
  });
}

export function BillingPage() {
  const [plans, setPlans] = useState<Plan[]>([]);
  const [sub, setSub] = useState<Subscription | null>(null);
  const [error, setError] = useState("");
  const [busySlug, setBusySlug] = useState("");
  const [params] = useSearchParams();

  async function load() {
    const [p, s] = await Promise.all([
      api.plans(),
      api.billingSummary(),
    ]);

    setPlans(p);
    setSub(s);
  }

  useEffect(() => {
    load().catch((e) => setError(e.message));
  }, []);

  // Retain the existing development stub-upgrade flow.
  useEffect(() => {
    const stub = params.get("stub_upgrade");
    if (!stub) return;

    api
      .stubUpgrade(stub)
      .then((s) => {
        setSub(s);
        setError("");
      })
      .catch((e) => setError(e.message));
  }, [params]);

  async function upgrade(slug: string) {
    try {
      setError("");
      setBusySlug(slug);

      const res = await api.checkout(slug);

      // Development-only stub mode.
      if (res.stub) {
        await api.stubUpgrade(slug);
        await load();
        setBusySlug("");
        return;
      }

      if (!res.key_id || !res.subscription_id) {
        throw new Error(
          "The API did not return a Razorpay key or subscription ID."
        );
      }

      const loaded = await loadRazorpayScript();

      if (!loaded || !window.Razorpay) {
        throw new Error("Could not load Razorpay Checkout. Please try again.");
      }

      const Razorpay = window.Razorpay;

      const checkout = new Razorpay({
        key: res.key_id,
        subscription_id: res.subscription_id,
        name: "Flow Suite",
        description: `${slug === "pro" ? "Pro" : "Business"} monthly subscription`,

        handler: async (response) => {
          try {
            setError("");

            const verified = await api.verifyCheckout({
              razorpay_payment_id: response.razorpay_payment_id,
              razorpay_subscription_id:
                response.razorpay_subscription_id,
              razorpay_signature: response.razorpay_signature,
            });

            setSub(verified);
            await load();
            setError("");
          } catch (err) {
            setError(
              err instanceof Error
                ? err.message
                : "Payment verification failed."
            );
          } finally {
            setBusySlug("");
          }
        },

        modal: {
          ondismiss: () => {
            setBusySlug("");
          },
        },

        theme: {
          color: "#2563eb",
        },
      });

      checkout.on("payment.failed", (response) => {
        setError(
          response.error?.description ??
            "Payment failed. Please try again."
        );
        setBusySlug("");
      });

      checkout.open();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to start checkout."
      );
      setBusySlug("");
    }
  }

  async function openPortal() {
    try {
      setError("");

      const result = await api.portal();

      if (result.url) {
        window.location.href = result.url;
      } else {
        setError(
          result.message ??
            "Subscription management is not available yet."
        );
      }
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unable to open billing."
      );
    }
  }

  function formatPrice(plan: Plan) {
    if (plan.amount_paise === 0) return "Free";

    const amount = new Intl.NumberFormat("en-IN", {
      style: "currency",
      currency: plan.currency,
      maximumFractionDigits: 0,
    }).format(plan.amount_paise / 100);

    return `${amount} / ${plan.billing_interval}`;
  }

  return (
    <div>
      <h1>Billing</h1>

      <p className="lede">
        Current plan: <strong>{sub?.plan_name ?? "…"}</strong>{" "}
        ({sub?.status})
      </p>

      {error && <p className="error">{error}</p>}

      <div className="plan-grid">
        {plans.map((p) => (
          <article
            key={p.id}
            className={
              sub?.plan_slug === p.slug ? "plan current" : "plan"
            }
          >
            <h2>{p.name}</h2>

            <p>{p.description}</p>

            <h3>{formatPrice(p)}</h3>

            <ul>
              {Object.entries(p.features).map(([k, v]) => (
                <li key={k}>
                  {k}: {String(v)}
                </li>
              ))}
            </ul>

            {p.slug !== "free" && sub?.plan_slug !== p.slug && (
              <button
                type="button"
                className="cta"
                disabled={busySlug !== ""}
                onClick={() => upgrade(p.slug)}
              >
                {busySlug === p.slug ? "Please wait..." : "Upgrade"}
              </button>
            )}

            {sub?.plan_slug === p.slug && (
              <span className="badge">Current</span>
            )}
          </article>
        ))}
      </div>

      <button
        type="button"
        className="ghost"
        onClick={openPortal}
      >
        Manage subscription
      </button>

      <p className="hint">
        Payments are processed through Razorpay. This project is
        currently being configured for Razorpay Test Mode.
      </p>
    </div>
  );
}
