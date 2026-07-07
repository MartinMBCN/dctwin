Sprint 4 Objective
A user can create an account, save their Digital Career Twin, log out, log back in, and retrieve the same Twin and Career Mirror. A Session Twin can be promoted to a Persistent Twin through lightweight account creation. The Persistent Twin becomes the long-lived canonical representation of the user's professional identity across multiple sessions and devices.

An account consists solely of a verified email address associated with a Persistent Twin. No username or password is required. If a valid email address is detected within the uploaded source material, it may be offered as the default account email. The user must confirm or replace the email address before account creation.

Requirement: Don't let the user accidentally lose their Session Twin without being informed and offered account creation.
Implementation: Use the best mechanism available for the type of navigation (custom modal for in-app navigation, browser confirmation where supported for tab close/refresh).

Explicit Session Control
As a user, I can choose how long this device remains logged in, up to a maximum of one month, and I can see when my session will expire.

Sprint 4 Auth model.
Enter email
   ↓
Generate one-time code
   ↓
Send code by email
   ↓
User enters code
   ↓
Does account exist?
      /          \
    Yes           No
     |             |
Retrieve       Create
account        account
      \          /
       \        /
    Attach/retrieve Twin

Codes expire after 60 minutes.
Codes are single-use.
Users can request a new code.
Only the most recent code is accepted.
Store a hash of the code, not the code itself.
Rate-limit requests by email and IP.
Normalize email to lowercase.
If a Session Twin exists at login/account creation, promote it to the user's Persistent Twin. If the user already has a Persistent Twin, reconcile or reject the Session Twin rather than silently overwriting it.

Session duration options
Log me out:
- At midnight
- In 7 days
- In 1 month

The user can also log out manually at any time.

Architecturally, this means account creation/login should create a session with an explicit expires_at value:

User
Session
  user_id
  created_at
  expires_at
  revoked_at
  last_seen_at

Acceptance Criteria

✓ A first-time visitor can create and interact with a Session Twin without creating an account.

If the user closes the browser tab/window or navigates away from the application before creating an account, they are warned that their Session Twin will be permanently deleted and invited to create an account to preserve it.

✓ A user cannot retrieve or modify another user's Persistent Twin.

✓ The user can create an account using an email address and a one-time verification code.

✓ Upon successful account creation, the existing Session Twin is promoted to the user's Persistent Twin.

✓ The user can close the browser, return later, authenticate, and retrieve the same Twin.

✓ Subsequent updates modify the Persistent Twin rather than creating a new one.
User can choose session duration at login/account creation.

Available durations are midnight, 7 days, or 1 month.

Session has a stored expires_at timestamp.

Expired sessions require re-verification by email code.

User can manually log out before expiry.

UI displays current session expiry.

One-time login codes are single-use and short-lived.

✓ A user can permanently delete their account and Persistent Twin.
