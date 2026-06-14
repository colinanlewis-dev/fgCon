# fgCon

A concession stand ordering and management web app built for field game events. Staff use it to take orders, manage menus, track combos, and view sales reports — all from a browser with no native app required.

## Features

- **Menu Manager** — Add, edit, and organize menu items by type (Cooked, Fresh, Side, Drink) and menu (e.g. Breakfast, Dinner). Toggle availability and mark items as combo sides.
- **Event Manager** — Create and manage events with a date, guest size, and assigned menu type. Only one event is active at a time.
- **Combo Manager** — Define combo meal settings (main + drink + side) with a max drink/side cost contribution and a combo surcharge. The orders page automatically finds the best combo combination per cart.
- **Orders** — Build and place orders against the active event. Supports:
  - Per-type item tiles (Cooked / Fresh / Side / Drink) with a quantity picker
  - Automatic combo detection with inline discount display on the main item
  - Fresh Items ½ Price toggle for end-of-event sell-down
  - VIP (complimentary) orders with an optional name/note
  - Cash or Venmo payment selection
  - Popular items panel showing the top 5 most-ordered items for the event
- **Reports** — Event and season-level reporting with Chart.js visualizations:
  - Revenue by item type (doughnut), top 10 items by revenue (bar)
  - Season revenue and order count per event (bar), top items across all events
  - Payment method breakdown with order count and total revenue
- **Authentication** — Password-gated login screen with signed 30-day session cookies. All pages and API routes require a valid session.

## Tech Stack

| Layer | Tech |
|-------|------|
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
└── templates/
    ├── home.html         # Landing page / nav grid
    ├── login.html        # Password login screen
    ├── menu.html         # Menu Manager
    ├── events.html       # Event Manager
    ├── combos.html       # Combo Manager
    ├── orders.html       # Order entry
    └── reports.html      # Reports dashboard
```

## Database Tables

| Table | Description |
|-------|-------------|
| `menuType` | Menu categories (e.g. Dinner, Breakfast) |
| `menu` | Menu items with type, cost, availability, and combo-side flag |
| `event` | Events with date, size, active status, and linked menu type |
| `orders` | Placed orders with VIP flag, combo flag, and payment method |
| `orderItems` | Line items per order with quantity and price at time of sale |
| `comboSettings` | Combo definitions with max drink/side cost contributions |

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
|----------|-------------|
| `SUPABASE_URL` | Your Supabase project URL |
| `SUPABASE_KEY` | Supabase anon/service key |
| `APP_PASSWORD` | Shared password for the login screen |
| `APP_SECRET` | Random string used to sign session cookies |

After adding or changing env vars, redeploy for them to take effect.

## Authentication

All routes are protected by a shared password. On first visit, users are redirected to `/login`. A correct password sets a signed `httponly` session cookie valid for 30 days. The cookie is signed with `APP_SECRET` using HMAC-SHA256, so it cannot be forged without the secret.
