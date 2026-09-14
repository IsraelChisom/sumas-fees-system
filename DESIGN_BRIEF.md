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

  **Superseded — see "The Clinical Ledger rebrand" near the end of this
  file.** Headings are now "Fraunces", body is "Archivo", and a third
  face, "JetBrains Mono", was added for every reference number, amount,
  and code. The color palette below is unchanged and still authoritative.

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

## Statement of Account: bank-statement hierarchy for Total Owed/Paid/Balance

Requested explicitly: make the student "account section" — the dashboard's
balance summary and the Outstanding Balance page — "look proper, like
those Bank UI[s]." Also asked directly whether Total Owed / Total Paid /
Balance are even needed there, or whether there's an alternative.

They're kept — a fees system's core job is telling a student what they
owe, so removing that entirely isn't the right answer — but the
*presentation* changes to match how a real bank or credit-card statement
actually weighs these three numbers on `student/balance.html`: they are
not equally important. The Balance is the one figure a student needs to
act on; Billed and Paid are supporting context that explains *how* the
balance got there.

**The dashboard header itself was tried this way too and then reverted**
— asked for explicitly, back to its original `.dashboard-stat` tiles
(three equal-weight figures side by side). The statement hierarchy stays
on the Balance page, which is where a student goes specifically to read
their account standing in detail; the dashboard is a jumping-off point to
several different actions, and the original three-tile summary is the
right amount of weight for a glance on the way to one of them.

- **`.balance-hero-*`** (on `student/balance.html`'s `.statement-summary`
  only): a single large serif figure for the Balance (labelled "Balance
  Due" while positive, "Balance" once settled), colored with two new
  tokens — `--status-confirmed-on-dark` / `--status-rejected-on-dark` —
  lighter tints of the existing status green/red, needed because the
  plain `--status-confirmed`/`--status-rejected` values are tuned for
  dark text on a light background and lose contrast on the espresso-dark
  fill here. Billed and Paid sit underneath as two small centered figures
  separated by a hairline divider, the way a bank app tucks "Money In /
  Money Out" beneath the headline "Available Balance" — not removed, just
  demoted to supporting detail, and only on the page dedicated to this
  detail.
- **`student/balance.html`** gained a `.statement-summary` — the
  `.balance-hero-*` figures, centered in their own flat espresso band at
  the top of the page — above the existing per-category ledger table,
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

## The Clinical Ledger rebrand

A test run of the `/anthropic-skills:frontend-design` skill was asked for,
explicitly framed as a throwaway exploration and deliberately given no
brand constraints, to see what an unconstrained pass would produce for
this project. It came back as a distinct concept — "Clinical Ledger":
grounded in what SUMAS's fees system actually is (a medical-sciences
university's payment/receipt system), built around Fraunces, Archivo and
JetBrains Mono, a deep clinical green, and a set of motifs literal to
receipts and payment references — a perforated dashed divider standing in
for a torn ticket edge, monospace treatment for every reference number
and amount, small mono pill tags. The reaction was strongly positive, and
it was asked for across the whole application — on the explicit condition
that the brand's actual brown/gold stayed, not the test's green.

That's exactly what changed and what didn't:

- **Unchanged:** every color token in `style.css` — `--espresso`,
  `--gold`, `--ivory`, `--paper`, `--border`, all three `--status-*`
  triads. The "brand color is brown" instruction was taken literally:
  this is a typography and motif rebuild on the existing palette, not a
  recolor. `--accent-soft` (new) is just the existing gold-tinted
  `--bs-primary-bg-subtle` value given a semantic name for the new
  mono-chip components that needed it.
- **Typeface swap:** `--font-heading` (Fraunces) and `--font-body`
  (Archivo) replace Lora/IBM Plex Sans at the token level in
  `app/static/css/style.css`, and `base.html`'s Google Fonts `<link>`
  was updated to match — because nearly every heading and body element
  in this codebase already read its font from those two variables
  rather than a hardcoded family name, this one change retyped the
  entire application in a single edit. A third token, `--font-mono`
  (JetBrains Mono), is new — this system runs on payment references and
  account numbers, so a monospace face earns a real structural role here,
  not decoration.
- **New "Ledger Motifs" component layer** (`style.css`, section 3b):
  - `.data-mono` — the monospace/tabular-nums utility, applied to every
    reference number, registration number, and table amount across the
    app (`invoices_list.html`, `payment_search.html`, `students_list.html`,
    `departmental_report.html`, `unmatched_list.html`, `fees_list.html`,
    `balance.html`, the dashboard's reg-number tag and
    `.balance-breakdown-amount`). A large *display* amount — the print
    documents' "Amount Payable", `.balance-hero-value`,
    `.dashboard-stat-value` — deliberately stays in the Fraunces heading
    face instead: the same distinction the test page drew between its
    large serif `.ticket-amount` and its small mono `.ticket-ref-value`,
    carried through consistently rather than making everything numeric
    monospace indiscriminately.
  - `.ledger-divider` / `.ref-chip` — the perforated dashed rule and
    gold-tinted reference chip. Applied to `invoice_view.html`'s and
    `receipt_view.html`'s print documents: `.print-reference-block` now
    sits on `--accent-soft` with a `.ledger-divider` above it, and
    `.print-reference` itself is mono — the same "torn ticket stub"
    reading the test page's hero mock invoice had, now on the real
    document.
  - `.mono-tag` / the rebuilt `.how-steps` — the homepage's "How It
    Works" is a genuine three-step sequence, so a `Step 0X` tag is
    honest here (unlike a numbered badge on something that isn't
    actually a sequence, still avoided everywhere else). Rebuilt from a
    vertical list with a large gold numeral into a three-column strip
    with dashed dividers between steps and a small mono `Step 0X` chip
    per step — the test page's ticket-tape flow, reapplied.
- **Real assets, not the test page's placeholder mark:** the test page
  used an abstract "SU" ticket-notch mark in its top bar since it had no
  asset access at the time. The real app already used the actual SUMAS
  crest and the real campus photograph (`sumas-crest.png`,
  `sumas-campus.jpg` — see the earlier homepage follow-ups above) on
  every page that carries a brand mark or hero image; nothing needed to
  change there, so none of the rebuild introduced a new placeholder mark.
- **Deliberately not touched:** the ReportLab-generated PDFs
  (`app/pdf.py`) still use ReportLab's built-in fonts, not Fraunces/
  Archivo/JetBrains Mono — those aren't web fonts and would need actual
  TTF files registered with `reportlab.pdfbase.ttfonts` to match. The
  browser-printed HTML versions of every invoice/receipt/report (the
  default view) carry the full rebrand; only the "Download PDF" button's
  output doesn't yet. A known follow-up, not an oversight.

### Correction: the first pass only reskinned, it didn't rebuild

The work above (typography, `.data-mono`, the perforated divider on
print documents, the ticket-tape "How It Works") was real, but it left
every page's actual *structure* untouched — the login card, the
dashboard, the tables, and critically `home.html` kept their original
layouts. The reference page's real identity is in its composition, not
just its color and font: a sticky top bar with in-page nav, a
plain-paper hero next to a tilted mock-invoice card (not a filled dark
band with a photo), a full-bleed dark stat stripe, two role cards, an
actual fee-structure table with pill/session chips, a trust grid, a
closing band. None of that existed anywhere in the app after the first
pass — pointed out directly, correctly, as "you were giving me the old
design."

`home.html` was rebuilt component-for-component to match:

- **`base.html` gained a `{% block navbar %}`** around the shared
  student-section top strip, so `home.html` can replace it outright with
  its own `.site-topbar` (sticky, blurred backdrop, crest + wordmark,
  in-page nav to How It Works/For You/Fee Structure, a real Log In
  button) — every other page keeps the original `.record-strip` as
  before; only the homepage overrides it.
- **The hero dropped the filled espresso band and the campus photo
  entirely**, replacing them with the reference page's actual
  composition: plain paper background, headline with an italic gold
  accent word, and — where the photo was — a tilted `.home-ticket` mock
  invoice card with the notched-edge, dashed-divider, mono-reference-chip
  treatment `.ref-chip`/`.ledger-divider` already established for the
  real invoice/receipt documents (section 3b). The campus photograph
  (`sumas-campus.jpg`) isn't used anywhere on the site now — the
  reference page's hero never had a photo slot, and forcing one back in
  would have been a different design again, not this one. It's still in
  `app/static/images/` if a future page wants it.
- **New `.stat-stripe`**: a genuine full-bleed dark band (same
  `calc(50% - 50vw)` breakout as `.home-closing`) with the three
  "Automatic / Recomputed / Scoped" facts, sitting directly under the
  hero exactly where the reference page puts it — previously these three
  facts existed as plain `.stat-tile`s inline in the page flow, not a
  distinct full-bleed section.
- **New `.roles-grid` / `.role-card`**: two bordered, `--radius-lg`
  rounded cards ("Student" / "Administrator"), each a mono-numbered list
  — replacing `.home-panel`, which used the app's internal
  `.record-actions` hairline-list idiom. Deliberately different from how
  the *logged-in* dashboard still presents actions to a student (that
  one is unchanged) — an anonymous visitor reading what the system does
  is a different moment than a signed-in user acting on their own
  record, and the reference page treats it that way.
- **New `.fee-table-shell` section — content that didn't exist on the
  homepage at all before**: a real table (Category/Level/Scope/Amount)
  using `.mono-tag` for scope pills and `.data-mono` for amounts, plus a
  `.session-chip` row for the 2022/2023–2027/2028 range, with the
  current session highlighted. On mobile the table scrolls inside its
  own `.fee-table-shell` container — the first cut of this used
  `table { width: 100% }` even in the mobile rule, which squeezed all
  four columns into the phone width instead of scrolling; fixed to
  `width: auto; min-width: 560px` so the table keeps its natural size
  and the container's `overflow-x: auto` actually has something to
  scroll.
- **New `.trust-grid`**: three `--espresso` top-rule cards (Nothing
  partially confirms / Mismatches are held not guessed / Ownership is
  enforced), replacing the single italic `.record-quote` paragraph that
  used to carry this content.
- **`.home-closing`** (renamed from `.home-cta`): now has two CTAs side
  by side (Log In to Continue + a ghost-styled "Check the fee
  structure"), matching the reference page's closing band instead of one
  button.
- **The FAQ section and the richer institutional footer (crest, Quick
  Links, Bursary contact, copyright bar) were kept** even though the
  reference page's own footer is a single line — deliberately: earlier
  follow-ups on this same page (see above) established that a bare
  footer is one of the biggest tells a page isn't a real institutional
  site, and the reference page was a marketing mockup with no such
  requirement to satisfy. FAQ content is additive, not a deviation from
  the reference — nothing in it was removed to make room for the rebuild.
