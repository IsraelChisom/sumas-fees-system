# SUMAS Fees Project — Design Brief

This is the authoritative visual design brief for the SUMAS Fees System,
given verbatim by the project owner and implemented across the app's
existing pages. **Every page or module built from now on must follow this
brief automatically** — it supersedes the earlier brown/gold "Design
system" description in `PROJECT_BRIEF.md`, which was a generic first pass.

## The brief

A complete visual redesign of the existing pages (login, student
dashboard, admin dashboard, student list, student form, fees list, fee
form) — professional and distinctive enough to genuinely impress a
university supervisor and lecturers at first glance, not a generic
default-looking AI template.

### Ground the design in what this actually is

This is an official school fees and receipt system for a university, so
it should feel institutional, trustworthy, and precise — closer to a bank
statement or an official certificate than a generic startup SaaS
dashboard.

### Specifically avoid these common AI-generated design tells

- A warm cream background with a terracotta/orange accent
- Every panel as an identical rounded card with the same soft grey shadow
- ALL-CAPS tracked-out labels above every heading
- Numbered badges (01 / 02 / 03) on things that aren't actually a sequence
- Buttons with a "→" arrow appended to the text
- Generic fade-in-on-scroll animation on every section
- Animated numbers counting up on dashboard stats, animated gradients,
  hover animations on every card/row

### Color — the school's actual brand colors are brown and white

- **Primary:** deep espresso brown `#3E2723` (dark and authoritative, like
  an old ledger cover — not a light coffee-shop terracotta)
- **Secondary brown:** warm coffee tan `#8B5E3C`, for secondary
  buttons/borders
- **Background:** warm ivory `#FAF6F0` (paper-like, not stark white)
- **Accent** (use sparingly — 1–2 places per page only, not everywhere):
  deep antique gold `#B8935A`, evoking an official seal — for the active
  sidebar indicator and primary call-to-action buttons
- **Body text:** warm near-black `#2B211D`, not pure black
- **Status colors stay functional and conventional, NOT brown-tinted**, so
  they remain instantly readable: muted green `#2F855A` (confirmed), muted
  amber `#B7791F` (pending), muted red `#C53030` (rejected)

### Typography

- **Headings:** "Lora" (serif, via Google Fonts) — classic, official,
  letterhead feel appropriate to a university document
- **Body, data, and tables:** "IBM Plex Sans" (via Google Fonts)

### Layout and motifs — grounded in the subject matter (fees, receipts, official records)

- The receipt page should visually resemble an actual official
  receipt/certificate — a bordered document with the school name at the
  top like a letterhead, not a plain card
- Tables (student lists, fee lists, claims) should look like a clean
  ledger/register: subtle row dividers, no heavy rounded corners,
  right-aligned numeric/currency columns
- Admin sidebar: flat solid espresso-brown background, with a gold
  left-border indicator on the active page — not a floating pill/badge
- Login page: a centered card with clear school branding at the top,
  subtle shadow — a proper product login screen, not a bare form

### Motion — a small number of deliberate, purposeful moments only, each tied to something the user actually did, never decorative or automatic

1. **Claim submission:** a brief, satisfying confirmation animation (e.g.
   a checkmark that draws itself) when a student successfully submits a
   payment claim
2. **Admin confirming a claim:** a short "stamped" animation on the status
   badge as it changes from Pending (amber) to Confirmed (green) — like an
   official approval stamp landing, under half a second
3. **Receipt reveal:** a subtle unfold/reveal effect when a receipt
   becomes available, reinforcing that this is an official document being
   issued
4. Standard 150ms hover transitions on buttons/links are fine and
   expected — this is not decoration, just normal polish

Respect `prefers-reduced-motion` — skip animations and show the end state
instantly if a user has that setting on.

### Framework

Use Bootstrap 5 via CDN for the underlying structure (navbars, forms,
tables) but restyle it fully with the palette and fonts above — it should
not look like default Bootstrap.

## Implementation notes (added during the redesign, for future reference)

- Palette, fonts, and every restyled component live in
  `app/static/css/style.css`. The CSS custom properties were renamed to
  match this palette directly (`--espresso`, `--tan`, `--gold`, `--ivory`,
  `--ink`, plus `--status-confirmed` / `--status-pending` /
  `--status-rejected`) — there's no more legacy `--navy`/`--gold-as-brown`
  aliasing from the previous palette pass.
- Motion moments 1 and 3 are wired up specifically, not generically (see
  PROJECT_BRIEF.md for the payment-claim → invoice workflow redesign that
  moved motion moment 1 from claim submission to invoice generation, and
  built motion moment 3 for the first time):
  - Generating an invoice redirects to its invoice page with
    `?generated=1`; `student/invoice_view.html` reads that flag to show a
    one-time, self-drawing SVG checkmark (`.action-confirmation` in
    `style.css` — a generic class, not claim-specific). It never appears
    on any other success flash.
  - A receipt becomes available the instant a payment is matched
    (`app/payments.py`'s `handle_payment_notification()`), and
    `student/receipt_view.html` always shows it via the `.receipt-reveal`
    unfold animation on `.print-document` — this page only ever renders
    once a receipt exists, so the reveal always plays.
  - Motion moment 2 ("stamped" confirm) doesn't apply anymore: it was
    built for the old admin claim-confirm workflow, which the invoice
    redesign removed entirely (a normal payment is matched automatically,
    with no admin click to animate). The admin exception queue
    (`admin/unmatched_list.html`) uses plain full-page form submits — if a
    future admin action ever again changes a status in front of the
    admin's eyes the way Confirm did, revive this pattern (a small
    fetch()-based script checking for an `X-Requested-With` header, falling
    back to a normal POST + redirect if JS fails) rather than reinventing it.
- Every other animation from the previous design pass (ambient gradient
  drift, floating particles, confetti, animated count-up numbers, card
  hover-lift/glow) was deliberately removed per this brief's avoid-list.
  Only standard button/link hover transitions remain automatic.

## The student section's "Academic Ledger" direction (adopted after the first pass still read as generic)

The first implementation of this brief — while following its letter (the
palette, the fonts, the ledger tables) — still read as a generic AI
dashboard on the student-facing pages specifically: a filled hero card for
the student's info, and a list of quick actions as icon-in-a-box tiles
with trailing chevrons. That's a recognizable SaaS-dashboard pattern, not
an institutional one, and it's what was actually driving the "this feels
like AI design" reaction — not the palette.

Three genuinely different directions were sketched (a design canvas, not
kept) and the student picked **"Academic Ledger"**: typographic and
document-like, closer to a real university portal than a dashboard. It's
now the committed look for the **student section specifically** — the
admin section (sidebar, stat tiles, `.qa-list`/`.qa-item` quick actions)
was deliberately left untouched, since it wasn't the complaint. Concretely,
for student-facing pages:

- **Top strip, not a boxed navbar** (`.record-strip` in `style.css`,
  wired into `base.html`'s non-admin branch): a plain espresso strip — a
  small bordered square crest mark with a single gold-outlined letter, a
  small-caps letter-spaced wordmark, and plain underlined text links
  ("Signed in as NAME" / "Log out"), not a rounded brand-icon box and a
  button-styled logout chip. Capped with a single 2px gold rule
  (`.record-strip-accent`) — the brief's "accent used sparingly" taken
  literally: one deliberate line, not repeated as a border treatment
  everywhere.
- **A bordered record strip, not a hero card** (`.record-panel` /
  `.record-field` — since superseded on the dashboard specifically by
  `.dashboard-header`, see the follow-up below; the identity-strip pattern
  itself is still correct and still used as-is on every other student
  page): the student's name/reg number/department/faculty/level sit in one
  hairline-bordered row with vertical dividers between fields, like a
  table header — no avatar square, no filled background, no gradient.
- **A plain typographic action list, not icon tiles**
  (`.record-actions` / `.record-action-row`): each action is a Lora title
  + muted description, hairline-divided, with a plain gold-underlined
  "Open" text link — no icon glyph, no chevron, no rounded/left-bordered
  box. (`.qa-list`/`.qa-item` — icon + chevron tiles — still exist and are
  still correct for the **admin** dashboard's quick actions; they were
  intentionally not touched or reused here.)
- **Callouts are italic serif notes, not left-border-accent cards**
  (`.record-quote`): a rounded card with a colored left border stripe is
  a specifically named AI-dashboard tell. Where earlier student pages used
  that pattern for a tip or note (e.g. `invoice_generate.html`'s
  installment explanation, and `admin/fee_form.html`'s edit-mode info
  card), it's now a plain italic `.record-quote` paragraph (student) or a
  plain `.card` with no accent (admin) instead.

New student-facing pages should extend this vocabulary — hairline
dividers and typography for hierarchy, not colored boxes — rather than
falling back to card-with-icon defaults.

**Follow-up applied to the admin dashboard too** (the left-border-accent
tell isn't student-specific): `.stat-tile` now uses a plain top rule
(matching `.table-card`'s), the same treatment on every tile — no more
colored left border. Where a figure needs to read as urgent (the
exception queue's unresolved count), that's `.stat-tile-alert`, which
colors the **number** red when the count is nonzero, rather than coloring
a box around it. `.qa-list`/`.qa-item` (icon + chevron quick actions)
were deliberately left alone — that pattern wasn't the complaint, and
it's still the right fit for the admin dashboard.

**Second follow-up: the student dashboard specifically, "too plain"**
(the `.record-panel` identity strip, on its own above a bare list of
actions, read as thin once the rest of the section had been redesigned).
Kept the Academic Ledger vocabulary but gave the dashboard — the page a
student sees most — real weight in three ways:

- **`.dashboard-header` replaces `.record-panel` on this page only**: a
  full-width flat espresso band (no gradient, no rounded avatar) carrying
  both the welcome heading + reg number/department/faculty/level tag line
  on the left, and live Total Owed / Total Paid / Balance figures on the
  right — so the header now states the student's actual standing instead
  of only their identity. Every other student page keeps `.record-panel`
  as-is; this substitution is specific to the dashboard.
- **A two-column layout** (`Bootstrap` `.row`/`.col-lg-8`/`.col-lg-4`)
  uses the full page width instead of a narrow single column: Account
  Actions (unchanged `.record-actions` markup) on the left, a new
  `.balance-breakdown` panel on the right.
- **`.balance-breakdown`** is a per-fee-category ledger list (category
  name + session, right-aligned balance colored red if owing / green if
  settled) — live data pulled from the same `_balance_rows()` helper the
  full balance statement uses, not just another menu entry. It links out
  to `/student/balance` for the full statement rather than duplicating it.

No new AI-dashboard tells were introduced: `.dashboard-header` is a flat
fill with no border-radius pretending to be a card, and
`.balance-breakdown-row` uses the same hairline-divider-row idiom as
`.record-action-row`, not icon tiles.

## Public homepage follow-up: "doesn't look like a professional university site" + full responsiveness pass

The first pass at `home.html` (hero band + two `.record-actions` columns +
`.how-steps` ledger) followed the letter of the brief but still read as
thin/generic once seen next to a real university site — mainly because it
had **no footer at all**, which is the single biggest tell that a page
isn't a real institutional site, plus a hero with no framing device and
capability lists floating with no visual anchor. Fixed without
introducing new AI-dashboard tells:

- **`.home-hero-rule`**: a single 2px gold hairline under the crest — a
  letterhead framing cue, used exactly once, not repeated as a border
  treatment.
- **`.home-panel`**: the "For Students"/"For Administrators" columns are
  now bordered panels with the same top-rule idiom as `.table-card` and
  `.stat-tile` elsewhere in the app (plain top rule, not a shadowed card),
  each with a one-line italic intro above its `.record-actions` list —
  reusing an existing vocabulary rather than inventing a new card style.
- **`.site-footer`**: a real full-bleed footer (`{% block footer %}` in
  `base.html`, empty everywhere except `home.html`) — espresso-dark to
  match the navbar/record-strip, with brand + Quick Links + a Bursary
  contact note, and a hairline-divided bottom bar reusing the existing
  `&copy; {{ current_year }} SUMAS — Eze Ezekiel (SUMAS/2022/0697)` line
  from `login.html`/`error.html` rather than inventing new footer copy.

Responsiveness was tightened at the same time, since students reach the
portal from phones and tablets at least as often as laptops:

- `.home-hero`'s padding and title size are now `clamp()`-based (fluid
  between phone and desktop) instead of jumping once at a single
  breakpoint, so it scales smoothly across the whole phone → tablet →
  desktop range rather than just at 768px.
- The student top strip (`.record-strip`) now shows a short `SUMAS`
  wordmark (`.wordmark-short`) below the `sm` breakpoint instead of
  dropping the institution name entirely, so brand identity survives on
  small phones — previously only the crest icon remained.
- `.site-footer-grid` collapses from three columns to one below 768px.

No fixed-pixel-width elements were found elsewhere in `style.css` that
would force horizontal scrolling on a phone (the admin sidebar already
collapses to a horizontal scroller below 992px, tables already scroll
inside `.table-card`) — the homepage was the actual gap.

## Public homepage follow-up 2: giving it the depth of a real institutional/bank homepage

Researched how real university portals and bank sites earn trust on a
first visit (data-driven messaging placed near the hero rather than
buried in the footer, an FAQ that answers real operational questions, a
plain-language note on how records are kept private) and added three
sections to `home.html`, all built from vocabulary the brief already
established rather than new card/icon patterns:

- **`.home-facts`**: a three-up row directly under the hero, reusing
  `.stat-tile` (the admin dashboard's plain-top-rule tile) as-is and
  `.how-step-title`/`.how-step-desc` for the text — short, honest facts
  about how the system behaves ("One Reference, Every Fee", "Automatic
  Matching", "One Record, Every Session"), not fabricated usage numbers.
  This project's payment gateway is a clearly-labelled simulator
  (`PROJECT_BRIEF.md`), so trust copy anywhere on the site must stay
  honest about what's real — no invented security/compliance badges.
- **A `.record-quote` trust note** under "How It Works", stating plainly
  that every invoice/payment/receipt is scoped to the signed-in student's
  own account and that only the Bursary resolves an exception — a real
  fact from the system's ownership-scoping (`PROJECT_BRIEF.md`), reusing
  the existing italic-serif callout style rather than a new badge/icon
  trust strip.
- **`.home-faq`**: a hairline-divided list matching `.how-steps`'
  bordered-ledger idiom, each question a Bootstrap `collapse` toggle
  (plain button, chevron rotates 180° on open — a standard user-triggered
  150ms transition, not automatic/decorative motion) rather than
  shadowed accordion cards. The five questions answer real behavior from
  `PROJECT_BRIEF.md` (installment payments, the payment-exception queue,
  the duplicate-invoice guard, receipt timing, who to contact) instead of
  generic placeholder FAQ copy.

The footer's Quick Links gained an `#faq` anchor to match. No new color,
radius, or shadow was introduced — everything above composes existing
`style.css` tokens and idioms.

## Public homepage follow-up 3: a real campus photograph in the hero, and a closing statement band

A generic Bootstrap "university theme" template (navy blue, a full-bleed
photo hero with text over a gradient, icon-tile feature row, a photo +
dark-panel "Apply for Admission" split section) was offered as a visual
reference. Its color language and icon tiles are exactly what this brief's
avoid-list rules out, and the project's espresso/gold "Academic Ledger"
identity was deliberately kept — but two of its *structural* ideas were
worth adopting, reinterpreted in the existing vocabulary rather than
copied:

- **A real photograph in the hero**, not a stock/generic image — an aerial
  shot of the College of Medicine building on the actual SUMAS campus
  (Igbo Eno, Enugu State), supplied by the project owner and confirmed to
  be SUMAS's own (other candidate photos carried third-party watermarks —
  `theeasternupdates.com` / `myschoolgist.com` — and were excluded rather
  than reproduced without permission). The hero's letterhead masthead
  (crest/rule/eyebrow) stays centered above a new `.home-hero-grid`:
  headline/copy/CTAs on the left, the photograph on the right in a thin
  gold `.home-hero-photo-frame` with an italic serif caption underneath —
  a captioned figure in a printed document, not a full-bleed image with
  text overlaid on a dark gradient (the specific pattern being avoided).
  Collapses to a single centered column below `992px`.
- **A closing CTA band**, replacing the previous small centered
  `.home-cta` prompt: the same flat-espresso-fill idiom used everywhere
  else (`.dashboard-header`, the hero, the footer) broken out to full
  viewport width immediately before `.site-footer`, so the page ends on
  one deliberate statement ("Settle Your Fees Without a Trip to the
  Bursary" + the Log In button) instead of a boxed afterthought. No photo
  repeated here — there is only the one real photograph, and reusing it a
  second time in a different crop read as padding rather than substance,
  so this section stays typographic.

No fabricated contact details (phone/email) were added despite the
reference's top utility bar — no real Bursary phone/email exists anywhere
else in this project's copy (every other page says "contact the SUMAS
Bursary office" without a specific number), and inventing one here would
break the no-placeholder-content rule this brief itself sets.

## Student account area: bank-statement hierarchy for Total Owed/Paid/Balance

Requested explicitly: make the student "account section" — the dashboard's
balance summary and the Outstanding Balance page — "look proper, like
those Bank UI[s]." Also asked directly whether Total Owed / Total Paid /
Balance are even needed there, or whether there's an alternative.

They're kept — a fees system's core job is telling a student what they
owe, so removing that entirely isn't the right answer — but the
*presentation* changes to match how a real bank or credit-card statement
actually weighs these three numbers: they are not equally important. The
Balance is the one figure a student needs to act on; Billed and Paid are
supporting context that explains *how* the balance got there. The old
`.dashboard-header-stats` gave all three equal visual weight (three
same-size tiles in a row) — a spreadsheet instinct, not a statement one.

- **`.balance-hero-*`** (new, in both `.dashboard-header` and the new
  `.statement-summary` on `student/balance.html`): a single large serif
  figure for the Balance (labelled "Balance Due" while positive, "Balance"
  once settled), colored with two new tokens —
  `--status-confirmed-on-dark` / `--status-rejected-on-dark` — lighter
  tints of the existing status green/red, needed because the plain
  `--status-confirmed`/`--status-rejected` values are tuned for dark text
  on a light background and lose contrast on the espresso-dark fill here.
  Billed and Paid sit underneath as two small right-aligned figures
  separated by a hairline divider, the way a bank app tucks "Money In /
  Money Out" beneath the headline "Available Balance" — not removed, just
  demoted to supporting detail.
- **`student/balance.html`** gained a `.statement-summary` — the same
  `.balance-hero-*` figures, centered in their own flat espresso band at
  the top of the page (reusing the component rather than inventing a
  second figure style) — above the existing per-category ledger table,
  which stays as the itemized detail a statement always has beneath its
  headline total. The table's own total row was left in place beneath the
  ledger; a real statement shows the headline figure both at the top and
  reconciled again at the bottom of the itemized detail, not just once.
- No new "AI dashboard" tells: `.balance-hero-value` is plain flat text at
  large size, not a donut/gauge/progress-ring (a specifically common
  "bank UI, AI-generated" default this brief's avoid-list would also
  reject if it were more explicit about it) — the "bank" feel comes from
  typographic hierarchy and restraint, the same vocabulary already used
  everywhere else in this app, not from a new chart widget.

## Invoice-generation form: Level and Academic Session became real, independent selects

Previously, the Level and Session selects on `student/invoices/generate`
were *derived* from whatever fee categories happened to exist — so the
Session list only ever showed sessions the admin had already configured
fees for, and Level only showed values up to whatever the widest existing
fee category happened to use. Requested: Session should offer a real
run of academic years (2022/2023 through 2027/2028) regardless of what's
been configured yet, and Level should go past 400 for departments whose
course genuinely runs longer (Nursing Science to 500 Level was the
concrete example given).

Both are now independent of fee-category data entirely:

- **Session** is `student.py`'s fixed `SESSIONS` tuple, always shown in
  full. A session with nothing set up yet is not an error state — the
  Fee Category select simply has nothing to offer for that combination
  (see below), same as a real portal before the Bursary has opened fees
  for an upcoming session.
- **Level** is generated at request time as `100` up to that student's own
  department's maximum, via `_max_level_for()` — which reads the new
  `department_program` table (department → max_level) and falls back to
  400 (`DEFAULT_MAX_LEVEL`) for any department with no row there. Admin
  manages this from a new **Programmes** page (`/admin/programs`,
  `admin/programs_list.html` / `program_form.html`, same
  list-plus-add/edit-form idiom as Fee Categories) — deliberately only
  needs an entry for a department whose course is NOT the common 400L
  case, so seeding stayed to one row (Nursing Science → 500) rather than
  enumerating every department.
- Because Level/Session no longer guarantee a matching Fee Category
  exists, `invoice_generate.html`'s filtering script now handles the
  "nothing set up for this combination" case explicitly — the Fee
  Category select and Generate button both disable, and a plain
  `<p class="muted-note">` explains why, rather than leaving a select
  with every `<option>` hidden and a stale, confusing blank value
  (the previous script's actual behavior whenever this could happen).
