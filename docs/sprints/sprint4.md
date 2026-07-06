Sprint 4 Objective
A user can create an account, save their Digital Career Twin, log out, log back in, and retrieve the same Twin and Career Mirror.

Sprint 4 Auth model.
Enter email
   ↓
Generate one-time code
   ↓
Send code by email
   ↓
User enters code
   ↓
Create/retrieve account
   ↓
Attach Session Twin to Persistent Twin

Codes expire after 10 minutes.
Codes are single-use.
Store a hash of the code, not the code itself.
Rate-limit requests by email and IP.
Normalize email to lowercase.
Promote anonymous Session Twin to Persistent Twin after login.

Acceptance Criteria
Sprint 4 Goal

A Session Twin can be promoted to a Persistent Twin through lightweight account creation.

Acceptance Criteria

✓ A first-time visitor can create and interact with a Session Twin without creating an account.

✓ If the user attempts to leave before creating an account, the system informs them that the Session Twin will be permanently deleted.

✓ The user can create an account using an email address and a one-time verification code.

✓ Upon successful account creation, the existing Session Twin is promoted to the user's Persistent Twin.

✓ The user can close the browser, return later, authenticate, and retrieve the same Twin.

✓ Subsequent updates modify the Persistent Twin rather than creating a new one.

✓ A user can permanently delete their account and Persistent Twin.
