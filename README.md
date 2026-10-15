# LSVDealer.com - Low Speed Vehicle Dealer Website

A static website for listing low speed vehicle dealers across the United States. This project is designed to be hosted on GitHub Pages.

## Project Structure

- `index.html` - Main homepage listing all dealers
- `dealer-*.html` - Individual dealer pages (30 total)
- `css/styles.css` - Dark theme styling for the website
- `dealers.py` - Python script to generate HTML files from dealer data

## Features

- Dark theme design
- Responsive layout for mobile and desktop
- 30 dealer pages with detailed information
- Dealer grid on homepage with links to individual pages
- Information about low speed vehicles and their benefits

## Setup

1. Clone this repository
2. Open `index.html` in your browser to view the site locally
3. Deploy to GitHub Pages for public access

## Customization

To modify dealer information or add new dealers:

1. Edit the dealer data in `dealers.py`
2. Run the script to regenerate HTML files: `python dealers.py`
3. Commit and push changes to GitHub

## License

© 2025 LSVDealer.com - All Rights Reserved

## Lead forms (TIGON IOT → Webhook Flows)

- `js/tigon-lead.js` sends every `form.tigon-lead-form` to the site's TIGON webhook (form name "Contact form") and adds a
  "Get a Quote" pop-up form, a Call Now / Financing bar, and (on dealer pages) a Call Now / Get a Quote / Apply for
  Financing row. It is loaded on every page, and `dealers.py` writes the same `<script>` tag when it regenerates pages.
- Any element with `data-tigon-open` opens the pop-up form. Add `data-brand`, `data-model`, `data-vin` and `data-sku` to the
  button (or an element with `data-tigon-cart`) to pre-fill the cart the visitor asked about.
- Lead form styles live at the end of `css/styles.css` (`.tgn-*` classes).
- No signing secret is used. The site is static, so leads are posted straight from the browser.
