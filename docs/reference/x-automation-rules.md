# X Automation Rules (reference)

**Source:** X Automation rules, updated October 2025. For developers.  
**You are responsible** for actions taken with your account or by apps associated with it.

---

## I. Ground rules

**Do:** Build helpful auto-broadcasts; run campaigns that **auto-reply to users who engage with your content**; auto-respond in DMs; try things that help people and comply with rules; keep good UX.

**Don’t:** Violate policies; abuse API or circumvent rate limits; use non-API automation (e.g. scripting the website); spam or send unsolicited messages.

---

## II. Activity-specific rules (what matters for Gerald)

### B.2 Automated mentions and replies

- **Don’t:** Automate replies/mentions to reach many users on an **unsolicited** basis (e.g. keyword-search-only auto-replies are not permitted).
- **Do:** You may send automated replies or mentions **so long as**:
  1. **In advance** of sending the reply, the recipient has **requested or clearly indicated intent** to be contacted by you (opted in), for example by **replying to a post from your account**, or **by sending you a Direct Message**.
  2. You provide a **clear, easy opt-out** and **promptly honor** opt-out requests.
  3. You send **only one automated reply or mention per user interaction**.
  4. The automated reply **is a reply to the user’s original post** (when your campaign is based on users replying to your post).

*Note:* A user **following** you is **not** by itself sufficient intent to receive an automated response.

### C. Automated Direct Messages

- **Don’t:** Send **unsolicited** DMs in a bulk or automated manner.
- **Do:** You may send automated DMs **so long as**:
  1. **In advance**, the recipient has **requested or clearly indicated intent** to be contacted by you via DM (e.g. by **sending you a Direct Message**).
  2. You provide a clear opt-out and honor it promptly.

*Note:* Being able to receive a DM (e.g. they follow you, or are in a pre-existing DM conversation) does **not** necessarily mean they have requested or expect **automated** DMs.

### D. After a user-initiated interaction ends

- Don’t send additional follow-up DMs or mention users in a post **unless you get permission** from the user.

---

## How this lines up with Gerald

| Rule | Our flow | Note |
|------|----------|------|
| Replies only when user opted in (e.g. replied to our post, or sent us a DM) | We DM first, then reply to their tweet | Intent for the **reply** is strict: they should have engaged us (reply to our post or DM’d us). Our “we DM’d them first” doesn’t by itself satisfy “they indicated intent to be contacted.” |
| One automated reply per user interaction | We send one follow-up reply per contact per run | We already do one reply per DM send. |
| Reply to the user’s original post | We reply to their **latest** tweet | We reply to a post of theirs; if the “interaction” is “they replied to our post,” the rule says reply to *that* post. We use “latest tweet” as a proxy when we don’t have a single “their reply” post. |
| DMs only when they indicated intent (e.g. sent us a DM) | We do outbound DM to discovered prospects | Strict reading: unsolicited/bulk DM is not allowed. Many outbound sales tools still run; risk is account enforcement. |

**Takeaway:** The API 403 (“reply not allowed … have not been mentioned or otherwise engaged by the author”) is X’s enforcement of the same idea: **replies are allowed when they’ve opted in** (e.g. replied to our post or DM’d us). When we get 403, we skip that contact and move on (waterfall). The one success (e.g. Timo) likely fit the “they engaged us” case in X’s view.

Store this file as the **bible**; link to it from follow-up and outreach docs. When in doubt, re-read the official rules (help.x.com / developer portal).
