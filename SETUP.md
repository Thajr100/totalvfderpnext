# Total VFD — Setup & go live

Everything you need to turn on Total VFD in ERPNext. The same steps appear inside **Total VFD Settings** as a checklist with buttons.

---

## Who does what

| Person | Does |
|--------|------|
| **IT / integrator** (once) | Install the app on the server, give you two web addresses/passwords from step A1 |
| **You (manager)** | Steps A2–A6 in ERPNext (about 10 minutes per company) |
| **Cashier / accounts** | Tick **Fiscalise** on invoices after setup |

---

## A. Setup in ERPNext (step by step)

Open **Total VFD** on the home screen → **Getting Started** (Total VFD Settings).

If you have more than one company, pick it at the top of the guide (**Setup for company**) and repeat A2–A5 for each company.

### A1 — Link to your vendor (IT can do this)

1. Paste **License server address** (from your integrator).
2. Paste **License password** (from your integrator).
3. Click **Save**.
4. Click **Test link to vendor** — you should see “Connected successfully.”

*Don’t have these? Click **Copy note for IT** on that screen and send it to support.*

### A2 — Ask your vendor for activation

1. Click **Copy email for vendor**.
2. Send the text to your Total VFD / software vendor (email or WhatsApp).
3. Wait for their reply with two items: a **short code** and a **license key**.

### A3 — Turn on your module license

1. Click **Enter vendor code and key**.
2. Paste the **short code** and **license key** from the email.
3. Click **Activate** — note the “active until” date.

Optional: **Is my license OK?** checks status without posting an invoice.

### A4 — Connect your fiscal device (Total VFD portal)

1. Click **Open company settings** (or go to **Company** → **Total VFD** tab).
2. Fill in from your Total VFD portal:
   - **Portal login token**
   - **Business ID**
   - **Device serial number**
3. Set **Live or test mode** to **test** for now.
4. **Save**.

### A5 — POS only (if you use a till)

1. Open **POS Profile** from the guide (or list).
2. Turn on **Fiscalise POS invoices by default** if you want every till receipt sent automatically.
3. Turn on **Use Total VFD receipt print format** for the QR on receipts.

### A6 — Try one test invoice

1. Click **New Sales Invoice**.
2. Add a line and customer (sandbox/test data is fine).
3. Tick **Fiscalise with Total VFD**.
4. **Submit**.
5. Open the **Fiscal Information** tab — status should be **Success**, with receipt number and QR.
6. Print with **Sales Invoice - Total VFD**.

7. Back on **Total VFD Settings**, click **I finished setup** when done.

---

## B. One-time server install (IT only)

Run from the project folder:

```bash
bash install_total_vfd.sh
```

Enter your bench folder and site name when asked.

Or manually:

```bash
cd /path/to/frappe-bench
bench get-app /path/to/totalvfderpnext/total_vfd
bench --site YOUR-SITE install-app total_vfd
bench --site YOUR-SITE migrate
bench build --app total_vfd
bench restart
bench --site YOUR-SITE enable-scheduler
```

Your integrator must also host the **license server** (PHP app) and give you the address + password for step A1.

---

## C. Go live (production checklist)

Do these **after** a successful test invoice (A6).

| # | Task | Where |
|---|------|--------|
| 1 | Confirm module license is **active** and not near expiry | Total VFD Settings → **Is my license OK?** |
| 2 | Switch **Live or test mode** to **production** | Company → Total VFD |
| 3 | Use real portal token / business ID / serial for live | Company → Total VFD |
| 4 | Submit one **real** low-value invoice with **Fiscalise** ticked | Sales Invoice |
| 5 | Verify TRA receipt number and QR on printout | Print: Sales Invoice - Total VFD |
| 6 | Train staff: tick **Fiscalise** when issuing official receipts | Sales Invoice / POS |
| 7 | Optional: default **Fiscalise** on for sales | Company → Total VFD |
| 8 | Confirm **scheduler** is on (retries failed sends every 5 minutes) | IT: `bench --site SITE enable-scheduler` |
| 9 | POS: test one live ticket if you use a till | POS Invoice |
| 10 | Before license expiry (~30 days warning): get renewal code + key from vendor | Total VFD Settings → renew |

---

## Daily use

- **Sales Invoice** or **POS Invoice**: tick **Fiscalise with Total VFD** before submit (or use company/POS defaults).
- Problems: open **Total VFD Fiscal Log** or **Total VFD Queue** from the Total VFD menu.

---

## Quick help

| Problem | What to do |
|---------|------------|
| Can’t fiscalise | Finish A1–A3 for that **company**; use **Is my license OK?** |
| Test link fails | Check address/password with integrator; no spaces in address |
| Vendor says wrong ID | Copy **email for vendor** again from step A2 |
| Invoice failed | Read **Fiscal Error** on the invoice; fix Company token/serial |
| Duplicate receipt (409) | Usually already fiscalised — check fiscal number on invoice |

---

## Support text for IT (copy/paste)

```
Please install Total VFD on our ERPNext site and provide:
1) License server web address
2) License password for that server
3) Confirmation that the license server is running

Our ERPNext site name: _______________
Company name in ERPNext: _______________
```
