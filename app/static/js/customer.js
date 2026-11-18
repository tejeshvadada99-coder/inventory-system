
/*
============================================================
 app/static/js/customer.js
 Customer Portal JavaScript
============================================================

Expected API endpoints:

POST  /auth/customer/register
POST  /auth/customer/login

GET   /customer/profile
PATCH /customer/profile
GET   /customer/purchase-history

GET   /customer/loyalty/balance
GET   /customer/loyalty/summary
GET   /customer/loyalty/transactions

POST  /reviews
GET   /reviews/my-reviews
GET   /reviews/product/{product_id}

The notification endpoints must be added to the backend
before notification loading can be enabled.
============================================================
*/

"use strict";


/* =========================================================
   CONFIGURATION
========================================================= */

const CustomerApp = {

    API_BASE: "",

    TOKEN_KEY: "customer_access_token",

    USER_KEY: "customer_user",

    DEFAULT_HEADERS: {
        "Accept": "application/json"
    }

};


/* =========================================================
   AUTHENTICATION HELPERS
========================================================= */

const CustomerAuth = {

    getToken() {
        return localStorage.getItem(CustomerApp.TOKEN_KEY);
    },

    setToken(token) {
        if (!token) {
            throw new Error("Authentication token is missing.");
        }

        localStorage.setItem(CustomerApp.TOKEN_KEY, token);
    },

    clearToken() {
        localStorage.removeItem(CustomerApp.TOKEN_KEY);
        localStorage.removeItem(CustomerApp.USER_KEY);
    },

    saveUser(user) {
        localStorage.setItem(
            CustomerApp.USER_KEY,
            JSON.stringify(user || {})
        );
    },

    getUser() {
        try {
            return JSON.parse(
                localStorage.getItem(CustomerApp.USER_KEY) || "{}"
            );
        } catch {
            return {};
        }
    },

    isLoggedIn() {
        return Boolean(this.getToken());
    },

    requireLogin() {
        if (!this.isLoggedIn()) {
            window.location.href = "/customer/login";
            return false;
        }

        return true;
    },

    logout() {
        this.clearToken();
        window.location.href = "/customer/login";
    }

};


/* =========================================================
   API HELPER
========================================================= */

async function customerAPI(
    endpoint,
    options = {}
) {

    const headers = {
        ...CustomerApp.DEFAULT_HEADERS,
        ...(options.headers || {})
    };

    const token = CustomerAuth.getToken();

    if (token) {
        headers.Authorization = `Bearer ${token}`;
    }

    const config = {
        ...options,
        headers
    };

    if (
        config.body &&
        typeof config.body !== "string"
    ) {
        headers["Content-Type"] = "application/json";
        config.body = JSON.stringify(config.body);
    }

    let response;

    try {

        response = await fetch(
            CustomerApp.API_BASE + endpoint,
            config
        );

    } catch (error) {

        throw new Error(
            "Unable to connect to the server. Check your internet connection."
        );

    }

    let data = {};

    const responseText = await response.text();

    if (responseText) {

        try {
            data = JSON.parse(responseText);
        } catch {
            data = {
                detail: responseText
            };
        }

    }

    if (!response.ok) {

        if (response.status === 401) {
            CustomerAuth.clearToken();
        }

        let message =
            data.detail ||
            data.message ||
            "Something went wrong. Please try again.";

        if (Array.isArray(message)) {
            message = message
                .map(item => item.msg || "Invalid input")
                .join(", ");
        }

        throw new Error(message);

    }

    return data;

}


/* =========================================================
   MESSAGE HELPERS
========================================================= */

function showCustomerMessage(
    message,
    type = "info",
    target = "[data-customer-message]"
) {

    const element = document.querySelector(target);

    if (!element) {
        console.log(message);
        return;
    }

    element.textContent = message;

    element.className =
        `customer-alert customer-alert-${type}`;

    element.hidden = false;

}


function hideCustomerMessage(
    target = "[data-customer-message]"
) {

    const element = document.querySelector(target);

    if (element) {
        element.hidden = true;
        element.textContent = "";
    }

}


function setButtonLoading(
    button,
    loading,
    loadingText = "Please wait..."
) {

    if (!button) return;

    if (loading) {

        button.dataset.originalText =
            button.textContent;

        button.disabled = true;
        button.textContent = loadingText;

    } else {

        button.disabled = false;

        if (button.dataset.originalText) {
            button.textContent =
                button.dataset.originalText;
        }

    }

}


/* =========================================================
   GENERAL HELPERS
========================================================= */

function setText(selector, value) {

    const element = document.querySelector(selector);

    if (element) {
        element.textContent =
            value === null || value === undefined
                ? "-"
                : String(value);
    }

}


function formatCurrency(amount) {

    return new Intl.NumberFormat("en-IN", {
        style: "currency",
        currency: "INR",
        maximumFractionDigits: 2
    }).format(Number(amount || 0));

}


function formatDate(dateValue) {

    if (!dateValue) return "-";

    const date = new Date(dateValue);

    if (Number.isNaN(date.getTime())) {
        return "-";
    }

    return date.toLocaleDateString("en-IN", {
        day: "2-digit",
        month: "short",
        year: "numeric"
    });

}


function createElement(
    tag,
    className,
    text
) {

    const element = document.createElement(tag);

    if (className) {
        element.className = className;
    }

    if (text !== undefined) {
        element.textContent = String(text);
    }

    return element;

}


function getArray(data) {
    if (Array.isArray(data)) return data;
    if (Array.isArray(data.items)) return data.items;
    if (Array.isArray(data.results)) return data.results;
    if (Array.isArray(data.purchases)) return data.purchases;
    if (Array.isArray(data.transactions)) return data.transactions;
    if (Array.isArray(data.reviews)) return data.reviews;
    return [];
}


/* =========================================================
   CUSTOMER REGISTRATION
========================================================= */

async function registerCustomer(form) {

    const button = form.querySelector(
        'button[type="submit"]'
    );

    hideCustomerMessage();

    const formData = new FormData(form);

    const payload = {
        name: formData.get("name")?.trim(),
        email: formData.get("email")?.trim(),
        mobile_number: formData.get("mobile_number")?.trim(),
        address: formData.get("address")?.trim() || null,
        password: formData.get("password"),
        confirm_password: formData.get("confirm_password")
    };

    if (
        !payload.name ||
        !payload.email ||
        !payload.mobile_number ||
        !payload.password
    ) {

        showCustomerMessage(
            "Please complete all required fields.",
            "error"
        );

        return;

    }

    if (
        payload.password !== payload.confirm_password
    ) {

        showCustomerMessage(
            "Passwords do not match.",
            "error"
        );

        return;

    }

    if (
        new TextEncoder().encode(payload.password).length > 72
    ) {

        showCustomerMessage(
            "Password is too long. Please use a shorter password.",
            "error"
        );

        return;

    }

    try {

        setButtonLoading(
            button,
            true,
            "Creating account..."
        );

        const result = await customerAPI(
            "/auth/customer/register",
            {
                method: "POST",
                body: payload
            }
        );

        showCustomerMessage(
            result.message ||
            "Registration successful. Please complete account verification.",
            "success"
        );

        form.reset();

    } catch (error) {

        showCustomerMessage(
            error.message,
            "error"
        );

    } finally {

        setButtonLoading(button, false);

    }

}


/* =========================================================
   CUSTOMER LOGIN
========================================================= */

async function loginCustomer(form) {

    const button = form.querySelector(
        'button[type="submit"]'
    );

    hideCustomerMessage();

    const formData = new FormData(form);

    const payload = {
        identifier: formData.get("identifier")?.trim(),
        password: formData.get("password")
    };

    if (!payload.identifier || !payload.password) {

        showCustomerMessage(
            "Enter your email or mobile number and password.",
            "error"
        );

        return;

    }

    try {

        setButtonLoading(
            button,
            true,
            "Signing in..."
        );

        const result = await customerAPI(
            "/auth/customer/login",
            {
                method: "POST",
                body: payload
            }
        );

        if (!result.access_token) {
            throw new Error(
                "The server did not return an access token."
            );
        }

        CustomerAuth.setToken(result.access_token);

        CustomerAuth.saveUser({
            full_name: result.full_name,
            role: result.role
        });

        window.location.href = "/customer/dashboard";

    } catch (error) {

        showCustomerMessage(
            error.message,
            "error"
        );

    } finally {

        setButtonLoading(button, false);

    }

}


/* =========================================================
   CUSTOMER PROFILE
========================================================= */

async function loadCustomerProfile() {

    if (!CustomerAuth.requireLogin()) return;

    try {

        const profile = await customerAPI(
            "/customer/profile"
        );

        setText(
            "[data-customer-name]",
            profile.name
        );

        setText(
            "[data-customer-email]",
            profile.email
        );

        setText(
            "[data-customer-mobile]",
            profile.mobile_number
        );

        setText(
            "[data-customer-address]",
            profile.address
        );

        setText(
            "[data-customer-created]",
            formatDate(profile.created_at)
        );

        setText(
            "[data-customer-points]",
            profile.loyalty_points ?? 0
        );

        const name = profile.name || "Customer";

        setText(
            "[data-customer-welcome]",
            `Welcome, ${name}`
        );

        const emailStatus = document.querySelector(
            "[data-email-verification-status]"
        );

        if (emailStatus) {

            emailStatus.textContent =
                profile.email_verified
                    ? "Verified"
                    : "Not verified";

        }

        const mobileStatus = document.querySelector(
            "[data-mobile-verification-status]"
        );

        if (mobileStatus) {

            mobileStatus.textContent =
                profile.mobile_verified
                    ? "Verified"
                    : "Not verified";

        }

    } catch (error) {

        showCustomerMessage(
            error.message,
            "error"
        );

    }

}


/* =========================================================
   UPDATE CUSTOMER PROFILE
========================================================= */

async function updateCustomerProfile(form) {

    const button = form.querySelector(
        'button[type="submit"]'
    );

    const formData = new FormData(form);

    const payload = {
        name: formData.get("name")?.trim(),
        address: formData.get("address")?.trim() || null
    };

    try {

        setButtonLoading(
            button,
            true,
            "Saving..."
        );

        const result = await customerAPI(
            "/customer/profile",
            {
                method: "PATCH",
                body: payload
            }
        );

        showCustomerMessage(
            result.message || "Profile updated successfully.",
            "success"
        );

        await loadCustomerProfile();

    } catch (error) {

        showCustomerMessage(
            error.message,
            "error"
        );

    } finally {

        setButtonLoading(button, false);

    }

}


/* =========================================================
   PURCHASE HISTORY
========================================================= */

async function loadPurchaseHistory() {

    if (!CustomerAuth.requireLogin()) return;

    const container = document.querySelector(
        "[data-purchase-history]"
    );

    if (!container) return;

    container.replaceChildren(
        createElement(
            "div",
            "customer-loading-state",
            "Loading purchase history..."
        )
    );

    try {

        const data = await customerAPI(
            "/customer/purchase-history"
        );

        const purchases = getArray(data);

        container.replaceChildren();

        if (!purchases.length) {

            container.appendChild(
                createElement(
                    "div",
                    "customer-empty-state",
                    "No purchases found yet."
                )
            );

            return;

        }

        purchases.forEach(bill => {

            const item = createElement(
                "div",
                "customer-purchase-item"
            );

            const details = createElement(
                "div",
                "customer-purchase-details"
            );

            details.appendChild(
                createElement(
                    "h3",
                    "",
                    `Receipt #${bill.bill_id}`
                )
            );

            details.appendChild(
                createElement(
                    "p",
                    "",
                    formatDate(bill.date)
                )
            );

            const amount = createElement(
                "div",
                "customer-purchase-amount",
                formatCurrency(bill.total_amount)
            );

            item.append(details, amount);

            container.appendChild(item);

        });

    } catch (error) {

        container.replaceChildren(
            createElement(
                "div",
                "customer-error-state",
                error.message
            )
        );

    }

}


/* =========================================================
   LOYALTY BALANCE
========================================================= */

async function loadLoyaltyBalance() {

    if (!CustomerAuth.requireLogin()) return;

    try {

        const data = await customerAPI(
            "/customer/loyalty/balance"
        );

        setText(
            "[data-customer-points]",
            data.available_points ?? 0
        );

        setText(
            "[data-loyalty-customer-name]",
            data.customer_name
        );

    } catch (error) {

        showCustomerMessage(
            error.message,
            "error"
        );

    }

}


/* =========================================================
   LOYALTY SUMMARY
========================================================= */

async function loadLoyaltySummary() {

    if (!CustomerAuth.requireLogin()) return;

    try {

        const data = await customerAPI(
            "/customer/loyalty/summary"
        );

        setText(
            "[data-points-earned]",
            data.total_earned ?? 0
        );

        setText(
            "[data-points-redeemed]",
            data.total_redeemed ?? 0
        );

        setText(
            "[data-points-available]",
            data.available_points ?? 0
        );

    } catch (error) {

        showCustomerMessage(
            error.message,
            "error"
        );

    }

}


/* =========================================================
   LOYALTY TRANSACTION HISTORY
========================================================= */

async function loadLoyaltyTransactions() {

    if (!CustomerAuth.requireLogin()) return;

    const container = document.querySelector(
        "[data-loyalty-transactions]"
    );

    if (!container) return;

    container.replaceChildren(
        createElement(
            "div",
            "customer-loading-state",
            "Loading loyalty transactions..."
        )
    );

    try {

        const data = await customerAPI(
            "/customer/loyalty/transactions?page=1&limit=20"
        );

        const transactions = getArray(data);

        container.replaceChildren();

        if (!transactions.length) {

            container.appendChild(
                createElement(
                    "div",
                    "customer-empty-state",
                    "No loyalty transactions yet."
                )
            );

            return;

        }

        transactions.forEach(transaction => {

            const item = createElement(
                "div",
                "customer-transaction"
            );

            const details = createElement("div");

            details.appendChild(
                createElement(
                    "div",
                    "customer-transaction-title",
                    transaction.description ||
                    transaction.transaction_type
                )
            );

            details.appendChild(
                createElement(
                    "div",
                    "customer-transaction-date",
                    formatDate(transaction.created_at)
                )
            );

            const isEarned =
                Number(transaction.points) >= 0;

            const points = createElement(
                "div",
                isEarned
                    ? "customer-points-earned"
                    : "customer-points-redeemed",
                `${isEarned ? "+" : ""}${transaction.points} points`
            );

            item.append(details, points);

            container.appendChild(item);

        });

    } catch (error) {

        container.replaceChildren(
            createElement(
                "div",
                "customer-error-state",
                error.message
            )
        );

    }

}


/* =========================================================
   PRODUCT REVIEWS
========================================================= */

async function submitProductReview(form) {

    const button = form.querySelector(
        'button[type="submit"]'
    );

    const formData = new FormData(form);

    const payload = {
        sale_id: Number(formData.get("sale_id")),
        rating: Number(formData.get("rating")),
        review_text:
            formData.get("review_text")?.trim() || null
    };

    if (
        !Number.isInteger(payload.sale_id) ||
        payload.sale_id <= 0
    ) {

        showCustomerMessage(
            "Select a valid purchased item.",
            "error"
        );

        return;

    }

    if (
        !Number.isInteger(payload.rating) ||
        payload.rating < 1 ||
        payload.rating > 5
    ) {

        showCustomerMessage(
            "Rating must be between 1 and 5.",
            "error"
        );

        return;

    }

    try {

        setButtonLoading(
            button,
            true,
            "Submitting review..."
        );

        const result = await customerAPI(
            "/reviews",
            {
                method: "POST",
                body: payload
            }
        );

        showCustomerMessage(
            result.message || "Review submitted successfully.",
            "success"
        );

        form.reset();

        await loadMyReviews();

    } catch (error) {

        showCustomerMessage(
            error.message,
            "error"
        );

    } finally {

        setButtonLoading(button, false);

    }

}


/* =========================================================
   MY REVIEWS
========================================================= */

async function loadMyReviews() {

    if (!CustomerAuth.requireLogin()) return;

    const container = document.querySelector(
        "[data-my-reviews]"
    );

    if (!container) return;

    try {

        const data = await customerAPI(
            "/reviews/my-reviews"
        );

        const reviews = getArray(data);

        container.replaceChildren();

        if (!reviews.length) {

            container.appendChild(
                createElement(
                    "div",
                    "customer-empty-state",
                    "You have not submitted any reviews."
                )
            );

            return;

        }

        reviews.forEach(review => {

            const card = createElement(
                "div",
                "customer-review-card"
            );

            card.appendChild(
                createElement(
                    "div",
                    "customer-review-title",
                    review.product_name ||
                    `Product #${review.product_id}`
                )
            );

            card.appendChild(
                createElement(
                    "div",
                    "customer-review-stars",
                    "★".repeat(
                        Math.max(
                            0,
                            Math.min(5, Number(review.rating) || 0)
                        )
                    )
                )
            );

            card.appendChild(
                createElement(
                    "p",
                    "customer-review-text",
                    review.review_text || "No written review."
                )
            );

            container.appendChild(card);

        });

    } catch (error) {

        container.replaceChildren(
            createElement(
                "div",
                "customer-error-state",
                error.message
            )
        );

    }

}


/* =========================================================
   PRODUCT REVIEWS BY PRODUCT
========================================================= */

async function loadProductReviews(productId) {

    const container = document.querySelector(
        "[data-product-reviews]"
    );

    if (!container) return;

    if (!Number.isInteger(Number(productId))) {
        return;
    }

    try {

        const data = await customerAPI(
            `/reviews/product/${encodeURIComponent(productId)}`
        );

        const reviews = getArray(data);

        container.replaceChildren();

        if (!reviews.length) {

            container.appendChild(
                createElement(
                    "div",
                    "customer-empty-state",
                    "No approved reviews yet."
                )
            );

            return;

        }

        reviews.forEach(review => {

            const card = createElement(
                "div",
                "customer-review-card"
            );

            card.appendChild(
                createElement(
                    "div",
                    "customer-review-title",
                    review.customer_name || "Verified customer"
                )
            );

            card.appendChild(
                createElement(
                    "div",
                    "customer-review-stars",
                    "★".repeat(
                        Math.max(
                            0,
                            Math.min(5, Number(review.rating) || 0)
                        )
                    )
                )
            );

            card.appendChild(
                createElement(
                    "p",
                    "customer-review-text",
                    review.review_text || ""
                )
            );

            container.appendChild(card);

        });

    } catch (error) {

        container.replaceChildren(
            createElement(
                "div",
                "customer-error-state",
                error.message
            )
        );

    }

}


/* =========================================================
   NOTIFICATIONS
========================================================= */

/*
Add these backend endpoints before enabling this feature:

GET   /customer/notifications
PATCH /customer/notifications/{notification_id}/read

*/

async function loadCustomerNotifications() {

    if (!CustomerAuth.requireLogin()) return;

    const container = document.querySelector(
        "[data-customer-notifications]"
    );

    if (!container) return;

    try {

        const data = await customerAPI(
            "/customer/notifications"
        );

        const notifications = getArray(data);

        container.replaceChildren();

        if (!notifications.length) {

            container.appendChild(
                createElement(
                    "div",
                    "customer-empty-state",
                    "You have no notifications."
                )
            );

            return;

        }

        notifications.forEach(notification => {

            const item = createElement(
                "div",
                "customer-notification"
            );

            const icon = createElement(
                "div",
                "customer-notification-icon",
                "🔔"
            );

            const content = createElement("div");

            content.appendChild(
                createElement(
                    "h4",
                    "",
                    notification.title
                )
            );

            content.appendChild(
                createElement(
                    "p",
                    "",
                    notification.message
                )
            );

            content.appendChild(
                createElement(
                    "p",
                    "",
                    formatDate(notification.created_at)
                )
            );

            item.append(icon, content);

            container.appendChild(item);

        });

    } catch (error) {

        container.replaceChildren(
            createElement(
                "div",
                "customer-error-state",
                error.message
            )
        );

    }

}


/* =========================================================
   PASSWORD VISIBILITY
========================================================= */

function setupPasswordVisibility() {

    document.querySelectorAll(
        "[data-password-toggle]"
    ).forEach(button => {

        button.addEventListener("click", () => {

            const input = document.querySelector(
                button.dataset.passwordToggle
            );

            if (!input) return;

            const show =
                input.type === "password";

            input.type = show
                ? "text"
                : "password";

            button.textContent = show
                ? "Hide"
                : "Show";

        });

    });

}


/* =========================================================
   LOGOUT BUTTONS
========================================================= */

function setupLogoutButtons() {

    document.querySelectorAll(
        "[data-customer-logout]"
    ).forEach(button => {

        button.addEventListener("click", () => {
            CustomerAuth.logout();
        });

    });

}


/* =========================================================
   FORM EVENT LISTENERS
========================================================= */

function setupCustomerForms() {

    document.querySelectorAll(
        "[data-customer-register]"
    ).forEach(form => {

        form.addEventListener("submit", event => {

            event.preventDefault();

            registerCustomer(form);

        });

    });


    document.querySelectorAll(
        "[data-customer-login]"
    ).forEach(form => {

        form.addEventListener("submit", event => {

            event.preventDefault();

            loginCustomer(form);

        });

    });


    document.querySelectorAll(
        "[data-customer-profile-form]"
    ).forEach(form => {

        form.addEventListener("submit", event => {

            event.preventDefault();

            updateCustomerProfile(form);

        });

    });


    document.querySelectorAll(
        "[data-customer-review-form]"
    ).forEach(form => {

        form.addEventListener("submit", event => {

            event.preventDefault();

            submitProductReview(form);

        });

    });

}


/* =========================================================
   DASHBOARD INITIALIZATION
========================================================= */

async function initializeCustomerDashboard() {

    if (!CustomerAuth.requireLogin()) return;

    await Promise.allSettled([

        loadCustomerProfile(),

        loadPurchaseHistory(),

        loadLoyaltyBalance(),

        loadLoyaltySummary(),

        loadLoyaltyTransactions(),

        loadMyReviews(),

        loadCustomerNotifications()

    ]);

}


/* =========================================================
   APPLICATION INITIALIZATION
========================================================= */

document.addEventListener(
    "DOMContentLoaded",
    () => {

        setupCustomerForms();

        setupPasswordVisibility();

        setupLogoutButtons();

        const dashboard =
            document.querySelector(
                "[data-customer-dashboard]"
            );

        if (dashboard) {
            initializeCustomerDashboard();
        }

        const productId =
            document.querySelector(
                "[data-product-reviews]"
            )?.dataset.productReviews;

        if (productId) {
            loadProductReviews(productId);
        }

    }
);


/* =========================================================
   GLOBAL CUSTOMER APP FUNCTIONS
========================================================= */

window.CustomerApp = {

    auth: CustomerAuth,

    api: customerAPI,

    register: registerCustomer,

    login: loginCustomer,

    logout: () => CustomerAuth.logout(),

    loadProfile: loadCustomerProfile,

    loadPurchaseHistory,

    loadLoyaltyBalance,

    loadLoyaltySummary,

    loadLoyaltyTransactions,

    loadMyReviews,

    loadProductReviews,

    loadNotifications: loadCustomerNotifications

};
