# Roomora AI — Complete Project Summary, Page-by-Page Documentation, Known Issues, and Roadmap

**Document purpose:** A detailed handoff/reference document describing the Roomora AI project, the role of each page, the current frontend/backend architecture, existing data and API capabilities, setup instructions, known bugs, unfinished integrations, and the intended next steps.

**Last consolidated:** 28 October 2026  
**Project:** Roomora AI — AI-assisted interior design and furniture shopping  
**Local operating system:** Windows  
**Main editor:** Visual Studio Code  
**Frontend technology:** HTML, CSS, JavaScript  
**Backend technology:** Python + FastAPI  
**Database:** SQLite via SQLAlchemy  
**Repository referenced in earlier setup:** `https://github.com/richapanchal/UDP_Roomora_AI.git`

> **Accuracy note:** The backend ZIP and project guidance files were inspected. The complete live frontend directory (`user.html`, `admin.html`, seller page, designer page, and related CSS/JS) was not included in the backend ZIP inspected for this document. Consequently, backend routes and fields described below are based on source code; frontend descriptions combine the login code supplied in chat, known filenames, project notes, and observed troubleshooting. Where a UI element is known to exist but its complete implementation could not be rechecked, that is stated rather than assumed to be fully functional.

---

## 1. Executive summary

Roomora AI is intended to be a website where people can plan or visualize interior designs, browse and buy furniture, find and book interior designers, save design requirements, and manage purchases. It has four main user roles:

1. **User/customer** — views the website, explores design options, browses furniture, adds items to a cart, books a designer, and saves designs.
2. **Seller** — manages furniture products and stock and updates the status of orders containing the seller's products.
3. **Designer** — manages availability and responds to customer booking requests.
4. **Admin** — manages users and roles, oversees products and their approval, monitors orders and bookings, and views overall statistics.

The app consists of two main parts:

- **Frontend:** static web pages under `Roomora_AI/user/`. HTML describes the pages, `user.css` styles the interface, and JavaScript handles forms, product cards, tabs, cart behavior, and client-side interactions.
- **Backend:** `roomora_backend/`, a FastAPI application that provides authentication, products, designers, bookings, orders, saved designs, administration, and a text-based AI requirements editor.

The intended user journey is:

1. Open the login page and sign in.
2. The app identifies the signed-in user's role and opens the matching dashboard.
3. A customer can describe a room-design idea and use the AI editor to refine design requirements in English or Hindi (and some Hinglish commands through the rules engine).
4. The customer can browse furniture and designers.
5. A customer can add products to a cart, place an order, book a designer, or save design requirements.
6. Sellers manage listings and order-item status; designers manage booking requests and availability; admins control users, product approvals, and platform-wide records.

**Current maturity:** The backend structure and several API flows exist, but the frontend integration is incomplete. Some UI operations remain sample/hard-coded or use local browser storage. Real image generation/editing, full email flows, real payments, and the correct live role-based login redirect remain unresolved.

---

## 2. Current local project structure

The previously used local project folder is:

```text
C:\Users\Admin\Desktop\Saumya\UDP Project\UDP_Roomora_AI
```

The expected high-level structure is:

```text
UDP_Roomora_AI/
├── Roomora_AI/
│   └── user/
│       ├── login.html
│       ├── user.html
│       ├── user.css
│       ├── roomora-logo.png
│       └── admin/
│           ├── admin.html
│           └── seller/
│               ├── seller.html
│               └── designer/
│                   └── designer.html
├── roomora_backend/
│   ├── app/
│   │   ├── main.py
│   │   ├── config.py
│   │   ├── database.py
│   │   ├── models.py
│   │   ├── schemas.py
│   │   ├── security.py
│   │   ├── ai_editor.py
│   │   └── routers/
│   │       ├── auth.py
│   │       ├── products.py
│   │       ├── designers.py
│   │       ├── orders.py
│   │       ├── designs.py
│   │       ├── ai.py
│   │       └── admin.py
│   ├── frontend_ai_editor/
│   │   └── ai-editor.js
│   ├── frontend_files/
│   │   └── api.js
│   ├── tests/
│   │   └── test_api.py
│   ├── requirements.txt
│   ├── seed.py
│   ├── README.md
│   ├── FASTAPI_GUIDE.md
│   └── IDEAS.md
└── start_roomora.bat   (startup helper file created during setup)
```

Some filenames exist in the backend recovery ZIP but were not in the original backend ZIP inspected, for example `.env.example` and `test_email.py`. This document does **not** assume that all such recovery files have been copied into the user's live folder. Also, the frontend page files are in the separate `Roomora_AI/user/` tree and were not all available in the backend ZIP.

### What the important files do

| File/folder | Responsibility |
|---|---|
| `Roomora_AI/user/login.html` | Login and signup UI, front-end form validation, and currently troublesome login redirect logic. |
| `Roomora_AI/user/user.html` | Main customer-facing page: design-related interface, furniture display, product cards/cart behavior, and design-prompt area. |
| `Roomora_AI/user/user.css` | Shared styling for customer and authentication pages; the login page links to this file. |
| `Roomora_AI/user/admin/admin.html` | Admin dashboard/panel. |
| `Roomora_AI/user/admin/seller/seller.html` | Seller dashboard/panel. |
| `Roomora_AI/user/admin/seller/designer/designer.html` | Designer dashboard/panel. |
| `roomora_backend/app/main.py` | Creates the FastAPI app, enables CORS, creates database tables, includes routers, and exposes the health route. |
| `roomora_backend/app/config.py` | Loads `.env` settings such as database URL, JWT secret, token expiry, and Anthropic API configuration. |
| `roomora_backend/app/database.py` | SQLAlchemy engine/session and database dependency. |
| `roomora_backend/app/models.py` | SQLite database table definitions. |
| `roomora_backend/app/schemas.py` | Request and response data validation using Pydantic. |
| `roomora_backend/app/security.py` | Password hashing, JWT creation/verification, current-user lookup, and role-check dependencies. |
| `roomora_backend/app/ai_editor.py` | Converts English/Hindi/Hinglish instructions into structured room-design requirements using Claude when configured or a simple rules fallback. |
| `roomora_backend/app/routers/` | Route handlers grouped by feature. |
| `roomora_backend/seed.py` | Inserts the demo users, six designer profiles, and ten demo furniture products once into an empty database. |
| `roomora_backend/frontend_ai_editor/ai-editor.js` | Optional floating text/voice editor to add to `user.html`; it calls the AI requirements endpoint. |
| `roomora_backend/frontend_files/api.js` | API helper provided in the backend package; the current frontend's full use of this helper has not been verified. |
| `roomora_backend/tests/test_api.py` | Automated API tests, including auth/journey and AI editor language/fallback tests. |
| `start_roomora.bat` | Helper intended to start the backend and frontend in separate command windows. Verify its local paths and virtual environment before relying on it. |

---

## 3. Page-by-page explanation

## 3.1 Login page — `login.html`

**Purpose:** Let an existing user sign in to Roomora AI, or switch to the signup form to create an account.

### Visible elements in the supplied HTML

- Roomora AI logo image: `roomora-logo.png`.
- Brand heading: **Roomora AI**.
- Tagline: **“Reimagine your space.”**
- Login and Sign Up tabs.
- Login form titled **“Welcome Back”** with explanatory text.
- Email field (`loginEmail`).
- Password field (`loginPassword`).
- **Forgot Password?** link.
- Login submit button.
- Signup form (hidden initially) with name, email, mobile, password, password rules, confirm-password, and Create Account button.
- Styling is loaded from `user.css` and the page uses the `auth-body`, `auth-container`, `auth-logo`, `auth-card`, `auth-tabs`, `auth-tab`, `form-group`, and `primary-button` classes.

### Login behavior required

1. The user types email and password.
2. The browser should submit those credentials to the backend `POST /auth/login`.
3. The backend checks the email and password against the database.
4. If valid, the backend returns an access token and the user's role.
5. The frontend stores the token and redirects to the page belonging to that role.

Expected dashboard mapping:

| Role returned by backend | Destination relative to `Roomora_AI/user/` |
|---|---|
| `user` | `user.html` |
| `admin` | `admin/admin.html` |
| `seller` | `admin/seller/seller.html` |
| `designer` | `admin/seller/designer/designer.html` |

### Actual problem in the original supplied login code

The original login submit listener only checked that the email and password fields were filled in, and then always executed:

```javascript
window.location.href = "user.html";
```

This is the direct reason every login was originally redirected to the user side. There was no role lookup and no call to the backend.

A later front-end-only demo-account mapping was supplied, but the user reported that the admin login still landed on the user side after updating the code and doing a hard refresh. That issue is **still unresolved**. The likely causes to check are:

- The browser is being served a different `login.html` from the one edited in VS Code.
- The frontend server was started in a different folder.
- Another listener or JavaScript file redirects to `user.html` after the new listener runs.
- The changes were not saved to the file that the server is actually serving.
- The current page code was not integrated with FastAPI's real authentication route.

The most reliable long-term repair is not another hard-coded JavaScript role list. It is to connect to `/auth/login` and use the returned `data.user.role` for the redirect.

### Signup elements and validation

The signup form asks for:

- Full name
- Email address
- Mobile number
- Password
- Confirm password

The password hint list requires:

- At least 8 characters
- One uppercase/capital letter
- One number
- One special character

The supplied original JavaScript performs client-side checks and displays an account-created alert. However, that original code does **not** call `POST /auth/signup`; it does not create a real database user. A replacement code draft was later provided that explicitly warns signup is not yet connected to the backend. The actual live file must be checked to see which version is currently in place.

### Email validation problem

The original JavaScript checked `email.toLowerCase().includes("gmail.com")`. That is too loose because it does not ensure the address ends with `@gmail.com`. The backend schema is stricter and requires an email ending in `@gmail.com`. If the current frontend still uses the original `includes()` check, it can accept inputs that the backend rejects.

### Forgot password

Currently, the link asks the user to enter an email and displays a placeholder message saying reset instructions will be sent in the production version. It does **not** generate a reset token or send an email. A working reset flow needs a backend route, a secure one-time token, expiration, and email sending.

### Authentication security warning

The front-end-only demo mapping stores passwords in JavaScript and can be inspected by anyone with access to the page source. It is suitable only for a local demonstration. The app must use backend authentication before real deployment.

---

## 3.2 Main customer page — `user.html`

**Purpose:** This is the main user-facing experience. It combines the room-design entry point, AI design prompt, furniture shopping, cart/checkout interactions, designer discovery/booking, and saved-design features.

The exact full current `user.html` source was not in the backend ZIP, so the following separates known page elements from the intended backend-supported flow.

### A. Main design area / “Describe your dream design”

The backend's frontend editor integration expects a text field with the ID `designPrompt`. This is intended to let a customer describe the desired room, style, furniture, materials, lighting, colors, and budget. The AI editor script can place a generated prompt into this field.

Example requirements the backend understands:

- Space type: Home, Cafe, Hotel, Office, College, Restaurant, or Shop.
- Style: e.g., Scandinavian, luxury, or minimalist.
- Wall color.
- Main colors.
- Furniture list.
- Materials.
- Lighting.
- Budget in Indian rupees.
- Additional notes.

The intended action is for the customer to enter design preferences, refine them via text/voice commands, and then use the prompt to generate a design.

**Current limitation:** A real generated redesign image is not connected. The backend README explicitly says the “AI result” box in `user.html` is still a placeholder. The text editor can produce a prompt/requirements object, but it cannot by itself turn that prompt or a room photo into a new image.

### B. AI-generated result area

The interface has an intended result area for displaying a generated interior design. This is where a generated image should ultimately appear, with the option to save the result or continue editing it.

**Current status:** Placeholder, not a completed image-generation workflow. The saved-design database model has an `image_url` field, but the end-to-end pipeline that generates, stores, and displays these images has not been implemented in the inspected backend.

### C. Furniture shopping section

The page contains furniture cards / a furniture grid. The backend refers to this section as **“Furniture for your space.”** The inspected data model and seed data include:

| Demo product | Category | Seed price (INR) |
|---|---|---:|
| Modern Boucle Sofa | Sofa | ₹42,999 |
| Oak Lounge Chair | Chair | ₹18,499 |
| Marble Coffee Table | Table | ₹14,999 |
| Arched Floor Lamp | Lighting | ₹7,999 |
| Minimal Bed | Bed | ₹36,500 |
| Oak Dining Set | Dining | ₹29,990 |
| Accent Armchair | Chair | ₹16,750 |
| Console Table | Table | ₹12,499 |
| Pendant Light | Lighting | ₹5,499 |
| Designer Rug | Decor | ₹9,999 |

The product cards can show product image, name, price, and an Add to Cart action. At least one observed product card showed **Marble Coffee Table**, price **₹14,999**, with an image placeholder/broken image and an Add to Cart button.

The frontend has been observed to render product cards inside `displayProducts()` and read the image with logic equivalent to:

```javascript
product.image_url || product.image || ""
```

with a fallback image when the image fails to load. The precise current set of fields should be checked in the live `user.html`.

### D. Cart and checkout concept

The frontend currently uses `localStorage` for cart state. This means items may remain in the browser after refresh, but the cart is not automatically a server-side order. The FastAPI backend has order endpoints, but the frontend needs to call them at checkout to create a durable order.

The backend checkout input expects:

- Product IDs and quantities
- Customer full name
- Mobile number
- Address
- City
- State (optional/default empty in the schema)
- Six-digit PIN/pincode
- Payment method, defaulting to COD

The server reads prices from the database rather than trusting a price supplied by the browser. This is important to prevent price manipulation.

### E. Designer discovery / “Book an interior designer”

The backend supports a public list of approved designer profiles. A designer card can show the designer's name, speciality, day rate, and availability. The booking form can collect:

- Designer ID
- Customer name
- Mobile
- Email
- Project type (such as Home, Cafe, Hotel)
- Start date
- Number of days
- Extra project details

The server computes the total booking amount as designer day price multiplied by booking days. The schema permits 1–60 days. The front-end form must call `POST /bookings` to persist the booking. The API is present; complete connection from the existing form must be verified.

### F. Saving designs

The backend provides saved designs. A saved design records:

- Title
- Prompt
- Space type
- Structured design requirements
- `image_url` (currently a string, not a guarantee that an image was actually generated)
- Creation date

Users can create a saved design, list their own saved designs, and delete their own records. The frontend needs to call these API routes. The full image upload/generation/history experience has not been implemented.

### G. Product images and local image files

One previously reported issue is the image for **Marble Coffee Table** not loading. The seed file contains an Unsplash URL for that product. An updated URL was suggested in the discussion, but modifying the URL in `seed.py` will not update an already-populated database, because `seed.py` exits when it detects existing users.

If using a local image such as `Cafe Design.jpg`:

1. Place the file inside the frontend folder, e.g. `Roomora_AI/user/images/Cafe Design.jpg`.
2. Use a browser path such as `images/Cafe%20Design.jpg` (or an absolute localhost URL while testing).
3. Do not use a Windows filesystem path such as `C:\Users\Admin\Desktop\Saumya\UDP Project\Cafe Design.jpg` in the HTML image source. The browser cannot use an arbitrary local Windows path as a website asset.
4. If the product list is still hard-coded in `user.html`, change the frontend data there. If the page uses API products, change the database record or use the product update API. Check which data source the live page uses before deciding where to make the change.

---

## 3.3 Admin dashboard — `admin/admin.html`

**Purpose:** Give the platform administrator overview and management controls across users, sellers, designers, products, orders, and bookings.

The backend API confirms the following administrative capabilities.

### A. Dashboard statistics

The API `GET /admin/stats` returns:

- `total_users` — number of users with role `user`.
- `total_sellers` — number of users with role `seller`.
- `total_designers` — number of designer profiles.
- `products_pending_approval` — products awaiting admin approval.
- `total_orders` — order count.
- `total_bookings` — designer booking count.
- `revenue_inr` — calculated from non-cancelled order items (not a proof of money actually collected).

These can power summary cards on the admin overview page. They must be fetched from the backend for live data rather than hard-coded sample numbers.

### B. User management

The backend supports:

- List users through `GET /admin/users`.
- Search by name/email.
- Filter by role.
- Change role among `user`, `seller`, `designer`, and `admin` via `PATCH /admin/users/{user_id}/role`.
- Block/unblock users via `PATCH /admin/users/{user_id}/block`.

The backend prevents an admin from blocking their own account. These actions require an authenticated admin token.

### C. Product review and approval

The admin can view pending products and approve/reject them. Relevant endpoints:

- `GET /products/pending`
- `PATCH /products/{product_id}/status`

Allowed statuses in the product route are `approved`, `rejected`, and `pending`. The customer product listing (`GET /products`) only returns approved products.

### D. Designer management

The admin can list approved designers publicly and can approve, leave pending, or suspend a designer profile:

- `GET /designers`
- `POST /designers` (admin can convert an existing user into a designer and create a profile)
- `PATCH /designers/{designer_id}/status`

The status route supports `approved`, `pending`, and `suspended`.

### E. Order oversight

The admin can view all orders through `GET /admin/orders`. Order totals and item statuses should be interpreted carefully: the backend's current revenue figure is based on non-cancelled order items and does not mean a payment has cleared.

### F. Export controls

Project notes mention export-related UI functions such as `exportReport` and `exportUsers`. Their frontend buttons have been referenced, but the full implementation and integration were not re-verified. CSV export is a known finishing task rather than a confirmed end-to-end feature.

### G. Important admin limitation

Navigating directly to `/admin/admin.html` is not, by itself, secure access control. Static HTML files are generally accessible to anyone who knows their URLs. Real authorization must be enforced on the backend for protected operations; the frontend should also check the current user's role and redirect non-admin users for a better experience.

---

## 3.4 Seller dashboard — `admin/seller/seller.html`

**Purpose:** Allow furniture sellers to manage their own product catalog and follow order fulfillment.

### A. Seller products

The backend supports:

- Viewing the seller's products using `GET /products/mine`.
- Adding a product through `POST /products`.
- Editing a product through `PUT /products/{product_id}`.
- Deleting a product through `DELETE /products/{product_id}` when no order references it.
- Fields: product name, category, short description, full description, selling price, MRP, stock, and image URL.

A newly-added product from a seller starts with `pending` status and needs admin approval. An admin-created product is approved immediately. Customers only see approved products.

The backend intentionally prevents a seller from editing or deleting someone else's product. It also prevents deletion of a product that already has order history; the seller should set its stock to zero instead.

### B. Seller order management

The seller can list their own order items through `GET /orders/seller` and update individual items using `PATCH /orders/items/{item_id}/status`.

Order-item status values include:

- `placed`
- `packed`
- `shipped`
- `delivered`
- `cancelled`

Each item is tied to a seller, because a single order may contain products from multiple sellers. A seller can only update their own items; an admin can act across sellers. Cancelling an item can restock the quantity.

### C. Inventory and reviews

Inventory/stock fields are present in the product model and can be updated. Project notes mention inventory alerts and CSV export as future/finishing improvements. The `IDEAS.md` notes that a Reviews page/button exists in the seller UI, but the inspected backend does not include a review/rating table or review API. Therefore seller review display/management must be treated as incomplete until verified and connected.

### D. Current integration risk

The backend API exists, but earlier project notes state that the frontend product and designer lists are still hard-coded and have not yet all been replaced with API calls. The seller dashboard must be checked to confirm that its add/edit/delete and order buttons send authorized requests and refresh their displayed data.

---

## 3.5 Designer dashboard — `admin/seller/designer/designer.html`

**Purpose:** Let interior designers manage their availability and booking requests from customers.

### A. Designer profile

The designer profile model stores:

- User reference
- Speciality description
- Price per day
- Availability toggle
- Approval status (`pending`, `approved`, or `suspended`)

The public designer list only exposes profiles with approved status.

### B. Availability

The endpoint `PATCH /designers/me/availability` flips the designer's `is_available` field. It requires a logged-in user with role `designer`. The front end should show the current availability and refresh it after a successful request.

### C. Booking requests

The designer's bookings are available from `GET /bookings/designer`; a designer can update booking status with `PATCH /bookings/{booking_id}/status`. Booking statuses include `pending`, `accepted`, `declined`, and `completed`.

A user can create their own booking with `POST /bookings` and view their own bookings with `GET /bookings/mine`.

### D. Portfolio and reviews

A designer portfolio/image upload and reviews/ratings are discussed in project ideas. The current inspected backend does not have a dedicated portfolio upload/storage feature or reviews database/routes, so those should not be described as fully working without further implementation.

### E. Permissions

Designer actions must be performed with the designer's token. A user-role token cannot access designer-only routes. Admin can manage designer approval/suspension through the admin routes.

---

## 3.6 Optional floating AI editor — `ai-editor.js`

**Purpose:** Add a floating AI assistant to the customer page for refining interior-design requirements by typing or voice.

The backend package includes `frontend_ai_editor/ai-editor.js`. To attach it to the page, the backend README recommends copying `ai-editor.js` next to `user.html` and adding this before `</body>`:

```html
<script src="ai-editor.js"></script>
```

The script creates a floating **AI Editor** button and a chat-like panel. Its UI includes:

- Text input with Send button.
- Microphone button for speech input.
- Language dropdown with English and Hindi options.
- Optional read-replies-aloud toggle.
- Undo last change button.
- Example command buttons.
- Requirement chips showing space, style, wall color, colors, furniture, materials, lighting, and budget.
- A message history panel.

Example commands include:

- `Make the wall sage green`
- `Add indoor plants`
- `Set budget to 50000`
- `दीवार का रंग हरा कर दो`
- `सोफे का रंग नीला कर दो`
- `बजट 2 लाख रखो`

### How the AI editor works

1. User types a command or speaks into the browser microphone.
2. The browser's Speech Recognition API converts voice to text (commonly works in Chrome/Edge and needs the site served from `localhost` rather than opened as a raw `file:///` path).
3. The script sends the command and current requirements to `POST /ai/edit-requirements`.
4. The backend either calls Claude (when `ANTHROPIC_API_KEY` is configured) or uses a keyword/rules fallback.
5. The backend returns updated structured requirements, a prompt, a reply, a list of changes, and the engine name.
6. The script updates the requirement chips and fills the `#designPrompt` text field when that element exists.
7. The user can then use the prompt in the design area.

The editor stores current requirements in browser localStorage using `roomoraRequirements`. It expects a token in localStorage under **`roomoraToken`**. The front-end demo login code previously supplied stores `roomoraRole` and `roomoraEmail` instead, so that demo-only code is not enough for the protected AI route. The real backend login integration must save `data.access_token` to `roomoraToken` (or the editor's expected key must be changed consistently).

### What this editor is not

It is a **text/requirements editor**, not an image generator. It updates the description of the desired room. It does not independently create pixels, edit a room photograph, change a sofa in an actual image, or persist generated images.

---

## 3.7 Planned room photo upload and actual AI image generation

This is a major goal discussed for Roomora AI and is not yet complete in the inspected backend.

### Desired end-user flow

1. User selects a photo of their real room/home.
2. The frontend previews the original photo.
3. The original is preserved unchanged.
4. The user provides a design prompt or selects style/color/budget requirements.
5. An image model receives both the photo and relevant instructions and creates a redesigned image based on the actual room.
6. The page shows original and redesigned images side by side (or with a before/after slider).
7. The user can submit follow-up prompts, including English or Hindi, such as “Change the sofa to dark green” or “सोफे का रंग गहरा हरा कर दो”.
8. Each new edit uses the appropriate prior edited output/reference and stores a separate version, so the original and prior attempts are not overwritten.
9. User can save the final design and download it or revisit the versions.

### Current status

- No full upload-and-redesign API was found in the backend ZIP.
- `/ai/edit-requirements` handles text instructions and structured requirements only.
- Claude text generation is not image generation.
- `SavedDesign.image_url` is only a database field, not an implemented generation/storage pipeline.
- The UI's AI result area is described in the README as a placeholder.
- Real image generation requires an image-generation/editing provider that supports API access and editing an input image (not merely generating an unrelated new image).
- The user has indicated that they have another image-generation tool, but its exact name and whether it provides API access have not yet been identified. Therefore the integration provider is undecided.
- OpenAI API account/billing setup was discussed, but the user then said they already have another tool. OpenAI API setup is not a confirmed requirement and should not be pursued until the other tool is identified and checked for API support.

### Requirements for a robust implementation

- Keep API credentials on the backend in `.env`, never in browser HTML/JavaScript or GitHub.
- Validate upload types (e.g., JPEG/PNG/WebP) and size limits.
- Store uploads and outputs under managed paths or a storage service, not as arbitrary user-provided filesystem paths.
- Return a safe image URL or image ID to the frontend.
- Keep original image immutable.
- Save each edit as a new version with prompt, timestamp, and parent image/version reference.
- Return readable errors when provider calls fail, time out, or hit rate limits.
- Add a progress/loading state in the frontend.
- Consider privacy and retention: a room photo may reveal personal/private home details; don't expose uploads publicly without authorization.

---

## 4. Backend API and responsibilities

Base URL in local development: `http://127.0.0.1:8000`  
Interactive documentation: `http://127.0.0.1:8000/docs`  
Health route: `GET /`  
Alternate documentation: `/redoc`

### 4.1 Authentication — `/auth`

| Method and route | Purpose |
|---|---|
| `POST /auth/signup` | Creates a normal customer account. Public signup does not create admin/seller/designer roles. |
| `POST /auth/login` | Validates credentials and returns a JWT access token plus user details including role. |
| `GET /auth/me` | Returns the currently logged-in user's profile based on the bearer token. |

Key rules:

- Passwords are stored as bcrypt hashes, not plaintext.
- Login returns an access token and role information.
- Protected requests use `Authorization: Bearer <access_token>`.
- Token expiry defaults to 1,440 minutes (24 hours) unless configured otherwise.
- Signup requires an email ending in `@gmail.com`, at least 10 mobile-number characters, and a password of at least 8 characters with one uppercase, one number, and one special character.
- Login rejects inactive/blocked accounts.

### 4.2 Furniture/products — `/products`

| Method and route | Purpose / permissions |
|---|---|
| `GET /products` | Public approved product list; supports search, category, minimum/maximum price, skip, and limit. |
| `GET /products/{product_id}` | Fetches a product by ID. |
| `GET /products/mine` | Seller/admin: products owned by the current user (or all, for admin semantics). |
| `GET /products/pending` | Admin: products waiting for approval. |
| `POST /products` | Seller/admin: creates a product; seller-created products start pending. |
| `PUT /products/{product_id}` | Seller/admin: update allowed product fields, subject to ownership. |
| `DELETE /products/{product_id}` | Seller/admin: deletes only if order history does not reference it. |
| `PATCH /products/{product_id}/status` | Admin: approve, reject, or return product to pending. |

Product attributes: ID, name, category, short/full description, price, MRP, stock, image URL, status, seller ID, creation date.

### 4.3 Designer profiles and bookings

| Method and route | Purpose / permissions |
|---|---|
| `GET /designers` | Public list of approved designers. |
| `POST /designers` | Admin creates a designer profile for an existing user and assigns designer role. |
| `PATCH /designers/{designer_id}/status` | Admin sets approved/pending/suspended. |
| `PATCH /designers/me/availability` | Designer flips availability. |
| `POST /bookings` | Logged-in customer creates a booking. |
| `GET /bookings/mine` | Customer views their own bookings. |
| `GET /bookings/designer` | Designer views booking requests assigned to them. |
| `PATCH /bookings/{booking_id}/status` | Designer updates booking status. |

Booking data includes the customer contact fields, project type, date, number of days, extra details, calculated total amount, booking status, and created timestamp.

### 4.4 Orders — `/orders`

| Method and route | Purpose / permissions |
|---|---|
| `POST /orders` | Creates an order from product IDs and quantities; server looks up the actual prices. |
| `GET /orders/mine` | Customer views their own orders. |
| `GET /orders/seller` | Seller/admin view order items associated with their products. |
| `PATCH /orders/items/{item_id}/status` | Seller/admin updates an item status (placed, packed, shipped, delivered, cancelled). |
| `PATCH /orders/items/{item_id}/cancel` | Customer cancels their own item only while it is still `placed`. |

**Payment limitation:** `payment_method` can be COD/UPI/card-like labels, but the current backend does not connect a payment gateway. `payment_status` defaults to `pending`. No real UPI/card charge or payment webhook is implemented.

### 4.5 Saved designs — `/designs`

| Method and route | Purpose |
|---|---|
| `POST /designs` | Save title, prompt, space type, structured requirements, and image URL. |
| `GET /designs/mine` | Fetch the signed-in user's saved designs. |
| `DELETE /designs/{design_id}` | Delete a saved design owned by the current user. |

These routes can persist structured design requirements today. The image URL field does not imply that image generation or uploaded-photo storage is working.

### 4.6 AI editor — `/ai`

| Method and route | Purpose |
|---|---|
| `POST /ai/edit-requirements` | Applies a text/voice command to structured design requirements and returns an updated prompt. Requires login. |
| `GET /ai/status` | Reports whether the active text engine is `claude` or `rules`. |

There is a small in-memory rate limit of 20 AI commands per user per minute. It resets when the backend restarts. The rules fallback understands only the terms and patterns coded into `ai_editor.py`; Claude is used if an Anthropic API key is present and usable. If a Claude call fails, the implementation is designed to fall back to the rules engine (also covered by tests).

### 4.7 Admin — `/admin`

Every admin route is protected by `require_role("admin")`.

| Method and route | Purpose |
|---|---|
| `GET /admin/stats` | Returns dashboard counts and calculated revenue. |
| `GET /admin/users` | List users with optional search and role filter. |
| `PATCH /admin/users/{user_id}/role` | Change a user's role among user/seller/designer/admin. |
| `PATCH /admin/users/{user_id}/block` | Toggle whether a user is active; admin cannot block themselves. |
| `GET /admin/orders` | List all orders. |

### 4.8 Common error codes

| Code | Meaning in this project |
|---:|---|
| `200` | Request succeeded. |
| `201` | Resource created. |
| `400` | Invalid operation (e.g. email already registered or invalid status). |
| `401` | Missing, invalid, or expired login token; or wrong email/password. |
| `403` | Signed-in account lacks permission, or account is blocked. |
| `404` | Requested product/user/booking/design/order item not found or not owned by requester. |
| `422` | Request body/query did not pass validation. |
| `429` | Too many AI commands in the rate-limit window. |
| `500` | Unhandled server error. Check the backend terminal. |

---

## 5. Database design

The backend uses SQLAlchemy models stored in a SQLite database (default filename: `roomora.db`, relative to the backend working directory unless `DATABASE_URL` is changed).

### 5.1 `users`

Stores user identity and login info: ID, name, unique email, mobile, hashed password, role, active/blocked status, and creation time.

Roles in the code: `user`, `seller`, `designer`, `admin`.

### 5.2 `products`

Stores furniture listings and their seller link: name, category, descriptions, price, MRP, stock, image URL, approval status, seller ID, created date.

Product statuses: `pending`, `approved`, `rejected`.

### 5.3 `designer_profiles`

Stores specialities, price/day, availability, status, and the related user ID. Each user can have at most one designer profile.

### 5.4 `bookings`

Stores customer-to-designer booking requests, project details, start date, number of days, calculated amount, current status, and creation date.

### 5.5 `orders`

Stores a customer's checkout: total amount, payment method/status, delivery/contact fields, and timestamp.

### 5.6 `order_items`

Stores individual products inside an order. This allows each product to be associated with its seller and to have its own shipping status. Product name and price are copied into the order item so past orders remain consistent if a listing changes later.

### 5.7 `saved_designs`

Stores the user's title, prompt, space type, JSON requirements, image URL, and created date. It can support saving text-based design plans. Version history for generated images has not yet been modeled.

---

## 6. Demo accounts

These are the demo credentials documented by `seed.py`/`README.md`. They work only if the database was seeded successfully and the frontend is connected to the same backend login flow (or if a local demo login implementation uses the same mapping).

| Role | Email | Password |
|---|---|---|
| Admin | `admin@roomora.com` | `Admin@1234` |
| Seller | `seller@roomora.com` | `Seller@1234` |
| User | `user@roomora.com` | `User@1234` |
| Designer | `saumya@roomora.com` | `Designer@1234` |
| Designer | `ruchi@roomora.com` | `Designer@1234` |
| Designer | `shreyash@roomora.com` | `Designer@1234` |
| Designer | `dhwanit@roomora.com` | `Designer@1234` |
| Designer | `rich@roomora.com` | `Designer@1234` |
| Designer | `anaya@roomora.com` | `Designer@1234` |

The seed function checks whether the database already contains a user. If it does, the script stops instead of updating existing records. Do not repeatedly rerun `seed.py` expecting edits to the product list to update an existing database. Do not delete `roomora.db` casually: that would erase local data.

---

## 7. Current known problems and unfinished work

This is the central problem checklist. Each item should remain open until tested and verified on the actual local project.

### 7.1 Admin and seller login redirect — currently unresolved

**Observed behavior:** Admin/seller credentials still redirect to the user side even after a code update and hard refresh.

**Original root cause:** The original `login.html` listener always redirected to `user.html` after only checking that both fields were nonempty.

**Why it may still happen:** The browser may be loading a different file, the server may be started from the wrong folder, another script/listener may perform a later redirect, or the frontend may not be using the backend role response.

**Correct durable approach:** Replace the front-end-only login handler with a single API-backed handler:

1. POST email and password to `http://127.0.0.1:8000/auth/login`.
2. Check `response.ok`; show `data.detail` if login fails.
3. Save `data.access_token` in `localStorage` as `roomoraToken`.
4. Read `data.user.role` from the response.
5. Redirect based on role to the matching relative path.
6. Remove duplicate login submit handlers or leftover `window.location.href = "user.html"` logic that affects the form.
7. Confirm the browser is viewing the same file being edited.

The backend role-checking routes are stronger than a front-end role string, but static pages also need front-end role checking to avoid confusing navigation. API protection must remain the actual security boundary.

### 7.2 Login is not reliably connected to FastAPI

The original frontend login did not call the backend. It just checked for nonempty fields and redirected. A demo mapping can help test navigation but is not authentication. The backend already offers `POST /auth/login` and returns a role; use that route rather than hard-coding passwords into JavaScript.

### 7.3 Signup does not create a backend account from the frontend

The original signup handler validated the form and displayed an alert but did not call `POST /auth/signup`. This means the browser can say an account was created even though no database record exists. It must send name/email/mobile/password to the backend and show API errors correctly.

### 7.4 Forgot password is a placeholder

No complete reset-token workflow and production reset email are confirmed. The existing alert is only a placeholder.

### 7.5 Email sending / verification is incomplete

The original login/signup page displayed wording suggesting a confirmation/security email might be sent. The inspected backend ZIP did not contain a complete production `app/email_service.py` or signup email integration. A `test_email.py` exists in the recovery pack, but that alone is not a complete signup/order/booking email system. Welcome, order confirmation, booking notifications, password reset, and verification emails remain unfinished.

### 7.6 Actual room image generation/editing is not implemented

This is a major product requirement: upload a room photo, generate a realistic redesigned result, then edit the result repeatedly through English and Hindi text prompts. The current backend AI route edits structured requirements only. There is no verified endpoint to upload a room image and return generated/edited image output. Need identify the image-generation tool the user already has, confirm API access and input-image editing, and then implement a backend adapter for it.

### 7.7 AI editor is not the same as image generation

The text editor can update requirements such as wall color, budget, furniture, style, and lighting, then create a text prompt. It doesn't render a new image. The AI result box being a placeholder is documented in the backend README.

### 7.8 AI editor token key may not match login storage

The provided `ai-editor.js` expects `localStorage.getItem("roomoraToken")`. The front-end-only demo redirect code stores only `roomoraRole` and `roomoraEmail`. Until login uses the backend and stores `access_token` under `roomoraToken`, requests to the protected AI route can fail with `401 Please login first`.

### 7.9 Product and designer data may still be hard-coded in the frontend

The backend README identifies replacing hard-coded product/designer arrays with `fetch(API + "/products")` and `fetch(API + "/designers")` as a next step. If so, changes made in SQLite or seller/admin API will not necessarily show up in the frontend until these arrays are replaced with API data.

### 7.10 Marble Coffee Table / product image is broken

A product card was observed with a broken or missing image. The current image fallback may display a placeholder, but the actual product photo was not loading. Potential reasons include a bad external image URL, a wrong local path, or edits made in `seed.py` without updating the already-populated SQLite product row.

For a local image, place it inside the frontend static directory and use a URL path served by the frontend, not a Windows path. If products are API-backed, update `products.image_url` in the database/API; if still hard-coded, update the frontend product data. Test the image URL directly in a browser.

### 7.11 Cart still uses browser storage, and checkout integration is incomplete

The frontend cart uses localStorage. The backend has an order API but the README lists connecting the cart to `POST /orders` as a next step. Cart persistence in one browser is not the same as a saved server-side order.

### 7.12 Payments are not real

The backend records payment method and a pending status; it does not charge UPI/card payments. A real payment integration would require a gateway (e.g., Razorpay), server-side order verification, and a webhook. Until then, describe checkout as demo/COD or order-recording functionality, not completed online payment.

### 7.13 Booking, saved designs, and product CRUD need frontend verification

The relevant FastAPI routes exist, but the frontend forms/buttons must be tested against those routes with bearer tokens and correct roles. The existence of an endpoint does not guarantee the corresponding front-end button is connected.

### 7.14 Reviews, ratings, portfolio upload, and other extras are unfinished

Project notes refer to Reviews pages/buttons in seller/designer screens, inventory alerts, CSV exports, portfolio upload, designer chat/WhatsApp, AR preview, wishlist, comparison, and order tracking timeline. The current backend models/routes inspected do not provide complete review/rating or portfolio storage APIs. Treat these as future or partially built features until implemented and tested.

### 7.15 Development configuration is not production safe

- `SECRET_KEY` defaults to a known development value; replace it in `.env` before deployment.
- CORS currently uses `allow_origins=["*"]`; restrict it to the actual website origin before deployment.
- Demo credentials must not be used in production.
- Do not expose API keys in browser JavaScript or commit `.env`.
- SQLite is acceptable for a simple local project but may be unsuitable for high-concurrency production use.
- Static frontend pages alone do not enforce authorization; role-protected API routes remain essential.

---

## 8. How to run Roomora AI locally on Windows

These steps reflect the previously used local folder layout. The exact paths should be adjusted if the folder has moved.

### A. Start the backend

1. Open the project root in VS Code:
   `C:\Users\Admin\Desktop\Saumya\UDP Project\UDP_Roomora_AI`
2. Open **Terminal → New Terminal**.
3. Move into the backend folder:

```powershell
cd "C:\Users\Admin\Desktop\Saumya\UDP Project\UDP_Roomora_AI\roomora_backend"
```

4. Activate the virtual environment if it exists:

```powershell
.\venv\Scripts\Activate.ps1
```

If PowerShell blocks activation, use the virtual environment's interpreter directly:

```powershell
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

If the virtual environment does not exist, create it and install dependencies:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install --upgrade pip
.\venv\Scripts\python.exe -m pip install -r requirements.txt
.\venv\Scripts\python.exe -m uvicorn app.main:app --reload
```

Keep the backend terminal open. Open `http://127.0.0.1:8000/docs`; the interactive API docs should load. `http://127.0.0.1:8000/` should return a JSON health response.

### B. Start the frontend

1. Open a second terminal in VS Code (do not stop the backend terminal).
2. Change to the frontend folder:

```powershell
cd "C:\Users\Admin\Desktop\Saumya\UDP Project\UDP_Roomora_AI\Roomora_AI\user"
```

3. Start the static server:

```powershell
python -m http.server 5500
```

4. Keep that terminal open and visit:
   `http://localhost:5500/login.html`

The backend listens on port 8000; the frontend static server listens on port 5500. Both must be running for frontend API calls to work.

### C. Starting by helper file

A `start_roomora.bat` helper was produced during the conversation and is intended to launch both servers in separate command windows. It needs to sit in the project root next to `roomora_backend` and `Roomora_AI`. Verify the backend virtual environment path (`venv\Scripts\python.exe`) and frontend path inside the file. If it doesn't open the website automatically, the URLs can still be entered manually.

### D. Database/seed warning

The backend automatically creates tables when it starts. The seed script is designed to run once against an empty database. It exits if any user data already exists. Do not delete the database to fix a product image or to apply unrelated code changes unless you explicitly intend to discard the saved records.

---

## 9. Environment variables and external services

The inspected `config.py` reads environment variables through `python-dotenv`. Known settings include:

| Setting | Purpose | Current note |
|---|---|---|
| `SECRET_KEY` | Signs JWT access tokens. | Has a development default; replace before deployment. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Token lifetime. | Defaults to 1440 minutes (24 hours). |
| `DATABASE_URL` | Database connection string. | Defaults to local SQLite `sqlite:///./roomora.db`. |
| `ANTHROPIC_API_KEY` | Enables the Claude-based text requirements editor. | Optional; rules fallback runs without it. |
| `AI_MODEL` | Claude model identifier. | Reads configured value, default shown in code is `claude-sonnet-5-5`. Verify against the actual Anthropic account/API availability before relying on it. |

An OpenAI API key is **not** used by the currently inspected backend. The user has said they already have another image-generation tool; its name/API capability remains unknown. Do not add an OpenAI API key or spend money on OpenAI API billing unless that provider is deliberately selected.

Never commit `.env` or secret API keys to GitHub. If a key is ever published accidentally, revoke/rotate it.

---

## 10. Testing and debugging checklist

### Login redirect

- Verify browser URL is exactly `http://localhost:5500/login.html`.
- View page source with Ctrl+U and verify it contains a marker from the saved file.
- Confirm the frontend server was launched inside `Roomora_AI/user` and not a different folder.
- Search the workspace (Ctrl+Shift+F) for `window.location.href = "user.html"` and review all results.
- Ensure only one login submit handler handles the form.
- Open browser Developer Tools (F12) → Console and Network to see JavaScript errors or failed `POST /auth/login` requests.
- Test backend login in `http://127.0.0.1:8000/docs` using `POST /auth/login` and check that the response includes `user.role`.
- If login succeeds but route is wrong, use the role returned by the backend—not the email text guessed on the frontend.

### Backend reachability

- `GET http://127.0.0.1:8000/` should return status information.
- `http://127.0.0.1:8000/docs` should open.
- `GET /products` should respond with a JSON list (approved product list).
- If a protected endpoint returns `401`, check whether the token is being sent as a Bearer token.
- If it returns `403`, verify account role and permissions.
- If browser Console reports CORS, check `CORSMiddleware` in `app/main.py`.

### Product images

- Open the exact image URL directly in a browser.
- Check whether the product uses a hard-coded frontend `image`/`image_url` field or data from `GET /products`.
- For a local asset, check file placement under `Roomora_AI/user/images/` and use the relative URL from the page.
- If changing seeded data, update the existing database row or use the update API; `seed.py` does not update populated data.

### AI text editor

- Make sure the backend is running.
- Make sure the AI editor script has been copied next to `user.html` and included with `<script src="ai-editor.js"></script>`.
- Make sure the `designPrompt` element exists.
- Make sure login stores a valid backend token as `roomoraToken`.
- Check `GET /ai/status` to see whether `claude` or `rules` is active.
- If using the rules fallback, test only supported words/phrases and remember it is not a full language model.
- For voice input, use Chrome/Edge over localhost and allow microphone permission.

### Automated backend tests

The project includes `tests/test_api.py` with a full-jump/journey test and tests for English, Hindi, Hinglish, Claude fallback, and a mocked Claude response. They can be run from the backend folder after dependencies are installed:

```powershell
python -m pip install pytest httpx
pytest -v
```

Tests were not executed as part of writing this document; run them in the user's working copy to confirm the current environment.

---

## 11. Feature status matrix

Status key:
- **Backend present:** relevant FastAPI route/model exists in the inspected backend.
- **Frontend present / needs verification:** UI exists or is referenced, but integration is not confirmed.
- **Placeholder / not implemented:** discussed feature is not yet a working end-to-end flow.

| Feature | Status | Notes |
|---|---|---|
| Login UI | Frontend present | `login.html` has the form and tabs. |
| Backend login | Backend present | `POST /auth/login` returns token + user role. |
| Correct admin/seller redirects | **Unresolved** | User still reports redirecting to the user side. |
| Signup UI/validation | Frontend present | The original handler does not create a backend account. |
| Backend signup | Backend present | `POST /auth/signup`; frontend integration still needs to be made/rechecked. |
| Forgot password | Placeholder | No verified end-to-end reset email flow. |
| User product grid | Frontend present | Hard-coded vs API-backed source needs confirmation. |
| Products API | Backend present | Search/filter, seller CRUD, admin approval. |
| Product image fallback | Frontend present | Marble Coffee Table image was broken; source/data update needs verification. |
| Local product-image serving | Feasible | Must use a web URL/path, not a Windows filesystem path. |
| Browser cart | Present/referenced | Uses localStorage. |
| Order API | Backend present | Frontend checkout must post items/contact details to `POST /orders`. |
| Payment processing | Not implemented | Payment status remains pending; no gateway/webhook. |
| Designer list | Backend present | Public list of approved designers. Frontend data integration needs verification. |
| Designer booking API | Backend present | Booking form connection needs verification. |
| Designer availability | Backend present | Requires designer role/token. |
| Saved requirements/design API | Backend present | Stores requirements and optional image URL, not an image-generation pipeline. |
| AI text requirements editor | Backend present | Claude or rules fallback; English/Hindi-oriented. |
| AI editor floating UI | Provided script | Must be copied/added and receive `roomoraToken`. |
| Voice input | Provided frontend code | Browser speech recognition; microphone permission required. |
| Real room-photo upload | Not implemented end-to-end | Desired feature not present in inspected backend. |
| AI-generated room redesign image | Not implemented | Result area is a placeholder. |
| Repeated image edits in English/Hindi | Not implemented end-to-end | Need image-editing API and version history. |
| Admin dashboard statistics | Backend present | `GET /admin/stats`; frontend must fetch it. |
| Admin user/role/block management | Backend present | Must use admin token. |
| Admin product approval | Backend present | Must connect UI to pending/status routes. |
| Seller product management | Backend present | Route permissions/ownership checks exist. |
| Seller order updates | Backend present | Per-item status model. |
| Designer booking workflow | Backend present | Frontend integration should be verified. |
| Reviews/ratings | Incomplete | UI references in notes; no complete backend model/routes found. |
| Designer portfolio upload | Not implemented in inspected backend | Mentioned as a possible future feature. |
| CSV export / inventory alerts | Needs verification/future work | Referenced by project notes; not confirmed end-to-end. |
| Email confirmation/order/booking mail | Incomplete | No complete production mail integration found. |
| Database seed data | Present | Admin, seller, user, six designers, ten products, but runs only for empty DB. |
| Automated API tests | Present | Need to run locally to confirm current state. |

---

## 12. Recommended next work order

To keep the project stable, complete the following in order rather than editing multiple pages at once.

### Priority 1 — Fix and unify authentication

1. Confirm the file served by `http://localhost:5500/login.html` is the same file being edited.
2. Remove the original hard-coded redirect and duplicate submit handlers.
3. Connect `login.html` to `POST /auth/login`.
4. Save `data.access_token` as `roomoraToken`.
5. Route according to `data.user.role`.
6. Connect signup to `POST /auth/signup` and display backend validation errors.
7. Add frontend role-aware redirects/guards on dashboards, while keeping API role checks as the actual security control.
8. Test all four roles against the seeded database.

### Priority 2 — Connect existing website UI to the current API

1. Replace hard-coded product arrays with `GET /products` (keeping filters if the UI has them).
2. Replace hard-coded designer arrays with `GET /designers`.
3. Connect seller product forms to product CRUD routes.
4. Connect admin product approval, user management, and statistics screens to admin endpoints.
5. Connect the customer checkout/cart to `POST /orders` and show orders from `GET /orders/mine`.
6. Connect designer booking form and the customer/designer booking lists.
7. Connect Save Design and saved-design list/delete to `/designs`.

### Priority 3 — Fix image source handling

1. Confirm whether product cards currently render hard-coded frontend data or API JSON.
2. Fix the Marble Coffee Table image in the correct source (frontend data or database).
3. Use a valid tested image URL or serve a local image from the frontend images directory.
4. Verify every image URL in the browser and keep the fallback behavior.

### Priority 4 — Implement room image generation with the tool the user already has

1. Identify the exact tool name.
2. Confirm API access and that the tool supports **editing an uploaded image using text instructions**, not just generating new images.
3. Read its official API documentation and confirm cost/rate limits.
4. Store provider credentials in backend `.env`.
5. Add secured FastAPI routes for upload, initial redesign, and subsequent image edit.
6. Store the original and each generated version without overwriting prior images.
7. Build the frontend upload preview, loading/error state, before/after view, prompt input, edit history, and save/download controls.
8. Test at least one English prompt and one Hindi prompt against the same reference room.
9. Keep the current text requirements editor; it can help formulate design prompts and remain useful even with a different image provider.

### Priority 5 — Finish production-style flows

- Implement forgot-password token + email.
- Add proper email service (signup verification, order/booking notifications if required).
- Add a payment gateway only if real online payment is a project requirement.
- Add reviews/ratings and designer portfolio APIs if those pages must be functional.
- Add image file limits, access checks, and safe storage.
- Replace the default JWT secret, restrict CORS, and remove demo credentials before deployment.
- Add configuration/setup instructions and a concise demo script for presentation/viva.

---

## 13. Suggested final demo walkthrough

A clean project presentation can demonstrate the parts that are working and be transparent about unfinished features:

1. Start backend and frontend in separate terminal windows.
2. Open `/docs` and show the running FastAPI app.
3. Sign in with the user demo account and show the customer page.
4. Explain the room-design requirement model and demonstrate the text AI editor with an English command and a Hindi command, if the AI editor is correctly connected to the backend.
5. Show product cards and explain how approved products are served through the products API (after API connection is completed).
6. Explain the cart/order workflow and clarify that payment gateway integration is not implemented yet.
7. Sign in as seller to demonstrate product and order-management APIs once the dashboard integration is connected.
8. Sign in as designer to demonstrate availability and booking workflow once the dashboard integration is connected.
9. Sign in as admin to demonstrate dashboard statistics, user roles, product approval, and order overview.
10. Explain the planned actual-photo redesign flow and show it only once an image provider is selected and connected. Do not describe the current text editor as a finished image generator.

---

## 14. Final state in one paragraph

Roomora AI is a local HTML/CSS/JavaScript frontend with a FastAPI/SQLite backend. The backend defines real data models and API routes for authentication, furniture products, designer profiles and bookings, orders, saved design requirements, admin operations, and a multilingual text-based design-requirements editor using Claude or a rule fallback. The frontend includes the login/signup design, product cards, and role-specific dashboard files, but several forms and listings have not yet been consistently connected to the backend. The known issues include the admin/seller login still redirecting to the user side, signup/forgot-password/email flows not being fully integrated, a broken Marble Coffee Table image, uncertainty over hard-coded versus API-backed frontend data, checkout/cart integration gaps, no real payment gateway, and no end-to-end upload/AI room-image generation/editing. The next safest step is to fix role-based backend login, connect the existing UI to the APIs, and then integrate the user's existing image-generation tool once its name and API capabilities are confirmed.

---

## Appendix A — Useful local URLs

| Purpose | URL |
|---|---|
| Frontend login | `http://localhost:5500/login.html` |
| Customer page | `http://localhost:5500/user.html` |
| Admin dashboard | `http://localhost:5500/admin/admin.html` |
| Seller dashboard | `http://localhost:5500/admin/seller/seller.html` |
| Designer dashboard | `http://localhost:5500/admin/seller/designer/designer.html` |
| FastAPI health | `http://127.0.0.1:8000/` |
| FastAPI interactive docs | `http://127.0.0.1:8000/docs` |
| FastAPI alternate docs | `http://127.0.0.1:8000/redoc` |
| Product list API | `http://127.0.0.1:8000/products` |
| AI status API | `http://127.0.0.1:8000/ai/status` |

---

## Appendix B — Key frontend-to-backend wiring reference

The backend README's intended login flow is conceptually:

```javascript
const API = "http://127.0.0.1:8000";

const response = await fetch(API + "/auth/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
        email: document.getElementById("loginEmail").value,
        password: document.getElementById("loginPassword").value
    })
});

const data = await response.json();

if (!response.ok) {
    alert(typeof data.detail === "string" ? data.detail : "Login failed");
    return;
}

localStorage.setItem("roomoraToken", data.access_token);

const pages = {
    user: "user.html",
    admin: "admin/admin.html",
    seller: "admin/seller/seller.html",
    designer: "admin/seller/designer/designer.html"
};

window.location.href = pages[data.user.role];
```

This is a wiring reference, not a full drop-in replacement for the entire form handler. The real implementation should catch network errors, ensure the returned role has a valid mapping, and avoid duplicate event listeners.

---

## Appendix C — Repository and source notes

The original backend ZIP included `README.md`, `FASTAPI_GUIDE.md`, `IDEAS.md`, the FastAPI app, route files, schema/model/security files, the text AI editor, a frontend AI editor script, API helper, requirements, seed data, and API tests. The separate recovery pack included additional copies and files such as `.env.example` and `test_email.py`, but did not demonstrate a complete production mail service or image-generation endpoint. This distinction matters when comparing the extracted package with the live working directory.

The current live frontend should be rechecked before making large changes. Preserve the existing visual design and page files; prefer connecting their controls to the existing backend rather than replacing the project with a new app.
