# BUILD 2026 participant credits

## Dashboard experience

`/dashboard/build-2026` is the participant-facing page for AI Forenza's BUILD 2026 credit allocation. The sidebar, API-key labels, and onboarding links use **BUILD 2026**. `/dashboard/hackathon` redirects to the new route.

The public landing page promotes the event at `/#build-2026`, with a hero announcement, desktop/mobile navigation links, and a branded “Join the build” section. It links to Hackyard's event information and the authenticated claim page, describes the $100 per-selected-project allocation, and shows the event dates and venue. Login/signup switching preserves the claim-page destination so a new participant returns to BUILD 2026 after authentication. The invitation accurately notes that event applications have closed.

The page includes the event hero, live credit amount, organizer-issued Team ID claim, one-time shared-key display, promotional balances, OpenCode setup, build ideas, event details, and participant questions. Claims and balances use the existing authenticated `/v1/hackathon/status` and `/v1/hackathon/claim` APIs.

## Source review

Reviewed the rendered site, computed styles, artwork, and these pages on 20 October 2026:

- [Event overview](https://hackyard.org/build2026)
- [Participant guide](https://hackyard.org/build2026/guide)
- [Prizes and credits](https://hackyard.org/build2026/prizes)

Relevant event facts:

- Physical build: **24–25 October 2026**, **IIT Guwahati**, **24 hours**.
- Participation: solo builders or teams of **2–4**.
- Applications closed **10 October**; selected projects are announced by Hackyard.
- The published LLM credit allocation is **$100 per selected project**, shared by teammates rather than granted per participant. The dashboard presents the AI Forenza allocation for this program.
- Hackyard manages selection, participant packages, arrival instructions, prizes, and other partner benefits. The dashboard links to those official details.

The amount displayed for open claims comes from `campaign.grant_amount_cents`. With no active campaign, the page explains that claims are waiting to open and displays the program's advertised $100 allocation. All grant balances come from the API; the design does not generate or simulate credits.

## Design and assets

The event-scoped CSS module follows the source palette: surface `#090c13`, raised surface `#111927`, lines `#2c3647`, electric blue `#2b5ce4`, action blue `#285be0`, ink `#e7f0fb`, muted text `#aebacc`, and links `#9cbdff`. It uses the source's Tektur display lettering, Inter Tight body text, IBM Plex Mono labels, outlined year, grid treatment, square actions, pale-blue information panel, and illustrated cards. Fonts are self-hosted through Next.js's font loader.

Assets in `apps/web/public/build2026/` are adapted from the user-supplied Hackyard event website:

- `hackyard-icon.png`: `/build2026-assets/hackyard-icon.png`.
- `builder.png`: a static export of the overview's inline builder illustration. The source cash-prize labels were removed so the dashboard can render its actual AI credit amount as HTML.
- `idea-agent.svg`, `idea-tool.svg`: the overview's small pixel-style build-idea illustrations, self-contained with the event palette.

The assets are served locally. Event typography and colors are scoped to the BUILD 2026 page, with a matching sidebar active state.

## Organizer handoff

Use the existing [organizer setup](hackathon-credits.md#deployment-and-organizer-setup) to enable the intended campaign and import eligible project Team IDs. The site's application/invite code is not automatically an AI Forenza claim code; it must be included in the organizer's eligible list. One organizer-issued code maps to one project's allocation, including solo projects.

When no campaign is active, the page shows a waiting state. A successfully claimed key is shown once, remains visible while opening setup documentation in a new tab, and is cleared on account changes or sign-out. Shared-key usage consumes only the promotional wallet at reference pricing.
