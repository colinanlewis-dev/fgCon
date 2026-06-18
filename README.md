# fgCon — Farmington Glen Concessions

A concession stand ordering and management web app built for Farmington Glen swim meets. Staff use it to take orders, manage menus, track combos, log runner costs, and view sales reports — all from a browser or installed PWA with no native app required.

## Features

### Orders
- Per-type item tiles (Cooked / Fresh / Snacks / Side / Drink) with quantity picker
- **Popular Items tile** — top 8 most-ordered items for the active event, updated as orders come in
- **Heat Sheet quick-add bar** — one-tap add/remove for non-food items (e.g. heat sheets)
- Automatic combo detection with inline discount display
- **Fresh Items ½ Price toggle** — instantly reprices Fresh and Cooked items to 50% off for end-of-event sell-down
- VIP (complimentary) orders with Home/Away team selection and optional name/note
- Cash or Venmo payment selection with cash tendered input and change calculation
- **Offline order queue** — orders placed without internet are saved locally and automatically synced when connection returns. Queued orders are visible in the Recent Orders list with a "Pending sync" indicator.

### Order Management
- **Recent Orders** list with per-order item summary, total, and VIP/Combo badges
- Edit any past order — adjust quantities, change payment method, update VIP status
- Delete orders with confirmation

### Menu Manager
- Add, edit, and organize items by type and menu (e.g. Breakfast, Dinner)
- Toggle availability per item
- Mark items as **Combo Main** or **Combo Snack** for combo eligibility
- Inline row editing with no page reload

### Event Manager
- Create and manage events with date, home/away team size, weather, seed money, meet cost, and notes
- **Meet Prep fields** — dynamic per-fresh-item prep quantity inputs, stored and parsed automatically
- Only one event is active at a time; setting a new event active deactivates others

### Runners / Returns
- Log supply runs made during a meet with item description and cost
- Runner costs feed into the Cashbox Total and season profit calculations

### Combo Manager
- Define combo meal settings (main + snack + drink) with max cost contributions and a combo surcharge
- Orders page automatically finds the best combo combination per cart and applies the discount

### Reports
- **Event Report** — Total revenue, orders, average order, combos used, and Cashbox Total (cash revenue + seed money − runner costs). Revenue by item type (doughnut chart), top 10 items by revenue (bar chart), payment method breakdown.
- **Season Report** — Revenue and order count per event (bar chart), top items across all events, total meet costs, total runner costs, and **Total Profit** (revenue − meet costs − runner costs).

### Authentication
- Password-gated login with signed 30-day session cookies
- All pages and API routes require a valid session

### PWA / Offline
- Installable on Windows, Mac, iPhone, iPad, and Android via browser "Add to Home Screen" / install prompt
- App shell and menu data cached on first load for fast startup on slow connections
- Offline banner displayed automatically when connectivity is lost
- Order queue persists across page reloads — no orders are lost if the device goes offline mid-meet

## Tech Stack

| Layer | Tech |
|---|---|
| Backend | [FastAPI](https://fastapi.tiangolo.com/) (Python) |
| Database | [Supabase](https://supabase.com/) (PostgreSQL via PostgREST) |
| Frontend | Vanilla HTML/JS (no framework) |
| Charts | [Chart.js 4.4](https://www.chartjs.org/) (CDN) |
| Hosting | [Vercel](https://vercel.com/) (serverless) |

## Project Structure

```
├── main.py               # FastAPI app — all routes and business logic
├── database.py           # Supabase client initialization
├── api/index.py          # Vercel serverless entry point
├── vercel.json           # Vercel rewrite config
├── requirements.txt      # Python dependencies
├── .env.example          # Environment variable template
├── static/
│   ├── glemons.png       # Season mascot image (shown on home and login pages)
│   ├── manifest.json     # PWA manifest
│   └── sw.js             # Service worker (caching + offline queue support)
└── templates/
    ├── home.html         # Landing page with Meet Tools / Meet Management sections
    ├── login.html        # Password login screen
    ├── menu.html         # Menu Manager
    ├── events.html       # Event Manager
    ├── combos.html       # Combo Manager
    ├── orders.html       # Order entry with offline queue
    ├── runners.html      # Runners / Returns log
    └── reports.html      # Event and season reports dashboard
```

## Database Tables

| Table | Description |
|---|---|
| `menuType` | Menu categories (e.g. Dinner, Breakfast) |
| `menu` | Menu items with type, cost, availability, combo-main, and combo-snack flags |
| `event` | Events with date, team sizes, active status, seed money, meet cost, prep notes, and linked menu type |
| `orders` | Placed orders with VIP flag, combo flag, and payment method |
| `orderItems` | Line items per order with quantity and price at time of sale |
| `comboSettings` | Combo definitions with max drink/side cost contributions |
| `runners` | Runner log entries with event, description, and cost |

## Local Development

1. **Clone the repo and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Create a `.env` file** (use `.env.example` as a template):
   ```
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-anon-key
   APP_PASSWORD=your-chosen-password
   APP_SECRET=a-long-random-secret-string
   ```

3. **Run the dev server:**
   ```bash
   uvicorn main:app --reload
   ```

4. Open [http://localhost:8000](http://localhost:8000).

## Deployment (Vercel)

```bash
npx vercel --prod
```

Set the following environment variables in **Vercel → Project → Settings → Environment Variables**:

| Variable | Description |
|---|---|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/service key |
| `APP_PASSWORD` | Shared password for the login screen |
| `APP_SECRET` | Random string used to sign session cookies |

After adding or changing env vars, redeploy for them to take effect.

## Authentication

All routes are protected by a shared password. On first visit, users are redirected to `/login`. A correct password sets a signed `httponly` session cookie valid for 30 days. The cookie is signed with `APP_SECRET` using HMAC-SHA256 and cannot be forged without the secret.

## PWA Installation

| Platform | Browser | How to install |
|---|---|---|
| Windows / Mac | Chrome or Edge | Click the install icon in the address bar, or browser menu → "Install app" |
| Mac | Safari (Sonoma+) | Share → "Add to Dock" |
| iPhone / iPad | Safari | Share → "Add to Home Screen" |
| Android | Chrome | "Add to Home Screen" banner or browser menu |

Once installed, the app opens full-screen with no browser chrome. The menu and app shell are cached on first load so the app is usable even when pool-deck WiFi is unreliable.
